import json

from unittest import skip

from carto.exceptions import CartoException
from django.contrib.gis.geos import Point
from django.test import TestCase

from unittest.mock import Mock, patch

from unicef_locations.models import CartoDBTable, ArcgisDBTable, Location
from unicef_locations.tasks_cartodb import update_sites_from_cartodb
from unicef_locations.tasks_arcgis import import_arcgis_locations
from unicef_locations.task_utils import create_location, remap_location
from unicef_locations.tests.factories import CartoDBTableFactory, ArcgisDBTableFactory, LocationFactory


class TestCreateLocations(TestCase):
    def setUp(self):
        self.point = "Point(20 20)"
        self.multipolygon = "MultiPolygon(((10 10, 10 20, 20 20, 20 15, 10 10)), \
            ((10 10, 10 20, 20 20, 20 15, 10 10)))"

    def test_multiple_objects(self):
        """Multiple objects match the pcode,
        just 'no added' should increment by 1
        """
        carto = CartoDBTableFactory()
        LocationFactory(p_code="123")
        LocationFactory(p_code="123")

        success, not_added, created, updated = create_location(
            "123",
            carto,
            None,
            None,
            "test",
            None,
            0,
            0,
            0,
        )
        self.assertFalse(success)
        self.assertEqual(not_added, 1)
        self.assertEqual(created, 0)
        self.assertEqual(updated, 0)
        
    def test_exists_no_geom(self):
        """If single object exists but 'the_geom' value is not set
        then nothing happens
        """
        carto = CartoDBTableFactory()
        LocationFactory(p_code="123")

        success, not_added, created, updated = create_location(
            "123",
            carto,
            None,
            None,
            "test",
            None,
            0,
            0,
            0,
        )
        self.assertFalse(success)
        self.assertEqual(not_added, 0)
        self.assertEqual(created, 0)
        self.assertEqual(updated, 0)
        
    def test_exists_point(self):
        """If single object exists and 'the_geom' value is Point
        then update point value

        Name is also updated
        """
        carto = CartoDBTableFactory()
        location = LocationFactory(p_code="123", point=None)
        site_name = "test"
        self.assertIsNone(location.point)
        self.assertNotEqual(location.name, site_name)

        success, not_added, created, updated = create_location(
            "123",
            carto,
            None,
            None,
            site_name,
            self.point,
            0,
            0,
            0,
        )
        self.assertTrue(success)
        self.assertEqual(not_added, 0)
        self.assertEqual(created, 0)
        self.assertEqual(updated, 1)
        location_updated = Location.objects.get(pk=location.pk)
        self.assertIsNotNone(location_updated.point)
        self.assertEqual(location_updated.name, site_name)

    def test_exists_geom(self):
        """If single object exists and 'the_geom' value is NOT Point
        then update geom value

        Name is also updated
        """
        carto = CartoDBTableFactory()
        location = LocationFactory(p_code="123", geom=None)
        site_name = "test"
        self.assertIsNone(location.geom)
        self.assertNotEqual(location.name, site_name)

        success, not_added, created, updated = create_location(
            "123",
            carto,
            None,
            None,
            "test",
            self.multipolygon,
            0,
            0,
            0,
        )
        self.assertTrue(success)
        self.assertEqual(not_added, 0)
        self.assertEqual(created, 0)
        self.assertEqual(updated, 1)
        location_updated = Location.objects.get(pk=location.pk)
        self.assertIsNotNone(location_updated.geom)
        self.assertEqual(location_updated.name, site_name)

    def test_new_point(self):
        """If location does NOT exist then create it
        and if 'the_geom' has 'Point' then set point value
        """
        carto = CartoDBTableFactory()
        self.assertFalse(Location.objects.filter(p_code="123").exists())
        name = "Test"

        success, not_added, created, updated = create_location(
            "123",
            carto,
            None,
            None,
            name,
            self.point,
            0,
            0,
            0,
        )
        self.assertTrue(success)
        self.assertEqual(not_added, 0)
        self.assertEqual(created, 1)
        self.assertEqual(updated, 0)
        location = Location.objects.get(p_code="123")
        self.assertIsNotNone(location.point)
        self.assertIsNone(location.geom)
        self.assertEqual(location.name, name)

    def test_new_geom(self):
        """If location does NOT exist then create it
        and if 'the_geom' has 'Point' then set geom value
        """
        carto = CartoDBTableFactory()
        self.assertFalse(Location.objects.filter(p_code="123").exists())
        name = "Test"

        success, not_added, created, updated = create_location(
            "123",
            carto,
            None,
            None,
            name,
            self.multipolygon,
            0,
            0,
            0,
        )
        self.assertTrue(success)
        self.assertEqual(not_added, 0)
        self.assertEqual(created, 1)
        self.assertEqual(updated, 0)
        location = Location.objects.get(p_code="123")
        self.assertIsNone(location.point)
        self.assertIsNotNone(location.geom)
        self.assertEqual(location.name, name)

    def test_new_parent(self):
        """If location does NOT exist then create it
        and if parent instance provided, set parent value as well
        """
        carto = CartoDBTableFactory()
        parent = LocationFactory(p_code="321")
        self.assertFalse(Location.objects.filter(p_code="123").exists())
        name = "Test"

        success, not_added, created, updated = create_location(
            "123",
            carto,
            True,
            parent,
            name,
            self.point,
            0,
            0,
            0,
        )
        self.assertTrue(success)
        self.assertEqual(not_added, 0)
        self.assertEqual(created, 1)
        self.assertEqual(updated, 0)
        location = Location.objects.get(p_code="123")
        self.assertIsNotNone(location.point)
        self.assertIsNone(location.geom)
        self.assertEqual(location.name, name)
        self.assertEqual(location.parent, parent)

    def test_update_parent(self):
        """If location does exist then update it
        and if parent instance provided, set parent value as well
        """
        carto = CartoDBTableFactory()
        parent1 = LocationFactory(p_code="p1")
        location = LocationFactory(p_code="123", parent=parent1)

        parent2 = LocationFactory(p_code="p2")
        name = "Test"

        self.assertEqual(location.parent, parent1)
        success, not_added, created, updated = create_location(
            "123",
            carto,
            True,
            parent2,
            name,
            self.point,
            0,
            0,
            0,
        )
        self.assertTrue(success)
        self.assertEqual(not_added, 0)
        self.assertEqual(created, 0)
        self.assertEqual(updated, 1)
        location = Location.objects.get(p_code="123")
        self.assertIsNotNone(location.point)
        self.assertIsNone(location.geom)
        self.assertEqual(location.name, name)
        self.assertEqual(location.parent, parent2)

    # TODO: extra remap test cases
    def test_remap(self):
        """If location does exist then update it
        and if parent instance provided, set parent value as well
        """
        remapped_pcode_1 = "remap_123"
        remapped_pcode_2 = "remap_321"
        carto = CartoDBTableFactory()
        remapped_location_1 = LocationFactory(p_code=remapped_pcode_1)
        remapped_location_2 = LocationFactory(p_code=remapped_pcode_2)
        remapped_pcodes = set()
        remapped_pcodes.add(remapped_location_1.p_code)
        remapped_pcodes.add(remapped_location_2.p_code)

        name = "Test"

        self.assertTrue(remapped_location_1.is_active)
        self.assertTrue(remapped_location_2.is_active)

        p_code = "123"
        remapped_location_id_pairs = remap_location(carto, p_code, [remapped_pcode_1, remapped_pcode_2])
        success, not_added, created, updated = create_location(
            p_code,
            carto,
            True,
            None,
            name,
            self.point,
            0,
            0,
            0,
        )
        self.assertTrue(success)
        self.assertEqual(not_added, 0)
        self.assertEqual(created, 0)
        self.assertEqual(updated, 1)
        location = Location.objects.get(p_code=p_code)
        self.assertIsNotNone(location.point)
        self.assertIsNone(location.geom)
        self.assertEqual(location.name, name)

        remapped_location_1 = Location.objects.all_locations().get(p_code=remapped_pcode_1)
        remapped_location_2 = Location.objects.all_locations().get(p_code=remapped_pcode_2)
        self.assertFalse(remapped_location_1.is_active)
        self.assertFalse(remapped_location_2.is_active)
        self.assertListEqual(
            list(remapped_location_id_pairs),
            [(location.id, remapped_location_1.id), (location.id, remapped_location_2.id)]
        )


