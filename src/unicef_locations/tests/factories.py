from django.contrib.gis.geos import GEOSGeometry
from unicef_locations import models

import factory


class GatewayTypeFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.GatewayType

    name = factory.Sequence(lambda n: f"GatewayType {n}")
    admin_level = factory.Sequence(lambda n: n)


class LocationFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.Location

    name = factory.Sequence(lambda n: f"Location {n}")
    gateway = factory.SubFactory(GatewayTypeFactory)
    point = GEOSGeometry("POINT(20 20)")
    p_code = factory.Sequence(lambda n: f"PCODE{n}")


class CartoDBTableFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.CartoDBTable

    domain = factory.Sequence(lambda n: f"Domain {n}")
    api_key = factory.Sequence(lambda n: f"API Key {n}")
    table_name = factory.Sequence(lambda n: f"table_name_{n}")
    location_type = factory.SubFactory(GatewayTypeFactory)
