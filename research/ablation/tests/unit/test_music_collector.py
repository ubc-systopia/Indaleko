"""Unit tests for the music activity collector and recorder."""

import os
import random
import sys
import unittest
import uuid
from datetime import datetime, UTC
from unittest.mock import MagicMock, patch

# Add project root to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from research.ablation.collectors.music_collector import MusicActivityCollector
from research.ablation.models.music_activity import MusicActivity
from research.ablation.ner.entity_manager import NamedEntityManager
from research.ablation.recorders.music_recorder import MusicActivityRecorder
from db.db_collections import IndalekoDBCollections


class TestMusicActivityCollector(unittest.TestCase):
    """Test cases for the music activity collector."""

    def setUp(self):
        """Set up test fixtures."""
        # Set a fixed seed for deterministic testing
        random.seed(42)

        # Create an entity manager
        self.entity_manager = NamedEntityManager()

        # Create a collector
        self.collector = MusicActivityCollector(entity_manager=self.entity_manager)

    def test_collect_method(self):
        """Test the collect method of the MusicActivityCollector."""
        # Collect a music activity
        activity_dict = self.collector.collect()

        # Verify the activity was created correctly
        self.assertIn("artist", activity_dict)
        self.assertIn("track", activity_dict)
        self.assertIn("album", activity_dict)
        self.assertIn("genre", activity_dict)
        self.assertIn("duration_seconds", activity_dict)
        self.assertIn("platform", activity_dict)
        self.assertIn("created_at", activity_dict)
        self.assertIn("source", activity_dict)

        # Verify the artist is one of the expected values
        self.assertIn(activity_dict["artist"], self.collector.artists)

        # Verify that tracks match the artist
        self.assertIn(activity_dict["track"], self.collector.tracks_by_artist[activity_dict["artist"]])

        # Verify that albums match the artist
        self.assertIn(activity_dict["album"], self.collector.albums_by_artist[activity_dict["artist"]])

        # Verify that genres match the artist
        self.assertIn(activity_dict["genre"], self.collector.genres_by_artist[activity_dict["artist"]])

        # Verify duration_seconds is in the expected range
        self.assertGreaterEqual(activity_dict["duration_seconds"], 120)
        self.assertLessEqual(activity_dict["duration_seconds"], 300)

        # Verify platform is one of the expected values
        self.assertIn(activity_dict["platform"], self.collector.platforms)

    def test_generate_batch_method(self):
        """Test the generate_batch method of the MusicActivityCollector."""
        # Generate a batch of 5 activities
        batch = self.collector.generate_batch(5)

        # Verify the batch contains 5 activities
        self.assertEqual(len(batch), 5)

        # Verify each activity has the required fields
        for activity_dict in batch:
            self.assertIn("artist", activity_dict)
            self.assertIn("track", activity_dict)
            self.assertIn("album", activity_dict)
            self.assertIn("genre", activity_dict)
            self.assertIn("duration_seconds", activity_dict)
            self.assertIn("platform", activity_dict)
            self.assertIn("created_at", activity_dict)
            self.assertIn("source", activity_dict)

    def test_generate_truth_data_method(self):
        """Test the generate_truth_data method of the MusicActivityCollector."""
        # Generate truth data for a query that contains an artist name
        query = "Find songs by Taylor Swift"
        truth_data = self.collector.generate_truth_data(query)

        # Verify truth data is a set of UUIDs
        self.assertIsInstance(truth_data, set)
        for entity_id in truth_data:
            self.assertIsInstance(entity_id, uuid.UUID)

        # Verify truth data contains entries for the artist
        self.assertGreater(len(truth_data), 0)

        # Generate truth data for a query that contains a track name
        query = "Find songs like Blank Space"
        truth_data = self.collector.generate_truth_data(query)

        # Verify truth data is a set of UUIDs
        self.assertIsInstance(truth_data, set)
        self.assertGreater(len(truth_data), 0)

        # Generate truth data for a query that contains a genre
        query = "Find Pop music"
        truth_data = self.collector.generate_truth_data(query)

        # Verify truth data is a set of UUIDs
        self.assertIsInstance(truth_data, set)
        self.assertGreater(len(truth_data), 0)

    def test_generate_matching_data_method(self):
        """Test the generate_matching_data method of the MusicActivityCollector."""
        # Generate matching data for a query that contains an artist name
        query = "Find songs by Taylor Swift"
        matching_data = self.collector.generate_matching_data(query, count=3)

        # Verify matching data is a list of dictionaries
        self.assertIsInstance(matching_data, list)
        self.assertEqual(len(matching_data), 3)

        # Verify each matching activity contains the artist name
        for activity_dict in matching_data:
            self.assertEqual(activity_dict["artist"], "Taylor Swift")

            # Verify the track is one of Taylor Swift's tracks
            self.assertIn(activity_dict["track"], self.collector.tracks_by_artist["Taylor Swift"])

    def test_generate_non_matching_data_method(self):
        """Test the generate_non_matching_data method of the MusicActivityCollector."""
        # Generate non-matching data for a query that contains an artist name
        query = "Find songs by Taylor Swift"
        non_matching_data = self.collector.generate_non_matching_data(query, count=3)

        # Verify non-matching data is a list of dictionaries
        self.assertIsInstance(non_matching_data, list)
        self.assertEqual(len(non_matching_data), 3)

        # Verify each non-matching activity does not contain the artist name
        for activity_dict in non_matching_data:
            self.assertNotEqual(activity_dict["artist"], "Taylor Swift")

        # Verify created_at dates are further in the past
        for activity_dict in non_matching_data:
            # Non-matching activities should be from 10-30 days ago
            days_ago = (datetime.now(UTC) - activity_dict["created_at"]).days
            self.assertGreaterEqual(days_ago, 10)

    def test_seed_method(self):
        """Test the seed method of the MusicActivityCollector."""
        # Create two collectors with different seeds
        collector1 = MusicActivityCollector(seed_value=123)
        collector2 = MusicActivityCollector(seed_value=456)

        # Generate activities from both collectors
        activity1 = collector1.collect()
        activity2 = collector2.collect()

        # Activities should be different with different seeds
        # At least one attribute should be different
        different_attributes = 0
        if activity1["artist"] != activity2["artist"]:
            different_attributes += 1
        if activity1["track"] != activity2["track"]:
            different_attributes += 1
        if activity1["album"] != activity2["album"]:
            different_attributes += 1
        if activity1["genre"] != activity2["genre"]:
            different_attributes += 1
        if activity1["platform"] != activity2["platform"]:
            different_attributes += 1

        # Verify at least one attribute is different
        self.assertGreater(different_attributes, 0)


