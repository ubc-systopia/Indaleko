"""Unit tests for ablation data models."""

import unittest
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import ValidationError

from ...models import (
    ActivityData,
    ActivityType,
    CollaborationActivity,
    LocationActivity,
    LocationCoordinates,
    MediaActivity,
    MediaType,
    MusicActivity,
    StorageActivity,
    StorageOperationType,
    TaskActivity,
    TruthData,
)
from ...utils.validation import validate_activity_data
from ..test_utils import AblationTestCase


class TestActivityBaseModel(AblationTestCase):
    """Test cases for the base ActivityData model."""

    def test_create_activity_data(self):
        """Test creating an ActivityData instance."""
        # Create an ActivityData instance
        activity = ActivityData(
            id=uuid4(),
            activity_type=ActivityType.MUSIC,
            created_at=datetime.now(UTC),
            modified_at=datetime.now(UTC),
            source="test",
            semantic_attributes={},
        )

        # Check that the instance was created correctly
        self.assertEqual(ActivityType.MUSIC, activity.activity_type)
        self.assertEqual("test", activity.source)
        self.assertIsInstance(activity.id, UUID)

    def test_activity_data_validation(self):
        """Test validation of ActivityData."""
        # Test with missing required fields
        with self.assertRaises(ValidationError):
            ActivityData(
                id=uuid4(),
                # Missing activity_type
                created_at=datetime.now(UTC),
                modified_at=datetime.now(UTC),
                source="test",
                semantic_attributes={},
            )

        # Test with invalid field types
        with self.assertRaises(ValidationError):
            ActivityData(
                id="not-a-uuid",  # Not a UUID
                activity_type=ActivityType.MUSIC,
                created_at=datetime.now(UTC),
                modified_at=datetime.now(UTC),
                source="test",
                semantic_attributes={},
            )

        with self.assertRaises(ValidationError):
            ActivityData(
                id=uuid4(),
                activity_type="invalid-type",  # Not an ActivityType
                created_at=datetime.now(UTC),
                modified_at=datetime.now(UTC),
                source="test",
                semantic_attributes={},
            )

        # Test with a naive datetime (no timezone)
        with self.assertRaises(ValidationError):
            ActivityData(
                id=uuid4(),
                activity_type=ActivityType.MUSIC,
                created_at=datetime.now(),  # Naive datetime (no timezone)
                modified_at=datetime.now(UTC),
                source="test",
                semantic_attributes={},
            )

    def test_truth_data_creation(self):
        """Test creating a TruthData instance."""
        # Create a TruthData instance
        truth = TruthData(
            query_id=uuid4(),
            query_text="Find songs by Artist X",
            matching_entities=[uuid4(), uuid4()],
            activity_types=[ActivityType.MUSIC],
            created_at=datetime.now(UTC),
        )

        # Check that the instance was created correctly
        self.assertEqual("Find songs by Artist X", truth.query_text)
        self.assertEqual(2, len(truth.matching_entities))
        self.assertEqual(1, len(truth.activity_types))
        self.assertEqual(ActivityType.MUSIC, truth.activity_types[0])

    def test_truth_data_validation(self):
        """Test validation of TruthData."""
        # Test with missing required fields
        with self.assertRaises(ValidationError):
            TruthData(
                query_id=uuid4(),
                # Missing query_text
                matching_entities=[uuid4(), uuid4()],
                activity_types=[ActivityType.MUSIC],
                created_at=datetime.now(UTC),
            )

        # Test with invalid field types
        with self.assertRaises(ValidationError):
            TruthData(
                query_id="not-a-uuid",  # Not a UUID
                query_text="Find songs by Artist X",
                matching_entities=[uuid4(), uuid4()],
                activity_types=[ActivityType.MUSIC],
                created_at=datetime.now(UTC),
            )

        # Test with invalid list items
        with self.assertRaises(ValidationError):
            TruthData(
                query_id=uuid4(),
                query_text="Find songs by Artist X",
                matching_entities=["not-a-uuid"],  # Not a list of UUIDs
                activity_types=[ActivityType.MUSIC],
                created_at=datetime.now(UTC),
            )