class TestUpdateSitesFromCartoDB(TestCase):
    def setUp(self):
        super(TestUpdateSitesFromCartoDB, self).setUp()
        self.mock_sql = Mock()

    def _run_update(self, carto_table_pk):
        with patch("unicef_locations.tasks_cartodb.SQLClient.send", self.mock_sql):
            return update_sites_from_cartodb(carto_table_pk)

    def _assert_response(self, response, expected_result):
        self.assertEqual(response, expected_result)

    def test_not_exist(self):
        """Test that when carto record does not exist, nothing happens"""
        self.assertFalse(CartoDBTable.objects.filter(pk=404).exists())
        self.assertFalse(update_sites_from_cartodb(404))

    def test_sql_client_error(self):
        """Check that a CartoException on SQLClient.send
        is handled gracefully
        """
        self.mock_sql.side_effect = CartoException
        carto = CartoDBTableFactory()
        self._run_update(carto.pk)
        # TODO: maybe test logs for errors
        # self._assert_response(response, None)

    def test_add(self):
        """Check that rows returned by SQLClient create a location record"""
        self.mock_sql.return_value = {"rows": [{
            "the_geom": "Point(20 20)",
            "name": "New Location",
            "pcode": "123",
            "max": 1,
            "count": 1,
        }]}
        carto = CartoDBTableFactory()
        self.assertFalse(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )
        response = self._run_update(carto.pk)

        location = Location.objects.get(name="New Location", p_code="123")
        self.assertIsNotNone(location)
        self._assert_response(response, None)

    def test_no_name(self):
        """Check that if name provided is just a space
        that a location record is NOT created
        """
        self.mock_sql.return_value = {"rows": [{
            "the_geom": "Point(20 20)",
            "name": " ",
            "pcode": "123",
            "max": 1,
            "count": 1,
        }]}
        carto = CartoDBTableFactory()
        self.assertFalse(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )
        response = self._run_update(carto.pk)
        self._assert_response(response, None)
        self.assertFalse(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )

    def test_add_with_parent(self):
        """Check that if parent is provided that record is created with parent
        """
        carto_parent = CartoDBTableFactory()
        parent = LocationFactory(p_code="456")
        self.mock_sql.return_value = {"rows": [{
            "the_geom": "Point(20 20)",
            "name": "New Location",
            "pcode": "123",
            "parent": "456",
            "max": 1,
            "count": 1,
        }]}
        carto = CartoDBTableFactory(
            parent=carto_parent,
            parent_code_col="parent",
        )
        self.assertFalse(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )
        response = self._run_update(carto.pk)
        location = Location.objects.get(name="New Location", p_code="123")
        self.assertIsNotNone(location)
        self._assert_response(response, None)
        self.assertEqual(location.parent, parent)

    def test_add_parent_multiple(self):
        """Check that if parent is provided but multiple locations match parent
        that location record is NOT created
        """
        carto_parent = CartoDBTableFactory()
        LocationFactory(p_code="456")
        LocationFactory(p_code="456")
        self.mock_sql.return_value = {"rows": [{
            "the_geom": "Point(20 20)",
            "name": "New Location",
            "pcode": "123",
            "parent": "456",
            "max": 1,
            "count": 1,
        }]}
        carto = CartoDBTableFactory(
            parent=carto_parent,
            parent_code_col="parent",
        )
        self.assertFalse(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )
        response = self._run_update(carto.pk)
        self._assert_response(response, None)
        self.assertFalse(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )

    def test_add_parent_invalid(self):
        """Check that if parent is provided but does not exist
        that location record is NOT created
        """
        carto_parent = CartoDBTableFactory()
        LocationFactory(p_code="456")
        self.mock_sql.return_value = {"rows": [{
            "the_geom": "Point(20 20)",
            "name": "New Location",
            "pcode": "123",
            "parent": "654",
            "max": 1,
            "count": 1,
        }]}
        carto = CartoDBTableFactory(
            parent=carto_parent,
            parent_code_col="parent"
        )
        self.assertFalse(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )
        response = self._run_update(carto.pk)
        self._assert_response(response, None)
        self.assertFalse(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )

    def test_duplicate_db_pcodes(self):
        """ Check if unallowed duplicate local pcodes exist"""
        self.mock_sql.return_value = {"rows": [{
            "the_geom": "Point(20 20)",
            "name": "New Location",
            "pcode": "123",
            "parent": "654",
            "max": 1,
            "count": 1,
        }]}
        carto = CartoDBTableFactory(
            parent_code_col="parent"
        )
        LocationFactory(p_code="123", gateway=carto.location_type).save()
        LocationFactory(p_code="123", gateway=carto.location_type).save()
        response = self._run_update(carto.pk)
        self._assert_response(response, None)

    def test_remap_table_invalid(self):
        """ """
        self.mock_sql.return_value = {"rows": [{
            "the_geom": "Point(20 20)",
            "name": "New Location",
            "pcode": "123",
            "max": 1,
            "count": 1,
        }]}
        carto = CartoDBTableFactory(
            remap_table_name="test_rmp",
        )

        LocationFactory(p_code="123", gateway=carto.location_type)
        response = self._run_update(carto.pk)
        # TODO: rewrite it to throw an exception?
        self._assert_response(response, None)