class TestMusicActivityRecorder(unittest.TestCase):
    """Test cases for the music activity recorder."""

    def setUp(self):
        """Set up test fixtures."""
        # Set a fixed seed for deterministic testing
        random.seed(42)

        # Mock the database connection
        self.db_mock = MagicMock()
        self.collection_mock = MagicMock()
        self.truth_collection_mock = MagicMock()
        
        # Setup the recorder with mocks
        self.patcher = patch('research.ablation.recorders.music_recorder.IndalekoDBConfig')
        self.mock_db_config = self.patcher.start()
        self.mock_db_config.return_value.get_arangodb.return_value = self.db_mock
        self.db_mock.collection.side_effect = lambda name: self.collection_mock if name == IndalekoDBCollections.Indaleko_Ablation_Music_Activity_Collection else self.truth_collection_mock

        # Create a recorder
        self.recorder = MusicActivityRecorder()
        self.recorder.db = self.db_mock
        self.recorder.collection = self.collection_mock
        self.recorder.truth_collection = self.truth_collection_mock

    def tearDown(self):
        """Clean up after tests."""
        self.patcher.stop()

    def test_record_method(self):
        """Test the record method of the MusicActivityRecorder."""
        # Create test data
        test_data = {
            "artist": "Taylor Swift",
            "track": "Blank Space",
            "album": "1989",
            "genre": "Pop",
            "duration_seconds": 180,
            "platform": "Spotify",
            "id": str(uuid.uuid4()),
            "_key": "test_key"
        }

        # Set up mock to return success
        self.collection_mock.insert.return_value = True

        # Record the data
        result = self.recorder.record(test_data)

        # Verify the result is True (success)
        self.assertTrue(result)

        # Verify the collection.insert method was called with the test data
        self.collection_mock.insert.assert_called_once_with(test_data)

    def test_record_batch_method(self):
        """Test the record_batch method of the MusicActivityRecorder."""
        # Create a batch of test data
        batch_data = []
        for i in range(3):
            batch_data.append({
                "artist": f"Artist {i}",
                "track": f"Track {i}",
                "album": f"Album {i}",
                "genre": "Pop",
                "duration_seconds": 180,
                "platform": "Spotify",
                "id": str(uuid.uuid4()),
                "_key": f"test_key_{i}"
            })

        # Set up mock to return success for each insert
        self.collection_mock.insert.return_value = True

        # Record the batch
        result = self.recorder.record_batch(batch_data)

        # Verify the result is True (success)
        self.assertTrue(result)

        # Verify the collection.insert method was called once for each item in the batch
        self.assertEqual(self.collection_mock.insert.call_count, len(batch_data))

    def test_record_truth_data_method(self):
        """Test the record_truth_data method of the MusicActivityRecorder."""
        # Create test query ID and entity IDs
        query_id = uuid.uuid4()
        entity_ids = {uuid.uuid4() for _ in range(3)}

        # Set up mock to return success
        self.truth_collection_mock.insert.return_value = True

        # Record the truth data
        result = self.recorder.record_truth_data(query_id, entity_ids)

        # Verify the result is True (success)
        self.assertTrue(result)

        # Verify the truth_collection.insert method was called
        self.truth_collection_mock.insert.assert_called_once()

        # Verify the truth data document contains the query ID and entity IDs
        call_args = self.truth_collection_mock.insert.call_args[0][0]
        self.assertEqual(call_args["query_id"], str(query_id))
        self.assertEqual(len(call_args["entity_ids"]), len(entity_ids))

    def test_get_collection_name_method(self):
        """Test the get_collection_name method of the MusicActivityRecorder."""
        # Get the collection name
        collection_name = self.recorder.get_collection_name()

        # Verify the collection name is correct
        self.assertEqual(collection_name, IndalekoDBCollections.Indaleko_Ablation_Music_Activity_Collection)

    def test_count_records_method(self):
        """Test the count_records method of the MusicActivityRecorder."""
        # Set up mock to return a cursor with a count
        mock_cursor = MagicMock()
        mock_cursor.__next__.return_value = 10
        self.db_mock.aql.execute.return_value = mock_cursor

        # Count records
        count = self.recorder.count_records()

        # Verify the count is correct
        self.assertEqual(count, 10)

        # Verify the aql.execute method was called with the correct query
        self.db_mock.aql.execute.assert_called_once()
        call_args = self.db_mock.aql.execute.call_args[0][0]
        self.assertIn(f"LENGTH({IndalekoDBCollections.Indaleko_Ablation_Music_Activity_Collection})", call_args)

    def test_delete_all_method(self):
        """Test the delete_all method of the MusicActivityRecorder."""
        # Set up mock to return success
        self.db_mock.aql.execute.return_value = MagicMock()

        # Delete all records
        result = self.recorder.delete_all()

        # Verify the result is True (success)
        self.assertTrue(result)

        # Verify the aql.execute method was called with the correct query
        self.db_mock.aql.execute.assert_called_once()
        call_args = self.db_mock.aql.execute.call_args[0][0]
        self.assertIn(f"REMOVE doc IN {IndalekoDBCollections.Indaleko_Ablation_Music_Activity_Collection}", call_args)


if __name__ == "__main__":
    unittest.main()