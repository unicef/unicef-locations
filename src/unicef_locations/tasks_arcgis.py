import json

import celery
# from arcgis.features import FeatureCollection, Feature, FeatureSet
from arcgis.gis import GIS
from arcgis.features import FeatureLayer
from celery.utils.log import get_task_logger
from django.contrib.gis.geos import MultiPolygon, Point, Polygon
# from django.db import IntegrityError
from django.db import transaction
from django.utils.encoding import force_text

from .models import ArcgisDBTable, Location
from .task_utils import (
    create_location,
    duplicate_pcodes_exist,
    filter_remapped_locations,
    remap_location,
    validate_remap_table
)

logger = get_task_logger(__name__)

@celery.current_app.task # noqa: ignore=C901
def import_arcgis_locations(arcgis_table_pk):
    results = []
    sites_created = sites_updated = sites_remapped = sites_not_added = 0

    try:
        arcgis_table = ArcgisDBTable.objects.get(pk=arcgis_table_pk)
    except ArcgisDBTable.DoesNotExist:
        logger.exception('Cannot retrieve ArcgisDBTable with pk: %s', arcgis_table_pk)
        return results

    database_pcodes = []
    for row in Location.objects.all_locations().filter(gateway=arcgis_table.location_type).values('p_code'):
        database_pcodes.append(row['p_code'])

    # https://esri.github.io/arcgis-python-api/apidoc/html/arcgis.features.toc.html#
    try:
        # if the layer/table is public it does not have to receive auth obj
        # feature_layer = FeatureLayer(arcgis_table.service_url)
        gis_auth = GIS('https://csabadenes.maps.arcgis.com', 'csabadenes', 'Parola123!')
        feature_layer = FeatureLayer(arcgis_table.service_url, gis=gis_auth)

        featurecollection = json.loads(feature_layer.query(out_sr=4326).to_geojson)
        rows = featurecollection['features']
    except RuntimeError:  # pragma: no-cover
        logger.exception("Cannot fetch location data from Arcgis")
        return results

    arcgis_pcodes = [str(row['properties'][arcgis_table.pcode_col].strip()) for row in rows]

    remap_old_pcodes = []
    if arcgis_table.remap_table_service_url:
        try:
            remap_table_pcode_pairs = []
            # remap_feature_layer = FeatureLayer(arcgis_table.remap_table_service_url, gis=gis_auth)
            # if the layer/table is public it does not have to receive auth obj
            remap_feature_layer = FeatureLayer(arcgis_table.remap_table_service_url)
            remap_rows = remap_feature_layer.query()

            for row in remap_rows:
                remap_table_pcode_pairs.append({
                    "old_pcode": row.get_value("old_pcode"),
                    "new_pcode": row.get_value("new_pcode"),
                })

            # validate remap table contents
            remap_table_valid, remapped_old_pcodes, remapped_new_pcodes = \
                validate_remap_table(remap_table_pcode_pairs, database_pcodes, arcgis_pcodes)

            if not remap_table_valid:
                return results
        except RuntimeError:  # pragma: no-cover
            logger.exception("Cannot fetch location remap data from Arcgis")
            return results

    # check for  duplicate pcodes in both local and new data
    if duplicate_pcodes_exist(database_pcodes, arcgis_pcodes, remap_old_pcodes):
        return results

    with transaction.atomic():
        # we should write lock the locations table until the location tree is rebuilt
        Location.objects.all_locations().select_for_update().only('id')

        with Location.objects.disable_mptt_updates():
            # REMAP locations
            if arcgis_table.remap_table_service_url and len(remap_table_pcode_pairs) > 0:
                # remapped_pcode_pairs ex.: {'old_pcode': 'ET0721', 'new_pcode': 'ET0714'}
                remap_table_pcode_pairs = list(filter(
                    filter_remapped_locations,
                    remap_table_pcode_pairs
                ))

                aggregated_remapped_pcode_pairs = {}
                for row in rows:
                    arcgis_pcode = str(row['properties'][arcgis_table.pcode_col]).strip()
                    for remap_row in remap_table_pcode_pairs:
                        # create the location or update the existing based on type and code
                        if arcgis_pcode == remap_row['new_pcode']:
                            if arcgis_pcode not in aggregated_remapped_pcode_pairs:
                                aggregated_remapped_pcode_pairs[arcgis_pcode] = []
                            aggregated_remapped_pcode_pairs[arcgis_pcode].append(remap_row['old_pcode'])

                # aggregated_remapped_pcode_pairs - {'new_pcode': ['old_pcode_1', old_pcode_2, ...], ...}
                for remapped_new_pcode, remapped_old_pcodes in aggregated_remapped_pcode_pairs.items():
                    remap_location(
                        arcgis_table,
                        remapped_new_pcode,
                        remapped_old_pcodes
                    )

            for row in rows:
                arcgis_pcode = str(row['properties'][arcgis_table.pcode_col]).strip()
                site_name = row['properties'][arcgis_table.name_col]

                if not site_name or site_name.isspace():
                    logger.warning("No name for location with PCode: {}".format(arcgis_pcode))
                    sites_not_added += 1
                    continue

                parent = None
                parent_code = None
                parent_instance = None

                if arcgis_table.parent_code_col and arcgis_table.parent:
                    msg = None
                    parent = arcgis_table.parent.__class__
                    parent_code = row['properties'][arcgis_table.parent_code_col]
                    try:
                        parent_instance = Location.objects.get(p_code=parent_code)
                    except Location.MultipleObjectsReturned:
                        msg = "Multiple locations found for parent code: {}".format(
                            parent_code
                        )
                    except Location.DoesNotExist:
                        msg = "No locations found for parent code: {}".format(
                            parent_code
                        )
                    except Exception as exp:
                        msg = force_text(exp)

                    if msg is not None:
                        logger.warning(msg)
                        sites_not_added += 1
                        continue

                if row['geometry']['type'] == 'Polygon':
                    geom = MultiPolygon([Polygon(coord) for coord in row['geometry']['coordinates']])
                elif row['geometry']['type'] == 'Point':
                    # TODO test with real data
                    geom = Point(row['geometry']['coordinates'])
                else:
                    logger.warning("Invalid Arcgis location type for: {}".format(arcgis_pcode))
                    sites_not_added += 1
                    continue

                # create the location or update the existing based on type and code
                succ, sites_not_added, sites_created, sites_updated, sites_remapped, \
                    partial_results = create_location(
                        arcgis_pcode, arcgis_table.location_type,
                        parent, parent_instance,
                        site_name, geom.json,
                        sites_not_added, sites_created, sites_updated
                    )

                results += partial_results

            orphaned_old_pcodes = set(database_pcodes) - (set(arcgis_pcodes) | set(remap_old_pcodes))
            if orphaned_old_pcodes:  # pragma: no-cover
                logger.warning("Archiving unused pcodes: {}".format(','.join(orphaned_old_pcodes)))
                Location.objects.filter(p_code__in=list(orphaned_old_pcodes)).update(is_active=False)

        Location.objects.rebuild()

    logger.warning("Table name {}: {} sites created, {} sites updated, {} sites remapped, {} sites skipped".format(
        arcgis_table.service_name, sites_created, sites_updated, sites_remapped, sites_not_added))

    return results
