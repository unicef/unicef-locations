from django.urls import reverse

import pytest

pytestmark = pytest.mark.django_db


def test_admin_location(django_app, admin_user, locations3):
    url = reverse('admin:locations_location_changelist')
    response = django_app.get(url, user=admin_user)
    assert response


def test_admin_location_filter(django_app, admin_user, locations3):
    url = "{}?is_active=True&o=1".format(reverse('admin:locations_location_changelist'))
    response = django_app.get(url, user=admin_user)

    assert response


def test_admin_location_edit(django_app, admin_user, location):
    url = reverse('admin:locations_location_change', args=[location.id])
    response = django_app.get(url, user=admin_user)
    response = response.form.submit()
    assert response


def test_admin_cartodbtable(django_app, admin_user, cartodbtable):
    url = reverse('admin:unicef_locations_cartodbtable_changelist')
    response = django_app.get(url, user=admin_user)
    assert response


def test_admin_cartodbtable_edit(django_app, admin_user, cartodbtable):
    url = reverse('admin:unicef_locations_cartodbtable_change', args=[cartodbtable.id])
    response = django_app.get(url, user=admin_user)
    response = response.form.submit()
    assert response
