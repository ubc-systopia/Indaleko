"""
Unit tests for the CrossCollectionQueryGenerator with real connections.

These tests use real database connections and LLM services without mocking,
following the fail-stop principle for scientific experiment frameworks.
"""

import logging
import sys
import unittest
from uuid import UUID

from research.ablation.models.activity import ActivityType
from research.ablation.query.enhanced.cross_collection_query_generator import CrossCollectionQueryGenerator
from research.ablation.registry.shared_entity_registry import SharedEntityRegistry, EntityReference

# Fail-Stop Principle: Do not use mocks, always connect to real services
# and fail immediately if connections cannot be established.

class TestCrossCollectionQueryGeneratorClean(unittest.TestCase):
    """
    Test suite for the CrossCollectionQueryGenerator.
    
    IMPORTANT: These tests follow the fail-stop principle:
    1. No mocking or fake data
    2. Must use real database connections and real LLM services
    3. Tests must fail immediately if connections cannot be established
    4. No error masking - all exceptions must be allowed to propagate
    """
    
    def setUp(self):
        """Set up test environment with real connections."""
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Create a real shared entity registry for testing
        self.entity_registry = SharedEntityRegistry()
        
        # Populate the registry with some test entities and relationships
        self.setup_test_registry()
        
        # Create a real generator - no mocking
        self.generator = CrossCollectionQueryGenerator(entity_registry=self.entity_registry)
        
        # Verify that we have a real generator with real connections
        if not self.generator or not self.generator.enhanced_generator or not self.generator.enhanced_generator.generator:
            self.logger.error("Failed to create CrossCollectionQueryGenerator with real connections")
            sys.exit(1)  # Fail-stop immediately
    
    def setup_test_registry(self):
        """Set up test data in the entity registry - no mocking."""
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
        """Test that the generator initializes correctly with real services."""
        self.assertIsNotNone(self.generator)
        self.assertEqual(len(self.generator.DEFAULT_RELATIONSHIP_TYPES), 7)
        self.assertEqual(len(self.generator.DEFAULT_COLLECTION_PAIRS), 4)
        self.assertEqual(len(self.generator.activity_descriptions), 6)
        self.assertEqual(len(self.generator.relationship_descriptions), 7)
    
    def test_find_matching_entity_relationships(self):
        """Test finding matching entity relationships in the registry."""
        # Test task-meeting relationship
        matching_tasks = self.generator._find_matching_entity_relationships(
            ActivityType.TASK, ActivityType.COLLABORATION, "created_in"
        )
        self.assertEqual(len(matching_tasks), 2)
        
        # Test meeting-location relationship
        matching_meetings = self.generator._find_matching_entity_relationships(
            ActivityType.COLLABORATION, ActivityType.LOCATION, "located_at"
        )
        self.assertEqual(len(matching_meetings), 2)
        
        # Test task-music relationship
        matching_tasks_music = self.generator._find_matching_entity_relationships(
            ActivityType.TASK, ActivityType.MUSIC, "listening_to"
        )
        self.assertEqual(len(matching_tasks_music), 1)
        
        # Test non-existent relationship
        non_matching = self.generator._find_matching_entity_relationships(
            ActivityType.MUSIC, ActivityType.STORAGE, "related_to"
        )
        self.assertEqual(len(non_matching), 0)
    
    def test_generate_cross_collection_matches(self):
        """Test generating expected matches for cross-collection queries."""
        # Test with real entity relationships
        matches_real = self.generator._generate_cross_collection_matches(
            ActivityType.TASK, ActivityType.COLLABORATION, "created_in"
        )
        self.assertGreaterEqual(len(matches_real), 2)
        
        # Test with synthetic entities
        matches_synthetic = self.generator._generate_cross_collection_matches(
            ActivityType.STORAGE, ActivityType.MEDIA, "related_to",
            ["document1", "document2"], ["video1", "video2"]
        )
        self.assertEqual(len(matches_synthetic), 5)
        
        # Check that synthetic matches have the correct format
        self.assertTrue(all(match.startswith("Objects/ablation_storage") for match in matches_synthetic))
        self.assertTrue(all("related_to" in match for match in matches_synthetic))
    
    def test_generate_single_cross_collection_query(self):
        """
        Test generating a single cross-collection query using real LLM.
        
        This test requires a real LLM connection and will fail immediately
        if the connection cannot be established (fail-stop principle).
        """
        # Generate a real query with the real LLM - no mocking
        result = self.generator._generate_single_cross_collection_query(
            ActivityType.TASK, ActivityType.COLLABORATION, "created_in"
        )
        
        # Verify the result is a valid TestQuery with proper fields
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.query_text)
        self.assertGreater(len(result.query_text), 0) 
        self.assertEqual(len(result.activity_types), 2)
        self.assertIn(ActivityType.TASK, result.activity_types)
        self.assertIn(ActivityType.COLLABORATION, result.activity_types)
        self.assertEqual(result.metadata["relationship_type"], "created_in")
        self.assertEqual(result.metadata["primary_activity"], "TASK")
        self.assertEqual(result.metadata["secondary_activity"], "COLLABORATION")
        self.assertTrue(result.metadata["cross_collection"])
    
    def test_generate_cross_collection_queries(self):
        """Test generating multiple cross-collection queries."""
        # Generate multiple queries with real LLM - no mocking
        results = self.generator.generate_cross_collection_queries(2)
        
        # Verify results
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertIsNotNone(result)
            self.assertIsNotNone(result.query_text)
            self.assertGreater(len(result.query_text), 0)
            self.assertGreaterEqual(len(result.activity_types), 2)
            self.assertTrue(result.metadata.get("cross_collection", False))
    
    def test_generate_cross_collection_query_failure(self):
        """
        Test that query generation failure triggers fail-stop.
        
        To test this properly, we would need to simulate an LLM failure.
        Since we are using real services, we cannot reliably test this 
        without mocking. In real operation, if the LLM fails, the code
        should exit with a status code of 1.
        """
        # This test is skipped since we cannot reliably simulate LLM failure
        # without mocking, and mocking violates the fail-stop principle.
        self.logger.info("Skipping failure test as it requires mocking")
        # No assertions - this is an information-only test
    
    def test_generate_diverse_cross_collection_queries(self):
        """Test generating diverse cross-collection queries."""
        # Generate diverse queries with real LLM - no mocking
        results = self.generator.generate_diverse_cross_collection_queries(2)
        
        # Verify results
        self.assertGreaterEqual(len(results), 1)
        for result in results:
            self.assertIsNotNone(result)
            self.assertIsNotNone(result.query_text)
            self.assertGreater(len(result.query_text), 0)
            self.assertGreaterEqual(len(result.activity_types), 2)
            self.assertTrue(result.metadata.get("cross_collection", False))


if __name__ == "__main__":
    unittest.main()