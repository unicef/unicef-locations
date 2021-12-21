import logging

from django.core.management import BaseCommand
from django.db import connection

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    args = ''
    help = 'Rename app'
    requires_migrations_checks = False

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--noinput', action='store_false',
            dest='interactive', default=True,
            help='Tells Django to NOT prompt the user for input of any kind.')

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("UPDATE django_content_type SET app_label='unicef_locations' WHERE app_label='locations'")
            tables = [
                "gatewaytype",
                "cartodbtable",
                "location",
                "locationremaphistory",
            ]
            for table in tables:
                cursor.execute("ALTER TABLE locations_{} RENAME TO unicef_locations_{}".format(table, table))
            cursor.execute("UPDATE django_migrations SET app='unicef_locations' WHERE app='locations'")
