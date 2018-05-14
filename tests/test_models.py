import pytest

pytestmark = pytest.mark.django_db


def test_a(location):
    assert str(location)
    assert location.point_lat_long
