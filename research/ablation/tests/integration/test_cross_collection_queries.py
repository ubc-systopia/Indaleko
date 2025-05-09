"""Integration tests for cross-collection query generation."""

import logging
import os
import sys
import unittest
from unittest.mock import patch

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
from research.ablation.registry.shared_entity_registry import SharedEntityRegistry
from research.ablation.recorders.enhanced_base import EnhancedActivityRecorder
from research.ablation.models.relationship_patterns import (
    TaskCollaborationPattern, 
    LocationCollaborationPattern
)
from research.ablation.query.enhanced.cross_collection_query_generator import CrossCollectionQueryGenerator


class TestCrossCollectionQueriesIntegration(unittest.TestCase):
    """Integration tests for cross-collection query generation."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment for all tests."""
        # Set up logging
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        cls.logger = logging.getLogger(__name__)
        
        # Create a shared entity registry for the test
        cls.entity_registry = SharedEntityRegistry()
        
        # Create enhanced recorders with the registry
        cls.task_recorder = EnhancedActivityRecorder(entity_registry=cls.entity_registry)
        cls.collaboration_recorder = EnhancedActivityRecorder(entity_registry=cls.entity_registry)
        cls.location_recorder = EnhancedActivityRecorder(entity_registry=cls.entity_registry)
        cls.music_recorder = EnhancedActivityRecorder(entity_registry=cls.entity_registry)
        
        # Set up relationship patterns
        cls.task_collaboration_pattern = TaskCollaborationPattern(
            task_recorder=cls.task_recorder,
            collaboration_recorder=cls.collaboration_recorder,
            entity_registry=cls.entity_registry
        )
        
        cls.location_collaboration_pattern = LocationCollaborationPattern(
            location_recorder=cls.location_recorder,
            collaboration_recorder=cls.collaboration_recorder,
            entity_registry=cls.entity_registry
        )
        
        # Generate test data with relationships
        cls.generate_test_data()
        
        # Create the query generator
        cls.query_generator = CrossCollectionQueryGenerator(entity_registry=cls.entity_registry)
    
    @classmethod
    def generate_test_data(cls):
        """Generate test data with cross-collection relationships."""
        cls.logger.info("Generating test data with relationships")
        
        # Generate task+meeting relationships
        for i in range(3):
            # Generate a meeting with tasks
            meeting, tasks = cls.task_collaboration_pattern.generate_meeting_with_tasks()
            cls.logger.info(f"Generated meeting '{meeting['title']}' with {len(tasks)} tasks")
            
            # Record the meeting
            cls.collaboration_recorder.record_with_references(meeting)
            
            # Record the tasks with references to the meeting
            for task in tasks:
                cls.task_recorder.record_with_references(task)
        
        # Generate task+related meetings
        for i in range(2):
            # Generate a task with related meetings
            task, meetings = cls.task_collaboration_pattern.generate_task_with_related_meetings()
            cls.logger.info(f"Generated task '{task['name']}' with {len(meetings)} related meetings")
            
            # Record the task
            cls.task_recorder.record_with_references(task)
            
            # Record the meetings with references to the task
            for meeting in meetings:
                cls.collaboration_recorder.record_with_references(meeting)
        
        # Generate meeting+location relationships
        for i in range(3):
            # Generate a meeting at a location
            meeting, location = cls.location_collaboration_pattern.generate_meeting_at_location()
            cls.logger.info(f"Generated meeting '{meeting['title']}' at location '{location['name']}'")
            
            # Record the meeting
            cls.collaboration_recorder.record_with_references(meeting)
            
            # Record the location
            cls.location_recorder.record_with_references(location)
    
    def test_registry_population(self):
        """Test that the registry has been populated with entities and relationships."""
        # Check that we have task entities
        task_entities = self.entity_registry.get_entities_by_collection("ablation_task")
        self.assertGreaterEqual(len(task_entities), 5)
        
        # Check that we have meeting entities
        meeting_entities = self.entity_registry.get_entities_by_collection("ablation_collaboration")
        self.assertGreaterEqual(len(meeting_entities), 5)
        
        # Check that we have location entities
        location_entities = self.entity_registry.get_entities_by_collection("ablation_location")
        self.assertGreaterEqual(len(location_entities), 3)
        
        # Check that we have task-meeting relationships
        task = task_entities[0]
        task_relationships = self.entity_registry.get_entity_references(task)
        self.assertGreaterEqual(len(task_relationships), 1)
        
        # Check that we have meeting-location relationships
        meeting = meeting_entities[0]
        meeting_relationships = self.entity_registry.get_entity_references(meeting)
        self.assertGreaterEqual(len(meeting_relationships), 1)
    
    @patch('research.ablation.query.enhanced.cross_collection_query_generator.CrossCollectionQueryGenerator._generate_single_cross_collection_query')
    def test_generate_cross_collection_queries_with_registry(self, mock_generate):
        """Test that cross-collection query generation uses the entity registry."""
        # Set up the mock to passthrough to the real method
        mock_generate.side_effect = self.query_generator._generate_single_cross_collection_query
        
        # Mock the LLM to return a predefined response
        with patch.object(self.query_generator.enhanced_generator.generator, 'get_completion') as mock_get_completion:
            mock_get_completion.return_value = """
            {
              "query": "Find documents related to tasks discussed in the weekly meeting",
              "entities": {
                "primary_entities": ["progress report", "code review"],
                "secondary_entities": ["weekly meeting", "team discussion"]
              },
              "relationship": "discussed_in",
              "primary_type": "TASK",
              "secondary_type": "COLLABORATION",
              "reasoning": "This query looks for tasks that were discussed during a specific meeting"
            }
            """
            
            # Call the method with specific relationship and collection pairs
            queries = self.query_generator.generate_cross_collection_queries(
                count=1,
                relationship_types=["discussed_in"],
                collection_pairs=[(ActivityType.TASK, ActivityType.COLLABORATION)]
            )
            
            # Verify the query was generated
            self.assertEqual(len(queries), 1)
            
            # Verify the query references both collections
            query = queries[0]
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
        # Look for tasks created in meetings
        task_matches = self.query_generator._find_matching_entity_relationships(
            ActivityType.TASK, ActivityType.COLLABORATION, "created_in"
        )
        
        # We should find at least some tasks with this relationship
        self.assertGreaterEqual(len(task_matches), 1)
        
        # Look for meetings with tasks
        meeting_matches = self.query_generator._find_matching_entity_relationships(
            ActivityType.COLLABORATION, ActivityType.TASK, "has_tasks"
        )
        
        # We should find at least some meetings with this relationship
        self.assertGreaterEqual(len(meeting_matches), 1)
        
        # Look for meetings at locations
        location_matches = self.query_generator._find_matching_entity_relationships(
            ActivityType.COLLABORATION, ActivityType.LOCATION, "located_at"
        )
        
        # We should find at least some meetings with this relationship
        self.assertGreaterEqual(len(location_matches), 1)
    
    def test_generate_expected_matches_with_real_entities(self):
        """Test generating expected matches using real entities from the registry."""
        # Generate expected matches for tasks created in meetings
        matches = self.query_generator._generate_cross_collection_matches(
            ActivityType.TASK, ActivityType.COLLABORATION, "created_in"
        )
        
        # We should get at least some matches based on real relationships
        self.assertGreaterEqual(len(matches), 1)
        
        # Check that the matches reference real UUIDs
        for match in matches:
            self.assertTrue(match.startswith("Objects/"))
            # UUID format is long enough to be a real UUID
            entity_id = match.split("/")[1]
            self.assertGreaterEqual(len(entity_id), 30)  # Typical UUID string is 36 chars
    

if __name__ == "__main__":
    unittest.main()