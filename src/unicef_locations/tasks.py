import time

import celery
from carto.exceptions import CartoException
from carto.sql import SQLClient
from celery.utils.log import get_task_logger
from django.db import IntegrityError, transaction
from django.utils.encoding import force_text

from .auth import LocationsCartoNoAuthClient
from .models import CartoDBTable, Location

logger = get_task_logger(__name__)


@celery.current_app.task # noqa: ignore=C901
def update_sites_from_cartodb(carto_table_pk):

    try:
        carto_table = CartoDBTable.objects.get(pk=carto_table_pk)
    except CartoDBTable.DoesNotExist:
        logger.exception('Cannot retrieve CartoDBTable with pk: %s', carto_table_pk)
        return None

    auth_client = LocationsCartoNoAuthClient(base_url="https://{}.carto.com/".format(carto_table.domain))
    sql_client = SQLClient(auth_client)
    sites_created = sites_updated = sites_remapped = sites_not_added = 0

    try:
        # query cartodb for the locations with geometries
        carto_succesfully_queried, rows = get_cartodb_locations(sql_client, carto_table)

        if not carto_succesfully_queried:
            return None
    except CartoException:  # pragma: no-cover
        logger.exception("CartoDB exception occured")
    else:
        # validations
        # get the list of the existing Pcodes and previous Pcodes from the database
        database_pcodes = []
        for row in Location.objects.all_locations().filter(gateway=carto_table.location_type).values('p_code'):
            database_pcodes.append(row['p_code'])

        # get the list of the new Pcodes from the Carto data
        new_carto_pcodes = [str(row[carto_table.pcode_col]) for row in rows]

        # validate remap table contents
        remap_table_valid, remap_table_pcode_pairs, remap_old_pcodes, remap_new_pcodes = \
            validate_remap_table(database_pcodes, new_carto_pcodes, carto_table, sql_client)

        if not remap_table_valid:
            return None

        # check for  duplicate pcodes in both local and Carto data
        if duplicate_pcodes_exist(database_pcodes, new_carto_pcodes, remap_old_pcodes):
            return None

        # wrap Location tree updates in a transaction, to prevent an invalid tree state due to errors
        with transaction.atomic():
            # should write lock the locations table until the tree is rebuilt
            Location.objects.all_locations().select_for_update().only('id')

            # disable tree 'generation' during single row updates, rebuild the tree after the rows are updated.
            with Location.objects.disable_mptt_updates():
                # update locations in two steps: step 1: remap, step 2: update. THe reason of this approach is that
                # a remapped 'old' pcode can appear as a newly inserted pcode. Remapping before updating/inserting
                # should prevent the problem of archiving 'good' locations when remapping.

                # REMAP locations
                if carto_table.remap_table_name and len(remap_table_pcode_pairs) > 0:
                    # remapped_pcode_pairs ex.: {'old_pcode': 'ET0721', 'new_pcode': 'ET0714'}
                    remap_table_pcode_pairs = list(filter(
                        filter_remapped_locations,
                        remap_table_pcode_pairs
                    ))

                    aggregated_remapped_pcode_pairs = {}
                    for row in rows:
                        carto_pcode = str(row[carto_table.pcode_col]).strip()
                        for remap_row in remap_table_pcode_pairs:
                            # create the location or update the existing based on type and code
                            if carto_pcode == remap_row['new_pcode']:
                                if carto_pcode not in aggregated_remapped_pcode_pairs:
                                    aggregated_remapped_pcode_pairs[carto_pcode] = []
                                aggregated_remapped_pcode_pairs[carto_pcode].append(remap_row['old_pcode'])

                    # aggregated_remapped_pcode_pairs - {'new_pcode': ['old_pcode_1', old_pcode_2, ...], ...}
                    for remapped_new_pcode, remapped_old_pcodes in aggregated_remapped_pcode_pairs.items():
                        remap_location(
                            carto_table,
                            remapped_new_pcode,
                            remapped_old_pcodes
                        )

                # UPDATE locations
                for row in rows:
                    carto_pcode = str(row[carto_table.pcode_col]).strip()
                    site_name = row[carto_table.name_col]

                    if not site_name or site_name.isspace():
                        logger.warning("No name for location with PCode: {}".format(carto_pcode))
                        sites_not_added += 1
                        continue

                    parent = None
                    parent_code = None
                    parent_instance = None

                    # attempt to reference the parent of this location
                    if carto_table.parent_code_col and carto_table.parent:
                        msg = None
                        parent = carto_table.parent.__class__
                        parent_code = row[carto_table.parent_code_col]
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

                    # create the location or update the existing based on type and code
                    succ, sites_not_added, sites_created, sites_updated = create_location(
                        carto_pcode, carto_table,
                        parent, parent_instance,
                        site_name, row,
                        sites_not_added, sites_created, sites_updated
                    )

                orphaned_old_pcodes = set(database_pcodes) - (set(new_carto_pcodes) | set(remap_old_pcodes))
                if orphaned_old_pcodes:  # pragma: no-cover
                    logger.warning("Archiving unused pcodes: {}".format(','.join(orphaned_old_pcodes)))
                    Location.objects.filter(
                        p_code__in=list(orphaned_old_pcodes),
                        is_active=True,
                    ).update(
                        is_active=False
                    )

            # rebuild location tree
            Location.objects.rebuild()

    logger.warning("Table name {}: {} sites created, {} sites updated, {} sites remapped, {} sites skipped".format(
        carto_table.table_name, sites_created, sites_updated, sites_remapped, sites_not_added))


