import pytest
from django.core.cache import cache
from django.core.urlresolvers import reverse

from rest_framework import status
from unicef_locations.models import Location, get_cache_key
from unicef_locations.tests.factories import LocationFactory

pytestmark = pytest.mark.django_db


def assert_heavy_detail_view_fundamentals(response):
    '''Utility function that collects common assertions for heavy detail tests'''

    assert sorted(response.json.keys()), [
        'geo_point', 'id', 'location_type', 'location_type_admin_level', 'name', 'p_code', 'parent'
    ]
    assert "Location" in response.json["name"]


def test_api_locationtypes_list(django_app, admin_user):
    url = reverse('locationtypes-list')
    res = django_app.get(url, user=admin_user)
    assert res.status_code == 200


def test_api_location_light_list(django_app, admin_user, locations3):
    url = reverse('locations-light-list')
    res = django_app.get(url, user=admin_user)
    assert sorted(res.json[0].keys()) == ["id", "name", "p_code"]


def test_api_location_heavy_list(django_app, admin_user, location):
    url = reverse('locations-list')

    response = django_app.get(url, user=admin_user)
    assert sorted(response.json[0].keys()) == [
        'geo_point', 'id', 'location_type', 'location_type_admin_level', 'name', 'p_code', 'parent'
    ]


def test_api_location_values(django_app, admin_user, locations3):
    l1, l2, l3 = locations3
    params = {"values": "{},{}".format(l1.id, l2.id)}
    response = django_app.get(reverse('locations-list'), user=admin_user, params=params)
    assert len(response.json) == 2, response.json


def test_api_location_heavy_detail(django_app, admin_user, locations3):
    l1, l2, l3 = locations3
    url = reverse('locations-detail', args=[l1.id])
    response = django_app.get(url, user=admin_user)
    assert_heavy_detail_view_fundamentals(response)


def test_api_location_heavy_detail_pcode(django_app, admin_user, locations3):
    l1, l2, l3 = locations3
    url = reverse('locations_detail_pcode', args=[l1.p_code])
    response = django_app.get(url, user=admin_user)
    assert_heavy_detail_view_fundamentals(response)


def test_api_location_list_cached(django_app, admin_user, locations3):
    # l1, l2, l3 = locations3
    url = reverse('locations-list')
    response = django_app.get(url, user=admin_user)
    assert len(response.json) == len(locations3)
    etag = response["ETag"]

    response = django_app.get(url, user=admin_user, headers=dict(IF_NONE_MATCH=etag))

    # response = self.forced_auth_req('get', reverse('locations-list'),
    #                                 user=self.unicef_staff, HTTP_IF_NONE_MATCH=etag)
    assert response.status_code == status.HTTP_304_NOT_MODIFIED


def test_api_location_list_modified(django_app, admin_user, locations3):
    url = reverse('locations-list')
    response = django_app.get(url, user=admin_user)
    assert len(response.json) == len(locations3)
    etag = response["ETag"]

    LocationFactory()

    response = django_app.get(url, user=admin_user, headers=dict(IF_NONE_MATCH=etag))
    assert len(response.json) == len(locations3) + 1


def test_location_delete_etag(django_app, admin_user, locations3):
    #         self.forced_auth_req('get', reverse('locations-list'), user=self.unicef_staff)
    #         schema_name = connection.schema_name
    #         etag_before = cache.get("{}-locations-etag".format(schema_name))
    #         Location.objects.all().delete()
    #         etag_after = cache.get("{}-locations-etag".format(schema_name))
    #         assert etag_before != etag_after
    url = reverse('locations-list')
    django_app.get(url, user=admin_user)
    etag_before = cache.get(get_cache_key())
    Location.objects.all().delete()

    django_app.get(url, user=admin_user)
    etag_after = cache.get(get_cache_key())
    assert etag_before != etag_after


def test_api_location_autocomplete(django_app, admin_user, locations3):
    url = reverse('locations:locations_autocomplete')

    response = django_app.get(url, user=admin_user, params={"q": "Loc"})

    assert len(response.json) == len(locations3)
    assert sorted(response.json[0].keys()) == ["id", "name", "p_code"]
    assert "Loc" in response.json[0]["name"]


def test_api_location_autocomplete_empty(django_app, admin_user, locations3):
    url = reverse('locations:locations_autocomplete')

    response = django_app.get(url, user=admin_user)

    assert len(response.json) == len(locations3)
    assert sorted(response.json[0].keys()) == ["id", "name", "p_code"]
    assert "Loc" in response.json[0]["name"]


