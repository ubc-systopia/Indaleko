"""Integration tests for the task activity collector and recorder."""

import unittest
import uuid

from ...collectors.task_collector import TaskActivityCollector
from ...ner.entity_manager import NamedEntityManager
from ...recorders.task_recorder import TaskActivityRecorder


class TestTaskIntegration(unittest.TestCase):
    """Integration tests for task collector and recorder."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for all tests."""
        # Create an entity manager
        cls.entity_manager = NamedEntityManager()

        # Create a collector
        cls.collector = TaskActivityCollector(entity_manager=cls.entity_manager)

        # Create a recorder
        cls.recorder = TaskActivityRecorder()

    def setUp(self):
        """Set up for each test."""
        # Clean up any existing test data
        self.recorder.delete_all()

    def test_collect_and_record_single(self):
        """Test collecting and recording a single task activity."""
        # Collect a task activity
        activity_dict = self.collector.collect()

        # Record the activity
        success = self.recorder.record(activity_dict)

        # Verify recording was successful
        self.assertTrue(success)

        # Verify the record count is 1
        count = self.recorder.count_records()
        self.assertEqual(count, 1)

    def test_collect_and_record_batch(self):
        """Test collecting and recording a batch of task activities."""
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
        query = "Find files I opened in Microsoft Word"
        entity_ids = self.collector.generate_truth_data(query)

        # Record the truth data
        success = self.recorder.record_truth_data(query_id, entity_ids)

        # Verify recording was successful
        self.assertTrue(success)

    def test_query_matching(self):
        """Test querying records based on search criteria."""
        # Generate matching data for a specific query
        query = "Find files I worked on in Visual Studio Code"
        matching_data = self.collector.generate_matching_data(query, count=3)

        # Record the matching data
        self.recorder.record_batch(matching_data)

        # Generate non-matching data
        non_matching_data = self.collector.generate_non_matching_data(query, count=2)

        # Record the non-matching data
        self.recorder.record_batch(non_matching_data)

        # Query for records with "Visual Studio Code"
        results = self.recorder.get_records_by_query("Visual Studio Code")

        # Verify we got the expected number of results
        self.assertEqual(len(results), 3)

        # Verify all results have "Visual Studio Code" in the application
        for result in results:
            self.assertEqual(result["application"], "Visual Studio Code")

    def test_end_to_end_workflow(self):
        """Test the end-to-end workflow from collection to querying."""
        # Start with an empty database
        self.recorder.delete_all()
        self.assertEqual(self.recorder.count_records(), 0)

        # Generate a query ID
        query_id = uuid.uuid4()

        # Generate a query
        query = "Find documents I edited in Microsoft Word using alice's account"

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

        # Query for records with "Microsoft Word"
        results = self.recorder.get_records_by_query("Microsoft Word")

        # Verify all results have "Microsoft Word" in the application
        for result in results:
            self.assertEqual(result["application"], "Microsoft Word")

        # Query for records with "alice"
        results = self.recorder.get_records_by_query("alice")

        # Verify all results have "alice" as the user
        for result in results:
            self.assertEqual(result["user"], "alice")

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
