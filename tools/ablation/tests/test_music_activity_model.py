"""
Tests for the music activity model.

This module contains unit tests for the music activity data models
in the ablation study framework.
"""

import unittest
from datetime import datetime, timezone, timedelta
from uuid import UUID

from tools.ablation.models.music_activity import (
    MusicGenre,
    PlaybackMode,
    StreamingQuality,
    TrackModel,
    AlbumModel,
    ArtistModel,
    PlaybackEventModel,
    MusicActivityModel,
    MusicSemanticAttributes,
    create_music_semantic_attribute,
    create_semantic_attributes_from_music_activity
)


class TestMusicActivityModel(unittest.TestCase):
    """Test case for the music activity models."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a sample artist
        self.artist = ArtistModel(
            name="Taylor Swift",
            genres=[MusicGenre.POP, MusicGenre.COUNTRY],
            origin="USA",
            formed_year=2006
        )

        # Create a sample album
        self.album = AlbumModel(
            title="1989",
            artist="Taylor Swift",
            release_date=datetime(2014, 10, 27, tzinfo=timezone.utc),
            genre=MusicGenre.POP,
            track_count=13,
            total_duration_seconds=3172
        )

        # Create a sample track
        self.track = TrackModel(
            title="Shake It Off",
            artist="Taylor Swift",
            album="1989",
            duration_seconds=219,
            release_date=datetime(2014, 8, 18, tzinfo=timezone.utc),
            genre=MusicGenre.POP,
            track_number=2,
            disc_number=1
        )

    def test_create_music_activity(self):
        """Test creating a music activity model."""
        # Create a sample music activity
        activity = MusicActivityModel(
            track=self.track,
            artist=self.artist,
            album=self.album,
            start_time=datetime.now(timezone.utc),
            playback_mode=PlaybackMode.NORMAL,
            streaming_quality=StreamingQuality.HIGH,
            volume_percent=80,
            device_type="smartphone"
        )

        # Check that the activity was created correctly
        self.assertEqual(activity.track.title, "Shake It Off")
        self.assertEqual(activity.artist.name, "Taylor Swift")
        self.assertEqual(activity.album.title, "1989")
        self.assertEqual(activity.playback_mode, PlaybackMode.NORMAL)
        self.assertEqual(activity.streaming_quality, StreamingQuality.HIGH)
        self.assertEqual(activity.volume_percent, 80)
        self.assertEqual(activity.device_type, "smartphone")
        self.assertFalse(activity.completed)
        self.assertIsNone(activity.end_time)
        self.assertIsNone(activity.duration_seconds)

    def test_update_end_time(self):
        """Test updating the end time of a music activity."""
        # Create a sample music activity
        activity = MusicActivityModel(
            track=self.track,
            artist=self.artist,
            album=self.album,
            start_time=datetime.now(timezone.utc) - timedelta(minutes=3)
        )

        # Update the end time
        activity.update_end_time()

        # Check that the end time was updated
        self.assertIsNotNone(activity.end_time)
        self.assertIsNotNone(activity.duration_seconds)
        self.assertGreater(activity.duration_seconds, 0)

    def test_add_event(self):
        """Test adding a playback event to a music activity."""
        # Create a sample music activity
        activity = MusicActivityModel(
            track=self.track,
            artist=self.artist,
            album=self.album
        )

        # Add some events
        activity.add_event("play", 0)
        activity.add_event("pause", 60)
        activity.add_event("play", 60)
        activity.add_event("skip", 90)

        # Check that the events were added correctly
        self.assertEqual(len(activity.events), 4)
        self.assertEqual(activity.events[0].event_type, "play")
        self.assertEqual(activity.events[0].position_seconds, 0)
        self.assertEqual(activity.events[1].event_type, "pause")
        self.assertEqual(activity.events[1].position_seconds, 60)

    def test_create_semantic_attributes(self):
        """Test creating semantic attributes from a music activity."""
        # Create a sample music activity
        activity = MusicActivityModel(
            track=self.track,
            artist=self.artist,
            album=self.album,
            completed=True,
            liked=True,
            rating=5,
            duration_seconds=219
        )

        # Create semantic attributes
        attributes = create_semantic_attributes_from_music_activity(activity)

        # Check that we got the expected number of attributes
        self.assertGreaterEqual(len(attributes), 10)

        # Check specific attributes
        artist_name_attr = None
        track_title_attr = None
        user_liked_attr = None

        for attr in attributes:
            if attr.Identifier["Identifier"] == str(MusicSemanticAttributes.ARTIST_NAME):
                artist_name_attr = attr
            elif attr.Identifier["Identifier"] == str(MusicSemanticAttributes.TRACK_TITLE):
                track_title_attr = attr
            elif attr.Identifier["Identifier"] == str(MusicSemanticAttributes.USER_LIKED):
                user_liked_attr = attr

        # Check that we found the expected attributes
        self.assertIsNotNone(artist_name_attr)
        self.assertIsNotNone(track_title_attr)
        self.assertIsNotNone(user_liked_attr)

        # Check attribute values
        self.assertEqual(artist_name_attr.Value, "Taylor Swift")
        self.assertEqual(track_title_attr.Value, "Shake It Off")
        self.assertEqual(user_liked_attr.Value, True)

    def test_create_single_semantic_attribute(self):
        """Test creating a single semantic attribute."""
        # Create a semantic attribute
        attr = create_music_semantic_attribute(
            MusicSemanticAttributes.ARTIST_NAME,
            "Artist Name",
            "Taylor Swift"
        )

        # Check that the attribute was created correctly
        self.assertEqual(attr.Identifier["Identifier"], str(MusicSemanticAttributes.ARTIST_NAME))
        self.assertEqual(attr.Identifier["Label"], "Artist Name")
        self.assertEqual(attr.Value, "Taylor Swift")


if __name__ == "__main__":
    unittest.main()
