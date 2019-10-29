import pytest
from unittest import mock

try:
    from django.urls import reverse
except ImportError:
    # TODO: remove when django<2.0 will be unsupported
    from django.core.urlresolvers import reverse

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
    url = reverse('admin:locations_cartodbtable_changelist')
    response = django_app.get(url, user=admin_user)
    assert response


def test_admin_cartodbtable_action(django_app, admin_user, cartodbtable):
    url = reverse('admin:locations_cartodbtable_changelist')

    with mock.patch('unicef_locations.admin.update_sites_from_cartodb'):
        res = django_app.get(url, user=admin_user)
        res.form['action'] = 'import_sites'
        res.form['_selected_action'].checked = True
        res = res.form.submit().follow()
        assert res


def test_admin_cartodbtable_edit(django_app, admin_user, cartodbtable):
    url = reverse('admin:locations_cartodbtable_change', args=[cartodbtable.id])
    response = django_app.get(url, user=admin_user)
    response = response.form.submit()
    assert response


def test_admin_arcgisdbtable(django_app, admin_user, arcgisdbtable):
    url = reverse('admin:locations_arcgisdbtable_changelist')
    response = django_app.get(url, user=admin_user)
    assert response


def test_admin_arcgisdbtable_action(django_app, admin_user, arcgisdbtable):
    url = reverse('admin:locations_arcgisdbtable_changelist')

    with mock.patch('unicef_locations.admin.import_arcgis_locations'):
        res = django_app.get(url, user=admin_user)
        res.form['action'] = 'import_sites'
        res.form['_selected_action'].checked = True
        res = res.form.submit().follow()
        assert res


def test_admin_arcgisdbtable_edit(django_app, admin_user, arcgisdbtable):
    url = reverse('admin:locations_arcgisdbtable_change', args=[arcgisdbtable.id])
    response = django_app.get(url, user=admin_user)
    response = response.form.submit()
    assert response
