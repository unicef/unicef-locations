from celery.utils.log import get_task_logger
from django.db import IntegrityError

from .models import Location

logger = get_task_logger(__name__)


def create_location(pcode, location_type, parent, parent_instance, remapped_old_pcodes, site_name,
                    geometry, sites_not_added, sites_created, sites_updated, sites_remapped):

    results = None
    try:
        location = None
        remapped_locations = None
        if remapped_old_pcodes:
            # check if the remapped location exists in the database
            remapped_locations = Location.objects.filter(p_code__in=list(remapped_old_pcodes))

            if not remapped_locations:
                # if remapped_old_pcodes are set and passed validations, but they are not found in the
                # list of the active locations(`Location.objects`), it means that they were already remapped.
                # in this case update the `main` location, and ignore the remap.
                location = Location.objects.get(p_code=pcode)
        else:
            location = Location.objects.get(p_code=pcode)

    except Location.MultipleObjectsReturned:
        logger.warning("Multiple locations found for: {}, {} ({})".format(
            location_type, site_name, pcode
        ))
        sites_not_added += 1
        return False, sites_not_added, sites_created, sites_updated, sites_remapped, results

    except Location.DoesNotExist:
        pass

    if not location:
        # try to create the location
        create_args = {
            'p_code': pcode,
            'gateway': location_type,
            'name': site_name
        }
        if parent and parent_instance:
            create_args['parent'] = parent_instance

        if not geometry:
            sites_not_added += 1
            return False, sites_not_added, sites_created, sites_updated, sites_remapped, results

        if 'Point' in geometry:
            create_args['point'] = geometry
        else:
            create_args['geom'] = geometry

        try:
            location = Location.objects.create(**create_args)
            sites_created += 1
        except IntegrityError:
            logger.exception('Error while creating location: %s', site_name)
            sites_not_added += 1
            return False, sites_not_added, sites_created, sites_updated, sites_remapped, results

        logger.info('{}: {} ({})'.format(
            'Added',
            location.name,
            location_type.name
        ))

        results = []
        if remapped_locations:
            for remapped_location in remapped_locations:
                remapped_location.is_active = False
                remapped_location.save()

                sites_remapped += 1
                logger.info('{}: {} ({})'.format(
                    'Remapped',
                    remapped_location.name,
                    location_type.name
                ))

                results.append((location.id, remapped_location.id))
        else:
            results = [(location.id, None)]

        return True, sites_not_added, sites_created, sites_updated, sites_remapped, results

    else:
        if not geometry:
            return False, sites_not_added, sites_created, sites_updated, sites_remapped, results

        # names can be updated for existing locations with the same code
        location.name = site_name

        if 'Point' in geometry:
            location.point = geometry
        else:
            location.geom = geometry

        if parent and parent_instance:
            logger.info("Updating parent:{} for location {}".format(parent_instance, location))
            location.parent = parent_instance
        else:
            location.parent = None

        try:
            location.save()
        except IntegrityError:
            logger.exception('Error while saving location: %s', site_name)
            return False, sites_not_added, sites_created, sites_updated, sites_remapped, results

        sites_updated += 1
        logger.info('{}: {} ({})'.format(
            'Updated',
            location.name,
            location_type.name
        ))

        results = [(location.id, None)]
        return True, sites_not_added, sites_created, sites_updated, sites_remapped, results


def validate_remap_table(remapped_pcode_pairs, database_pcodes, new_pcodes, ):  # pragma: no-cover
    remap_old_pcodes = []
    remap_new_pcodes = []
    remap_table_valid = True

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
        if remap_row['new_pcode'] not in new_pcodes:
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


def duplicate_pcodes_exist(database_pcodes, new_pcodes, remap_old_pcodes):  # pragma: no-cover
    duplicates_found = False
    temp = {}
    duplicate_database_pcodes = []
    for database_pcode in database_pcodes:
        if database_pcode in temp:
            if database_pcode not in duplicate_database_pcodes:
                duplicate_database_pcodes.append(database_pcode)
        temp[database_pcode] = 1

    if duplicate_database_pcodes:
        logger.exception("Duplicates found in the existing database pcodes: {}".
                         format(','.join(duplicate_database_pcodes)))
        duplicates_found = True

    temp = {}
    duplicate_new_pcodes = []
    for new_pcode in new_pcodes:
        if new_pcode in temp:
            if new_pcode not in duplicate_new_pcodes:
                duplicate_new_pcodes.append(new_pcode)
        temp[new_pcode] = 1

    if duplicate_new_pcodes:
        logger.exception("Duplicates found in the new pcodes: {}".
                         format(','.join(duplicate_new_pcodes)))
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
