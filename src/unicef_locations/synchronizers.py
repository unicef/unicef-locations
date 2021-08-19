import logging
import time
from datetime import datetime

from carto.exceptions import CartoException
from carto.sql import SQLClient
from django.db import transaction
from django.db.models.deletion import Collector

from unicef_locations.auth import LocationsCartoNoAuthClient
from unicef_locations.exceptions import InvalidRemap
from unicef_locations.models import CartoDBTable, Location
from unicef_locations.utils import get_remapping

logger = logging.getLogger(__name__)


class LocationSynchronizer:
    """Component to update locations"""

    def __init__(self, pk) -> None:
        self.carto = CartoDBTable.objects.get(pk=pk)
        self.sql_client = SQLClient(LocationsCartoNoAuthClient(base_url=f"https://{self.carto.domain}.carto.com/"))

    def create_or_update_locations(self):
        """
        Create or update locations based on p-code (only active locations are considerate)

        """
        logging.info('Create/Update new locations')
        rows = self.get_cartodb_locations()
        new, updated, skipped, error = 0, 0, 0, 0
        for row in rows:
            pcode = row[self.carto.pcode_col]
            name = row[self.carto.name_col]
            geom = row['the_geom']

            if all([name, pcode, geom]):
                geom_key = 'point' if 'Point' in row['the_geom'] else 'geom'
                default_dict = {
                    'gateway': self.carto.location_type,
                    'name': name,
                    geom_key: geom,
                }

                parent_pcode = row[self.carto.parent_code_col] if self.carto.parent_code_col in row else None
                if parent_pcode:
                    try:
                        parent = Location.objects.get(p_code=parent_pcode, is_active=True)
                        default_dict['parent'] = parent
                    except (Location.DoesNotExist, Location.MultipleObjectsReturned):
                        skipped += 1
                        logger.info(f"Skipping row pcode {pcode}")
                        continue

                try:
                    location, created = Location.objects.get_or_create(p_code=pcode, is_active=True,
                                                                       defaults=default_dict)
                    if created:
                        new += 1
                    else:
                        for attr, value in default_dict.items():
                            setattr(location, attr, value)
                        location.save()
                        updated += 1

                except Location.MultipleObjectsReturned:
                    logger.warning(f"Multiple locations found for: {self.carto.location_type}, {name} ({pcode})")
                    error += 1

            else:
                skipped += 1
                logger.info(f"Skipping row pcode {pcode}")

        return new, updated, skipped, error

    def query_with_retries(self, query, offset, max_retries=5):
        """
        Query CartoDB with retries
        """
        retries = 0
        while retries < max_retries:
            time.sleep(0.1)
            retries += 1
            try:
                sites = self.sql_client.send(query)
            except CartoException:
                if retries < max_retries:
                    logger.warning('Retrying again table page at offset {}'.format(offset))

            if 'error' in sites:
                raise CartoException
            return sites['rows']
        raise CartoException

    def get_cartodb_locations(self, cartodb_id_col='cartodb_id'):
        """
        returns locations referenced by cartodb_table
        """
        rows = []
        try:
            row_count = self.sql_client.send(f'select count(*) from {self.carto.table_name}')['rows'][0]['count']
            max_id = self.sql_client.send(
                f'select MAX({cartodb_id_col}) from {self.carto.table_name}')['rows'][0]['max']
        except CartoException:  # pragma: no-cover
            logger.exception(f"Cannot fetch pagination prequisites from CartoDB for table {self.carto.table_name}")
            raise CartoException

        offset, limit = 0, 100

        # failsafe in the case when cartodb id's are too much off compared to the nr. of records
        if max_id > (5 * row_count):
            limit = max_id + 1
            logger.warning("The CartoDB primary key seems off, pagination is not possible")

        parent_qry = f', {self.carto.parent_code_col}' if self.carto.parent_code_col and self.carto.parent else ''
        base_qry = f'select st_AsGeoJSON(the_geom) as the_geom, {self.carto.name_col}, ' \
                   f'{self.carto.pcode_col}{parent_qry} from {self.carto.table_name}'

        while offset <= max_id:
            logger.info(f'Requesting rows between {offset} and {offset + limit} for {self.carto.table_name}')
            paged_qry = base_qry + f' WHERE {cartodb_id_col} > {offset} AND {cartodb_id_col} <= {offset + limit}'
            time.sleep(0.1)  # do not spam Carto with requests
            new_rows = self.query_with_retries(paged_qry, offset)
            rows += new_rows
            offset += limit

        return rows

    def handle_obsolete_locations(self, to_deactivate):
        """
        Handle obsolate locations:
        - deactivate referenced locations
        - delete non referenced locations
        """
        logging.info('Clean Obsolate Locations')
        for location in Location.objects.filter(p_code__in=to_deactivate):
            collector = Collector(using='default')
            collector.collect([location])
            if collector.dependencies or location.get_children():
                location.name = f"{location.name} [{datetime.today().strftime('%Y-%m-%d')}]"
                location.is_active = False
                location.save()
                logger.info(f'Deactivating {location}')
            else:
                location.delete()
                logger.info(f'Deleting {location}')

    def apply_remap(self, old2new):
        """
        Use remap table to swap p-codes
        """
        logging.info('Apply Remap')
        for old, new in old2new.items():
            if old != new:
                try:
                    old_location = Location.objects.get(p_code=old, is_active=True)
                except Location.DoesNotExist:
                    raise InvalidRemap(f'Old location {old} does not exist or is not active')
                old_location.p_code = new
                old_location.save()
                logger.info(f'Update through remapping {old} -> {new}')

    def clean_upper_level(self):
        """
        Check upper level active locations with no reference
        - delete if is leaf
        - deactivate if all children are inactive (doesn't exist an active child)
        """
        logging.info('Clean upper level')
        qs = Location.objects.filter(gateway__admin_level=self.carto.location_type.admin_level - 1, is_active=False)
        for location in qs:
            collector = Collector(using='default')
            collector.collect([location])
            if not collector.dependencies:
                if location.is_leaf_node():
                    location.delete()
                    logger.info(f'Deleting parent {location}')
                # else:
                #     children = location.get_children()
                #     if not children.filter(is_active=True).exists():
                #         location.is_active = False
                #         location.save()
                #         logger.info(f'Deactivating parent {location}')

    def sync(self):
        try:
            with transaction.atomic():
                old2new, to_deactivate = get_remapping(self.sql_client, self.carto)
                self.handle_obsolete_locations(to_deactivate)
                self.apply_remap(old2new)
                new, updated, skipped, error = self.create_or_update_locations()
                self.clean_upper_level()
                return new, updated, skipped, error

        except CartoException:
            message = "CartoDB exception occured"
            logger.exception(message)
