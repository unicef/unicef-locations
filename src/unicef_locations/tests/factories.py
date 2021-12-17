from django.contrib.gis.geos import GEOSGeometry
from faker import Faker

import factory

from unicef_locations import models

faker = Faker()


class LocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Location

    name = factory.Sequence(lambda n: 'Location {}'.format(n))
    point = GEOSGeometry("POINT(20 20)")
    p_code = factory.Sequence(lambda n: 'PCODE{}'.format(n))
    admin_level = factory.Sequence(lambda n: faker.random_number(4))


class CartoDBTableFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.CartoDBTable

    domain = factory.Sequence(lambda n: 'Domain {}'.format(n))
    api_key = factory.Sequence(lambda n: 'API Key {}'.format(n))
    table_name = factory.Sequence(lambda n: 'table_name_{}'.format(n))
    remap_table_name = None
    admin_level = factory.Sequence(lambda n: faker.random_number(4))
