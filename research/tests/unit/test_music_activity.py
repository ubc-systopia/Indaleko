"""Unit tests for the music activity models."""

import unittest
from datetime import datetime
from uuid import UUID

from research.ablation.models.activity import ActivityType

# Import the models to test
from research.ablation.models.music_activity import MusicActivity


class TestMusicActivity(unittest.TestCase):
    """Test the MusicActivity model."""

    def setUp(self):
        """Set up test data."""
        self.test_data = {
            "artist": "Taylor Swift",
            "track": "Blank Space",
            "album": "1989",
            "genre": "Pop",
            "duration_seconds": 180,
            "platform": "Spotify",
        }

    def test_init(self):
        """Test that the activity is initialized correctly."""
        activity = MusicActivity(**self.test_data)

        # Check that the activity type is set correctly
        self.assertEqual(activity.activity_type, ActivityType.MUSIC)

        # Check that the fields are set correctly
        self.assertEqual(activity.artist, self.test_data["artist"])
        self.assertEqual(activity.track, self.test_data["track"])
        self.assertEqual(activity.album, self.test_data["album"])
        self.assertEqual(activity.genre, self.test_data["genre"])
        self.assertEqual(activity.duration_seconds, self.test_data["duration_seconds"])
        self.assertEqual(activity.platform, self.test_data["platform"])

        # Check that the timestamp is set
        self.assertIsInstance(activity.created_at, datetime)
        self.assertIsInstance(activity.modified_at, datetime)

        # Check that the ID is set
        self.assertIsInstance(activity.id, UUID)

    def test_semantic_attributes(self):
        """Test that semantic attributes are created correctly."""
        activity = MusicActivity(**self.test_data)

        # Check that semantic attributes are created
        self.assertGreater(len(activity.semantic_attributes), 0)

        # Check that artist attribute is set
        self.assertIn("music.artist", activity.semantic_attributes)
        self.assertEqual(activity.semantic_attributes["music.artist"]["Value"], self.test_data["artist"])

        # Check that track attribute is set
        self.assertIn("music.track", activity.semantic_attributes)
        self.assertEqual(activity.semantic_attributes["music.track"]["Value"], self.test_data["track"])

        # Check that album attribute is set
        self.assertIn("music.album", activity.semantic_attributes)
        self.assertEqual(activity.semantic_attributes["music.album"]["Value"], self.test_data["album"])

        # Check that genre attribute is set
        self.assertIn("music.genre", activity.semantic_attributes)
        self.assertEqual(activity.semantic_attributes["music.genre"]["Value"], self.test_data["genre"])

        # Check that duration attribute is set
        self.assertIn("music.duration", activity.semantic_attributes)
        self.assertEqual(activity.semantic_attributes["music.duration"]["Value"], self.test_data["duration_seconds"])

        # Check that source attribute is set
        self.assertIn("music.source", activity.semantic_attributes)
        self.assertEqual(activity.semantic_attributes["music.source"]["Value"], self.test_data["platform"])

    def test_without_optional_fields(self):
        """Test that the activity works without optional fields."""
        # Remove optional fields
        data = self.test_data.copy()
        del data["album"]
        del data["genre"]

        activity = MusicActivity(**data)

        # Check that the activity type is set correctly
        self.assertEqual(activity.activity_type, ActivityType.MUSIC)

        # Check that the required fields are set correctly
        self.assertEqual(activity.artist, data["artist"])
        self.assertEqual(activity.track, data["track"])
        self.assertEqual(activity.duration_seconds, data["duration_seconds"])
        self.assertEqual(activity.platform, data["platform"])

        # Check that the optional fields are None
        self.assertIsNone(activity.album)
        self.assertIsNone(activity.genre)

        # Check that semantic attributes for optional fields are not set
        self.assertNotIn("music.album", activity.semantic_attributes)
        self.assertNotIn("music.genre", activity.semantic_attributes)


if __name__ == "__main__":
    unittest.main()
