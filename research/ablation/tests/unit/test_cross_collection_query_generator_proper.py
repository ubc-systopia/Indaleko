"""Unit tests for the CrossCollectionQueryGenerator that follow strict fail-stop principles.

IMPORTANT: These tests follow the fail-stop principle:
1. No mocking of database connections or LLM services
2. All connections are real - tests fail immediately if connections cannot be established
3. No error masking - all exceptions must be allowed to propagate
4. Never substitute mock/fake data for real data
"""

import logging
import sys
import unittest

from db.db_config import IndalekoDBConfig
from research.ablation.models.activity import ActivityType
from research.ablation.query.enhanced.cross_collection_query_generator import (
    CrossCollectionQueryGenerator,
)
from research.ablation.registry.shared_entity_registry import SharedEntityRegistry


def verify_real_connection():
    """Verify that a real database connection can be established.

    This function follows the fail-stop principle - it will exit immediately
    if a database connection cannot be established, rather than allowing tests
    to continue with mocked data.
    """
    logger = logging.getLogger(__name__)
    try:
        db_config = IndalekoDBConfig()
        db = db_config.get_arangodb()
        if not db:
            logger.error("CRITICAL: Failed to connect to database")
            sys.exit(1)  # Fail-stop on database connection failure
        logger.info("Successfully connected to database")
        return db_config, db
    except Exception as e:
        logger.error(f"CRITICAL: Error connecting to database: {e!s}")
        sys.exit(1)  # Fail-stop on exception


# Immediately verify connection to ensure fail-stop behavior
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
verify_real_connection()


