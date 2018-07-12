# -*- coding: utf-8 -*-

import pytest


@pytest.fixture()
def location(db):
    from unicef_locations.tests.factories import LocationFactory
    return LocationFactory()


@pytest.fixture()
def locations3(db):
    return [location(db) for _ in range(3)]


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
