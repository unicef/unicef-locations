from carto.exceptions import CartoException
from django.test import TestCase
from django.core.exceptions import ValidationError

from unittest.mock import Mock, patch

from unicef_locations import forms
from unicef_locations.tests.factories import GatewayTypeFactory


class TestCartoDBTableForm(TestCase):
    def setUp(self):
        super(TestCartoDBTableForm, self).setUp()
        self.mock_sql = Mock()
        gateway = GatewayTypeFactory()
        self.data = {
            "api_key": "123",
            "domain": "example.com",
            "table_name": "test",
            "name_col": "name",
            "pcode_col": "pcode",
            "parent_code_col": "parent",
            "remap_table_name": "test_remap",
            "location_type": gateway.pk,
        }

    def _test_clean(self, form):
        with patch("unicef_locations.forms.SQLClient.send", self.mock_sql):
            return form.is_valid()

    def test_no_connection(self):
        """Check that validation fails when SQLClient request fails"""
        self.mock_sql.side_effect = CartoException
        form = forms.CartoDBTableForm(self.data)
        self.assertFalse(self._test_clean(form))
        errors = form.errors.as_data()
        self.assertEqual(len(errors["__all__"]), 1)
        self.assertEqual(
            errors["__all__"][0].message,
            "Couldn't connect to CartoDB table: test"
        )

    def test_no_name_col(self):
        """Check that validation fails when `name_col` is missing"""
        self.mock_sql.return_value = {"rows": [{
            "pcode": "",
            "parent": "",
        }]}
        form = forms.CartoDBTableForm(self.data)
        self.assertFalse(self._test_clean(form))
        errors = form.errors.as_data()
        self.assertEqual(len(errors["__all__"]), 1)
        self.assertEqual(
            errors["__all__"][0].message,
            "The Name column (name) is not in table: test"
        )

    def test_no_pcode_col(self):
        """Check that validation fails when `pcode_col` is missing"""
        self.mock_sql.return_value = {"rows": [{
            "name": "",
            "parent": "",
        }]}
        form = forms.CartoDBTableForm(self.data)
        self.assertFalse(self._test_clean(form))
        errors = form.errors.as_data()
        self.assertEqual(len(errors["__all__"]), 1)
        self.assertEqual(
            errors["__all__"][0].message,
            "The PCode column (pcode) is not in table: test"
        )

    def test_no_parent_code_col(self):
        """Check that validation fails when `parent_code_col` is missing"""
        self.mock_sql.return_value = {"rows": [{
            "name": "",
            "pcode": "",
        }]}
        form = forms.CartoDBTableForm(self.data)
        self.assertFalse(self._test_clean(form))
        errors = form.errors.as_data()
        self.assertEqual(len(errors["__all__"]), 1)
        self.assertEqual(
            errors["__all__"][0].message,
            "The Parent Code column (parent) is not in table: test"
        )

    def test_no_remap_table(self):
        """Check validation when there is no `remap_table`"""
        self.data["remap_table_name"] = ""
        self.mock_sql.return_value = {"rows": [{
            "name": "",
            "pcode": "",
            "parent": "",
        }]}

        form = forms.CartoDBTableForm(self.data)
        self.assertTrue(self._test_clean(form))

    def test_remap_table_no_old_pcode(self):
        """Check that validation fails when there is no `old_pcode` in the `remap_table`"""
        self.mock_sql.return_value = {"rows": [{
            "name": "",
            "pcode": "",
            "parent": "",
            "new_pcode": "",
        }]}

        form = forms.CartoDBTableForm(self.data)
        self.assertFalse(self._test_clean(form))
        errors = form.errors.as_data()
        self.assertEqual(len(errors["__all__"]), 1)
        self.assertEqual(
            errors["__all__"][0].message,
            "The Old PCode column (old_pcode) is not in table: test_remap"
        )

    def test_remap_table_no_new_pcode(self):
        """Check that validation fails when there is no `new_pcode` in the `remap_table`"""
        self.mock_sql.return_value = {"rows": [{
            "name": "",
            "pcode": "",
            "parent": "",
            "old_pcode": "",
        }]}

        form = forms.CartoDBTableForm(self.data)
        self.assertFalse(self._test_clean(form))
        errors = form.errors.as_data()
        self.assertEqual(len(errors["__all__"]), 1)
        self.assertEqual(
            errors["__all__"][0].message,
            "The New PCode column (new_pcode) is not in table: test_remap"
        )

    def test_clean(self):
        """Check that validation passes"""
        self.mock_sql.return_value = {"rows": [{
            "name": "",
            "pcode": "",
            "parent": "",
            "old_pcode": "",
            "new_pcode": "",
        }]}
        form = forms.CartoDBTableForm(self.data)
        self.assertTrue(self._test_clean(form))
        self.assertEqual(form.errors.as_data(), {})