def create_location(pcode, carto_table, parent, parent_instance, site_name, row,
                    sites_not_added, sites_created, sites_updated):
    """
    :param pcode: pcode of the new/updated location
    :param carto_table:
    :param parent:
    :param parent_instance:
    :param site_name:
    :param row: the new location data as received from CartoDB
    :param sites_not_added:
    :param sites_created:
    :param sites_updated:
    :return:
    """

    logger.info('{}: {} ({})'.format(
        'Importing location',
        pcode,
        carto_table.location_type.name
    ))

    location = None
    try:
        # TODO: revisit this, maybe include (location name?) carto_table in the check
        # see below at update branch - names can be updated for existing locations with the same code
        location = Location.objects.all_locations().get(p_code=pcode)

    except Location.MultipleObjectsReturned:
        logger.warning("Multiple locations found for: {}, {} ({})".format(
            carto_table.location_type, site_name, pcode
        ))
        sites_not_added += 1
        return False, sites_not_added, sites_created, sites_updated

    except Location.DoesNotExist:
        pass

    if not location:
        # try to create the location
        create_args = {
            'p_code': pcode,
            'gateway': carto_table.location_type,
            'name': site_name
        }
        if parent and parent_instance:
            create_args['parent'] = parent_instance

        if not row['the_geom']:
            sites_not_added += 1
            return False, sites_not_added, sites_created, sites_updated

        if 'Point' in row['the_geom']:
            create_args['point'] = row['the_geom']
        else:
            create_args['geom'] = row['the_geom']

        try:
            location = Location.objects.create(**create_args)
            sites_created += 1
        except IntegrityError:
            logger.exception('Error while creating location: %s', site_name)
            sites_not_added += 1
            return False, sites_not_added, sites_created, sites_updated

        logger.info('{}: {} ({})'.format(
            'Added',
            location.name,
            carto_table.location_type.name
        ))

        return True, sites_not_added, sites_created, sites_updated

    else:
        if not row['the_geom']:
            return False, sites_not_added, sites_created, sites_updated

        # names can be updated for existing locations with the same code
        location.name = site_name
        # TODO: re-confirm if this is not a problem. (assuming that every row in the new data is active)
        location.is_active = True

        if 'Point' in row['the_geom']:
            location.point = row['the_geom']
        else:
            location.geom = row['the_geom']

        if parent and parent_instance:
            logger.info("Updating parent:{} for location {}".format(parent_instance, location))
            location.parent = parent_instance
        else:
            location.parent = None

        try:
            location.save()
        except IntegrityError:
            logger.exception('Error while saving location: %s', site_name)
            return False, sites_not_added, sites_created, sites_updated

        sites_updated += 1
        logger.info('{}: {} ({})'.format(
            'Updated',
            location.name,
            carto_table.location_type.name
        ))

        return True, sites_not_added, sites_created, sites_updated


