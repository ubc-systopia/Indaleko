"""
Tests for the truth data tracker module.

This module contains unit tests for the truth data tracking functionality
in the ablation study framework.
"""

import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from typing import Dict, List, Any

from tools.ablation.query.truth_tracker import TruthDataTracker


class TestTruthDataTracker(unittest.TestCase):
    """Test case for the TruthDataTracker class."""

    def setUp(self):
        """Set up test fixtures."""
        # Use a test-specific collection name to avoid interfering with real data
        self.tracker = TruthDataTracker(collection_name="TestAblationQueryTruth")
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Clear any existing test data
        self.tracker.clear_truth_data()

    def tearDown(self):
        """Tear down test fixtures."""
        # Clear test data
        self.tracker.clear_truth_data()
        self.temp_dir.cleanup()

    def test_record_and_get_truth(self):
        """Test recording and retrieving truth data."""
        # Generate a test query
        query_id = str(uuid.uuid4())
        matching_ids = [str(uuid.uuid4()) for _ in range(5)]
        activity_type = "music"
        query_text = "What songs did I listen to by Taylor Swift last week?"
        components = {
            "entities": [
                {"name": "Taylor Swift", "type": "artist"}
            ],
            "temporal": {
                "period": "last week"
            }
        }

        # Record the truth data
        self.tracker.record_query_truth(
            query_id=query_id,
            matching_ids=matching_ids,
            activity_type=activity_type,
            query_text=query_text,
            query_components=components
        )

        # Get the matching IDs
        retrieved_ids = self.tracker.get_matching_ids(query_id)

        # Check that we got the same IDs back
        self.assertEqual(set(retrieved_ids), set(matching_ids))

        # Get the complete truth record
        truth_record = self.tracker.get_truth_record(query_id)

        # Check that the record has the expected fields
        self.assertIsNotNone(truth_record)
        self.assertEqual(truth_record["query_id"], query_id)
        self.assertEqual(truth_record["query_text"], query_text)
        self.assertEqual(truth_record["activity_type"], activity_type)
        self.assertEqual(set(truth_record["matching_ids"]), set(matching_ids))
        self.assertEqual(truth_record["components"], components)

    def test_calculate_metrics(self):
        """Test calculating metrics."""
        # Generate a test query
        query_id = str(uuid.uuid4())
        matching_ids = [str(uuid.uuid4()) for _ in range(5)]
        activity_type = "music"
        query_text = "What songs did I listen to by Taylor Swift last week?"

        # Record the truth data
        self.tracker.record_query_truth(
            query_id=query_id,
            matching_ids=matching_ids,
            activity_type=activity_type,
            query_text=query_text
        )

        # Test case 1: Perfect match
        result_ids = matching_ids.copy()
        metrics = self.tracker.calculate_metrics(query_id, result_ids)

        self.assertEqual(metrics["precision"], 1.0)
        self.assertEqual(metrics["recall"], 1.0)
        self.assertEqual(metrics["f1"], 1.0)
        self.assertEqual(metrics["true_positives"], 5)
        self.assertEqual(metrics["false_positives"], 0)
        self.assertEqual(metrics["false_negatives"], 0)

        # Test case 2: Some false positives
        result_ids = matching_ids.copy() + [str(uuid.uuid4()) for _ in range(5)]
        metrics = self.tracker.calculate_metrics(query_id, result_ids)

        self.assertEqual(metrics["precision"], 0.5)
        self.assertEqual(metrics["recall"], 1.0)
        self.assertEqual(metrics["f1"], 2 * 0.5 * 1.0 / (0.5 + 1.0))
        self.assertEqual(metrics["true_positives"], 5)
        self.assertEqual(metrics["false_positives"], 5)
        self.assertEqual(metrics["false_negatives"], 0)

        # Test case 3: Some false negatives
        result_ids = matching_ids[:2]  # Only return 2 of 5 matches
        metrics = self.tracker.calculate_metrics(query_id, result_ids)

        self.assertEqual(metrics["precision"], 1.0)
        self.assertEqual(metrics["recall"], 0.4)  # 2/5
        self.assertEqual(metrics["f1"], 2 * 1.0 * 0.4 / (1.0 + 0.4))
        self.assertEqual(metrics["true_positives"], 2)
        self.assertEqual(metrics["false_positives"], 0)
        self.assertEqual(metrics["false_negatives"], 3)

        # Test case 4: No matches
        result_ids = [str(uuid.uuid4()) for _ in range(3)]
        metrics = self.tracker.calculate_metrics(query_id, result_ids)

        self.assertEqual(metrics["precision"], 0.0)
        self.assertEqual(metrics["recall"], 0.0)
        self.assertEqual(metrics["f1"], 0.0)
        self.assertEqual(metrics["true_positives"], 0)
        self.assertEqual(metrics["false_positives"], 3)
        self.assertEqual(metrics["false_negatives"], 5)

    def test_save_and_load_truth_data(self):
        """Test saving and loading truth data."""
        # Generate and record some test queries
        for i in range(3):
            query_id = str(uuid.uuid4())
            matching_ids = [str(uuid.uuid4()) for _ in range(3)]
            activity_type = "music"
            query_text = f"Test query {i}"

            self.tracker.record_query_truth(
                query_id=query_id,
                matching_ids=matching_ids,
                activity_type=activity_type,
                query_text=query_text
            )

        # Save the truth data
        output_path = self.temp_path / "truth_data.json"
        self.tracker.save_truth_data(output_path)

        # Check that the file exists
        self.assertTrue(output_path.exists())

        # Clear the existing data
        self.tracker.clear_truth_data()

        # Check that the data was cleared
        self.assertEqual(len(self.tracker.get_all_query_ids()), 0)

        # Load the truth data
        self.tracker.load_truth_data(output_path)

        # Check that we got the data back
        self.assertEqual(len(self.tracker.get_all_query_ids()), 3)


if __name__ == "__main__":
    unittest.main()
