"""Integration tests for the location activity collector and recorder."""

import unittest
import uuid

from ...collectors.location_collector import LocationActivityCollector
from ...ner.entity_manager import NamedEntityManager
from ...recorders.location_recorder import LocationActivityRecorder


class TestLocationIntegration(unittest.TestCase):
    """Integration tests for location collector and recorder."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for all tests."""
        # Create an entity manager
        cls.entity_manager = NamedEntityManager()

        # Create a collector
        cls.collector = LocationActivityCollector(entity_manager=cls.entity_manager)

        # Create a recorder
        cls.recorder = LocationActivityRecorder()

    def setUp(self):
        """Set up for each test."""
        # Clean up any existing test data
        self.recorder.delete_all()

    def test_collect_and_record_single(self):
        """Test collecting and recording a single location activity."""
        # Collect a location activity
        activity_dict = self.collector.collect()

        # Record the activity
        success = self.recorder.record(activity_dict)

        # Verify recording was successful
        self.assertTrue(success)

        # Verify the record count is 1
        count = self.recorder.count_records()
        self.assertEqual(count, 1)

    def test_collect_and_record_batch(self):
        """Test collecting and recording a batch of location activities."""
        # Collect a batch of 5 activities
        batch = self.collector.generate_batch(5)

        # Record the batch
        success = self.recorder.record_batch(batch)

        # Verify recording was successful
        self.assertTrue(success)

        # Verify the record count is 5
        count = self.recorder.count_records()
        self.assertEqual(count, 5)

    def test_truth_data_recording(self):
        """Test recording truth data for a query."""
        # Generate a query ID
        query_id = uuid.uuid4()

        # Generate truth data for a query
        query = "Find files I accessed while at the Coffee Shop"
        entity_ids = self.collector.generate_truth_data(query)

        # Record the truth data
        success = self.recorder.record_truth_data(query_id, entity_ids)

        # Verify recording was successful
        self.assertTrue(success)

    def test_query_matching(self):
        """Test querying records based on search criteria."""
        # Generate matching data for a specific query
        query = "Find files I accessed while at the Home"
        matching_data = self.collector.generate_matching_data(query, count=3)

        # Record the matching data
        self.recorder.record_batch(matching_data)

        # Generate non-matching data
        non_matching_data = self.collector.generate_non_matching_data(query, count=2)

        # Record the non-matching data
        self.recorder.record_batch(non_matching_data)

        # Query for records with "Home"
        results = self.recorder.get_records_by_query("Home")

        # Verify we got the expected number of results
        self.assertEqual(len(results), 3)

        # Verify all results have "Home" in the location name
        for result in results:
            self.assertEqual(result["location_name"], "Home")

    def test_end_to_end_workflow(self):
        """Test the end-to-end workflow from collection to querying."""
        # Start with an empty database
        self.recorder.delete_all()
        self.assertEqual(self.recorder.count_records(), 0)

        # Generate a query ID
        query_id = uuid.uuid4()

        # Generate a query
        query = "Find files I accessed while at the Library using my iPhone"

        # Generate matching data
        matching_data = self.collector.generate_matching_data(query, count=5)

        # Record the matching data
        self.recorder.record_batch(matching_data)

        # Generate truth data for the query
        entity_ids = self.collector.generate_truth_data(query)

        # Record the truth data
        self.recorder.record_truth_data(query_id, entity_ids)

        # Generate some non-matching data
        non_matching_data = self.collector.generate_non_matching_data(query, count=10)

        # Record the non-matching data
        self.recorder.record_batch(non_matching_data)

        # Verify the record count
        self.assertEqual(self.recorder.count_records(), 15)

        # Query for records with "Library"
        results = self.recorder.get_records_by_query("Library")

        # Verify we got the expected number of results
        self.assertEqual(len(results), 5)

        # Verify all results have "Library" in the location name
        for result in results:
            self.assertEqual(result["location_name"], "Library")

        # Query for records with "iPhone"
        results = self.recorder.get_records_by_query("iPhone")

        # Verify all results have "iPhone" as the device name
        for result in results:
            self.assertEqual(result["device_name"], "iPhone")

    def tearDown(self):
        """Clean up after each test."""
        # Clean up the test data
        self.recorder.delete_all()

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        # Clean up the test data
        cls.recorder.delete_all()


if __name__ == "__main__":
    unittest.main()
