from django.test import SimpleTestCase

from unicef_locations.tests.factories import CartoDBTableFactory, LocationFactory


def test_point_lat_long(location):
    assert isinstance(location.point_lat_long, str)


class TestStrUnicode(SimpleTestCase):
    '''Ensure calling str() on model instances returns the right text.'''

    def test_location(self):
        # Test with nonascii gateway name
        location = LocationFactory.build(admin_level_name='xyz', name='R\xe4dda Barnen', p_code='abc')
        self.assertEqual(str(location), 'R\xe4dda Barnen (xyz: abc)')

        # Test with str gateway name
        location = LocationFactory.build(admin_level_name='xyz', name='R\xe4dda Barnen', p_code='abc')
        self.assertEqual(str(location), 'R\xe4dda Barnen (xyz: abc)')

    def test_carto_db_table(self):
        carto_db_table = CartoDBTableFactory.build(table_name='R\xe4dda Barnen')
        self.assertEqual(str(carto_db_table), 'R\xe4dda Barnen')

        carto_db_table = CartoDBTableFactory.build(table_name='xyz')
        self.assertEqual(str(carto_db_table), 'xyz')