class TestMusicActivityModel(AblationTestCase):
    """Test cases for the MusicActivity model."""

    def test_create_music_activity(self):
        """Test creating a MusicActivity instance."""
        # Create a MusicActivity instance
        music = MusicActivity(
            artist="Test Artist",
            track="Test Track",
            album="Test Album",
            genre="Test Genre",
            duration_seconds=180,
            platform="Spotify",
        )

        # Check that the instance was created correctly
        self.assertEqual("Test Artist", music.artist)
        self.assertEqual("Test Track", music.track)
        self.assertEqual("Test Album", music.album)
        self.assertEqual("Test Genre", music.genre)
        self.assertEqual(180, music.duration_seconds)
        self.assertEqual("Spotify", music.platform)
        self.assertEqual(ActivityType.MUSIC, music.activity_type)

        # Check that semantic attributes were created
        self.assertIn("music.artist", music.semantic_attributes)
        self.assertIn("music.track", music.semantic_attributes)
        self.assertIn("music.album", music.semantic_attributes)
        self.assertIn("music.genre", music.semantic_attributes)
        self.assertIn("music.duration", music.semantic_attributes)
        self.assertIn("music.source", music.semantic_attributes)

    def test_music_activity_validation(self):
        """Test validation of MusicActivity."""
        # Test with missing required fields
        with self.assertRaises(ValidationError):
            MusicActivity(
                # Missing artist
                track="Test Track",
                album="Test Album",
                genre="Test Genre",
                duration_seconds=180,
                platform="Spotify",
            )

        # Test with invalid field types
        with self.assertRaises(ValidationError):
            MusicActivity(
                artist="Test Artist",
                track="Test Track",
                album="Test Album",
                genre="Test Genre",
                duration_seconds="not-an-int",  # Not an integer
                platform="Spotify",
            )

        # Test custom validation
        errors = validate_activity_data(
            {
                "id": str(uuid4()),
                "activity_type": "MUSIC",
                "created_at": datetime.now(UTC).isoformat(),
                "modified_at": datetime.now(UTC).isoformat(),
                "source": "test",
                "semantic_attributes": {},
                "artist": "Test Artist",
                "track": "Test Track",
                "album": "Test Album",
                "genre": "Test Genre",
                "duration_seconds": 180,
                "platform": "Spotify",
            },
            ActivityType.MUSIC,
        )

        # Should be no errors
        self.assertEqual(0, len(errors))


class TestLocationActivityModel(AblationTestCase):
    """Test cases for the LocationActivity model."""

    def test_create_location_activity(self):
        """Test creating a LocationActivity instance."""
        # Create coordinates
        coords = LocationCoordinates(
            latitude=37.7749,
            longitude=-122.4194,
            accuracy_meters=10.0,
        )

        # Create a LocationActivity instance
        location = LocationActivity(
            location_name="San Francisco",
            coordinates=coords,
            location_type="city",
            device_name="Phone",
            wifi_ssid="TestWiFi",
            source="gps",
        )

        # Check that the instance was created correctly
        self.assertEqual("San Francisco", location.location_name)
        self.assertEqual(coords, location.coordinates)
        self.assertEqual("city", location.location_type)
        self.assertEqual("Phone", location.device_name)
        self.assertEqual("TestWiFi", location.wifi_ssid)
        self.assertEqual("gps", location.source)
        self.assertEqual(ActivityType.LOCATION, location.activity_type)

        # Check that semantic attributes were created
        self.assertIn("location.name", location.semantic_attributes)
        self.assertIn("location.coordinates", location.semantic_attributes)
        self.assertIn("location.type", location.semantic_attributes)
        self.assertIn("location.device", location.semantic_attributes)
        self.assertIn("location.wifi_ssid", location.semantic_attributes)
        self.assertIn("location.source", location.semantic_attributes)

    def test_location_coordinates(self):
        """Test LocationCoordinates."""
        # Create coordinates
        coords = LocationCoordinates(
            latitude=37.7749,
            longitude=-122.4194,
            accuracy_meters=10.0,
        )

        # Check that the instance was created correctly
        self.assertEqual(37.7749, coords.latitude)
        self.assertEqual(-122.4194, coords.longitude)
        self.assertEqual(10.0, coords.accuracy_meters)

        # Check string representation
        self.assertEqual("37.7749,-122.4194", str(coords))


