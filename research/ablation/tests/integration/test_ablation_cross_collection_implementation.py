"""
Integration test for the enhanced ablation tester with cross-collection queries.

This test verifies that the updated AblationTester correctly handles cross-collection
queries by properly joining related collections and measuring their relationships.
"""

import logging
import os
import sys
import unittest
from uuid import uuid4

# Set up the environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
        if current_path == os.path.dirname(current_path):  # Reached root directory
            break
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.insert(0, current_path)

# Import required modules
from research.ablation.ablation_tester import AblationTester, AblationConfig
from research.ablation.models.relationship_patterns import (
    MusicLocationPattern,
    MusicTaskPattern,
    TaskCollaborationPattern,
    LocationCollaborationPattern,
)
from research.ablation.registry.shared_entity_registry import SharedEntityRegistry
from db.db_config import IndalekoDBConfig


class TestAblationCrossCollectionImplementation(unittest.TestCase):
    """Test the cross-collection functionality of the AblationTester."""

    @classmethod
    def setUpClass(cls):
        """Set up the test environment with real database connections."""
        # Set up logging
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        cls.logger = logging.getLogger(__name__)

        # Create database connection
        try:
            cls.db_config = IndalekoDBConfig()
            cls.db = cls.db_config.get_arangodb()
            cls.logger.info("Successfully connected to ArangoDB database")
        except Exception as e:
            cls.logger.error(f"Failed to connect to database: {e}")
            sys.exit(1)  # Fail-stop immediately

        # Create the test collections if they don't exist
        collections = ["AblationMusicActivity", "AblationLocationActivity", "AblationTaskActivity", "AblationCollaborationActivity"]
        for collection_name in collections:
            if not cls.db.has_collection(collection_name):
                cls.db.create_collection(collection_name)
                cls.logger.info(f"Created collection {collection_name}")

        # Create a shared entity registry
        cls.entity_registry = SharedEntityRegistry()

        # Create relationship patterns
        cls.music_location_pattern = MusicLocationPattern(entity_registry=cls.entity_registry)
        cls.music_task_pattern = MusicTaskPattern(entity_registry=cls.entity_registry)
        cls.task_collaboration_pattern = TaskCollaborationPattern(entity_registry=cls.entity_registry)
        cls.location_collaboration_pattern = LocationCollaborationPattern(entity_registry=cls.entity_registry)

        # Initialize the ablation tester
        cls.tester = AblationTester()

        # Generate test data with relationships
        cls._generate_test_data()

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        # Clean up test collections
        collections = ["AblationMusicActivity", "AblationLocationActivity", "AblationTaskActivity", "AblationCollaborationActivity"]
        for collection_name in collections:
            if cls.db.has_collection(collection_name):
                # First truncate the collection
                cls.db.aql.execute(f"FOR doc IN {collection_name} REMOVE doc IN {collection_name}")
                cls.logger.info(f"Cleared collection {collection_name}")

    @classmethod
    def _generate_test_data(cls):
        """Generate test data with cross-collection relationships."""
        cls.logger.info("Generating test data with relationships")

        # Create music-location relationships
        for i in range(2):
            location, music = cls.music_location_pattern.generate_music_at_location()
            from arango.exceptions import DocumentInsertError

            try:
                # Store location in database
                cls.db.collection("AblationLocationActivity").insert(location)

                # Store music in database
                cls.db.collection("AblationMusicActivity").insert(music)
            except DocumentInsertError:
                cls.logger.exception(f"Failed to insert document")
                sys.exit(1)  # Fail-stop immediately

            cls.logger.info(f"Created music-location relationship: {music['artist']} at {location['location_name']}")

        # Create music-task relationships
        for i in range(2):
            task, music = cls.music_task_pattern.generate_music_during_task()

            # Store task in database
            cls.db.collection("AblationTaskActivity").insert(task)

            # Store music in database
            cls.db.collection("AblationMusicActivity").insert(music)

            cls.logger.info(f"Created music-task relationship: {music['artist']} during {task['task_name']}")

        # Create task with playlist
        task, music_list = cls.music_task_pattern.generate_task_playlist()

        # Store task in database
        cls.db.collection("AblationTaskActivity").insert(task)

        # Store music in database
        for music in music_list:
            cls.db.collection("AblationMusicActivity").insert(music)

        cls.logger.info(f"Created task-playlist relationship: {task['task_name']} with {len(music_list)} tracks")

        # Create task-collaboration relationships
        meeting, tasks = cls.task_collaboration_pattern.generate_meeting_with_tasks()

        # Store meeting in database
        cls.db.collection("AblationCollaborationActivity").insert(meeting)

        # Store tasks in database
        for task in tasks:
            cls.db.collection("AblationTaskActivity").insert(task)

        cls.logger.info(f"Created meeting-tasks relationship: {meeting['event_type']} with {len(tasks)} tasks")

        # Create location-collaboration relationships
        location, meeting = cls.location_collaboration_pattern.generate_meeting_at_location()

        # Store location in database
        cls.db.collection("AblationLocationActivity").insert(location)

        # Store meeting in database
        cls.db.collection("AblationCollaborationActivity").insert(meeting)

        cls.logger.info(f"Created location-meeting relationship: {meeting['event_type']} at {location['location_name']}")

        # Store the IDs for test verification
        cls.music_location_ids = {
            "location": location["id"],
            "meeting": meeting["id"]
        }

        # Create truth data for testing
        cls.tester.store_truth_data(
            uuid4(),
            "AblationMusicActivity",
            [music["_key"] for music in music_list]
        )

        cls.logger.info("Test data generation complete")

    def test_extract_search_terms_cross_collection(self):
        """Test the _extract_search_terms method with cross-collection query indicators."""
        # A query with multiple collection references
        query = "Find music by Taylor Swift that I listened to at the office during my marketing project"

        # Extract terms for MusicActivity
        terms = self.tester._extract_search_terms(query, "AblationMusicActivity")

        # Verify basic terms were extracted
        self.assertEqual(terms["artist"], "Taylor Swift")

        # Verify cross-collection indicators were detected
        self.assertTrue(terms["has_location_reference"])
        self.assertTrue(terms["has_task_reference"])
        self.assertFalse(terms.get("has_meeting_reference", False))

    def test_identify_related_collections(self):
        """Test the _identify_related_collections method."""
        # A query with multiple collection references
        query = "Find music by Taylor Swift that I listened to at the office during my marketing project"

        # Identify related collections for MusicActivity
        related = self.tester._identify_related_collections(query, "AblationMusicActivity")

        # Verify related collections were identified
        self.assertIn("AblationLocationActivity", related)
        self.assertIn("AblationTaskActivity", related)
        self.assertNotIn("AblationCollaborationActivity", related)

    def test_identify_collection_relationships(self):
        """Test the _identify_collection_relationships method."""
        # Define collections
        primary = "AblationMusicActivity"
        related = ["AblationLocationActivity", "AblationTaskActivity"]

        # Get search terms
        search_terms = self.tester._extract_search_terms(
            "Find music by Taylor Swift that I listened to at the office during my marketing project",
            primary
        )

        # Identify relationships
        relationships = self.tester._identify_collection_relationships(primary, related, search_terms)

        # Verify relationship fields were identified
        self.assertIn((primary, "AblationLocationActivity"), relationships)
        self.assertIn((primary, "AblationTaskActivity"), relationships)

        # Verify correct relationship fields were used
        self.assertIn("listened_at", relationships[(primary, "AblationLocationActivity")])
        self.assertIn("played_during", relationships[(primary, "AblationTaskActivity")])

    def test_build_cross_collection_query(self):
        """Test the _build_cross_collection_query method."""
        # Define collections and relationships
        primary = "AblationMusicActivity"
        related = ["AblationLocationActivity"]

        # Get search terms
        search_terms = self.tester._extract_search_terms("Find music by Taylor Swift at the office", primary)

        # Identify relationships
        relationships = self.tester._identify_collection_relationships(primary, related, search_terms)

        # Build the query
        aql_query = self.tester._build_cross_collection_query(
            primary, related, relationships, search_terms, set()
        )

        # Verify the query contains JOIN statements
        self.assertIn("FOR primary IN AblationMusicActivity", aql_query)
        self.assertIn("FOR related", aql_query)
        self.assertIn("FILTER related", aql_query)
        self.assertIn("RETURN primary", aql_query)

        # Verify primary filters
        self.assertIn("primary.artist == @artist", aql_query)

        # Verify relationship filters
        self.assertIn("references.listened_at", aql_query)

    def test_execute_cross_collection_query(self):
        """Test the _execute_cross_collection_query method."""
        # Create a test query
        query_id = uuid4()
        query_text = "Find music by Taylor Swift at the office"
        primary_collection = "AblationMusicActivity"
        related_collections = ["AblationLocationActivity"]

        # Get search terms
        search_terms = self.tester._extract_search_terms(query_text, primary_collection)

        # Get truth data
        truth_data = self.tester.get_truth_data(query_id, primary_collection)

        # Execute the cross-collection query
        results, aql_query, bind_vars = self.tester._execute_cross_collection_query(
            query_id, query_text, primary_collection, related_collections, search_terms, truth_data
        )

        # Verify the query executed successfully
        self.assertIsNotNone(results)
        self.assertIsNotNone(aql_query)
        self.assertIsNotNone(bind_vars)

        # Log the results
        self.logger.info(f"Cross-collection query returned {len(results)} results")
        self.logger.info(f"AQL query: {aql_query}")

    def test_ablation_tester_with_cross_collection(self):
        """Test the AblationTester with cross-collection queries."""
        # Create a test query
        query_id = uuid4()
        query_text = "Find music I listened to at the office during my marketing project"

        # Configure the ablation test
        config = AblationConfig(
            collections_to_ablate=[
                "AblationMusicActivity",
                "AblationLocationActivity",
                "AblationTaskActivity"
            ],
            query_limit=100,
            include_metrics=True,
            include_execution_time=True,
            verbose=True
        )

        # Run the ablation test
        results = self.tester.run_ablation_test(config, query_id, query_text)

        # Verify we got results
        self.assertIsNotNone(results)
        self.assertGreater(len(results), 0)

        # Verify cross-collection metadata is present
        for key, result in results.items():
            if "_impact_on_" in key:
                self.assertIsNotNone(result.metadata)
                self.assertIn("ablated_collection", result.metadata)


if __name__ == "__main__":
    unittest.main()