class TestCrossCollectionQueryGeneratorProper(unittest.TestCase):
    """Test suite for the CrossCollectionQueryGenerator that uses real connections."""

    def setUp(self):
        """Set up test environment with real connections."""
        # Set up logger
        self.logger = logging.getLogger(__name__)

        # Create a real database connection
        db_config, db = verify_real_connection()

        # Create a real shared entity registry
        self.entity_registry = SharedEntityRegistry()

        # Populate the registry with test entities and relationships
        self.setup_test_registry()

        # Create the generator with real dependencies
        self.generator = CrossCollectionQueryGenerator(entity_registry=self.entity_registry)

    def setup_test_registry(self):
        """Set up test data in the entity registry."""
        # Create task entities
        task1_id = self.entity_registry.register_entity("task", "Complete project report", "ablation_task")
        task2_id = self.entity_registry.register_entity("task", "Review code changes", "ablation_task")

        # Create meeting entities
        meeting1_id = self.entity_registry.register_entity("meeting", "Weekly status meeting", "ablation_collaboration")
        meeting2_id = self.entity_registry.register_entity("meeting", "Project planning", "ablation_collaboration")

        # Create location entities
        location1_id = self.entity_registry.register_entity("location", "Conference room A", "ablation_location")
        location2_id = self.entity_registry.register_entity("location", "Coffee shop", "ablation_location")

        # Create music entities
        song1_id = self.entity_registry.register_entity("song", "Relaxing playlist", "ablation_music")

        # Create relationships
        # Tasks created in meetings
        self.entity_registry.add_relationship(task1_id, meeting1_id, "created_in")
        self.entity_registry.add_relationship(task2_id, meeting2_id, "created_in")

        # Meetings have tasks
        self.entity_registry.add_relationship(meeting1_id, task1_id, "has_tasks")
        self.entity_registry.add_relationship(meeting2_id, task2_id, "has_tasks")

        # Meetings at locations
        self.entity_registry.add_relationship(meeting1_id, location1_id, "located_at")
        self.entity_registry.add_relationship(meeting2_id, location2_id, "located_at")

        # Locations hosted meetings
        self.entity_registry.add_relationship(location1_id, meeting1_id, "hosted_meetings")
        self.entity_registry.add_relationship(location2_id, meeting2_id, "hosted_meetings")

        # Task at location (indirect relationship)
        self.entity_registry.add_relationship(task1_id, location1_id, "at_location")

        # Music playing during task
        self.entity_registry.add_relationship(task2_id, song1_id, "listening_to")

    def test_initialization(self):
        """Test that the generator initializes correctly."""
        self.assertIsNotNone(self.generator)
        self.assertEqual(len(self.generator.DEFAULT_RELATIONSHIP_TYPES), 7)
        self.assertEqual(len(self.generator.DEFAULT_COLLECTION_PAIRS), 4)
        self.assertEqual(len(self.generator.activity_descriptions), 6)
        self.assertEqual(len(self.generator.relationship_descriptions), 7)

    def test_find_matching_entity_relationships(self):
        """Test finding matching entity relationships in the registry."""
        # Test task-meeting relationship
        matching_tasks = self.generator._find_matching_entity_relationships(
            ActivityType.TASK,
            ActivityType.COLLABORATION,
            "created_in",
        )
        self.assertEqual(len(matching_tasks), 2)

        # Test meeting-location relationship
        matching_meetings = self.generator._find_matching_entity_relationships(
            ActivityType.COLLABORATION,
            ActivityType.LOCATION,
            "located_at",
        )
        self.assertEqual(len(matching_meetings), 2)

        # Test task-music relationship
        matching_tasks_music = self.generator._find_matching_entity_relationships(
            ActivityType.TASK,
            ActivityType.MUSIC,
            "listening_to",
        )
        self.assertEqual(len(matching_tasks_music), 1)

        # Test non-existent relationship
        non_matching = self.generator._find_matching_entity_relationships(
            ActivityType.MUSIC,
            ActivityType.STORAGE,
            "related_to",
        )
        self.assertEqual(len(non_matching), 0)

    def test_generate_cross_collection_matches(self):
        """Test generating expected matches for cross-collection queries."""
        # Test with real entity relationships
        matches_real = self.generator._generate_cross_collection_matches(
            ActivityType.TASK,
            ActivityType.COLLABORATION,
            "created_in",
        )
        self.assertGreaterEqual(len(matches_real), 2)

        # Test with provided entity IDs
        task_ids = ["task1", "task2"]
        meeting_ids = ["meeting1", "meeting2"]
        matches_with_ids = self.generator._generate_cross_collection_matches(
            ActivityType.TASK,
            ActivityType.COLLABORATION,
            "created_in",
            task_ids,
            meeting_ids,
        )
        # The number of matches depends on the implementation, but should include at least the provided entities
        self.assertGreaterEqual(len(matches_with_ids), 2)  # At least the provided entities

        # The format of matches depends on the implementation
        # Just ensure we have matches
        self.assertGreaterEqual(len(matches_with_ids), 1)

    def test_generate_single_cross_collection_query(self):
        """Test generating a single cross-collection query with real LLM."""
        # Call the method that uses real LLM
        result = self.generator._generate_single_cross_collection_query(
            ActivityType.TASK,
            ActivityType.COLLABORATION,
            "created_in",
        )

        # Verify the result
        self.assertIsNotNone(result)
        self.assertTrue(hasattr(result, "query_text"))
        self.assertTrue(hasattr(result, "activity_types"))
        self.assertTrue(hasattr(result, "metadata"))
        self.assertEqual(result.activity_types, [ActivityType.TASK, ActivityType.COLLABORATION])
        self.assertEqual(result.metadata["relationship_type"], "created_in")
        self.assertEqual(result.metadata["primary_activity"], "TASK")
        self.assertEqual(result.metadata["secondary_activity"], "COLLABORATION")
        self.assertTrue(result.metadata["cross_collection"])

    def test_generate_cross_collection_queries(self):
        """Test generating multiple cross-collection queries."""
        # Generate 2 queries with real connections
        results = self.generator.generate_cross_collection_queries(2)

        # Verify we got 2 queries back
        self.assertEqual(len(results), 2)

        # Verify each query has the correct structure
        for query in results:
            self.assertTrue(hasattr(query, "query_text"))
            self.assertTrue(hasattr(query, "activity_types"))
            self.assertTrue(hasattr(query, "expected_matches"))
            self.assertTrue(hasattr(query, "metadata"))
            self.assertTrue(query.metadata["cross_collection"])

    def test_generate_cross_collection_query_with_specific_types(self):
        """Test generating a query with specific relationship types and collection pairs."""
        # Generate a query with a specific relationship type and collection pair
        results = self.generator.generate_cross_collection_queries(
            count=1,
            relationship_types=["located_at"],
            collection_pairs=[(ActivityType.COLLABORATION, ActivityType.LOCATION)],
        )

        # Verify we got 1 query back with the specified relationship
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].metadata["relationship_type"], "located_at")
        self.assertEqual(results[0].metadata["primary_activity"], "COLLABORATION")
        self.assertEqual(results[0].metadata["secondary_activity"], "LOCATION")

    def test_generate_diverse_cross_collection_queries(self):
        """Test generating diverse cross-collection queries."""
        # Generate 3 diverse queries with real connections
        results = self.generator.generate_diverse_cross_collection_queries(3, similarity_threshold=0.4)

        # Verify we got 3 distinct queries
        self.assertEqual(len(results), 3)

        # Check that they're different from each other
        queries = [q.query_text for q in results]
        for i in range(len(queries)):
            for j in range(i + 1, len(queries)):
                # A crude check for diversity - could be improved with real similarity metrics
                self.assertNotEqual(queries[i], queries[j])


if __name__ == "__main__":
    unittest.main()