#
# class TestLocationViews(TestCase):
#     @classmethod
#     def setUpTestData(cls):
#         cls.unicef_staff = UserFactory(is_staff=True)
#         cls.locations = [LocationFactory() for x in range(5)]
#         # heavy_detail_expected_keys are the keys that should be in response.data.keys()
#         cls.heavy_detail_expected_keys = sorted(
#             ('id', 'name', 'p_code', 'location_type', 'location_type_admin_level', 'parent', 'geo_point')
#         )
#
#     def test_api_locationtypes_list(self):
#         response = self.forced_auth_req('get', reverse('locationtypes-list'), user=self.unicef_staff)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_api_location_light_list(self):
#         response = self.forced_auth_req('get', reverse('locations-light-list'), user=self.unicef_staff)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(sorted(response.data[0].keys()), ["id", "name", "p_code"])
#         # sort the expected locations by name, the same way the API results are sorted
#         self.locations.sort(key=lambda location: location.name)
#         self.assertEqual(response.data[0]["name"], '{} [{} - {}]'.format(
#             self.locations[0].name, self.locations[0].gateway.name, self.locations[0].p_code))
#
#     def test_api_location_heavy_list(self):
#         response = self.forced_auth_req('get', reverse('locations-list'), user=self.unicef_staff)
#
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(sorted(response.data[0].keys()), self.heavy_detail_expected_keys)
#         self.assertIn("Location", response.data[0]["name"])
#
#     def test_api_location_values(self):
#         params = {"values": "{},{}".format(self.locations[0].id, self.locations[1].id)}
#         response = self.forced_auth_req(
#             'get',
#             reverse('locations-list'),
#             user=self.unicef_staff,
#             data=params
#         )
#
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response.data), 2)
#
#     def _assert_heavy_detail_view_fundamentals(self, response):
#         '''Utility function that collects common assertions for heavy detail tests'''
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(sorted(response.data.keys()), self.heavy_detail_expected_keys)
#         self.assertIn("Location", response.data["name"])
#
#     def test_api_location_heavy_detail(self):
#         url = reverse('locations-detail', args=[self.locations[0].id])
#         response = self.forced_auth_req('get', url, user=self.unicef_staff)
#         self._assert_heavy_detail_view_fundamentals(response)
#
#     def test_api_location_heavy_detail_pk(self):
#         url = reverse('locations-detail', args=[self.locations[0].id])
#         response = self.forced_auth_req('get', url, user=self.unicef_staff)
#         self._assert_heavy_detail_view_fundamentals(response)
#
#     def test_api_location_heavy_detail_pcode(self):
#         url = reverse('locations_detail_pcode', args=[self.locations[0].p_code])
#         response = self.forced_auth_req('get', url, user=self.unicef_staff)
#         self._assert_heavy_detail_view_fundamentals(response)
#
#     def test_api_location_list_cached(self):
#         response = self.forced_auth_req('get', reverse('locations-list'), user=self.unicef_staff)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response.data), 5)
#         etag = response["ETag"]
#
#         response = self.forced_auth_req('get', reverse('locations-list'),
#                                         user=self.unicef_staff, HTTP_IF_NONE_MATCH=etag)
#         self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)
#
#     def test_api_location_list_modified(self):
#         response = self.forced_auth_req('get', reverse('locations-list'), user=self.unicef_staff)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response.data), 5)
#         etag = response["ETag"]
#
#         LocationFactory()
#
#         response = self.forced_auth_req('get', reverse('locations-list'),
#                                         user=self.unicef_staff, HTTP_IF_NONE_MATCH=etag)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response.data), 6)
#
#     def test_location_delete_etag(self):
#         # Activate cache-aside with a request.
#         self.forced_auth_req('get', reverse('locations-list'), user=self.unicef_staff)
#         schema_name = connection.schema_name
#         etag_before = cache.get("{}-locations-etag".format(schema_name))
#         Location.objects.all().delete()
#         etag_after = cache.get("{}-locations-etag".format(schema_name))
#         assert etag_before != etag_after
#
#     def test_api_location_autocomplete(self):
#         response = self.forced_auth_req('get', reverse('locations:locations_autocomplete'),
#                                         user=self.unicef_staff, data={"q": "Loc"})
#
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response.data), 5)
#         self.assertEqual(sorted(response.data[0].keys()), ["id", "name", "p_code"])
#         self.assertIn("Loc", response.data[0]["name"])
#
#
# class TestLocationAutocompleteView(TestCase):
#     def setUp(self):
#         super(TestLocationAutocompleteView, self).setUp()
#         self.unicef_staff = UserFactory(is_staff=True, username='TestLocationAutocompleteView')
#         self.client = TenantClient(self.tenant)
#
#     def test_non_auth(self):
#         LocationFactory()
#         response = self.client.get(reverse("locations:locations-autocomplete-light"))
#         self.assertEqual(response.status_code, status.HTTP_302_FOUND)
#
#     def test_get(self):
#         LocationFactory()
#         self.client.force_login(self.unicef_staff)
#         response = self.client.get(reverse("locations:locations-autocomplete-light"))
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         data = response.json()
#         self.assertEqual(len(data["results"]), 1)
#
#     def test_get_filter(self):
#         LocationFactory(name="Test")
#         LocationFactory(name="Other")
#         self.client.force_login(self.unicef_staff)
#         response = self.client.get("{}?q=te".format(
#             reverse("locations:locations-autocomplete-light")
#         ))
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         data = response.json()
#         self.assertEqual(len(data["results"]), 1)

# def test_non_auth(django_app):
#     url = reverse("locations:locations-autocomplete-light")
#     response = django_app.get(url)
#     assert response.status_code == status.HTTP_302_FOUND
#


def test_get(django_app, admin_user, location):
    url = reverse("locations:locations-autocomplete-light")
    response = django_app.get(url, user=admin_user)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json["results"]) == 1


def test_get_filter(django_app, admin_user, locations3):
    l1, l2, l3 = locations3
    url = reverse("locations:locations-autocomplete-light")
    response = django_app.get(f"{url}?q={l1.name}", user=admin_user)
    assert len(response.json["results"]) == 1, response.json


def test_get_filter_empty(django_app, locations3):
    l1, l2, l3 = locations3
    url = reverse("locations:locations-autocomplete-light")
    response = django_app.get(url)
    assert response
