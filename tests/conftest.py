# -*- coding: utf-8 -*-

import pytest

from unicef_locations.tests.factories import LocationFactory


@pytest.fixture()
def location(db):
    return LocationFactory()


@pytest.fixture()
def locations3(db):
    return [LocationFactory() for _ in range(3)]


@pytest.fixture()
def gateway():
    from unicef_locations.tests.factories import GatewayTypeFactory
    return GatewayTypeFactory()


@pytest.fixture()
def cartodbtable():
    from unicef_locations.tests.factories import CartoDBTableFactory
    return CartoDBTableFactory()


@pytest.fixture()
def user_staff():
    from unicef_locations.tests.factories import CartoDBTableFactory
    return CartoDBTableFactory()