class TestArcgisTableForm(TestCase):
    def setUp(self):
        super(TestArcgisTableForm, self).setUp()
        self.mock_response = Mock()
        gateway = GatewayTypeFactory()
        self.data = {
            "service_name": "test",
            "service_url": "test://test.test",
            "remap_table_service_url": "test://test_remap.test",
            "name_col": "name",
            "pcode_col": "pcode",
            "parent_code_col": "parent",
            "location_type": gateway.pk,
        }
        self.feature = {
            "properties": {
                "name": "New Location",
                "pcode": "123",
                "parent": "12",
            },
            "geometry": {
                "type": "Point", # Point | Polygon
                "coordinates": (20, 20)
            },
        }
        self.remap_table = [{
            "old_pcode": "op",
            "new_pcode": "np",
        }]

    def _test_clean(self, form):
        with patch("unicef_locations.forms.FeatureLayer", self.mock_response):
            return form.is_valid()

    def test_no_connection(self):
        """Check that validation fails when the arcgis dataset doesn't load"""
        self.data['remap_table_service_url'] = ''
        self.mock_response.side_effect = RuntimeError
        form = forms.ArcgisDBTableForm(self.data)
        self.assertFalse(self._test_clean(form))
        errors = form.errors.as_data()
        self.assertEqual(len(errors["__all__"]), 1)
        self.assertEqual(
            errors["__all__"][0].message,
            'Cannot load Arcgis dataset from: {}'.format(self.data['service_url'])
        )

    def test_remap_table_conn_err(self):
        self.mock_response.side_effect = RuntimeError
        form = forms.ArcgisDBTableForm(self.data)
        self.assertFalse(self._test_clean(form))
        errors = form.errors.as_data()
        self.assertEqual(len(errors["__all__"]), 1)
        self.assertEqual(
            errors["__all__"][0].message,
            'Cannot load Arcgis remap table from: {}'.format(self.data['remap_table_service_url'])
        )

    def test_no_name_col(self):
        """Check that validation fails when `name_col` is missing"""
        self.data['remap_table_service_url'] = ''
        del(self.feature["properties"]["name"])
        with patch("unicef_locations.forms.FeatureSet.to_geojson", Mock()):
            self.mock_response.return_value = self.data
            form = forms.ArcgisDBTableForm(self.data)
            self.assertFalse(self._test_clean(form))
            errors = form.errors.as_data()
            self.assertEqual(len(errors["__all__"]), 1)
            self.assertEqual(
                errors["__all__"][0].message,
                "The Name column (name) is not in table: test"
            )

    '''
    def test_no_pcode_col(self):
        """Check that validation fails when `pcode_col` is missing"""
        self.mock_sql.return_value = {"rows": [{
            "name": "",
            "parent": "",
        }]}
        form = forms.CartoDBTableForm(self.data)
        self.assertFalse(self._test_clean(form))
        errors = form.errors.as_data()
        self.assertEqual(len(errors["__all__"]), 1)
        self.assertEqual(
            errors["__all__"][0].message,
            "The PCode column (pcode) is not in table: test"
        )

    def test_no_parent_code_col(self):
        """Check that validation fails when `parent_code_col` is missing"""
        self.mock_sql.return_value = {"rows": [{
            "name": "",
            "pcode": "",
        }]}
        form = forms.CartoDBTableForm(self.data)
        self.assertFalse(self._test_clean(form))
        errors = form.errors.as_data()
        self.assertEqual(len(errors["__all__"]), 1)
        self.assertEqual(
            errors["__all__"][0].message,
            "The Parent Code column (parent) is not in table: test"
        )

    def test_no_remap_table(self):
        """Check validation when there is no `remap_table`"""
        self.data["remap_table_name"] = ""
        self.mock_sql.return_value = {"rows": [{
            "name": "",
            "pcode": "",
            "parent": "",
        }]}

        form = forms.CartoDBTableForm(self.data)
        self.assertTrue(self._test_clean(form))

    def test_remap_table_no_old_pcode(self):
        """Check that validation fails when there is no `old_pcode` in the `remap_table`"""
        self.mock_sql.return_value = {"rows": [{
            "name": "",
            "pcode": "",
            "parent": "",
            "new_pcode": "",
        }]}

        form = forms.CartoDBTableForm(self.data)
        self.assertFalse(self._test_clean(form))
        errors = form.errors.as_data()
        self.assertEqual(len(errors["__all__"]), 1)
        self.assertEqual(
            errors["__all__"][0].message,
            "The Old PCode column (old_pcode) is not in table: test_remap"
        )

    def test_remap_table_no_new_pcode(self):
        """Check that validation fails when there is no `new_pcode` in the `remap_table`"""
        self.mock_sql.return_value = {"rows": [{
            "name": "",
            "pcode": "",
            "parent": "",
            "old_pcode": "",
        }]}

        form = forms.CartoDBTableForm(self.data)
        self.assertFalse(self._test_clean(form))
        errors = form.errors.as_data()
        self.assertEqual(len(errors["__all__"]), 1)
        self.assertEqual(
            errors["__all__"][0].message,
            "The New PCode column (new_pcode) is not in table: test_remap"
        )

    def test_clean(self):
        """Check that validation passes"""
        self.mock_sql.return_value = {"rows": [{
            "name": "",
            "pcode": "",
            "parent": "",
            "old_pcode": "",
            "new_pcode": "",
        }]}
        form = forms.CartoDBTableForm(self.data)
        self.assertTrue(self._test_clean(form))
        self.assertEqual(form.errors.as_data(), {})
    '''
