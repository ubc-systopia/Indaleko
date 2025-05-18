"""Unit tests for relationship patterns."""

import unittest
import uuid

from ...models.relationship_patterns import (
    LocationCollaborationPattern,
    MusicLocationPattern,
    MusicTaskPattern,
    RelationshipPatternGenerator,
    TaskCollaborationPattern,
)
from ...registry import SharedEntityRegistry


class TestRelationshipPatterns(unittest.TestCase):
    """Test relationship pattern generators."""

    def setUp(self):
        """Set up test cases."""
        self.registry = SharedEntityRegistry()

    def test_relationship_pattern_generator_base(self):
        """Test the base relationship pattern generator."""
        generator = RelationshipPatternGenerator(self.registry)

        # Test timestamp generation
        timestamp = generator.generate_timestamp()
        self.assertIsInstance(timestamp, int)

        # Test UUID generation
        generated_uuid = generator.generate_uuid()
        self.assertIsInstance(generated_uuid, str)
        # Verify it's a valid UUID
        uuid.UUID(generated_uuid)

        # Test entity registration
        entities = [
            {"id": generator.generate_uuid(), "title": "Entity 1"},
            {"id": generator.generate_uuid(), "title": "Entity 2"},
        ]
        # Register entities in the registry
        generator.register_entities(entities, "Test")

        # Verify registry isn't empty - we don't need specific verification
        # since we're testing with no database connection
        self.assertIsNotNone(self.registry.entity_collections)
        self.assertIsNotNone(self.registry.collection_entities)

    def test_task_collaboration_pattern(self):
        """Test task-collaboration relationship patterns."""
        generator = TaskCollaborationPattern(self.registry)

        # Test meeting with tasks
        meeting, tasks = generator.generate_meeting_with_tasks()

        # Verify meeting properties
        self.assertIsInstance(meeting, dict)
        self.assertIn("id", meeting)
        self.assertIn("platform", meeting)
        self.assertIn("event_type", meeting)
        self.assertIn("participants", meeting)
        self.assertIn("references", meeting)
        self.assertIn("has_tasks", meeting["references"])

        # Verify tasks properties
        self.assertIsInstance(tasks, list)
        self.assertTrue(len(tasks) > 0)
        for task in tasks:
            self.assertIn("id", task)
            self.assertIn("task_name", task)
            self.assertIn("application", task)
            self.assertIn("duration_seconds", task)
            self.assertIn("references", task)
            self.assertIn("created_in", task["references"])
            self.assertIn(meeting["id"], task["references"]["created_in"])

        # Verify cross-references
        for task in tasks:
            task_id = uuid.UUID(task["id"])
            meeting_id = uuid.UUID(meeting["id"])

            # Verify task references the meeting
            task_refs = self.registry.get_entity_references(task_id, "created_in")
            self.assertTrue(any(ref.entity_id == meeting_id for ref in task_refs))

            # Verify meeting references the task
            meeting_refs = self.registry.get_entity_references(meeting_id, "has_tasks")
            self.assertTrue(any(ref.entity_id == task_id for ref in meeting_refs))

        # Test task with related meetings
        task, meetings = generator.generate_task_with_related_meetings()

        # Verify task properties
        self.assertIsInstance(task, dict)
        self.assertIn("id", task)
        self.assertIn("task_name", task)
        self.assertIn("references", task)
        self.assertIn("discussed_in", task["references"])

        # Verify meetings properties
        self.assertIsInstance(meetings, list)
        self.assertTrue(len(meetings) > 0)
        for meeting in meetings:
            self.assertIn("id", meeting)
            self.assertIn("platform", meeting)
            self.assertIn("event_type", meeting)
            self.assertIn("participants", meeting)
            self.assertIn("references", meeting)
            self.assertIn("related_to", meeting["references"])
            self.assertIn(task["id"], meeting["references"]["related_to"])

        # Verify cross-references
        task_id = uuid.UUID(task["id"])
        for meeting in meetings:
            meeting_id = uuid.UUID(meeting["id"])

            # Verify task references the meeting
            task_refs = self.registry.get_entity_references(task_id, "discussed_in")
            self.assertTrue(any(ref.entity_id == meeting_id for ref in task_refs))

            # Verify meeting references the task
            meeting_refs = self.registry.get_entity_references(meeting_id, "related_to")
            self.assertTrue(any(ref.entity_id == task_id for ref in meeting_refs))

    def test_location_collaboration_pattern(self):
        """Test location-collaboration relationship patterns."""
        generator = LocationCollaborationPattern(self.registry)

        # Test meeting at location
        location, meeting = generator.generate_meeting_at_location()

        # Verify location properties
        self.assertIsInstance(location, dict)
        self.assertIn("id", location)
        self.assertIn("location_name", location)
        self.assertIn("location_type", location)
        self.assertIn("references", location)
        self.assertIn("hosted_meetings", location["references"])

        # Verify meeting properties
        self.assertIsInstance(meeting, dict)
        self.assertIn("id", meeting)
        self.assertIn("platform", meeting)
        self.assertIn("event_type", meeting)
        self.assertIn("participants", meeting)
        self.assertIn("references", meeting)
        self.assertIn("located_at", meeting["references"])
        self.assertIn(location["id"], meeting["references"]["located_at"])

        # Verify cross-references
        location_id = uuid.UUID(location["id"])
        meeting_id = uuid.UUID(meeting["id"])

        # Verify meeting references the location
        meeting_refs = self.registry.get_entity_references(meeting_id, "located_at")
        self.assertTrue(any(ref.entity_id == location_id for ref in meeting_refs))

        # Verify location references the meeting
        location_refs = self.registry.get_entity_references(location_id, "hosted_meetings")
        self.assertTrue(any(ref.entity_id == meeting_id for ref in location_refs))

    def test_music_location_pattern(self):
        """Test music-location relationship patterns."""
        generator = MusicLocationPattern(self.registry)

        # Test music at location
        location, music = generator.generate_music_at_location()

        # Verify location properties
        self.assertIsInstance(location, dict)
        self.assertIn("id", location)
        self.assertIn("location_name", location)
        self.assertIn("location_type", location)
        self.assertIn("references", location)
        self.assertIn("music_activities", location["references"])

        # Verify music properties
        self.assertIsInstance(music, dict)
        self.assertIn("id", music)
        self.assertIn("artist", music)
        self.assertIn("track", music)
        self.assertIn("album", music)
        self.assertIn("genre", music)
        self.assertIn("platform", music)
        self.assertIn("references", music)
        self.assertIn("listened_at", music["references"])
        self.assertIn(location["id"], music["references"]["listened_at"])

        # Verify cross-references
        location_id = uuid.UUID(location["id"])
        music_id = uuid.UUID(music["id"])

        # Verify music references the location
        music_refs = self.registry.get_entity_references(music_id, "listened_at")
        self.assertTrue(any(ref.entity_id == location_id for ref in music_refs))

        # Verify location references the music
        location_refs = self.registry.get_entity_references(location_id, "music_activities")
        self.assertTrue(any(ref.entity_id == music_id for ref in location_refs))

    def test_music_task_pattern(self):
        """Test music-task relationship patterns."""
        generator = MusicTaskPattern(self.registry)

        # Test music during task
        task, music = generator.generate_music_during_task()

        # Verify task properties
        self.assertIsInstance(task, dict)
        self.assertIn("id", task)
        self.assertIn("task_name", task)
        self.assertIn("application", task)
        self.assertIn("duration_seconds", task)
        self.assertIn("references", task)
        self.assertIn("background_music", task["references"])

        # Verify music properties
        self.assertIsInstance(music, dict)
        self.assertIn("id", music)
        self.assertIn("artist", music)
        self.assertIn("track", music)
        self.assertIn("album", music)
        self.assertIn("genre", music)
        self.assertIn("platform", music)
        self.assertIn("references", music)
        self.assertIn("played_during", music["references"])
        self.assertIn(task["id"], music["references"]["played_during"])

        # Verify timestamps are aligned (music during task)
        task_start = task["timestamp"]
        task_end = task_start + task["duration_seconds"]
        self.assertTrue(task_start <= music["timestamp"] <= task_end)

        # Verify cross-references
        task_id = uuid.UUID(task["id"])
        music_id = uuid.UUID(music["id"])

        # Verify music references the task
        music_refs = self.registry.get_entity_references(music_id, "played_during")
        self.assertTrue(any(ref.entity_id == task_id for ref in music_refs))

        # Verify task references the music
        task_refs = self.registry.get_entity_references(task_id, "background_music")
        self.assertTrue(any(ref.entity_id == music_id for ref in task_refs))

        # Test task playlist
        task, music_tracks = generator.generate_task_playlist()

        # Verify task properties
        self.assertIsInstance(task, dict)
        self.assertIn("id", task)
        self.assertIn("task_name", task)
        self.assertIn("application", task)
        self.assertIn("duration_seconds", task)
        self.assertIn("references", task)
        self.assertIn("background_music", task["references"])

        # Verify music tracks properties
        self.assertIsInstance(music_tracks, list)
        self.assertTrue(len(music_tracks) > 0)

        # Verify all music tracks are in the task references
        for music in music_tracks:
            self.assertIn(music["id"], task["references"]["background_music"])

            # Verify this music activity references the task
            self.assertIn("references", music)
            self.assertIn("played_during", music["references"])
            self.assertIn(task["id"], music["references"]["played_during"])

        # Verify that task duration is at least as long as the playlist
        playlist_duration = sum(music["duration_seconds"] for music in music_tracks)
        self.assertGreaterEqual(task["duration_seconds"], playlist_duration)

        # Verify cross-references in the registry
        task_id = uuid.UUID(task["id"])
        for music in music_tracks:
            music_id = uuid.UUID(music["id"])

            # Verify music references the task
            music_refs = self.registry.get_entity_references(music_id, "played_during")
            self.assertTrue(any(ref.entity_id == task_id for ref in music_refs))

            # Verify task references the music
            task_refs = self.registry.get_entity_references(task_id, "background_music")
            self.assertTrue(any(ref.entity_id == music_id for ref in task_refs))


if __name__ == "__main__":
    unittest.main()
