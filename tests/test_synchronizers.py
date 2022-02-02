import requests
from carto.exceptions import CartoException

import pytest
from unittest.mock import patch

from unicef_locations.synchronizers import LocationSynchronizer

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
                'count': 3,
                'max': 12
            }
        ]
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
