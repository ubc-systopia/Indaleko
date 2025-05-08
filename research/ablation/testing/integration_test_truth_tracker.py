"""
Integration test for the TruthTracker component.

This module contains integration tests that verify the TruthTracker
works correctly with a real database connection.
"""

import logging
import tempfile
import unittest
import uuid
from pathlib import Path

from db.db_collections import IndalekoDBCollections
from db.db_config import IndalekoDBConfig

from ..query.truth_tracker import TruthTracker


class IntegrationTestTruthTracker(unittest.TestCase):
    """Integration tests for the TruthTracker class."""

    def setUp(self):
        """Set up test fixtures."""
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Set up connection to the test database
        try:
            self.db_config = IndalekoDBConfig()
            self.db = self.db_config.get_arangodb()

            # Ensure the collection exists
            collections = self.db.collections()
            collection_names = [c["name"] for c in collections]

            if IndalekoDBCollections.Indaleko_Ablation_Query_Truth_Collection not in collection_names:
                self.db.create_collection(IndalekoDBCollections.Indaleko_Ablation_Query_Truth_Collection)

        except Exception as e:
            self.logger.error(f"FATAL: Database connection failed: {e}")
            self.fail(f"Database connection is required for these tests. Error: {e}")
            # Never reaches here, but keeping for clarity

        # Initialize the TruthTracker
        self.tracker = TruthTracker()

        # Create a temporary directory for file operations
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Test query data
        self.test_queries = [
            {
                "id": str(uuid.uuid4()),
                "text": "What music did I listen to last week?",
                "matching_ids": [str(uuid.uuid4()) for _ in range(3)],
                "activity_types": ["MUSIC"],
                "difficulty": "easy",
                "metadata": {"entities": [], "temporal": "last week"},
            },
            {
                "id": str(uuid.uuid4()),
                "text": "Where was I on Tuesday afternoon?",
                "matching_ids": [str(uuid.uuid4()) for _ in range(2)],
                "activity_types": ["LOCATION"],
                "difficulty": "medium",
                "metadata": {"entities": [], "temporal": "Tuesday afternoon"},
            },
            {
                "id": str(uuid.uuid4()),
                "text": "What tasks did I complete related to the Indaleko project?",
                "matching_ids": [str(uuid.uuid4()) for _ in range(4)],
                "activity_types": ["TASK"],
                "difficulty": "hard",
                "metadata": {"entities": ["Indaleko"], "relations": ["related to"]},
            },
        ]

        # Clear the collection before tests
        self.tracker.clear_all_records()

    def tearDown(self):
        """Tear down test fixtures."""
        # Clean up database
        self.tracker.clear_all_records()

        # Clean up temporary directory
        self.temp_dir.cleanup()

    def _populate_test_data(self):
        """Helper to populate the database with test queries."""
        for query in self.test_queries:
            self.tracker.record_query_truth(
                query_id=query["id"],
                matching_ids=query["matching_ids"],
                query_text=query["text"],
                activity_types=query["activity_types"],
                difficulty=query["difficulty"],
                metadata=query["metadata"],
            )

    def test_record_and_retrieve(self):
        """Test recording and retrieving truth data."""
        # Record test queries
        self._populate_test_data()

        # Retrieve each query and verify it matches
        for query in self.test_queries:
            record = self.tracker.get_truth_record(query["id"])
            self.assertIsNotNone(record)
            self.assertEqual(record["query_id"], query["id"])
            self.assertEqual(record["query_text"], query["text"])
            self.assertEqual(set(record["matching_ids"]), set(query["matching_ids"]))
            self.assertEqual(record["activity_types"], query["activity_types"])
            self.assertEqual(record["difficulty"], query["difficulty"])

            # Get just the matching IDs
            matching_ids = self.tracker.get_matching_ids(query["text"])
            self.assertEqual(set(matching_ids), set(query["matching_ids"]))

    def test_fuzzy_matching(self):
        """Test fuzzy matching for queries with similar text."""
        # Record test queries
        self._populate_test_data()

        # Try variations of the test queries
        test_variations = [
            {
                "original": "What music did I listen to last week?",
                "variation": "What songs did I listen to last week?",
                "expected_match": True,
            },
            {
                "original": "Where was I on Tuesday afternoon?",
                "variation": "Where was I located on Tuesday afternoon?",
                "expected_match": True,
            },
            {
                "original": "What tasks did I complete related to the Indaleko project?",
                "variation": "What was I working on for Indaleko?",
                "expected_match": True,
            },
            {
                "original": "What music did I listen to last week?",
                "variation": "What files did I modify yesterday?",
                "expected_match": False,
            },
        ]

        for test in test_variations:
            original = test["original"]
            variation = test["variation"]

            # Get original query's matching IDs
            original_query = next((q for q in self.test_queries if q["text"] == original), None)
            self.assertIsNotNone(original_query)

            # Get matching IDs for the variation
            matching_ids = self.tracker.get_matching_ids(variation)

            if test["expected_match"]:
                self.assertEqual(set(matching_ids), set(original_query["matching_ids"]))
            else:
                self.assertNotEqual(set(matching_ids), set(original_query["matching_ids"]))

    def test_save_and_load_file(self):
        """Test saving and loading truth data to/from a file."""
        # Record test queries
        self._populate_test_data()

        # Save to file
        file_path = self.temp_path / "truth_data.json"
        success = self.tracker.save_to_file(file_path)
        self.assertTrue(success)
        self.assertTrue(file_path.exists())

        # Clear the database
        self.tracker.clear_all_records()

        # Verify data is gone
        for query in self.test_queries:
            record = self.tracker.get_truth_record(query["id"])
            self.assertIsNone(record)

        # Load from file
        success = self.tracker.load_from_file(file_path)
        self.assertTrue(success)

        # Verify data is back
        for query in self.test_queries:
            record = self.tracker.get_truth_record(query["id"])
            self.assertIsNotNone(record)
            self.assertEqual(record["query_id"], query["id"])
            self.assertEqual(record["query_text"], query["text"])

    def test_activity_type_distribution(self):
        """Test getting activity type distribution."""
        # Record test queries
        self._populate_test_data()

        # Get distribution
        distribution = self.tracker.get_activity_type_distribution()

        # Check distribution
        expected = {"MUSIC": 1, "LOCATION": 1, "TASK": 1}
        self.assertEqual(distribution, expected)


if __name__ == "__main__":
    unittest.main()
