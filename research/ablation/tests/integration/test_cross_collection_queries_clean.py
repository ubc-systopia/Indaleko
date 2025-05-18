"""
Integration tests for cross-collection query generation with real connections.

These tests use real database connections and LLM services without mocking,
following the fail-stop principle for scientific experiment frameworks.
"""

import logging
import os
import sys
import unittest

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
from research.ablation.models.activity import ActivityType
from research.ablation.registry.shared_entity_registry import SharedEntityRegistry, EntityReference
from research.ablation.recorders.enhanced_base import EnhancedActivityRecorder
from research.ablation.models.relationship_patterns import (
    TaskCollaborationPattern, 
    LocationCollaborationPattern
)
from research.ablation.query.enhanced.cross_collection_query_generator import CrossCollectionQueryGenerator


# Fail-Stop Principle: Do not use mocks, always connect to real services
# and fail immediately if connections cannot be established.

class TestCrossCollectionQueriesIntegration(unittest.TestCase):
    """
    Integration tests for cross-collection query generation.
    
    IMPORTANT: These tests follow the fail-stop principle:
    1. No mocking or fake data
    2. Must use real database connections and real LLM services
    3. Tests must fail immediately if connections cannot be established
    4. No error masking - all exceptions must be allowed to propagate
    """

    @classmethod
    def setUpClass(cls):
        """Set up test environment for all tests with real database connections."""
        # Set up logging
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        cls.logger = logging.getLogger(__name__)
        
        # Create a shared entity registry for the test
        cls.entity_registry = SharedEntityRegistry()
        
        # Create enhanced recorders with real database connections
        cls.task_recorder = EnhancedActivityRecorder(entity_registry=cls.entity_registry)
        cls.collaboration_recorder = EnhancedActivityRecorder(entity_registry=cls.entity_registry)
        cls.location_recorder = EnhancedActivityRecorder(entity_registry=cls.entity_registry)
        cls.music_recorder = EnhancedActivityRecorder(entity_registry=cls.entity_registry)
        
        # Set up relationship patterns
        cls.task_collaboration_pattern = TaskCollaborationPattern(
            entity_registry=cls.entity_registry
        )
        
        cls.location_collaboration_pattern = LocationCollaborationPattern(
            entity_registry=cls.entity_registry
        )
        
        # Create the query generator with real LLM connection
        cls.query_generator = CrossCollectionQueryGenerator(entity_registry=cls.entity_registry)
        
        # Verify that essential components have been created properly
        if not cls.task_recorder or not cls.collaboration_recorder or not cls.location_recorder:
            cls.logger.error("Failed to create recorders with real database connections")
            sys.exit(1)  # Fail-stop immediately
        
        if not cls.query_generator or not cls.query_generator.enhanced_generator:
            cls.logger.error("Failed to create query generator with real LLM connection")
            sys.exit(1)  # Fail-stop immediately
    
    def test_registry_population(self):
        """Test registering entities in the registry directly."""
        # Register test entities directly in the registry
        task_id = self.entity_registry.register_entity('task', 'Test Task', 'ablation_task')
        meeting_id = self.entity_registry.register_entity('meeting', 'Test Meeting', 'ablation_collaboration')
        location_id = self.entity_registry.register_entity('location', 'Test Location', 'ablation_location')
        
        # Create relationships
        self.entity_registry.add_relationship(task_id, meeting_id, 'created_in')
        self.entity_registry.add_relationship(meeting_id, location_id, 'located_at')
        
        # Verify registry state
        task_entities = self.entity_registry.get_entities_by_collection('ablation_task')
        self.assertGreaterEqual(len(task_entities), 1)
        
        # Verify relationships
        task_relationships = self.entity_registry.get_entity_references(task_id)
        self.assertGreaterEqual(len(task_relationships), 1)
        
        meeting_relationships = self.entity_registry.get_entity_references(meeting_id)
        self.assertGreaterEqual(len(meeting_relationships), 1)
    
    def test_generate_cross_collection_queries_with_registry(self):
        """
        Test real query generation with real entity registry and LLM.
        
        This test uses real LLM connections and will fail immediately
        if connections cannot be established (fail-stop principle).
        """
        # Set up test entities
        task_id = self.entity_registry.register_entity('task', 'Sprint Planning Task', 'ablation_task')
        meeting_id = self.entity_registry.register_entity('meeting', 'Sprint Planning Meeting', 'ablation_collaboration')
        self.entity_registry.add_relationship(task_id, meeting_id, 'discussed_in')
        
        # Generate real cross-collection queries with real LLM
        queries = self.query_generator.generate_cross_collection_queries(
            count=1,
            relationship_types=["discussed_in"],
            collection_pairs=[(ActivityType.TASK, ActivityType.COLLABORATION)]
        )
        
        # Verify the real query was generated
        self.assertEqual(len(queries), 1)
        
        # Verify the query structure - real query from real LLM
        query = queries[0]
        self.assertIsNotNone(query.query_text)
        self.assertGreater(len(query.query_text), 0)
        self.assertEqual(len(query.activity_types), 2)
        self.assertIn(ActivityType.TASK, query.activity_types)
        self.assertIn(ActivityType.COLLABORATION, query.activity_types)
        
        # Verify the metadata
        self.assertEqual(query.metadata["relationship_type"], "discussed_in")
        self.assertEqual(query.metadata["primary_activity"], "TASK")
        self.assertEqual(query.metadata["secondary_activity"], "COLLABORATION")
        
        # Verify expected matches were generated
        self.assertGreaterEqual(len(query.expected_matches), 1)
    
    def test_find_real_entity_matches(self):
        """Test finding real entity matches based on registry relationships."""
        # Set up some test entities and relationships
        task_id = self.entity_registry.register_entity('task', 'Test Task', 'ablation_task')
        meeting_id = self.entity_registry.register_entity('meeting', 'Test Meeting', 'ablation_collaboration')
        location_id = self.entity_registry.register_entity('location', 'Test Location', 'ablation_location')
        
        # Create relationships
        self.entity_registry.add_relationship(task_id, meeting_id, 'created_in')
        self.entity_registry.add_relationship(meeting_id, task_id, 'has_tasks')
        self.entity_registry.add_relationship(meeting_id, location_id, 'located_at')
        
        # Look for tasks created in meetings
        task_matches = self.query_generator._find_matching_entity_relationships(
            ActivityType.TASK, ActivityType.COLLABORATION, "created_in"
        )
        
        # We should find our test task
        self.assertGreaterEqual(len(task_matches), 1)
        self.assertIn(task_id, task_matches)
        
        # Look for meetings with tasks
        meeting_matches = self.query_generator._find_matching_entity_relationships(
            ActivityType.COLLABORATION, ActivityType.TASK, "has_tasks"
        )
        
        # We should find our test meeting
        self.assertGreaterEqual(len(meeting_matches), 1)
        self.assertIn(meeting_id, meeting_matches)
        
        # Look for meetings at locations
        location_matches = self.query_generator._find_matching_entity_relationships(
            ActivityType.COLLABORATION, ActivityType.LOCATION, "located_at"
        )
        
        # We should find our test meeting
        self.assertGreaterEqual(len(location_matches), 1)
        self.assertIn(meeting_id, location_matches)
    
    def test_generate_expected_matches_with_real_entities(self):
        """Test generating expected matches using real entities from the registry."""
        # Set up some test entities and relationships
        task_id = self.entity_registry.register_entity('task', 'Test Task 2', 'ablation_task')
        meeting_id = self.entity_registry.register_entity('meeting', 'Test Meeting 2', 'ablation_collaboration')
        
        # Create relationship
        self.entity_registry.add_relationship(task_id, meeting_id, 'created_in')
        
        # Generate expected matches for tasks created in meetings
        matches = self.query_generator._generate_cross_collection_matches(
            ActivityType.TASK, ActivityType.COLLABORATION, "created_in"
        )
        
        # We should get at least some matches based on real relationships
        self.assertGreaterEqual(len(matches), 1)
        
        # Check that the matches reference our entity
        expected_match = f"Objects/{task_id}"
        self.assertIn(expected_match, matches)


if __name__ == "__main__":
    unittest.main()