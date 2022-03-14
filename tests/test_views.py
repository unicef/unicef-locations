from django.core.cache import cache
from django.http import HttpResponse
from django.urls import reverse
from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from unittest import mock

from unicef_locations.cache import etag_cached
from unicef_locations.config import conf
from unicef_locations.tests.factories import LocationFactory
from unicef_locations.utils import get_location_model
from unicef_locations.views import LocationsViewSet


def test_api_location_light_list(
        django_app,
        admin_user,
        locations3,
        django_assert_num_queries,
):
    url = reverse('unicef_locations:locations-light-list')
    with django_assert_num_queries(10):
        res = django_app.get(url, user=admin_user)
    assert sorted(res.json[0].keys()) == ['admin_level', 'admin_level_name', 'id', 'name', 'name_display',
                                          'p_code', 'parent']


def test_api_location_heavy_list(
        django_app,
        admin_user,
        location,
        django_assert_num_queries,
):
    url = reverse('unicef_locations:locations-list')

    with django_assert_num_queries(10):
        response = django_app.get(url, user=admin_user)
    assert sorted(response.json[0].keys()) == [
        'admin_level', 'admin_level_name', 'geo_point', 'id', 'name', 'name_display', 'p_code', 'parent'
    ]


def test_api_location_queries(
        django_app,
        admin_user,
        location,
        django_assert_num_queries,
):
    url = reverse('unicef_locations:locations-list')

    with django_assert_num_queries(10):
        django_app.get(url, user=admin_user)

    query_count = 3
    with django_assert_num_queries(query_count):
        django_app.get(url, user=admin_user)

    # add another location with reference to parent
    # and ensure no extra queries
    LocationFactory(parent=location)
    with django_assert_num_queries(query_count):
        django_app.get(url, user=admin_user)


def test_api_location_values(django_app, admin_user, locations3):
    l1, l2, l3 = locations3
    params = {"values": "{},{}".format(l1.id, l2.id)}
    response = django_app.get(reverse('unicef_locations:locations-list'), user=admin_user, params=params)
    assert len(response.json) == 2, response.json


def test_api_location_heavy_detail(django_app, admin_user, locations3):
    l1, l2, l3 = locations3
    url = reverse('unicef_locations:locations-detail', args=[l1.id])
    response = django_app.get(url, user=admin_user)
    assert sorted(response.json.keys()), ['geo_point', 'id', 'admin_level', 'admin_level_name',
                                          'name', 'p_code', 'parent']
    assert "Location" in response.json["name"]


def test_api_location_heavy_detail_pcode(django_app, admin_user, locations3):
    l1, l2, l3 = locations3
    url = reverse('unicef_locations:locations_detail_pcode', args=[l1.p_code])
    response = django_app.get(url, user=admin_user)
    assert sorted(response.json.keys()), ['geo_point', 'id', 'admin_level', 'admin_level_name', 'name', 'p_code',
                                          'parent']
    assert "Location" in response.json["name"]


def test_api_location_list_cached(django_app, admin_user, locations3):
    # l1, l2, l3 = locations3
    url = reverse('unicef_locations:locations-list')
    response = django_app.get(url, user=admin_user)
    assert len(response.json) == len(locations3)
    etag = response["ETag"]

    response = django_app.get(url, user=admin_user, headers=dict(IF_NONE_MATCH=etag))

    # response = self.forced_auth_req('get', reverse('locations-list'),
    #                                 user=self.unicef_staff, HTTP_IF_NONE_MATCH=etag)
    assert response.status_code == status.HTTP_304_NOT_MODIFIED


def test_api_location_list_modified(django_app, admin_user, locations3):
    url = reverse('unicef_locations:locations-list')
    response = django_app.get(url, user=admin_user)
    assert len(response.json) == len(locations3)
    etag = response["ETag"]
    LocationFactory()

    response = django_app.get(url, user=admin_user, headers=dict(IF_NONE_MATCH=etag))
    assert len(response.json) == len(locations3) + 1


def test_location_assert_etag(django_app, admin_user, locations3):
    url = reverse('unicef_locations:locations-list')
    factory = APIRequestFactory()
    request = factory.get(url)
    LocationsViewSet.as_view({'get': 'list'})(request)
    assert cache.get(conf.GET_CACHE_KEY(Request(request)))


def test_location_delete_etag(django_app, admin_user, locations3):
    url = reverse('unicef_locations:locations-list')
    factory = APIRequestFactory()
    request = factory.get(url)
    LocationsViewSet.as_view({'get': 'list'})(request)
    etag_before = cache.get(conf.GET_CACHE_KEY(Request(request)))
    get_location_model().objects.all().delete()

    LocationsViewSet.as_view({'get': 'list'})(request)
    etag_after = cache.get(conf.GET_CACHE_KEY(Request(request)))
    assert etag_before != etag_after


def test_api_location_autocomplete(django_app, admin_user, locations3):
    url = reverse('unicef_locations:locations_autocomplete')

    response = django_app.get(url, user=admin_user, params={"q": "Loc"})

    assert len(response.json) == len(locations3)
    assert sorted(response.json[0].keys()) == ['admin_level', 'admin_level_name', 'id', 'name', 'name_display',
                                               'p_code', 'parent']
    assert "Loc" in response.json[0]["name"]


def test_api_location_autocomplete_empty(django_app, admin_user, locations3):
    url = reverse('unicef_locations:locations_autocomplete')

    response = django_app.get(url, user=admin_user)

    assert len(response.json) == len(locations3)
    assert sorted(response.json[0].keys()) == ['admin_level', 'admin_level_name', 'id', 'name', 'name_display',
                                               'p_code', 'parent']
    assert "Loc" in response.json[0]["name"]


def test_cache_key_configuration():
    func = mock.Mock()
    conf.GET_CACHE_KEY = func

    # with mock.patch('test_views.test_cache_key') as cache_key:
    class Dummy:
        request = mock.Mock()

        @etag_cached('prefix')
        def test(self):
            return HttpResponse()

    Dummy().test()
    assert func.call_count == 1
