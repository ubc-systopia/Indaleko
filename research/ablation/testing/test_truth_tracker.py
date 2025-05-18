"""
Tests for the TruthTracker class.

This module contains unit tests for the TruthTracker class used in the
ablation testing framework to track ground truth data for queries.
"""

import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

from ..models.activity import ActivityType
from ..query.truth_tracker import TruthTracker


class TestTruthTracker(unittest.TestCase):
    """Test case for the TruthTracker class."""

    @patch("research.ablation.query.truth_tracker.IndalekoDBConfig")
    def setUp(self, mock_db_config):
        """Set up test fixtures."""
        # Configure the mock database
        self.mock_db = MagicMock()
        self.mock_collection = MagicMock()
        self.mock_cursor = MagicMock()

        # Set up the db config mock
        mock_db_config.return_value.get_arangodb.return_value = self.mock_db
        self.mock_db.collection.return_value = self.mock_collection
        self.mock_db.aql.execute.return_value = self.mock_cursor

        # Create a temporary directory for file operations
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Initialize the TruthTracker
        self.tracker = TruthTracker()

    def tearDown(self):
        """Tear down test fixtures."""
        self.temp_dir.cleanup()

    def test_get_matching_ids_exact_match(self):
        """Test getting matching IDs with exact query match."""
        # Mock data
        query_text = "What songs did I listen to last week?"
        matching_ids = ["doc1", "doc2", "doc3"]
        activity_types = [ActivityType.MUSIC]

        # Set up mock cursor to return matching IDs
        self.mock_cursor.__iter__.return_value = [matching_ids]

        # Call the method
        result = self.tracker.get_matching_ids(query_text, activity_types)

        # Check that the correct AQL query was executed
        self.mock_db.aql.execute.assert_called_once()
        call_args = self.mock_db.aql.execute.call_args[1]
        self.assertEqual(call_args["bind_vars"]["query_text"], query_text)
        self.assertEqual(call_args["bind_vars"]["activity_types"], ["MUSIC"])

        # Check the result
        self.assertEqual(result, matching_ids)

    def test_get_matching_ids_fuzzy_match(self):
        """Test getting matching IDs with fuzzy query match."""
        # Mock data
        query_text = "What songs did I listen to last week?"
        matching_ids = ["doc1", "doc2", "doc3"]

        # Set up mock to return empty for exact match, then matching IDs for fuzzy match
        empty_cursor = MagicMock()
        empty_cursor.__iter__.return_value = []

        match_cursor = MagicMock()
        match_cursor.__iter__.return_value = [matching_ids]

        # First call returns empty results, second call returns matching IDs
        self.mock_db.aql.execute.side_effect = [empty_cursor, match_cursor]

        # Call the method
        result = self.tracker.get_matching_ids(query_text)

        # Check that the fuzzy AQL query was executed
        self.assertEqual(self.mock_db.aql.execute.call_count, 2)

        # Check the result
        self.assertEqual(result, matching_ids)

    def test_record_query_truth(self):
        """Test recording query truth data."""
        # Mock data
        query_id = str(uuid.uuid4())
        query_text = "What songs did I listen to by Taylor Swift?"
        matching_ids = ["doc1", "doc2", "doc3"]
        activity_types = ["MUSIC"]
        difficulty = "medium"
        metadata = {"entities": ["Taylor Swift"]}

        # Set up mock to return success for insert
        self.mock_collection.insert.return_value = {"_id": "123"}

        # Call the method
        result = self.tracker.record_query_truth(
            query_id=query_id,
            matching_ids=matching_ids,
            query_text=query_text,
            activity_types=activity_types,
            difficulty=difficulty,
            metadata=metadata,
        )

        # Check that insert was called with the correct document
        self.mock_collection.insert.assert_called_once()
        doc = self.mock_collection.insert.call_args[0][0]
        self.assertEqual(doc["query_id"], query_id)
        self.assertEqual(doc["query_text"], query_text)
        self.assertEqual(doc["matching_ids"], matching_ids)
        self.assertEqual(doc["activity_types"], activity_types)
        self.assertEqual(doc["difficulty"], difficulty)
        self.assertEqual(doc["metadata"], metadata)

        # Check the result
        self.assertTrue(result)

    def test_get_truth_record(self):
        """Test getting a truth record."""
        # Mock data
        query_id = str(uuid.uuid4())
        truth_record = {
            "query_id": query_id,
            "query_text": "What songs did I listen to?",
            "matching_ids": ["doc1", "doc2"],
            "activity_types": ["MUSIC"],
        }

        # Set up mock cursor to return the truth record
        self.mock_cursor.__iter__.return_value = [truth_record]

        # Call the method
        result = self.tracker.get_truth_record(query_id)

        # Check that the correct AQL query was executed
        self.mock_db.aql.execute.assert_called_once()
        call_args = self.mock_db.aql.execute.call_args[1]
        self.assertEqual(call_args["bind_vars"]["query_id"], query_id)

        # Check the result
        self.assertEqual(result, truth_record)

    def test_save_and_load_to_file(self):
        """Test saving and loading truth data to/from a file."""
        # Mock data
        truth_records = [
            {
                "query_id": str(uuid.uuid4()),
                "query_text": "What songs did I listen to?",
                "matching_ids": ["doc1", "doc2"],
                "activity_types": ["MUSIC"],
            },
            {
                "query_id": str(uuid.uuid4()),
                "query_text": "Where was I last Tuesday?",
                "matching_ids": ["doc3", "doc4"],
                "activity_types": ["LOCATION"],
            },
        ]

        # Set up mock cursor to return truth records
        self.mock_cursor.__iter__.return_value = truth_records

        # Call save_to_file
        file_path = self.temp_path / "truth_data.json"
        result = self.tracker.save_to_file(file_path)

        # Check that the correct AQL query was executed
        self.mock_db.aql.execute.assert_called_once()

        # Check that the file was created and contains the expected data
        self.assertTrue(file_path.exists())
        with open(file_path) as f:
            saved_data = json.load(f)
            self.assertEqual(saved_data, truth_records)

        # Check the result
        self.assertTrue(result)

        # Reset mocks for testing load_from_file
        self.mock_db.reset_mock()
        self.mock_collection.reset_mock()

        # Call load_from_file
        result = self.tracker.load_from_file(file_path)

        # Check that the correct collection was used
        self.mock_db.collection.assert_called_once()

        # Check that insert was called for each record
        self.assertEqual(self.mock_collection.insert.call_count, 2)

        # Check the result
        self.assertTrue(result)

    def test_clear_all_records(self):
        """Test clearing all query truth records."""
        # Call the method
        result = self.tracker.clear_all_records()

        # Check that the correct AQL query was executed
        self.mock_db.aql.execute.assert_called_once()

        # Check the result
        self.assertTrue(result)

    def test_get_activity_type_distribution(self):
        """Test getting the distribution of activity types."""
        # Mock data
        distribution_data = [
            {"activity_type": "MUSIC", "count": 10},
            {"activity_type": "LOCATION", "count": 5},
            {"activity_type": "TASK", "count": 3},
        ]

        # Set up mock cursor to return distribution data
        self.mock_cursor.__iter__.return_value = distribution_data

        # Call the method
        result = self.tracker.get_activity_type_distribution()

        # Check that the correct AQL query was executed
        self.mock_db.aql.execute.assert_called_once()

        # Check the result
        expected = {"MUSIC": 10, "LOCATION": 5, "TASK": 3}
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