def remap_location(carto_table, new_pcode, remapped_pcodes):
    """
    :param carto_table:
    :param new_pcode: pcode the others will be remapped to
    :param remapped_pcodes: pcodes to be remapped and archived/removed

    :return: [(new_location.id, remapped_location.id), ...]
    """

    remapped_locations = Location.objects.all_locations().filter(p_code__in=list(remapped_pcodes))
    if not remapped_locations:
        logger.info('Remapped pcodes: [{}] cannot be found in the database!'.format(",".join(remapped_pcodes)))
        return

    logger.info('Preparing to remap : [{}] to {}'.format(",".join(remapped_pcodes), new_pcode))

    try:
        new_location = Location.objects.all_locations().get(p_code=new_pcode)
        # the approach below is not good - remap should work across location levels, and probably for archived locs too
        # new_location = Location.objects.get(p_code=new_pcode, gateway=carto_table.location_type)
    except Location.MultipleObjectsReturned:
        logger.warning("REMAP: multiple locations found for new pcode: {} ({})".format(
            new_pcode, carto_table.location_type
        ))
        return None
    except Location.DoesNotExist:
        # if the remap destination location does not exist in the DB, we have to create it.
        # the `name`  and `parent` will be updated in the next step of the update process.
        create_args = {
            'p_code': new_pcode,
            'gateway': carto_table.location_type,
            'name': new_pcode   # the name is temporary
        }
        new_location = Location.objects.create(**create_args)

    results = []
    for remapped_location in remapped_locations:
        remapped_location.is_active = False
        remapped_location.save()

        logger.info('Prepared to remap {} to {} ({})'.format(
            remapped_location.p_code,
            new_location.p_code,
            carto_table.location_type.name
        ))

        results.append((new_location.id, remapped_location.id))

    return results


def filter_remapped_locations(remap_row):
    # old_location_id = Location.objects.all_locations().get(p_code=remap_row['old_pcode']).id
    # return len(get_location_ids_in_use([old_location_id])) > 0
    return True


def get_cartodb_locations(sql_client, carto_table):
    rows = []
    cartodb_id_col = 'cartodb_id'

    try:
        query_row_count = sql_client.send('select count(*) from {}'.format(carto_table.table_name))
        row_count = query_row_count['rows'][0]['count']

        # do not spam Carto with requests, wait 1 second
        time.sleep(1)
        query_max_id = sql_client.send('select MAX({}) from {}'.format(cartodb_id_col, carto_table.table_name))
        max_id = query_max_id['rows'][0]['max']
    except CartoException:  # pragma: no-cover
        logger.exception("Cannot fetch pagination prequisites from CartoDB for table {}".format(
            carto_table.table_name
        ))
        return False, []

    offset = 0
    limit = 100

    # failsafe in the case when cartodb id's are too much off compared to the nr. of records
    if max_id > (5 * row_count):
        limit = max_id + 1
        logger.warning("The CartoDB primary key seemf off, pagination is not possible")

    if carto_table.parent_code_col and carto_table.parent:
        qry = 'select st_AsGeoJSON(the_geom) as the_geom, {}, {}, {} from {}'.format(
            carto_table.name_col,
            carto_table.pcode_col,
            carto_table.parent_code_col,
            carto_table.table_name)
    else:
        qry = 'select st_AsGeoJSON(the_geom) as the_geom, {}, {} from {}'.format(
            carto_table.name_col,
            carto_table.pcode_col,
            carto_table.table_name)

    while offset <= max_id:
        paged_qry = qry + ' WHERE {} > {} AND {} <= {}'.format(
            cartodb_id_col,
            offset,
            cartodb_id_col,
            offset + limit
        )
        logger.info('Requesting rows between {} and {} for {}'.format(
            offset,
            offset + limit,
            carto_table.table_name
        ))

        # do not spam Carto with requests, wait 1 second
        time.sleep(1)
        sites = sql_client.send(paged_qry)
        rows += sites['rows']
        offset += limit

        if 'error' in sites:
            # it seems we can have both valid results and error messages in the same CartoDB response
            logger.exception("CartoDB API error received: {}".format(sites['error']))
            # When this error occurs, we receive truncated locations, probably it's better to interrupt the import
            return False, []

    return True, rows


