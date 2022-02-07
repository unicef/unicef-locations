import pytest

from unicef_locations.tests.factories import LocationFactory


@pytest.fixture()
def location(db):
    return LocationFactory()


@pytest.fixture()
def locations3(db):
    return [LocationFactory() for _ in range(3)]


@pytest.fixture()
def cartodbtable():
    from unicef_locations.tests.factories import CartoDBTableFactory
    return CartoDBTableFactory()


@pytest.fixture()
def user_staff():
    from unicef_locations.tests.factories import CartoDBTableFactory
    return CartoDBTableFactory()


@pytest.fixture()
def carto_response(cartodbtable):
    return [
        {
            'the_geom': '{"type":"MultiPolygon",'
                        '"coordinates":[[['
                        '[28.8912701692831,-2.43352336201351],[28.8912892169238,-2.43353354233907],'
                        '[28.8918478389067,-2.43521500746656],[28.8912701692831,-2.43352336201351]'
                        ']]]}',
            cartodbtable.name_col: 'Rwanda',
            cartodbtable.pcode_col: 'RW01',
            'parent_code_col': 'RW'
        }
    ]
