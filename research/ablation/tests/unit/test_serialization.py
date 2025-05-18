"""Unit tests for serialization utilities."""

import json
import os
import tempfile
import unittest
from datetime import UTC, datetime
from uuid import uuid4

from ...error import ValidationError
from ...models import (
    ActivityData,
    ActivityType,
    LocationActivity,
    LocationCoordinates,
    MusicActivity,
    TruthData,
)
from ...utils.serialization import (
    batch_from_json,
    batch_load_from_file,
    batch_save_to_file,
    batch_to_json,
    from_dict,
    from_json,
    load_from_file,
    save_to_file,
    to_dict,
    to_json,
)
from ..test_utils import AblationTestCase


class TestSerializationUtils(AblationTestCase):
    """Test cases for serialization utilities."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

        # Create test data
        self.activity_data = ActivityData(
            id=uuid4(),
            activity_type=ActivityType.MUSIC,
            created_at=datetime.now(UTC),
            modified_at=datetime.now(UTC),
            source="test",
            semantic_attributes={},
        )

        self.music_data = MusicActivity(
            artist="Test Artist",
            track="Test Track",
            album="Test Album",
            genre="Test Genre",
            duration_seconds=180,
            platform="Spotify",
        )

        coords = LocationCoordinates(
            latitude=37.7749,
            longitude=-122.4194,
            accuracy_meters=10.0,
        )

        self.location_data = LocationActivity(
            location_name="San Francisco",
            coordinates=coords,
            location_type="city",
            device_name="Phone",
            wifi_ssid="TestWiFi",
            source="gps",
        )

        self.truth_data = TruthData(
            query_id=uuid4(),
            query_text="Find songs by Artist X",
            matching_entities=[uuid4(), uuid4()],
            activity_types=[ActivityType.MUSIC],
            created_at=datetime.now(UTC),
        )

    def test_to_dict(self):
        """Test conversion to dictionary."""
        # Test with ActivityData
        activity_dict = to_dict(self.activity_data)
        self.assertIsInstance(activity_dict, dict)
        self.assertEqual(str(self.activity_data.id), activity_dict["id"])
        self.assertEqual(self.activity_data.activity_type.name, activity_dict["activity_type"])

        # Test with TruthData
        truth_dict = to_dict(self.truth_data)
        self.assertIsInstance(truth_dict, dict)
        self.assertEqual(str(self.truth_data.query_id), truth_dict["query_id"])
        self.assertEqual(self.truth_data.query_text, truth_dict["query_text"])

        # Test with dictionary
        test_dict = {"a": 1, "b": 2}
        self.assertEqual(test_dict, to_dict(test_dict))

    def test_to_json(self):
        """Test conversion to JSON."""
        # Test with ActivityData
        activity_json = to_json(self.activity_data)
        self.assertIsInstance(activity_json, str)

        # Validate JSON format
        activity_data = json.loads(activity_json)
        self.assertEqual(str(self.activity_data.id), activity_data["id"])

        # Test pretty JSON
        pretty_json = to_json(self.activity_data, pretty=True)
        self.assertIn("\n", pretty_json)

        # Test with MusicActivity
        music_json = to_json(self.music_data)
        music_data = json.loads(music_json)
        self.assertEqual(self.music_data.artist, music_data["artist"])
        self.assertEqual(self.music_data.track, music_data["track"])

        # Test with TruthData
        truth_json = to_json(self.truth_data)
        truth_data = json.loads(truth_json)
        self.assertEqual(str(self.truth_data.query_id), truth_data["query_id"])

    def test_from_dict(self):
        """Test conversion from dictionary."""
        # Test with ActivityData
        activity_dict = to_dict(self.activity_data)
        activity = from_dict(activity_dict)
        self.assertIsInstance(activity, ActivityData)
        self.assertEqual(self.activity_data.id, activity.id)
        self.assertEqual(self.activity_data.activity_type, activity.activity_type)

        # Test with MusicActivity
        music_dict = to_dict(self.music_data)
        music = from_dict(music_dict)
        self.assertIsInstance(music, MusicActivity)
        self.assertEqual(self.music_data.artist, music.artist)
        self.assertEqual(self.music_data.track, music.track)

        # Test with TruthData
        truth_dict = to_dict(self.truth_data)
        truth = from_dict(truth_dict)
        self.assertIsInstance(truth, TruthData)
        self.assertEqual(self.truth_data.query_id, truth.query_id)
        self.assertEqual(self.truth_data.query_text, truth.query_text)

        # Test with invalid data
        with self.assertRaises(ValidationError):
            from_dict({})

    def test_from_json(self):
        """Test conversion from JSON."""
        # Test with ActivityData
        activity_json = to_json(self.activity_data)
        activity = from_json(activity_json)
        self.assertIsInstance(activity, ActivityData)
        self.assertEqual(self.activity_data.id, activity.id)
        self.assertEqual(self.activity_data.activity_type, activity.activity_type)

        # Test with MusicActivity
        music_json = to_json(self.music_data)
        music = from_json(music_json)
        self.assertIsInstance(music, MusicActivity)
        self.assertEqual(self.music_data.artist, music.artist)
        self.assertEqual(self.music_data.track, music.track)

        # Test with TruthData
        truth_json = to_json(self.truth_data)
        truth = from_json(truth_json)
        self.assertIsInstance(truth, TruthData)
        self.assertEqual(self.truth_data.query_id, truth.query_id)
        self.assertEqual(self.truth_data.query_text, truth.query_text)

        # Test with invalid JSON
        with self.assertRaises(ValidationError):
            from_json("{invalid}")

    def test_batch_to_json(self):
        """Test batch conversion to JSON."""
        # Create a list of data
        data_list = [self.activity_data, self.music_data, self.location_data, self.truth_data]

        # Convert to JSON
        json_str = batch_to_json(data_list)
        self.assertIsInstance(json_str, str)

        # Validate JSON format
        data = json.loads(json_str)
        self.assertIsInstance(data, list)
        self.assertEqual(4, len(data))

        # Test pretty JSON
        pretty_json = batch_to_json(data_list, pretty=True)
        self.assertIn("\n", pretty_json)

    def test_batch_from_json(self):
        """Test batch conversion from JSON."""
        # Create a list of data
        data_list = [self.activity_data, self.music_data, self.location_data, self.truth_data]

        # Convert to JSON
        json_str = batch_to_json(data_list)

        # Convert back
        result = batch_from_json(json_str)
        self.assertIsInstance(result, list)
        self.assertEqual(4, len(result))
        self.assertIsInstance(result[0], ActivityData)
        self.assertIsInstance(result[1], MusicActivity)
        self.assertIsInstance(result[2], LocationActivity)
        self.assertIsInstance(result[3], TruthData)

        # Test with invalid JSON
        with self.assertRaises(ValidationError):
            batch_from_json("{invalid}")

        # Test with JSON that is not a list
        with self.assertRaises(ValidationError):
            batch_from_json("{}")

    def test_save_and_load(self):
        """Test saving and loading to/from a file."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp_path = temp.name

        try:
            # Save to file
            save_to_file(self.music_data, temp_path)

            # Load from file
            result = load_from_file(temp_path)
            self.assertIsInstance(result, MusicActivity)
            self.assertEqual(self.music_data.artist, result.artist)
            self.assertEqual(self.music_data.track, result.track)

            # Test with nonexistent file
            with self.assertRaises(ValidationError):
                load_from_file("nonexistent.json")
        finally:
            # Clean up
            os.unlink(temp_path)

    def test_batch_save_and_load(self):
        """Test batch saving and loading to/from a file."""
        # Create a list of data
        data_list = [self.activity_data, self.music_data, self.location_data, self.truth_data]

        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp_path = temp.name

        try:
            # Save to file
            batch_save_to_file(data_list, temp_path)

            # Load from file
            result = batch_load_from_file(temp_path)
            self.assertIsInstance(result, list)
            self.assertEqual(4, len(result))
            self.assertIsInstance(result[0], ActivityData)
            self.assertIsInstance(result[1], MusicActivity)
            self.assertIsInstance(result[2], LocationActivity)
            self.assertIsInstance(result[3], TruthData)

            # Test with nonexistent file
            with self.assertRaises(ValidationError):
                batch_load_from_file("nonexistent.json")
        finally:
            # Clean up
            os.unlink(temp_path)


if __name__ == "__main__":
    unittest.main()
