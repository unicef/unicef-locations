from django.contrib.gis.geos import GEOSGeometry

import factory

from unicef_locations import models


class GatewayTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.GatewayType

    name = factory.Sequence(lambda n: 'GatewayType {}'.format(n))
    admin_level = factory.Sequence(lambda n: n)


class LocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Location

    name = factory.Sequence(lambda n: 'Location {}'.format(n))
    gateway = factory.SubFactory(GatewayTypeFactory)
    point = GEOSGeometry("POINT(20 20)")
    p_code = factory.Sequence(lambda n: 'PCODE{}'.format(n))


class CartoDBTableFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.CartoDBTable

    domain = factory.Sequence(lambda n: 'Domain {}'.format(n))
    api_key = factory.Sequence(lambda n: 'API Key {}'.format(n))
    table_name = factory.Sequence(lambda n: 'table_name_{}'.format(n))
    remap_table_name = None
    location_type = factory.SubFactory(GatewayTypeFactory)


class LocationRemapHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.LocationRemapHistory

    old_location = factory.SubFactory(LocationFactory)
    new_location = factory.SubFactory(LocationFactory)
