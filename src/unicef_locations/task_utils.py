# from carto.exceptions import CartoException
from celery.utils.log import get_task_logger
from django.db import IntegrityError

from .models import Location

logger = get_task_logger(__name__)


def create_location(pcode, datadef_table, parent, parent_instance, site_name, the_geom,
                    sites_not_added, sites_created, sites_updated):
    """
    :param pcode: pcode of the new/updated location
    :param datadef_table: table that holds the imported dataset properties, carto or arcgis
    :param parent:
    :param parent_instance:
    :param site_name:
    :param the_geom: the imported locations geometry
    :param sites_not_added:
    :param sites_created:
    :param sites_updated:
    :return:
    """

    logger.info('{}: {} ({})'.format(
        'Importing location',
        pcode,
        datadef_table.location_type.name
    ))

    location = None
    try:
        # TODO: revisit this, maybe include (location name?) carto/arcgis table in the check
        # see below at update branch - names can be updated for existing locations with the same code
        location = Location.objects.all_locations().get(p_code=pcode)

    except Location.MultipleObjectsReturned:
        logger.warning("Multiple locations found for: {}, {} ({})".format(
            datadef_table.location_type, site_name, pcode
        ))
        sites_not_added += 1
        return False, sites_not_added, sites_created, sites_updated

    except Location.DoesNotExist:
        pass

    if not location:
        # try to create the location
        create_args = {
            'p_code': pcode,
            'gateway': datadef_table.location_type,
            'name': site_name
        }
        if parent and parent_instance:
            create_args['parent'] = parent_instance

        if 'Point' in the_geom:
            create_args['point'] = the_geom
        else:
            create_args['geom'] = the_geom

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
            datadef_table.location_type.name
        ))

        return True, sites_not_added, sites_created, sites_updated

    else:
        if not the_geom:
            return False, sites_not_added, sites_created, sites_updated

        # names can be updated for existing locations with the same code
        location.name = site_name
        # TODO: re-confirm if this is not a problem. (assuming that every row in the new data is active)
        location.is_active = True

        if 'Point' in the_geom:
            location.point = the_geom
        else:
            location.geom = the_geom

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
            datadef_table.location_type.name
        ))

        return True, sites_not_added, sites_created, sites_updated


def remap_location(datadef_table, new_pcode, remapped_pcodes):
    """
    :param datadef_table: table tha holds the imported dataset properties, carto or arcgis
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
        # new_location = Location.objects.get(p_code=new_pcode, gateway=datadef_table.location_type)
    except Location.MultipleObjectsReturned:
        logger.warning("REMAP: multiple locations found for new pcode: {} ({})".format(
            new_pcode, datadef_table.location_type
        ))
        return None
    except Location.DoesNotExist:
        # if the remap destination location does not exist in the DB, we have to create it.
        # the `name`  and `parent` will be updated in the next step of the update process.
        create_args = {
            'p_code': new_pcode,
            'gateway': datadef_table.location_type,
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
            datadef_table.location_type.name
        ))

        results.append((new_location.id, remapped_location.id))

    return results


def filter_remapped_locations(remap_row):
    # old_location_id = Location.objects.all_locations().get(p_code=remap_row['old_pcode']).id
    # return len(get_location_ids_in_use([old_location_id])) > 0
    return True


def validate_remap_table(remap_table_pcode_pairs, database_pcodes, imported_pcodes):  # pragma: no-cover
    remap_old_pcodes = []
    remap_new_pcodes = []
    remap_table_valid = True

    # validate remap table
    bad_old_pcodes = []
    bad_new_pcodes = []
    for remap_row in remap_table_pcode_pairs:
        if 'old_pcode' not in remap_row or 'new_pcode' not in remap_row:
            return False, remap_old_pcodes, remap_new_pcodes

        remap_old_pcodes.append(remap_row['old_pcode'])
        remap_new_pcodes.append(remap_row['new_pcode'])

        # check for non-existing remap pcodes in the database
        if remap_row['old_pcode'] not in database_pcodes:
            bad_old_pcodes.append(remap_row['old_pcode'])
        # check for non-existing remap pcodes in the Carto dataset
        if remap_row['new_pcode'] not in imported_pcodes:
            bad_new_pcodes.append(remap_row['new_pcode'])

    if len(bad_old_pcodes) > 0:
        logger.exception(
            "Invalid old_pcode found in the remap table: {}".format(','.join(bad_old_pcodes)))
        remap_table_valid = False

    if len(bad_new_pcodes) > 0:
        logger.exception(
            "Invalid new_pcode found in the remap table: {}".format(','.join(bad_new_pcodes)))
        remap_table_valid = False

    return remap_table_valid, remap_old_pcodes, remap_new_pcodes


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