class TestTaskActivityModel(AblationTestCase):
    """Test cases for the TaskActivity model."""

    def test_create_task_activity(self):
        """Test creating a TaskActivity instance."""
        # Create a TaskActivity instance
        task = TaskActivity(
            task_name="Coding",
            application="VS Code",
            window_title="project.py",
            duration_seconds=3600,
            active=True,
            source="windows_task_manager",
        )

        # Check that the instance was created correctly
        self.assertEqual("Coding", task.task_name)
        self.assertEqual("VS Code", task.application)
        self.assertEqual("project.py", task.window_title)
        self.assertEqual(3600, task.duration_seconds)
        self.assertEqual(True, task.active)
        self.assertEqual("windows_task_manager", task.source)
        self.assertEqual(ActivityType.TASK, task.activity_type)

        # Check that semantic attributes were created
        self.assertIn("task.name", task.semantic_attributes)
        self.assertIn("task.application", task.semantic_attributes)
        self.assertIn("task.window_title", task.semantic_attributes)
        self.assertIn("task.duration", task.semantic_attributes)
        self.assertIn("task.active", task.semantic_attributes)
        self.assertIn("task.source", task.semantic_attributes)


class TestCollaborationActivityModel(AblationTestCase):
    """Test cases for the CollaborationActivity model."""

    def test_create_collaboration_activity(self):
        """Test creating a CollaborationActivity instance."""
        # Create a CollaborationActivity instance
        collab = CollaborationActivity(
            platform="Teams",
            event_type="Meeting",
            participants=[
                {"name": "User 1", "email": "user1@example.com"},
                {"name": "User 2", "email": "user2@example.com"},
            ],
            content="Project meeting",
            duration_seconds=1800,
            source="outlook",
        )

        # Check that the instance was created correctly
        self.assertEqual("Teams", collab.platform)
        self.assertEqual("Meeting", collab.event_type)
        self.assertEqual(2, len(collab.participants))
        self.assertEqual("User 1", collab.participants[0].name)
        self.assertEqual("user1@example.com", collab.participants[0].email)
        self.assertEqual("Project meeting", collab.content)
        self.assertEqual(1800, collab.duration_seconds)
        self.assertEqual("outlook", collab.source)
        self.assertEqual(ActivityType.COLLABORATION, collab.activity_type)

        # Check that semantic attributes were created
        self.assertIn("collaboration.platform", collab.semantic_attributes)
        self.assertIn("collaboration.type", collab.semantic_attributes)
        self.assertIn("collaboration.participants", collab.semantic_attributes)
        self.assertIn("collaboration.content", collab.semantic_attributes)
        self.assertIn("collaboration.duration", collab.semantic_attributes)
        self.assertIn("collaboration.source", collab.semantic_attributes)


class TestStorageActivityModel(AblationTestCase):
    """Test cases for the StorageActivity model."""

    def test_create_storage_activity(self):
        """Test creating a StorageActivity instance."""
        # Create a StorageActivity instance
        storage = StorageActivity(
            path="/path/to/file.txt",
            file_type="Document",
            size_bytes=1024,
            operation=StorageOperationType.CREATE,
            source="ntfs",
        )

        # Check that the instance was created correctly
        self.assertEqual("/path/to/file.txt", storage.path)
        self.assertEqual("Document", storage.file_type)
        self.assertEqual(1024, storage.size_bytes)
        self.assertEqual(StorageOperationType.CREATE, storage.operation)
        self.assertEqual("ntfs", storage.source)
        self.assertEqual(ActivityType.STORAGE, storage.activity_type)

        # Check that semantic attributes were created
        self.assertIn("storage.path", storage.semantic_attributes)
        self.assertIn("storage.file_type", storage.semantic_attributes)
        self.assertIn("storage.size", storage.semantic_attributes)
        self.assertIn("storage.operation", storage.semantic_attributes)
        self.assertIn("storage.timestamp", storage.semantic_attributes)
        self.assertIn("storage.source", storage.semantic_attributes)

    def test_storage_factory_methods(self):
        """Test factory methods for StorageActivity."""
        # Test file created
        created = StorageActivity.create_file_created(
            path="/path/to/file.txt",
            file_type="Document",
            size_bytes=1024,
            source="ntfs",
        )
        self.assertEqual(StorageOperationType.CREATE, created.operation)

        # Test file accessed
        accessed = StorageActivity.create_file_accessed(
            path="/path/to/file.txt",
            file_type="Document",
            size_bytes=1024,
            source="ntfs",
        )
        self.assertEqual(StorageOperationType.READ, accessed.operation)

        # Test file modified
        modified = StorageActivity.create_file_modified(
            path="/path/to/file.txt",
            file_type="Document",
            size_bytes=1024,
            source="ntfs",
        )
        self.assertEqual(StorageOperationType.UPDATE, modified.operation)

        # Test file deleted
        deleted = StorageActivity.create_file_deleted(
            path="/path/to/file.txt",
            file_type="Document",
            size_bytes=1024,
            source="ntfs",
        )
        self.assertEqual(StorageOperationType.DELETE, deleted.operation)

        # Test file renamed
        renamed = StorageActivity.create_file_renamed(
            old_path="/path/to/old.txt",
            new_path="/path/to/new.txt",
            file_type="Document",
            size_bytes=1024,
            source="ntfs",
        )
        self.assertEqual(StorageOperationType.RENAME, renamed.operation)
        self.assertEqual("/path/to/new.txt", renamed.path)
        self.assertEqual("/path/to/old.txt", renamed.related_path)

        # Test file moved
        moved = StorageActivity.create_file_moved(
            old_path="/old/path/file.txt",
            new_path="/new/path/file.txt",
            file_type="Document",
            size_bytes=1024,
            source="ntfs",
        )
        self.assertEqual(StorageOperationType.MOVE, moved.operation)
        self.assertEqual("/new/path/file.txt", moved.path)
        self.assertEqual("/old/path/file.txt", moved.related_path)

        # Test file copied
        copied = StorageActivity.create_file_copied(
            original_path="/original/path/file.txt",
            new_path="/new/path/file.txt",
            file_type="Document",
            size_bytes=1024,
            source="ntfs",
        )
        self.assertEqual(StorageOperationType.COPY, copied.operation)
        self.assertEqual("/new/path/file.txt", copied.path)
        self.assertEqual("/original/path/file.txt", copied.related_path)