class TestUpdateSitesFromArcgis(TestCase):
    def setUp(self):
        super(TestUpdateSitesFromArcgis, self).setUp()
        self.mock_results = Mock()
        self.features = [{
            "properties": {
                "name": "New Location",
                "pcode": "123",
                "parent": "12",
            },
            "geometry": {
                "type": "Point", # Point | Polygon
                "coordinates": (20, 20)
            },
        }]
        self.mock_results.return_value = {"features": self.features}
        self.mock_results.__str__ = self.mock_results
        self.mock_results.__str__.return_value = json.dumps({"features": self.features})

    def _run_update(self, arcgis_table_pk):
        with patch("unicef_locations.tasks_arcgis.FeatureLayer") ,\
                patch("unicef_locations.tasks_arcgis.FeatureSet.to_geojson", self.mock_results):
            return import_arcgis_locations(arcgis_table_pk)

    def _assert_response(self, response, expected_result):
        self.assertEqual(response, expected_result)

    def test_not_exist(self):
        self.assertFalse(ArcgisDBTable.objects.filter(pk=404).exists())
        self.assertFalse(import_arcgis_locations(404))

    def test_add(self):
        ag_parent = ArcgisDBTableFactory()
        arcgisdbtable = ArcgisDBTableFactory(
            parent=ag_parent,
            parent_code_col="parent"
        )
        self.assertFalse(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )

        LocationFactory(p_code="12")
        response = self._run_update(arcgisdbtable.pk)
        location = Location.objects.get(name="New Location", p_code="123")
        response = self._run_update(arcgisdbtable.pk)

        self.assertIsNotNone(location)
        self._assert_response(response, None)

    def test_add_parent_multiple(self):
        """Check for disallowed multiple parent locations"""
        ag_parent = ArcgisDBTableFactory()
        LocationFactory(p_code="12")
        LocationFactory(p_code="12")
        arcgisdbtable = ArcgisDBTableFactory(
            parent=ag_parent,
            parent_code_col="parent",
        )
        self.assertFalse(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )
        response = self._run_update(arcgisdbtable.pk)
        self._assert_response(response, None)
        #TODO: probably we should check the logs instead for the warning message
        self.assertFalse(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )

    def test_add_parent_invalid(self):
        """Check that if parent is provided but does not exist
        that location record is NOT created
        """
        ag_parent = ArcgisDBTableFactory()
        LocationFactory(p_code="456")
        arcgisdbtable = ArcgisDBTableFactory(
            parent=ag_parent,
            parent_code_col="parent"
        )
        self.assertFalse(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )
        response = self._run_update(arcgisdbtable.pk)
        self._assert_response(response, None)
        #TODO: probably we should check the logs instead for the warning message
        self.assertFalse(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )

    def test_remap(self):
        pass
