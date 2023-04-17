from django.core.exceptions import ImproperlyConfigured

import pytest

from unicef_locations.cache import get_cache_key
from unicef_locations.config import AppSettings


def dummy():
    return 1


@pytest.fixture()
def conf():
    return AppSettings("TEST")


def test_missing(settings, conf):
    with pytest.raises(AttributeError):
        assert conf.MISSED


def test_string(settings, conf):
    settings.TEST_CACHE_VERSION_KEY = "aaa"
    assert conf.CACHE_VERSION_KEY == settings.TEST_CACHE_VERSION_KEY


def test_callable(settings, conf):
    settings.TEST_GET_CACHE_KEY = dummy
    assert conf.GET_CACHE_KEY == dummy


def test_callable_no_importable(settings, conf):
    settings.TEST_GET_CACHE_KEY = "aaaa"
    with pytest.raises(ImproperlyConfigured):
        assert conf.GET_CACHE_KEY


def test_callable_wrong(settings, conf):
    settings.TEST_GET_CACHE_KEY = 1
    with pytest.raises(ImproperlyConfigured):
        assert conf.GET_CACHE_KEY


def test_callable_by_name(settings, conf):
    settings.TEST_GET_CACHE_KEY = "unicef_locations.cache.get_cache_key"
    assert conf.GET_CACHE_KEY == get_cache_key