class TestMediaActivityModel(AblationTestCase):
    """Test cases for the MediaActivity model."""

    def test_create_media_activity(self):
        """Test creating a MediaActivity instance."""
        # Create a MediaActivity instance
        media = MediaActivity(
            media_type=MediaType.VIDEO,
            title="Test Video",
            platform="YouTube",
            duration_seconds=600,
            creator="Test Creator",
            url="https://example.com/video",
            source="browser_extension",
        )

        # Check that the instance was created correctly
        self.assertEqual(MediaType.VIDEO, media.media_type)
        self.assertEqual("Test Video", media.title)
        self.assertEqual("YouTube", media.platform)
        self.assertEqual(600, media.duration_seconds)
        self.assertEqual("Test Creator", media.creator)
        self.assertEqual("https://example.com/video", media.url)
        self.assertEqual("browser_extension", media.source)
        self.assertEqual(ActivityType.MEDIA, media.activity_type)

        # Check that semantic attributes were created
        self.assertIn("media.type", media.semantic_attributes)
        self.assertIn("media.title", media.semantic_attributes)
        self.assertIn("media.platform", media.semantic_attributes)
        self.assertIn("media.duration", media.semantic_attributes)
        self.assertIn("media.creator", media.semantic_attributes)
        self.assertIn("media.source", media.semantic_attributes)

    def test_media_factory_methods(self):
        """Test factory methods for MediaActivity."""
        # Test video activity
        video = MediaActivity.create_video_activity(
            title="Test Video",
            platform="YouTube",
            duration_seconds=600,
            creator="Test Creator",
            url="https://example.com/video",
            source="browser_extension",
        )
        self.assertEqual(MediaType.VIDEO, video.media_type)

        # Test audio activity
        audio = MediaActivity.create_audio_activity(
            title="Test Audio",
            platform="Spotify",
            duration_seconds=240,
            creator="Test Creator",
            url="https://example.com/audio",
            source="browser_extension",
        )
        self.assertEqual(MediaType.AUDIO, audio.media_type)

        # Test stream activity
        stream = MediaActivity.create_stream_activity(
            title="Test Stream",
            platform="Twitch",
            duration_seconds=3600,
            creator="Test Creator",
            url="https://example.com/stream",
            source="browser_extension",
        )
        self.assertEqual(MediaType.STREAM, stream.media_type)

        # Test image activity
        image = MediaActivity.create_image_activity(
            title="Test Image",
            platform="Instagram",
            creator="Test Creator",
            url="https://example.com/image",
            source="browser_extension",
        )
        self.assertEqual(MediaType.IMAGE, image.media_type)

        # Test game activity
        game = MediaActivity.create_game_activity(
            title="Test Game",
            platform="Steam",
            duration_seconds=7200,
            creator="Test Creator",
            source="app",
        )
        self.assertEqual(MediaType.GAME, game.media_type)


if __name__ == "__main__":
    unittest.main()
