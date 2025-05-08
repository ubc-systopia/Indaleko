"""Unit tests for the task activity components."""

import os
import random
import sys
import unittest
import uuid

# Add project root to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from research.ablation.collectors.task_collector import TaskActivityCollector
from research.ablation.models.task_activity import TaskActivity
from research.ablation.ner.entity_manager import NamedEntityManager


class TestTaskActivity(unittest.TestCase):
    """Test cases for the task activity model and collector."""

    def setUp(self):
        """Set up test fixtures."""
        # Set a fixed seed for deterministic testing
        random.seed(42)

        # Create an entity manager
        self.entity_manager = NamedEntityManager()

        # Create a collector
        self.collector = TaskActivityCollector(entity_manager=self.entity_manager)

    def test_task_activity_model(self):
        """Test the TaskActivity model."""
        # Create a task activity
        activity = TaskActivity(
            task_name="Document editing",
            application="Microsoft Word",
            window_title="Proposal.docx - Word",
            duration_seconds=3600,
            active=True,
            source="windows_task_manager",
        )

        # Convert to dictionary for validation
        activity_dict = activity.dict()

        # Verify the activity was created correctly
        self.assertEqual(activity_dict["task_name"], "Document editing")
        self.assertEqual(activity_dict["application"], "Microsoft Word")
        self.assertEqual(activity_dict["window_title"], "Proposal.docx - Word")
        self.assertEqual(activity_dict["duration_seconds"], 3600)
        self.assertEqual(activity_dict["active"], True)
        self.assertEqual(activity_dict["source"], "windows_task_manager")

        # Verify semantic attributes were added
        self.assertIn("task.name", activity.semantic_attributes)
        self.assertIn("task.application", activity.semantic_attributes)
        self.assertIn("task.window_title", activity.semantic_attributes)
        self.assertIn("task.duration", activity.semantic_attributes)
        self.assertIn("task.active", activity.semantic_attributes)
        self.assertIn("task.source", activity.semantic_attributes)

    def test_collector_collect(self):
        """Test the collect method of the TaskActivityCollector."""
        # Collect a task activity
        activity_dict = self.collector.collect()

        # Verify the activity was created correctly
        self.assertIn("task_name", activity_dict)
        self.assertIn("application", activity_dict)
        self.assertIn("window_title", activity_dict)
        self.assertIn("duration_seconds", activity_dict)
        self.assertIn("active", activity_dict)
        self.assertIn("source", activity_dict)

        # Verify the application is one of the expected values
        self.assertIn(activity_dict["application"], self.collector.applications)

        # Verify the task name is appropriate for the application
        self.assertIn(activity_dict["task_name"], self.collector.tasks_by_application[activity_dict["application"]])

        # Verify the window title is appropriate for the application
        self.assertIn(
            activity_dict["window_title"], self.collector.window_titles_by_application[activity_dict["application"]],
        )

    def test_collector_generate_batch(self):
        """Test the generate_batch method of the TaskActivityCollector."""
        # Generate a batch of 5 activities
        batch = self.collector.generate_batch(5)

        # Verify the batch contains 5 activities
        self.assertEqual(len(batch), 5)

        # Verify each activity has the required fields
        for activity_dict in batch:
            self.assertIn("task_name", activity_dict)
            self.assertIn("application", activity_dict)
            self.assertIn("window_title", activity_dict)
            self.assertIn("duration_seconds", activity_dict)
            self.assertIn("active", activity_dict)
            self.assertIn("source", activity_dict)

    def test_collector_generate_truth_data(self):
        """Test the generate_truth_data method of the TaskActivityCollector."""
        # Generate truth data for a query that contains an application name
        query = "Find files I edited in Microsoft Word"
        truth_data = self.collector.generate_truth_data(query)

        # Verify truth data is a set of UUIDs
        self.assertIsInstance(truth_data, set)
        for entity_id in truth_data:
            self.assertIsInstance(entity_id, uuid.UUID)

        # Verify truth data contains entries for the application
        self.assertGreater(len(truth_data), 0)

    def test_collector_generate_matching_data(self):
        """Test the generate_matching_data method of the TaskActivityCollector."""
        # Generate matching data for a query that contains an application name
        query = "Find files I worked on in Microsoft Excel"
        matching_data = self.collector.generate_matching_data(query, count=3)

        # Verify matching data is a list of dictionaries
        self.assertIsInstance(matching_data, list)
        self.assertEqual(len(matching_data), 3)

        # Verify each matching activity contains the application name
        for activity_dict in matching_data:
            self.assertEqual(activity_dict["application"], "Microsoft Excel")

            # Verify the task name is appropriate for the application
            self.assertIn(activity_dict["task_name"], self.collector.tasks_by_application["Microsoft Excel"])

            # Verify the window title is appropriate for the application
            self.assertIn(activity_dict["window_title"], self.collector.window_titles_by_application["Microsoft Excel"])

    def test_collector_generate_non_matching_data(self):
        """Test the generate_non_matching_data method of the TaskActivityCollector."""
        # Generate non-matching data for a query that contains an application name
        query = "Find files I opened in Visual Studio Code"
        non_matching_data = self.collector.generate_non_matching_data(query, count=3)

        # Verify non-matching data is a list of dictionaries
        self.assertIsInstance(non_matching_data, list)
        self.assertEqual(len(non_matching_data), 3)

        # Verify each non-matching activity does not contain the application name
        for activity_dict in non_matching_data:
            self.assertNotEqual(activity_dict["application"], "Visual Studio Code")

    def test_collector_with_random_seed(self):
        """Test collecting with different random seeds."""
        # Create two collectors with different seeds
        collector1 = TaskActivityCollector(seed_value=123)
        collector2 = TaskActivityCollector(seed_value=456)

        # Generate activities from both collectors
        activity1 = collector1.collect()
        activity2 = collector2.collect()

        # Activities should be different with different seeds
        # At least one attribute should be different
        different_attributes = 0
        if activity1["task_name"] != activity2["task_name"]:
            different_attributes += 1
        if activity1["application"] != activity2["application"]:
            different_attributes += 1
        if activity1["window_title"] != activity2["window_title"]:
            different_attributes += 1

        # Verify at least one attribute is different
        self.assertGreater(different_attributes, 0)


if __name__ == "__main__":
    unittest.main()
