import celery
from celery.utils.log import get_task_logger

from unicef_locations.synchronizers import LocationSynchronizer

logger = get_task_logger(__name__)


@celery.current_app.task(bind=True)
def import_locations(self, carto_table_pk):
    """Import locations from carto"""
    LocationSynchronizer(carto_table_pk).sync()
