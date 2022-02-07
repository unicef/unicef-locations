import requests
from carto.exceptions import CartoException

import pytest
from unittest.mock import patch

from unicef_locations.exceptions import InvalidRemap
from unicef_locations.synchronizers import LocationSynchronizer
from unicef_locations.utils import get_remapping

pytestmark = pytest.mark.django_db


@patch('carto.sql.SQLClient.send')
def test_get_remapping(mock_send, cartodbtable):
    cartodbtable.remap_table_name = 'Remap table name'
    cartodbtable.save(update_fields=['remap_table_name'])
    synchronizer = LocationSynchronizer(pk=cartodbtable.pk)
    mock_send.return_value = {
        'rows': [
            {
                'old_pcode': 'RWA',
                'new_pcode': 'RW',
                'matching': 1
            },
            {
                'old_pcode': 'RW',
                'new_pcode': 'RWA',
                'matching': 1
            }
        ]
    }

    acyclic_dict, to_deactivate = get_remapping(synchronizer.sql_client, cartodbtable)
    assert acyclic_dict == {'RW': 'temp1', 'RWA': 'temp0', 'temp0': 'RW', 'temp1': 'RWA'}
    assert not to_deactivate


@patch('carto.sql.SQLClient.send')
def test_get_remapping_to_deactivate(mock_send, cartodbtable):
    cartodbtable.remap_table_name = 'Remap table name'
    cartodbtable.save(update_fields=['remap_table_name'])
    synchronizer = LocationSynchronizer(pk=cartodbtable.pk)
    mock_send.return_value = {
        'rows': [
            {
                'old_pcode': 'RWA',
                'new_pcode': 'RW',
                'matching': 0
            }
        ]
    }

    acyclic_dict, to_deactivate = get_remapping(synchronizer.sql_client, cartodbtable)
    assert not acyclic_dict
    assert to_deactivate == ['RWA']


@patch('carto.sql.SQLClient.send')
def test_get_remapping_invalid(mock_send, cartodbtable):
    cartodbtable.remap_table_name = 'Remap table name'
    cartodbtable.save(update_fields=['remap_table_name'])
    synchronizer = LocationSynchronizer(pk=cartodbtable.pk)
    row = {
        'old_pcode': 'RWA',
        'new_pcode': 'RW',
        'matching': 1
    }
    mock_send.return_value = {
        'rows': [row, row]
    }
    with pytest.raises(InvalidRemap):
        get_remapping(synchronizer.sql_client, cartodbtable)


@patch('unicef_locations.auth.LocationsCartoNoAuthClient.send')
def test_get_remapping_exception(mock_send, cartodbtable):
    cartodbtable.remap_table_name = 'Remap table name'
    cartodbtable.save(update_fields=['remap_table_name'])
    synchronizer = LocationSynchronizer(pk=cartodbtable.pk)
    mock_resp = requests.models.Response()
    mock_resp.status_code = 400

    mock_send.return_value = mock_resp
    with pytest.raises(CartoException):
        get_remapping(synchronizer.sql_client, cartodbtable)
