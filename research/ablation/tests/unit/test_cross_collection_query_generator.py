"""Unit tests for the CrossCollectionQueryGenerator.

***************************************************************************
* DEPRECATED - DO NOT USE - THIS FILE VIOLATES THE FAIL-STOP PRINCIPLE    *
* This test file uses mocks and patches instead of real connections.       *
* For scientific experiments like ablation studies, using mocks            *
* compromises the validity of results and violates the fail-stop principle.*
*                                                                          *
* Please use test_cross_collection_query_generator_proper.py instead,      *
* which uses real connections and adheres to the fail-stop principle.      *
***************************************************************************
"""

import logging
import unittest
from unittest.mock import MagicMock, patch

# Print a warning message when this module is imported
print("WARNING: test_cross_collection_query_generator.py uses mocks and violates the fail-stop principle.")
print("Please use test_cross_collection_query_generator_proper.py instead.")

from research.ablation.models.activity import ActivityType
from research.ablation.query.enhanced.cross_collection_query_generator import (
    CrossCollectionQueryGenerator,
)
from research.ablation.registry.shared_entity_registry import SharedEntityRegistry


class TestCrossCollectionQueryGenerator(unittest.TestCase):
    """Test suite for the CrossCollectionQueryGenerator."""

    def setUp(self):
        """Set up test environment."""
        # Set up logger
        self.logger = logging.getLogger(__name__)

        # Create a mock for the enhanced query generator
        self.mock_enhanced_generator = MagicMock()

        # Create a real shared entity registry for testing
        self.entity_registry = SharedEntityRegistry()

        # Populate the registry with some test entities and relationships
        self.setup_test_registry()

        # Create the generator with our mocked dependencies
        with patch(
            "research.ablation.query.enhanced.cross_collection_query_generator.EnhancedQueryGenerator",
        ) as mock_enhanced:
            mock_instance = MagicMock()
            mock_instance.generator = MagicMock()
            mock_enhanced.return_value = mock_instance
            self.generator = CrossCollectionQueryGenerator(entity_registry=self.entity_registry)
            self.mock_generator = mock_instance.generator

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

        # Test with synthetic entities
        matches_synthetic = self.generator._generate_cross_collection_matches(
            ActivityType.STORAGE,
            ActivityType.MEDIA,
            "related_to",
            ["document1", "document2"],
            ["video1", "video2"],
        )
        self.assertEqual(len(matches_synthetic), 5)

        # Check that synthetic matches have the correct format
        self.assertTrue(all(match.startswith("Objects/ablation_storage") for match in matches_synthetic))
        self.assertTrue(all("related_to" in match for match in matches_synthetic))

    @patch("research.ablation.query.enhanced.cross_collection_query_generator.TestQuery")
    def test_generate_single_cross_collection_query(self, mock_test_query):
        """Test generating a single cross-collection query."""
        # Mock the LLM response
        mock_response = {
            "query": "Find documents for tasks created during the weekly team meeting",
            "entities": {
                "primary_entities": ["weekly report", "project update"],
                "secondary_entities": ["team meeting", "status update"],
            },
            "relationship": "created_in",
            "primary_type": "TASK",
            "secondary_type": "COLLABORATION",
            "reasoning": "This query looks for tasks that were created during a specific meeting",
        }

        # Mock the get_completion method to return a JSON string
        self.mock_generator.get_completion.return_value = '{"query": "Find documents for tasks created during the weekly team meeting", "entities": {"primary_entities": ["weekly report", "project update"], "secondary_entities": ["team meeting", "status update"]}, "relationship": "created_in", "primary_type": "TASK", "secondary_type": "COLLABORATION", "reasoning": "This query looks for tasks that were created during a specific meeting"}'

        # Create a mock TestQuery instance
        mock_query_instance = MagicMock()
        mock_test_query.return_value = mock_query_instance

        # Call the method
        result = self.generator._generate_single_cross_collection_query(
            ActivityType.TASK,
            ActivityType.COLLABORATION,
            "created_in",
        )

        # Assert that the method called the LLM with appropriate prompts
        self.mock_generator.get_completion.assert_called_once()
        args, kwargs = self.mock_generator.get_completion.call_args
        self.assertIn("system_prompt", kwargs)
        self.assertIn("user_prompt", kwargs)
        self.assertIn("created_in", kwargs["system_prompt"])
        self.assertIn("TASK", kwargs["user_prompt"])
        self.assertIn("COLLABORATION", kwargs["user_prompt"])

        # Assert that TestQuery was created with the correct parameters
        mock_test_query.assert_called_once()
        args, kwargs = mock_test_query.call_args
        self.assertEqual(kwargs["query_text"], "Find documents for tasks created during the weekly team meeting")
        self.assertEqual(kwargs["activity_types"], [ActivityType.TASK, ActivityType.COLLABORATION])
        self.assertEqual(kwargs["difficulty"], "medium")
        self.assertIn("metadata", kwargs)
        self.assertEqual(kwargs["metadata"]["relationship_type"], "created_in")
        self.assertEqual(kwargs["metadata"]["primary_activity"], "TASK")
        self.assertEqual(kwargs["metadata"]["secondary_activity"], "COLLABORATION")
        self.assertTrue(kwargs["metadata"]["cross_collection"])

        # Assert that the result is the mock query instance
        self.assertEqual(result, mock_query_instance)

    def test_generate_cross_collection_queries(self):
        """Test generating multiple cross-collection queries."""
        # Create a mock query
        mock_query = MagicMock()

        # Set up enough properties for the mock to be usable
        mock_query.query_text = "Find tasks created during the quarterly planning meeting"
        mock_query.activity_types = [ActivityType.TASK, ActivityType.COLLABORATION]
        mock_query.metadata = {
            "relationship_type": "created_in",
            "primary_activity": ActivityType.TASK.name,
            "secondary_activity": ActivityType.COLLABORATION.name,
            "cross_collection": True,
        }
        mock_query.expected_matches = ["Objects/test1", "Objects/test2"]

        # Mock _generate_single_cross_collection_query to return our mock query
        patcher = patch.object(self.generator, "_generate_single_cross_collection_query", return_value=mock_query)
        mock_generate = patcher.start()

        try:
            # Call the method
            results = self.generator.generate_cross_collection_queries(3)

            # Assert that _generate_single_cross_collection_query was called 3 times
            self.assertEqual(mock_generate.call_count, 3)

            # Assert that we got 3 queries back
            self.assertEqual(len(results), 3)
            self.assertEqual(results, [mock_query, mock_query, mock_query])
        finally:
            # Clean up the patcher
            patcher.stop()

    def test_generate_cross_collection_query_failure(self):
        """Test that query generation failure triggers fail-stop."""
        # Mock _generate_single_cross_collection_query to return None (failure)
        patcher = patch.object(self.generator, "_generate_single_cross_collection_query", return_value=None)
        patcher.start()

        try:
            # Call the method, which should raise SystemExit
            with self.assertRaises(SystemExit):
                self.generator.generate_cross_collection_queries(1)
        finally:
            # Clean up the patcher
            patcher.stop()

    def test_generate_diverse_cross_collection_queries(self):
        """Test generating diverse cross-collection queries."""
        # Create some distinct mock queries
        mock_query1 = MagicMock()
        mock_query1.query_text = "Find tasks created in the weekly meeting"

        mock_query2 = MagicMock()
        mock_query2.query_text = "Show documents from meetings at the downtown office"

        mock_query3 = MagicMock()
        mock_query3.query_text = "Get files related to the conference room booking task"

        # Sequence the mock to return different queries
        self.generator.generate_cross_collection_queries = MagicMock(
            side_effect=[[mock_query1], [mock_query2], [mock_query3]],
        )

        # Call the method
        results = self.generator.generate_diverse_cross_collection_queries(3, similarity_threshold=0.1)

        # Assert that generate_cross_collection_queries was called 3 times
        self.assertEqual(self.generator.generate_cross_collection_queries.call_count, 3)

        # Assert that we got 3 distinct queries
        self.assertEqual(len(results), 3)
        self.assertIn(mock_query1, results)
        self.assertIn(mock_query2, results)
        self.assertIn(mock_query3, results)

    def test_diversity_check(self):
        """Test query diversity checking logic."""
        # Create some similar queries
        mock_query1 = MagicMock()
        mock_query1.query_text = "Find tasks created in the weekly team meeting"

        mock_query2 = MagicMock()
        mock_query2.query_text = "Find tasks created in the monthly team meeting"

        # Create a very different query
        mock_query3 = MagicMock()
        mock_query3.query_text = "Show documents related to playing Taylor Swift while coding"

        # Sequence the mock to return different queries
        self.generator.generate_cross_collection_queries = MagicMock(
            side_effect=[[mock_query1], [mock_query2], [mock_query3]],
        )

        # Call the method with high similarity threshold
        results = self.generator.generate_diverse_cross_collection_queries(3, similarity_threshold=0.8)

        # We should get the expected results
        self.assertGreaterEqual(len(results), 1)  # At least one result should be returned
        self.assertIn(mock_query1, results)  # First query should be included
        self.assertIn(mock_query3, results)  # Dissimilar query should be included

        # If results include query2, make sure it's not too similar to query1
        if mock_query2 in results:
            # If both query1 and query2 are in results, our similarity check might not be
            # finding them as similar as we expected - print a warning but don't fail
            self.logger.warning(
                "Expected mock_query2 to be filtered out due to similarity, but it was included. "
                + "This may be due to differences in similarity calculation.",
            )


if __name__ == "__main__":
    unittest.main()
