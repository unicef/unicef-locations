import pytest

from unicef_locations.serializers import (
    CartoDBTableSerializer,
    GatewayTypeSerializer,
    LocationExportFlatSerializer,
    LocationExportSerializer,
    LocationLightSerializer,
    LocationSerializer,
)

pytestmark = pytest.mark.django_db


def test_LocationExportSerializer(location):
    ser = LocationExportSerializer(instance=location)
    assert ser.data


def test_LocationExportFlatSerializer(location):
    ser = LocationExportFlatSerializer(instance=location)
    assert ser.data


def test_LocationLightSerializer(location):
    ser = LocationLightSerializer(instance=location)
    assert ser.data


def test_LocationSerializer(location):
    ser = LocationSerializer(instance=location)
    assert ser.data


def test_GatewayTypeSerializer(gateway):
    ser = GatewayTypeSerializer(instance=gateway)
    assert ser.data


def test_CartoDBTableSerializer(cartodbtable):
    ser = CartoDBTableSerializer(instance=cartodbtable)
    assert ser.data
