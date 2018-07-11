# -*- coding: utf-8 -*-
from django.urls import reverse
from drf_api_checker.pytest import contract, frozenfixture
from drf_api_checker.recorder import Recorder
from rest_framework.test import APIClient

from tests.demoproject.demo.factories import UserFactory


class MyRecorder(Recorder):
    @property
    def client(self):
        user = UserFactory(is_superuser=True)
        client = APIClient()
        client.force_authenticate(user)
        return client


@frozenfixture
def gateway():
    from unicef_locations.tests.factories import GatewayTypeFactory
    return GatewayTypeFactory()


@frozenfixture
def location():
    from unicef_locations.tests.factories import LocationFactory
    return LocationFactory(parent=None)


@contract(recorder_class=MyRecorder)
def test_api_locationtypes_list(django_app, admin_user, gateway):
    return reverse('locationtypes-list')


@contract(recorder_class=MyRecorder)
def test_api_location_light_list(django_app, admin_user, location):
    return reverse('locations-light-list')


@contract()
def test_api_location_list(django_app, admin_user, location):
    return reverse('locations-list')

    #
    # url = reverse('locations-light-list')
    # res = django_app.get(url, user=admin_user)
    # assert sorted(res.json[0].keys()) == ["id", "name", "p_code"]

# def test_api_location_heavy_list(django_app, admin_user, location):
#     url = reverse('locations-list')
#
#     response = django_app.get(url, user=admin_user)
#     assert sorted(response.json[0].keys()) == [
#         'geo_point', 'id', 'location_type', 'location_type_admin_level', 'name', 'p_code', 'parent'
#     ]
#
#
# def test_api_location_values(django_app, admin_user, locations3):
#     l1, l2, l3 = locations3
#     params = {"values": "{},{}".format(l1.id, l2.id)}
#     response = django_app.get(reverse('locations-list'), user=admin_user, params=params)
#     assert len(response.json) == 2, response.json
#
#
# def test_api_location_heavy_detail(django_app, admin_user, locations3):
#     l1, l2, l3 = locations3
#     url = reverse('locations-detail', args=[l1.id])
#     response = django_app.get(url, user=admin_user)
#     assert sorted(response.json.keys()), ['geo_point', 'id', 'location_type',
#                                           'location_type_admin_level', 'name',
#                                           'p_code', 'parent']
#     assert "Location" in response.json["name"]
#
#
# def test_api_location_heavy_detail_pcode(django_app, admin_user, locations3):
#     l1, l2, l3 = locations3
#     url = reverse('locations_detail_pcode', args=[l1.p_code])
#     response = django_app.get(url, user=admin_user)
#     assert sorted(response.json.keys()), ['geo_point', 'id', 'location_type',
#                                           'location_type_admin_level', 'name',
#                                           'p_code', 'parent']
#     assert "Location" in response.json["name"]
#
#
# def test_api_location_list_cached(django_app, admin_user, locations3):
#     # l1, l2, l3 = locations3
#     url = reverse('locations-list')
#     response = django_app.get(url, user=admin_user)
#     assert len(response.json) == len(locations3)
#     etag = response["ETag"]
#
#     response = django_app.get(url, user=admin_user, headers=dict(IF_NONE_MATCH=etag))
#
#     # response = self.forced_auth_req('get', reverse('locations-list'),
#     #                                 user=self.unicef_staff, HTTP_IF_NONE_MATCH=etag)
#     assert response.status_code == status.HTTP_304_NOT_MODIFIED
#
#
# def test_api_location_list_modified(django_app, admin_user, locations3):
#     url = reverse('locations-list')
#     response = django_app.get(url, user=admin_user)
#     assert len(response.json) == len(locations3)
#     etag = response["ETag"]
#
#     LocationFactory()
#
#     response = django_app.get(url, user=admin_user, headers=dict(IF_NONE_MATCH=etag))
#     assert len(response.json) == len(locations3) + 1
#
#
# def test_location_delete_etag(django_app, admin_user, locations3):
#     #         self.forced_auth_req('get', reverse('locations-list'), user=self.unicef_staff)
#     #         schema_name = connection.schema_name
#     #         etag_before = cache.get("{}-locations-etag".format(schema_name))
#     #         Location.objects.all().delete()
#     #         etag_after = cache.get("{}-locations-etag".format(schema_name))
#     #         assert etag_before != etag_after
#     url = reverse('locations-list')
#     django_app.get(url, user=admin_user)
#     etag_before = cache.get(get_cache_key())
#     Location.objects.all().delete()
#
#     django_app.get(url, user=admin_user)
#     etag_after = cache.get(get_cache_key())
#     assert etag_before != etag_after
#
#
# def test_api_location_autocomplete(django_app, admin_user, locations3):
#     url = reverse('locations:locations_autocomplete')
#
#     response = django_app.get(url, user=admin_user, params={"q": "Loc"})
#
#     assert len(response.json) == len(locations3)
#     assert sorted(response.json[0].keys()) == ["id", "name", "p_code"]
#     assert "Loc" in response.json[0]["name"]
#
#
# def test_api_location_autocomplete_empty(django_app, admin_user, locations3):
#     url = reverse('locations:locations_autocomplete')
#
#     response = django_app.get(url, user=admin_user)
#
#     assert len(response.json) == len(locations3)
#     assert sorted(response.json[0].keys()) == ["id", "name", "p_code"]
#     assert "Loc" in response.json[0]["name"]