# TODO: Reenable coverage after the location import task is refactored
def validate_remap_table(database_pcodes, new_carto_pcodes, carto_table, sql_client):  # pragma: no-cover
    remapped_pcode_pairs = []
    remap_old_pcodes = []
    remap_new_pcodes = []
    remap_table_valid = True

    if carto_table.remap_table_name:
        try:
            remap_qry = 'select old_pcode::text, new_pcode::text from {}'.format(
                carto_table.remap_table_name)
            remapped_pcode_pairs = sql_client.send(remap_qry)['rows']
        except CartoException:  # pragma: no-cover
            logger.exception("CartoDB exception occured on the remap table query")
            remap_table_valid = False
        else:
            # validate remap table
            bad_old_pcodes = []
            bad_new_pcodes = []
            for remap_row in remapped_pcode_pairs:
                if 'old_pcode' not in remap_row or 'new_pcode' not in remap_row:
                    return False, remapped_pcode_pairs, remap_old_pcodes, remap_new_pcodes

                remap_old_pcodes.append(remap_row['old_pcode'])
                remap_new_pcodes.append(remap_row['new_pcode'])

                # check for non-existing remap pcodes in the database
                if remap_row['old_pcode'] not in database_pcodes:
                    bad_old_pcodes.append(remap_row['old_pcode'])
                # check for non-existing remap pcodes in the Carto dataset
                if remap_row['new_pcode'] not in new_carto_pcodes:
                    bad_new_pcodes.append(remap_row['new_pcode'])

            if len(bad_old_pcodes) > 0:
                logger.exception(
                    "Invalid old_pcode found in the remap table: {}".format(','.join(bad_old_pcodes)))
                remap_table_valid = False

            if len(bad_new_pcodes) > 0:
                logger.exception(
                    "Invalid new_pcode found in the remap table: {}".format(','.join(bad_new_pcodes)))
                remap_table_valid = False

    return remap_table_valid, remapped_pcode_pairs, remap_old_pcodes, remap_new_pcodes


# TODO: Reenable coverage after the location import task is refactored
def duplicate_pcodes_exist(database_pcodes, new_carto_pcodes, remap_old_pcodes):  # pragma: no-cover
    duplicates_found = False
    temp = {}
    duplicate_database_pcodes = []
    for database_pcode in database_pcodes:
        if database_pcode in temp:
            duplicate_database_pcodes.append(database_pcode)
        temp[database_pcode] = 1

    if duplicate_database_pcodes:
        logger.exception("Duplicates found in the existing database pcodes: {}".
                         format(','.join(duplicate_database_pcodes)))
        duplicates_found = True

    temp = {}
    duplicate_carto_pcodes = []
    for new_carto_pcode in new_carto_pcodes:
        if new_carto_pcode in temp:
            duplicate_carto_pcodes.append(new_carto_pcode)
        temp[new_carto_pcode] = 1

    if duplicate_carto_pcodes:
        logger.exception("Duplicates found in the new CartoDB pcodes: {}".
                         format(','.join(duplicate_database_pcodes)))
        duplicates_found = True

    temp = {}
    duplicate_remap_old_pcodes = []
    for remap_old_pcode in remap_old_pcodes:
        if remap_old_pcode in temp:
            duplicate_remap_old_pcodes.append(remap_old_pcode)
        temp[remap_old_pcode] = 1

    if duplicate_remap_old_pcodes:
        logger.exception("Duplicates found in the remap table `old pcode` column: {}".
                         format(','.join(duplicate_remap_old_pcodes)))
        duplicates_found = True

    return duplicates_found
