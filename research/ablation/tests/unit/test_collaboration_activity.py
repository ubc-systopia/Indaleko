"""Unit tests for the collaboration activity components."""

import os
import random
import sys
import unittest
import uuid

# Add project root to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from research.ablation.collectors.collaboration_collector import (
    CollaborationActivityCollector,
)
from research.ablation.models.collaboration_activity import (
    CollaborationActivity,
    Participant,
)
from research.ablation.ner.entity_manager import NamedEntityManager


class TestCollaborationActivity(unittest.TestCase):
    """Test cases for the collaboration activity model and collector."""

    def setUp(self):
        """Set up test fixtures."""
        # Set a fixed seed for deterministic testing
        random.seed(42)

        # Create an entity manager
        self.entity_manager = NamedEntityManager()

        # Create a collector
        self.collector = CollaborationActivityCollector(entity_manager=self.entity_manager)

    def test_collaboration_activity_model(self):
        """Test the CollaborationActivity model."""
        # Create participants
        participants = [
            Participant(name="John Smith", email="john.smith@example.com"),
            Participant(name="Jane Doe", email="jane.doe@example.com"),
        ]

        # Create a collaboration activity
        activity = CollaborationActivity(
            platform="Microsoft Teams",
            event_type="Meeting",
            participants=participants,
            content="Weekly team sync for Indaleko project",
            duration_seconds=3600,
            source="teams",
        )

        # Convert to dictionary for validation
        activity_dict = activity.dict()

        # Verify the activity was created correctly
        self.assertEqual(activity_dict["platform"], "Microsoft Teams")
        self.assertEqual(activity_dict["event_type"], "Meeting")
        self.assertEqual(activity_dict["content"], "Weekly team sync for Indaleko project")
        self.assertEqual(activity_dict["duration_seconds"], 3600)
        self.assertEqual(activity_dict["source"], "teams")

        # Verify participants
        self.assertEqual(len(activity_dict["participants"]), 2)
        self.assertEqual(activity_dict["participants"][0]["name"], "John Smith")
        self.assertEqual(activity_dict["participants"][0]["email"], "john.smith@example.com")
        self.assertEqual(activity_dict["participants"][1]["name"], "Jane Doe")
        self.assertEqual(activity_dict["participants"][1]["email"], "jane.doe@example.com")

        # Verify semantic attributes were added
        self.assertIn("collaboration.platform", activity.semantic_attributes)
        self.assertIn("collaboration.type", activity.semantic_attributes)
        self.assertIn("collaboration.participants", activity.semantic_attributes)
        self.assertIn("collaboration.content", activity.semantic_attributes)
        self.assertIn("collaboration.duration", activity.semantic_attributes)
        self.assertIn("collaboration.source", activity.semantic_attributes)

    def test_collector_collect(self):
        """Test the collect method of the CollaborationActivityCollector."""
        # Collect a collaboration activity
        activity_dict = self.collector.collect()

        # Verify the activity was created correctly
        self.assertIn("platform", activity_dict)
        self.assertIn("event_type", activity_dict)
        self.assertIn("participants", activity_dict)
        self.assertIn("content", activity_dict)
        self.assertIn("duration_seconds", activity_dict)
        self.assertIn("source", activity_dict)

        # Verify the platform is one of the expected values
        self.assertIn(activity_dict["platform"], self.collector.platforms)

        # Verify the event type is one of the expected values
        self.assertIn(activity_dict["event_type"], self.collector.event_types)

        # Verify there are participants
        self.assertGreater(len(activity_dict["participants"]), 0)

    def test_collector_generate_batch(self):
        """Test the generate_batch method of the CollaborationActivityCollector."""
        # Generate a batch of 5 activities
        batch = self.collector.generate_batch(5)

        # Verify the batch contains 5 activities
        self.assertEqual(len(batch), 5)

        # Verify each activity has the required fields
        for activity_dict in batch:
            self.assertIn("platform", activity_dict)
            self.assertIn("event_type", activity_dict)
            self.assertIn("participants", activity_dict)
            self.assertIn("content", activity_dict)
            self.assertIn("duration_seconds", activity_dict)
            self.assertIn("source", activity_dict)

    def test_collector_generate_truth_data(self):
        """Test the generate_truth_data method of the CollaborationActivityCollector."""
        # Generate truth data for a query that contains a platform name
        query = "Find documents shared during Microsoft Teams meetings"
        truth_data = self.collector.generate_truth_data(query)

        # Verify truth data is a set of UUIDs
        self.assertIsInstance(truth_data, set)
        for entity_id in truth_data:
            self.assertIsInstance(entity_id, uuid.UUID)

        # Verify truth data contains entries for the platform
        self.assertGreater(len(truth_data), 0)

    def test_collector_generate_matching_data(self):
        """Test the generate_matching_data method of the CollaborationActivityCollector."""
        # Generate matching data for a query that contains a platform and event type
        query = "Find files from Zoom Meetings"
        matching_data = self.collector.generate_matching_data(query, count=3)

        # Verify matching data is a list of dictionaries
        self.assertIsInstance(matching_data, list)
        self.assertEqual(len(matching_data), 3)

        # Verify each matching activity contains the platform or event type
        for activity_dict in matching_data:
            self.assertTrue(activity_dict["platform"] == "Zoom" or activity_dict["event_type"] == "Meeting")

    def test_collector_generate_non_matching_data(self):
        """Test the generate_non_matching_data method of the CollaborationActivityCollector."""
        # Generate non-matching data for a query that contains a participant name
        query = "Find files shared by John Smith"
        non_matching_data = self.collector.generate_non_matching_data(query, count=3)

        # Verify non-matching data is a list of dictionaries
        self.assertIsInstance(non_matching_data, list)
        self.assertEqual(len(non_matching_data), 3)

        # Verify each non-matching activity does not contain the participant
        for activity_dict in non_matching_data:
            participants = activity_dict["participants"]
            participant_names = [p["name"] if isinstance(p, dict) else p.name for p in participants]
            self.assertNotIn("John Smith", participant_names)

    def test_collector_with_random_seed(self):
        """Test collecting with different random seeds."""
        # Create two collectors with different seeds
        collector1 = CollaborationActivityCollector(seed_value=123)
        collector2 = CollaborationActivityCollector(seed_value=456)

        # Generate activities from both collectors
        activity1 = collector1.collect()
        activity2 = collector2.collect()

        # Activities should be different with different seeds
        # At least one attribute should be different
        different_attributes = 0
        if activity1["platform"] != activity2["platform"]:
            different_attributes += 1
        if activity1["event_type"] != activity2["event_type"]:
            different_attributes += 1
        if activity1["source"] != activity2["source"]:
            different_attributes += 1

        # Verify at least one attribute is different
        self.assertGreater(different_attributes, 0)

    def test_participant_string_representation(self):
        """Test the string representation of participants."""
        # Create a participant with email
        participant1 = Participant(name="John Smith", email="john.smith@example.com")
        self.assertEqual(str(participant1), "John Smith <john.smith@example.com>")

        # Create a participant without email
        participant2 = Participant(name="Jane Doe")
        self.assertEqual(str(participant2), "Jane Doe")


if __name__ == "__main__":
    unittest.main()
