import requests
from carto.exceptions import CartoException

import pytest
from unittest.mock import call, patch

from unicef_locations.synchronizers import LocationSynchronizer
from unicef_locations.tests.factories import GatewayTypeFactory, LocationFactory

pytestmark = pytest.mark.django_db


def test_location_synchronizer_init(cartodbtable):
    synchronizer = LocationSynchronizer(pk=cartodbtable.pk)
    assert synchronizer.carto is not None
    assert synchronizer.sql_client is not None


@patch('carto.sql.SQLClient.send')
def test_location_synchronizer_get_cartodb_locations(mock_send, cartodbtable):
    synchronizer = LocationSynchronizer(pk=cartodbtable.pk)
    mock_send.return_value = {
        'rows': [
            {
                'count': 1,
                'max': 1,
            }],
        'time': 0.053,
        'fields': {
            'count': {'type': 'number', 'pgtype': 'int8'},
            'max': {'type': 'number', 'pgtype': 'int4'}
        },
        'total_rows': 1
    }
    with mock_send:
        rows = synchronizer.get_cartodb_locations()
    assert rows is not None


@patch('carto.sql.SQLClient.send')
@patch('logging.Logger.warning')
def test_location_synchronizer_get_cartodb_locations_failsafe_max(logger_mock, mock_send, cartodbtable):
    synchronizer = LocationSynchronizer(pk=cartodbtable.pk)
    mock_send.return_value = {
        'rows': [
            {
                'count': 3,
                'max': 1200
            }
        ]
    }
    with mock_send:
        rows = synchronizer.get_cartodb_locations()
    assert rows is not None
    logger_mock.assert_called_with("The CartoDB primary key seems off, pagination is not possible")


@patch('unicef_locations.auth.LocationsCartoNoAuthClient.send')
@patch('logging.Logger.exception')
def test_location_synchronizer_get_cartodb_locations_exception(logger_mock, mock_send, cartodbtable):
    synchronizer = LocationSynchronizer(pk=cartodbtable.pk)
    mock_resp = requests.models.Response()
    mock_resp.status_code = 400

    mock_send.return_value = mock_resp
    with pytest.raises(CartoException):
        synchronizer.get_cartodb_locations()
    logger_mock.assert_called_with(f"Cannot fetch pagination prerequisites "
                                   f"from CartoDB for table {cartodbtable.table_name}")


@patch('carto.sql.SQLClient.send')
def test_location_synchronizer_query_with_retries_exception(mock_send, cartodbtable):
    synchronizer = LocationSynchronizer(pk=cartodbtable.pk)
    mock_send.return_value = {
        'error': 'mocked error response'
    }
    query = " this is a mocked query string"
    with pytest.raises(CartoException):
        synchronizer.query_with_retries(query, 0)


@patch('unicef_locations.synchronizers.LocationSynchronizer.get_cartodb_locations')
@patch('logging.Logger.warning')
def test_location_synchronizer_create_or_update_locations(logger_mock, mock_cartodb_locations, cartodbtable):
    LocationFactory(p_code='RW', is_active=True)
    cartodbtable.parent_code_col = 'parent_code_col'
    cartodbtable.save(update_fields=['parent_code_col'])
    synchronizer = LocationSynchronizer(pk=cartodbtable.pk)
    mock_cartodb_locations.return_value = [
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
    new, updated, skipped, error = synchronizer.create_or_update_locations()
    assert new == 1
    assert skipped == updated == error == 0

    new, updated, skipped, error = synchronizer.create_or_update_locations()
    assert updated == 1
    assert new == skipped == error == 0

    LocationFactory(p_code='RW01', is_active=True)
    with pytest.raises(CartoException):
        synchronizer.create_or_update_locations()
        logger_mock.assert_called_with(
            f"Multiple locations found for: {cartodbtable.location_type}, "
            f"{cartodbtable.name_col} ({cartodbtable.pcode_col})")

    mock_cartodb_locations.return_value[0][cartodbtable.pcode_col] = ''
    new, updated, skipped, error = synchronizer.create_or_update_locations()
    assert skipped == 1
    assert new == updated == error == 0


@patch('logging.Logger.info')
def test_location_synchronizer_handle_obsolete_locations(logger_mock, cartodbtable):
    synchronizer = LocationSynchronizer(pk=cartodbtable.pk)
    location_1 = LocationFactory(p_code='RW', is_active=True)
    LocationFactory(parent=location_1, p_code='RW01', is_active=True)
    location_2 = LocationFactory(p_code='PER', is_active=True)
    assert location_1.is_active
    assert location_2.is_active

    synchronizer.handle_obsolete_locations(['RW', 'PER'])
    location_1.refresh_from_db()
    assert not location_1.is_active
    expected_calls = [
        call(f"Deactivating {location_1}"),
        call(f"Deleting {location_2}")]
    logger_mock.assert_has_calls(expected_calls)


@patch('logging.Logger.info')
def test_location_synchronizer_clean_upper_level(logger_mock, cartodbtable):
    synchronizer = LocationSynchronizer(pk=cartodbtable.pk)
    location_1 = LocationFactory(p_code='RW', is_active=True)
    location_2 = LocationFactory(
        parent=location_1, p_code='RW01', is_active=False,
        gateway=GatewayTypeFactory(admin_level=cartodbtable.location_type.admin_level - 1))

    synchronizer.clean_upper_level()
    location_1.refresh_from_db()
    assert location_1.is_active
    expected_calls = [
        call(f"Deleting parent {location_2}")]
    logger_mock.assert_has_calls(expected_calls)
