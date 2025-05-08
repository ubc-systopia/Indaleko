"""Integration tests for the collaboration activity collector and recorder."""

import unittest
import uuid

from ...collectors.collaboration_collector import CollaborationActivityCollector
from ...ner.entity_manager import NamedEntityManager
from ...recorders.collaboration_recorder import CollaborationActivityRecorder


class TestCollaborationIntegration(unittest.TestCase):
    """Integration tests for collaboration collector and recorder."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for all tests."""
        # Create an entity manager
        cls.entity_manager = NamedEntityManager()

        # Create a collector
        cls.collector = CollaborationActivityCollector(entity_manager=cls.entity_manager)

        # Create a recorder
        cls.recorder = CollaborationActivityRecorder()

    def setUp(self):
        """Set up for each test."""
        # Clean up any existing test data
        self.recorder.delete_all()

    def test_collect_and_record_single(self):
        """Test collecting and recording a single collaboration activity."""
        # Collect a collaboration activity
        activity_dict = self.collector.collect()

        # Record the activity
        success = self.recorder.record(activity_dict)

        # Verify recording was successful
        self.assertTrue(success)

        # Verify the record count is 1
        count = self.recorder.count_records()
        self.assertEqual(count, 1)

    def test_collect_and_record_batch(self):
        """Test collecting and recording a batch of collaboration activities."""
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
        query = "Find files shared in Microsoft Teams meetings"
        entity_ids = self.collector.generate_truth_data(query)

        # Record the truth data
        success = self.recorder.record_truth_data(query_id, entity_ids)

        # Verify recording was successful
        self.assertTrue(success)

    def test_query_matching(self):
        """Test querying records based on search criteria."""
        # Generate matching data for a specific query
        query = "Find files from Slack meetings"
        matching_data = self.collector.generate_matching_data(query, count=3)

        # Record the matching data
        self.recorder.record_batch(matching_data)

        # Generate non-matching data
        non_matching_data = self.collector.generate_non_matching_data(query, count=2)

        # Record the non-matching data
        self.recorder.record_batch(non_matching_data)

        # Query for records with "Slack"
        results = self.recorder.get_records_by_query("Slack")

        # Verify we got the expected number of results
        self.assertEqual(len(results), 3)

        # Verify all results have "Slack" in the platform
        for result in results:
            self.assertEqual(result["platform"], "Slack")

    def test_end_to_end_workflow(self):
        """Test the end-to-end workflow from collection to querying."""
        # Start with an empty database
        self.recorder.delete_all()
        self.assertEqual(self.recorder.count_records(), 0)

        # Generate a query ID
        query_id = uuid.uuid4()

        # Generate a query
        query = "Find files shared by John Smith in a Zoom meeting"

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

        # Query for records with "Zoom"
        results = self.recorder.get_records_by_query("Zoom")

        # Verify all results have "Zoom" in the platform
        for result in results:
            self.assertEqual(result["platform"], "Zoom")

        # Query for records with "John Smith"
        results = self.recorder.get_records_by_query("John Smith")

        # Verify John Smith is a participant in each result
        for result in results:
            participants = result.get("participants", [])
            participant_names = [p.get("name") if isinstance(p, dict) else str(p) for p in participants]
            found = False
            for name in participant_names:
                if "John Smith" in name:
                    found = True
                    break
            self.assertTrue(found, "John Smith should be a participant")

    def test_participant_query_matching(self):
        """Test querying records based on participant."""
        # Create a query specifically looking for a participant
        query = "Find files shared by Sarah Brown"

        # Generate matching data with Sarah Brown as a participant
        matching_data = self.collector.generate_matching_data(query, count=4)

        # Record the matching data
        self.recorder.record_batch(matching_data)

        # Query for records with "Sarah Brown"
        results = self.recorder.get_records_by_query("Sarah Brown")

        # Verify we got the expected number of results
        self.assertEqual(len(results), 4)

        # Verify Sarah Brown is a participant in each result
        for result in results:
            participants = result.get("participants", [])
            participant_found = False
            for p in participants:
                name = p.get("name") if isinstance(p, dict) else getattr(p, "name", "")
                if name == "Sarah Brown":
                    participant_found = True
                    break
            self.assertTrue(participant_found, "Sarah Brown should be a participant")

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
