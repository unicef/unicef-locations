from carto.exceptions import CartoException
from celery.utils.log import get_task_logger
from django.apps import apps
from django.conf import settings

from unicef_locations.exceptions import InvalidRemap

logger = get_task_logger(__name__)


def get_location_model():
    get_model = apps.get_model

    return get_model(settings.UNICEF_LOCATIONS_MODEL)


def get_remapping(sql_client, carto_table):
    remap_dict = dict()
    to_deactivate = list()
    if carto_table.remap_table_name:
        try:
            remap_qry = f'select old_pcode::text, new_pcode::text, matching::int from {carto_table.remap_table_name}'
            remap_table = sql_client.send(remap_qry)['rows']
        except CartoException as e:
            logger.exception(str(e))
            raise CartoException
        for remap_row in remap_table:
            old, new, matching = remap_row['old_pcode'], remap_row['new_pcode'], remap_row['matching']
            if matching:
                if old in remap_dict:
                    raise InvalidRemap('Old location cannot be remapped twice')
                remap_dict[old] = new
            else:
                to_deactivate.append(old)

    temp = 0
    acyclic_dict = dict()
    adjusters = dict()
    for key, value in remap_dict.items():
        if key in remap_dict.values() and key != value:
            acyclic_dict[key] = f'temp{temp}'
            adjusters[f'temp{temp}'] = value
            temp += 1
        else:
            acyclic_dict[key] = value
    for key, value in adjusters.items():
        acyclic_dict[key] = value
    return acyclic_dict, to_deactivate
