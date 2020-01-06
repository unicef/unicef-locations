from django.test import TestCase, SimpleTestCase

from unicef_locations.models import Location
from unicef_locations.tests.factories import CartoDBTableFactory, GatewayTypeFactory, LocationFactory

import pytest

pytestmark = pytest.mark.django_db

def test_point_lat_long(location):
    assert isinstance(location.point_lat_long, str)


class TestStrUnicode(SimpleTestCase):
    '''Ensure calling str() on model instances returns the right text.'''

    def test_gateway_type(self):
        gateway_type = GatewayTypeFactory.build(name='xyz')
        self.assertEqual(str(gateway_type), u'xyz')

        gateway_type = GatewayTypeFactory.build(name=u'R\xe4dda Barnen')
        self.assertEqual(str(gateway_type), u'R\xe4dda Barnen')

    def test_location(self):
        # Test with nonascii gateway name
        gateway_type = GatewayTypeFactory.build(name=u'xyz')
        location = LocationFactory.build(gateway=gateway_type, name=u'R\xe4dda Barnen', p_code='abc')
        self.assertEqual(str(location), u'R\xe4dda Barnen (xyz PCode: abc)')

        # Test with str gateway name
        gateway_type = GatewayTypeFactory.build(name='xyz')
        location = LocationFactory.build(gateway=gateway_type, name=u'R\xe4dda Barnen', p_code='abc')
        self.assertEqual(str(location), u'R\xe4dda Barnen (xyz PCode: abc)')

    def test_carto_db_table(self):
        carto_db_table = CartoDBTableFactory.build(table_name=u'R\xe4dda Barnen')
        self.assertEqual(str(carto_db_table), u'R\xe4dda Barnen')

        carto_db_table = CartoDBTableFactory.build(table_name='xyz')
        self.assertEqual(str(carto_db_table), u'xyz')


class TestModels(TestCase):
    '''Cover archived locations in manager'''

    def test_archived_location(self):
        location = LocationFactory(is_active=False)
        self.assertIsNotNone(Location.objects.archived_locations())
