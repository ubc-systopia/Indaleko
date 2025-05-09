"""Integration test for the new music-based relationship patterns."""

import logging
import unittest
import uuid

from ...models.relationship_patterns import MusicLocationPattern, MusicTaskPattern
from ...query.aql_translator import AQLQueryTranslator
from ...query.llm_query_generator import ActivityType
from ...registry import SharedEntityRegistry


class TestMusicRelationshipPatternsIntegration(unittest.TestCase):
    """Integration test for music relationship patterns with AQL translation."""

    @classmethod
    def setUpClass(cls):
        """Set up class-level resources."""
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        # Create shared registry
        cls.registry = SharedEntityRegistry()

        # Create pattern generators
        cls.music_location_pattern = MusicLocationPattern(cls.registry)
        cls.music_task_pattern = MusicTaskPattern(cls.registry)

        # Create AQL translator
        cls.aql_translator = AQLQueryTranslator()

    def test_music_location_aql_translation(self):
        """Test AQL translation for music-location relationship patterns."""
        # Generate music activity at location
        location, music = self.music_location_pattern.generate_music_at_location()

        # Translate a query that involves both collections
        query_text = "music played at specific locations"
        activity_types = [ActivityType.MUSIC, ActivityType.LOCATION]

        aql, bind_vars = self.aql_translator.translate_to_aql(
            query_text=query_text,
            collection="MusicActivity",
            activity_types=activity_types,
            relationship_type="listened_at",
        )

        # Verify the AQL query contains the right fields
        self.assertIn("primary_doc.references.listened_at", aql)

        # Create a more specific query and verify it filters properly
        specific_query = "taylor swift music played at home"

        aql, bind_vars = self.aql_translator.translate_to_aql(
            query_text=specific_query,
            collection="MusicActivity",
            activity_types=activity_types,
            relationship_type="listened_at",
        )

        # Should have artist-specific filtering
        self.assertIn("taylor swift", aql.lower())

    def test_music_task_aql_translation(self):
        """Test AQL translation for music-task relationship patterns."""
        # Generate music during task
        task, music = self.music_task_pattern.generate_music_during_task()

        # Translate a query that involves both collections
        query_text = "music played during coding tasks"
        activity_types = [ActivityType.MUSIC, ActivityType.TASK]

        aql, bind_vars = self.aql_translator.translate_to_aql(
            query_text=query_text,
            collection="MusicActivity",
            activity_types=activity_types,
            relationship_type="played_during",
        )

        # Verify the AQL query contains the right fields
        self.assertIn("primary_doc.references.played_during", aql)

        # Should have task filtering since "task" is mentioned
        self.assertIn("active == true", aql.lower())

    def test_multi_hop_relationships(self):
        """Test multi-hop relationship paths with the new patterns."""
        # Define a multi-hop path: Task -> Music -> Location
        relationship_paths = [
            ("TaskActivity", "background_music", "MusicActivity"),
            ("MusicActivity", "listened_at", "LocationActivity"),
        ]

        # Translate a complex query that spans three collections
        query_text = "productive music played during coding tasks at my home office"

        aql, bind_vars = self.aql_translator.translate_multi_hop_query(
            query_text=query_text, primary_collection="TaskActivity", relationship_paths=relationship_paths,
        )

        # Verify the multi-hop query contains references to all three collections
        self.assertIn("TaskActivity", aql)
        self.assertIn("MusicActivity", aql)
        self.assertIn("LocationActivity", aql)
        self.assertIn("related1", aql)  # First hop
        self.assertIn("related2", aql)  # Second hop

    def test_generate_relationship_data(self):
        """Test generating and accessing relationship data between collections."""
        # Generate a task with a playlist
        task, music_tracks = self.music_task_pattern.generate_task_playlist()

        # Verify we can generate relationship instance data
        self.assertIsInstance(task, dict)
        self.assertIsInstance(music_tracks, list)
        self.assertTrue(len(music_tracks) > 0)

        # Verify references exist in the data
        self.assertIn("references", task)
        self.assertIn("background_music", task["references"])

        # Verify all music tracks reference the task
        for music in music_tracks:
            self.assertIn("references", music)
            self.assertIn("played_during", music["references"])
            self.assertIn(task["id"], music["references"]["played_during"])

        # Generate a music activity at a location
        location, music = self.music_location_pattern.generate_music_at_location()

        # Verify references are bidirectional
        self.assertIn("references", location)
        self.assertIn("music_activities", location["references"])
        self.assertIn(music["id"], location["references"]["music_activities"])

        self.assertIn("references", music)
        self.assertIn("listened_at", music["references"])
        self.assertIn(location["id"], music["references"]["listened_at"])

        # Verify references in the shared registry
        location_id = uuid.UUID(location["id"])
        music_id = uuid.UUID(music["id"])

        music_refs = self.registry.get_entity_references(music_id, "listened_at")
        self.assertTrue(any(ref.entity_id == location_id for ref in music_refs))

        location_refs = self.registry.get_entity_references(location_id, "music_activities")
        self.assertTrue(any(ref.entity_id == music_id for ref in location_refs))


if __name__ == "__main__":
    unittest.main()
