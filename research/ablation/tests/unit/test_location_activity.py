"""Unit tests for the location activity components."""

import os
import random
import sys
import unittest
import uuid

# Add project root to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from research.ablation.collectors.location_collector import LocationActivityCollector
from research.ablation.models.location_activity import (
    LocationActivity,
    LocationCoordinates,
)
from research.ablation.ner.entity_manager import NamedEntityManager


class TestLocationActivity(unittest.TestCase):
    """Test cases for the location activity model and collector."""

    def setUp(self):
        """Set up test fixtures."""
        # Set a fixed seed for deterministic testing
        random.seed(42)

        # Create an entity manager
        self.entity_manager = NamedEntityManager()

        # Create a collector
        self.collector = LocationActivityCollector(entity_manager=self.entity_manager)

    def test_location_activity_model(self):
        """Test the LocationActivity model."""
        # Create a location coordinates object
        coordinates = LocationCoordinates(latitude=37.7749, longitude=-122.4194, accuracy_meters=10.0)

        # Create a location activity
        activity = LocationActivity(
            location_name="Home",
            coordinates=coordinates,
            location_type="residential",
            device_name="iPhone",
            wifi_ssid="HomeNetwork_5G",
            source="gps",
        )

        # Convert to dictionary for validation
        activity_dict = activity.dict()

        # Verify the activity was created correctly
        self.assertEqual(activity_dict["location_name"], "Home")
        self.assertEqual(activity_dict["location_type"], "residential")
        self.assertEqual(activity_dict["device_name"], "iPhone")
        self.assertEqual(activity_dict["wifi_ssid"], "HomeNetwork_5G")
        self.assertEqual(activity_dict["source"], "gps")

        # Verify coordinates
        self.assertEqual(activity_dict["coordinates"]["latitude"], 37.7749)
        self.assertEqual(activity_dict["coordinates"]["longitude"], -122.4194)
        self.assertEqual(activity_dict["coordinates"]["accuracy_meters"], 10.0)

        # Verify semantic attributes were added
        self.assertIn("location.name", activity.semantic_attributes)
        self.assertIn("location.coordinates", activity.semantic_attributes)
        self.assertIn("location.type", activity.semantic_attributes)
        self.assertIn("location.device", activity.semantic_attributes)
        self.assertIn("location.wifi_ssid", activity.semantic_attributes)
        self.assertIn("location.source", activity.semantic_attributes)

    def test_collector_collect(self):
        """Test the collect method of the LocationActivityCollector."""
        # Collect a location activity
        activity_dict = self.collector.collect()

        # Verify the activity was created correctly
        self.assertIn("location_name", activity_dict)
        self.assertIn("location_type", activity_dict)
        self.assertIn("coordinates", activity_dict)
        self.assertIn("source", activity_dict)

        # Verify the location name is one of the expected values
        self.assertIn(activity_dict["location_name"], self.collector.locations)

        # Verify the location type is correct for the location
        self.assertEqual(activity_dict["location_type"], self.collector.location_types[activity_dict["location_name"]])

    def test_collector_generate_batch(self):
        """Test the generate_batch method of the LocationActivityCollector."""
        # Generate a batch of 5 activities
        batch = self.collector.generate_batch(5)

        # Verify the batch contains 5 activities
        self.assertEqual(len(batch), 5)

        # Verify each activity has the required fields
        for activity_dict in batch:
            self.assertIn("location_name", activity_dict)
            self.assertIn("location_type", activity_dict)
            self.assertIn("coordinates", activity_dict)
            self.assertIn("source", activity_dict)

    def test_collector_generate_truth_data(self):
        """Test the generate_truth_data method of the LocationActivityCollector."""
        # Generate truth data for a query that contains a location name
        query = "Find files I accessed while at Home"
        truth_data = self.collector.generate_truth_data(query)

        # Verify truth data is a set of UUIDs
        self.assertIsInstance(truth_data, set)
        for entity_id in truth_data:
            self.assertIsInstance(entity_id, uuid.UUID)

        # Verify truth data contains entries for the location
        self.assertGreater(len(truth_data), 0)

    def test_collector_generate_matching_data(self):
        """Test the generate_matching_data method of the LocationActivityCollector."""
        # Generate matching data for a query that contains a location name
        query = "Find files I accessed while at the Coffee Shop"
        matching_data = self.collector.generate_matching_data(query, count=3)

        # Verify matching data is a list of dictionaries
        self.assertIsInstance(matching_data, list)
        self.assertEqual(len(matching_data), 3)

        # Verify each matching activity contains the location name
        for activity_dict in matching_data:
            self.assertEqual(activity_dict["location_name"], "Coffee Shop")

            # Verify the location type is correct
            self.assertEqual(activity_dict["location_type"], "commercial")

    def test_collector_generate_non_matching_data(self):
        """Test the generate_non_matching_data method of the LocationActivityCollector."""
        # Generate non-matching data for a query that contains a location name
        query = "Find files I accessed while at the Library"
        non_matching_data = self.collector.generate_non_matching_data(query, count=3)

        # Verify non-matching data is a list of dictionaries
        self.assertIsInstance(non_matching_data, list)
        self.assertEqual(len(non_matching_data), 3)

        # Verify each non-matching activity does not contain the location name
        for activity_dict in non_matching_data:
            self.assertNotEqual(activity_dict["location_name"], "Library")

    def test_collector_with_random_seed(self):
        """Test collecting with different random seeds."""
        # Create two collectors with different seeds
        collector1 = LocationActivityCollector(seed_value=123)
        collector2 = LocationActivityCollector(seed_value=456)

        # Generate activities from both collectors
        activity1 = collector1.collect()
        activity2 = collector2.collect()

        # Activities should be different with different seeds
        # At least one attribute should be different
        different_attributes = 0
        if activity1["location_name"] != activity2["location_name"]:
            different_attributes += 1
        if activity1["location_type"] != activity2["location_type"]:
            different_attributes += 1
        if activity1["source"] != activity2["source"]:
            different_attributes += 1

        # Verify at least one attribute is different
        self.assertGreater(different_attributes, 0)


if __name__ == "__main__":
    unittest.main()
