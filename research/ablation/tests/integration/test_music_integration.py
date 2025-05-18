"""Integration tests for music activity components."""

import os
import sys
import unittest
from uuid import uuid4

# Add project root to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from research.ablation.collectors.music_collector import MusicActivityCollector
from research.ablation.ner.entity_manager import NamedEntityManager
from research.ablation.recorders.music_recorder import MusicActivityRecorder


class TestMusicActivityIntegration(unittest.TestCase):
    """Integration tests for music activity collection and recording."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for all tests."""
        # Create an entity manager
        cls.entity_manager = NamedEntityManager()

        # Create a collector with a fixed seed
        cls.collector = MusicActivityCollector(entity_manager=cls.entity_manager, seed_value=42)

        # Create a recorder
        cls.recorder = MusicActivityRecorder()

        # Skip tests if database is not available
        if cls.recorder.db is None:
            raise unittest.SkipTest("Database connection not available")

        # Clean up any existing test data
        cls.recorder.delete_all()

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests have run."""
        # Delete all test data
        if cls.recorder.db is not None:
            cls.recorder.delete_all()

    def setUp(self):
        """Set up test fixtures before each test."""
        # Skip tests if database is not available
        if self.recorder.db is None:
            self.skipTest("Database connection not available")

    def test_collect_and_record_single(self):
        """Test collecting and recording a single music activity."""
        # Collect music activity data
        data = self.collector.collect()

        # Record the data
        result = self.recorder.record(data)

        # Verify recording was successful
        self.assertTrue(result)

        # Verify one record was created
        self.assertEqual(self.recorder.count_records(), 1)

    def test_generate_and_record_batch(self):
        """Test generating and recording a batch of music activities."""
        # Generate a batch of music activities
        batch_size = 5
        batch = self.collector.generate_batch(batch_size)

        # Record the batch
        result = self.recorder.record_batch(batch)

        # Verify recording was successful
        self.assertTrue(result)

        # Verify the correct number of records were created
        # (initial count plus the batch size)
        initial_count = self.recorder.count_records()
        self.assertEqual(initial_count, 1 + batch_size)  # 1 from previous test + batch_size

    def test_generate_and_record_matching_data(self):
        """Test generating and recording matching data for a query."""
        # Create a query
        query = "Find songs by Taylor Swift"

        # Generate matching data for the query
        count = 3
        matching_data = self.collector.generate_matching_data(query, count=count)

        # Record the matching data
        result = self.recorder.record_batch(matching_data)

        # Verify recording was successful
        self.assertTrue(result)

        # Verify all records have the correct artist
        for data in matching_data:
            self.assertEqual(data["artist"], "Taylor Swift")

    def test_generate_and_record_truth_data(self):
        """Test generating and recording truth data for a query."""
        # Create a query and query ID
        query = "Find songs by Beyoncé"
        query_id = uuid4()

        # Generate truth data for the query
        truth_data = self.collector.generate_truth_data(query)

        # Record the truth data
        result = self.recorder.record_truth_data(query_id, truth_data)

        # Verify recording was successful
        self.assertTrue(result)

    def test_delete_all_records(self):
        """Test deleting all music activity records."""
        # Verify we have some records to start with
        initial_count = self.recorder.count_records()
        self.assertGreater(initial_count, 0)

        # Delete all records
        result = self.recorder.delete_all()

        # Verify deletion was successful
        self.assertTrue(result)

        # Verify all records were deleted
        self.assertEqual(self.recorder.count_records(), 0)

        # Create a new record to make sure we don't leave the collection empty
        data = self.collector.collect()
        self.recorder.record(data)
        self.assertEqual(self.recorder.count_records(), 1)


if __name__ == "__main__":
    unittest.main()
