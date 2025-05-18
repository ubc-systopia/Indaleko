"""Integration test for combining multiple activity types in a single test run."""

import logging
import os
import sys
import unittest
from uuid import uuid4

# Add project root to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Import the components we need to test
# Import the activity collectors and recorders
from research.ablation.collectors.music_collector import MusicActivityCollector
from research.ablation.ner.entity_manager import NamedEntityManager
from research.ablation.recorders.music_recorder import MusicActivityRecorder

try:
    from research.ablation.collectors.task_collector import TaskActivityCollector
    from research.ablation.recorders.task_recorder import TaskActivityRecorder

    TASK_AVAILABLE = True
except ImportError:
    TASK_AVAILABLE = False
    logging.warning("Task activity components not available, skipping task tests")

try:
    from research.ablation.collectors.location_collector import (
        LocationActivityCollector,
    )
    from research.ablation.recorders.location_recorder import LocationActivityRecorder

    LOCATION_AVAILABLE = True
except ImportError:
    LOCATION_AVAILABLE = False
    logging.warning("Location activity components not available, skipping location tests")


class TestCombinedActivities(unittest.TestCase):
    """Integration test for running multiple activity collectors and recorders together."""

    @classmethod
    def setUpClass(cls):
        """Set up the test environment once for all tests."""
        # Create a shared entity manager
        cls.entity_manager = NamedEntityManager()

        # Create collectors with a fixed seed
        cls.music_collector = MusicActivityCollector(entity_manager=cls.entity_manager, seed_value=42)
        cls.music_recorder = MusicActivityRecorder()

        # Skip tests if any required component is not available
        if cls.music_recorder.db is None:
            raise unittest.SkipTest("Database connection not available")

        # Initialize other collectors if available
        if TASK_AVAILABLE:
            cls.task_collector = TaskActivityCollector(entity_manager=cls.entity_manager, seed_value=42)
            cls.task_recorder = TaskActivityRecorder()

        if LOCATION_AVAILABLE:
            cls.location_collector = LocationActivityCollector(entity_manager=cls.entity_manager, seed_value=42)
            cls.location_recorder = LocationActivityRecorder()

        # Clean up any existing test data
        cls.music_recorder.delete_all()

        if TASK_AVAILABLE:
            cls.task_recorder.delete_all()

        if LOCATION_AVAILABLE:
            cls.location_recorder.delete_all()

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        # Delete all test data
        if cls.music_recorder.db is not None:
            cls.music_recorder.delete_all()

        if TASK_AVAILABLE:
            cls.task_recorder.delete_all()

        if LOCATION_AVAILABLE:
            cls.location_recorder.delete_all()

    def test_combined_data_generation(self):
        """Test generating and recording data from multiple activity types."""
        # Create a query that should match multiple activity types
        query = "Find files related to my Taylor Swift concert at home last week"

        # Generate and record music activities
        music_data = self.music_collector.generate_matching_data(query, count=3)
        music_result = self.music_recorder.record_batch(music_data)
        self.assertTrue(music_result)

        # Generate and record task activities if available
        if TASK_AVAILABLE:
            task_data = self.task_collector.generate_matching_data(query, count=3)
            task_result = self.task_recorder.record_batch(task_data)
            self.assertTrue(task_result)

        # Generate and record location activities if available
        if LOCATION_AVAILABLE:
            location_data = self.location_collector.generate_matching_data(query, count=3)
            location_result = self.location_recorder.record_batch(location_data)
            self.assertTrue(location_result)

        # Verify music data was recorded
        music_count = self.music_recorder.count_records()
        self.assertEqual(music_count, 3)

        # Verify task data was recorded if available
        if TASK_AVAILABLE:
            task_count = self.task_recorder.count_records()
            self.assertEqual(task_count, 3)

        # Verify location data was recorded if available
        if LOCATION_AVAILABLE:
            location_count = self.location_recorder.count_records()
            self.assertEqual(location_count, 3)

    def test_truth_data_generation(self):
        """Test generating and recording truth data from multiple activity types."""
        # Create a query and query ID
        query = "Show me files related to my meeting at the coffee shop"
        query_id = uuid4()

        # Generate truth data for music activities
        music_truth = self.music_collector.generate_truth_data(query)
        music_result = self.music_recorder.record_truth_data(query_id, music_truth)
        self.assertTrue(music_result)

        # Generate truth data for task activities if available
        if TASK_AVAILABLE:
            task_truth = self.task_collector.generate_truth_data(query)
            task_result = self.task_recorder.record_truth_data(query_id, task_truth)
            self.assertTrue(task_result)

        # Generate truth data for location activities if available
        if LOCATION_AVAILABLE:
            location_truth = self.location_collector.generate_truth_data(query)
            location_result = self.location_recorder.record_truth_data(query_id, location_truth)
            self.assertTrue(location_result)


if __name__ == "__main__":
    unittest.main()
