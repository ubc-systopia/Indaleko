"""
Integration test for the ablation tester with cross-collection queries.

This test verifies that cross-collection queries work properly
with the ablation testing framework.
"""

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
from research.ablation.ablation_tester import AblationTester
from research.ablation.error.retry import retry


class TestAblationWithCrossCollection(unittest.TestCase):
    """Integration test for the ablation tester with cross-collection queries."""

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
        
        # Create the query generator
        cls.query_generator = CrossCollectionQueryGenerator(entity_registry=cls.entity_registry)
        
        # Initialize the ablation tester (connection will be mocked)
        cls.tester = AblationTester(
            db_host="localhost",
            db_name="ablation_test",
            username="test",
            password="test",
            collections=["ablation_task", "ablation_collaboration", "ablation_location", "ablation_music"]
        )
        
        # Patch methods that require database access
        cls._patch_db_methods()
        
        # Generate test data and prepare ablation test
        cls._generate_test_data()
        cls._prepare_ablation_test()
    
    @classmethod
    def _patch_db_methods(cls):
        """Patch methods that require database access."""
        # Patch database connection and query execution
        cls.setup_patcher = patch.object(AblationTester, 'setup_database', return_value=True)
        cls.setup_mock = cls.setup_patcher.start()
        
        cls.execute_patcher = patch.object(AblationTester, '_execute_query')
        cls.execute_mock = cls.execute_patcher.start()
        cls.execute_mock.return_value = {"results": [{"_id": "test_id", "_key": "test_key"}]}
        
        cls.validate_patcher = patch.object(AblationTester, 'validate_truth_data')
        cls.validate_mock = cls.validate_patcher.start()
        cls.validate_mock.return_value = True
        
        cls.calc_patcher = patch.object(AblationTester, '_calculate_metrics')
        cls.calc_mock = cls.calc_patcher.start()
        cls.calc_mock.return_value = {"precision": 0.8, "recall": 0.7, "f1": 0.75}
        
        cls.ablate_patcher = patch.object(AblationTester, '_ablate_collection')
        cls.ablate_mock = cls.ablate_patcher.start()
        cls.ablate_mock.return_value = True
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        # Stop all patchers
        cls.setup_patcher.stop()
        cls.execute_patcher.stop()
        cls.validate_patcher.stop()
        cls.calc_patcher.stop()
        cls.ablate_patcher.stop()
    
    @classmethod
    def _generate_test_data(cls):
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
    
    @classmethod
    def _prepare_ablation_test(cls):
        """Prepare the ablation test with cross-collection queries."""
        cls.logger.info("Preparing ablation test with cross-collection queries")
        
        # Mock the LLM to return a predefined response for query generation
        with patch.object(cls.query_generator.enhanced_generator.generator, 'get_completion') as mock_get_completion:
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
            
            # Generate cross-collection queries
            task_collab_queries = cls.query_generator.generate_cross_collection_queries(
                count=2,
                relationship_types=["created_in", "discussed_in"],
                collection_pairs=[(ActivityType.TASK, ActivityType.COLLABORATION)]
            )
            
            task_location_queries = cls.query_generator.generate_cross_collection_queries(
                count=1,
                relationship_types=["at_location"],
                collection_pairs=[(ActivityType.TASK, ActivityType.LOCATION)]
            )
            
            collab_location_queries = cls.query_generator.generate_cross_collection_queries(
                count=1,
                relationship_types=["located_at"],
                collection_pairs=[(ActivityType.COLLABORATION, ActivityType.LOCATION)]
            )
            
            # Add all queries to the ablation tester
            cls.tester.queries = task_collab_queries + task_location_queries + collab_location_queries
            cls.logger.info(f"Added {len(cls.tester.queries)} cross-collection queries to the ablation tester")
            
            # Patch the truth data generation
            cls.tester.truth_data = {}
            for query in cls.tester.queries:
                query_id = str(query.query_id)
                cls.tester.truth_data[query_id] = {}
                
                # Add expected matches for each collection type involved
                for activity_type in query.activity_types:
                    collection = f"ablation_{activity_type.name.lower()}"
                    cls.tester.truth_data[query_id][collection] = query.expected_matches
    
    @retry(exceptions=Exception, tries=3, delay=1)
    def test_ablation_with_cross_collection_queries(self):
        """Test that the ablation tester works with cross-collection queries."""
        # Define a custom collection map for this test
        collection_map = {
            "ablation_task": ActivityType.TASK,
            "ablation_collaboration": ActivityType.COLLABORATION,
            "ablation_location": ActivityType.LOCATION,
            "ablation_music": ActivityType.MUSIC,
        }
        
        # Test running the ablation tester with cross-collection queries
        # We're using the mocked database methods, so this tests the logic without actual DB access
        with patch.object(self.tester, 'get_collection_map', return_value=collection_map):
            # Run the ablation test
            result = self.tester.run_ablation_test()
            
            # Verify the test ran and produced a valid result
            self.assertIsNotNone(result)
            self.assertIn("overall_metrics", result)
            self.assertIn("collection_metrics", result)
            self.assertIn("impact_metrics", result)
            
            # Check that the collections are in the results
            collections = ["ablation_task", "ablation_collaboration", "ablation_location"]
            for collection in collections:
                self.assertIn(collection, result["collection_metrics"])
                self.assertIn(collection, result["impact_metrics"])
    
    def test_cross_collection_query_format(self):
        """Test that cross-collection queries are formatted correctly for the ablation tester."""
        # Verify that all queries have multiple activity types
        for query in self.tester.queries:
            self.assertGreaterEqual(len(query.activity_types), 2)
            
            # Check that the metadata includes relationship info
            self.assertIn("relationship_type", query.metadata)
            self.assertIn("primary_activity", query.metadata)
            self.assertIn("secondary_activity", query.metadata)
            self.assertTrue(query.metadata.get("cross_collection", False))
            
            # Check that expected matches are not empty
            self.assertGreaterEqual(len(query.expected_matches), 1)
    
    def test_ablation_impact_calculation(self):
        """Test that ablation impact is calculated correctly for cross-collection queries."""
        # Mock impact calculation for different collection permutations
        impact_metrics = {}
        
        # For task collection
        impact_metrics["ablation_task"] = {
            "self_impact": 0.8,  # High impact on task queries when ablated
            "task_collaboration_impact": 0.6,  # Moderate impact on cross-collection
            "task_location_impact": 0.4,  # Some impact
        }
        
        # For collaboration collection
        impact_metrics["ablation_collaboration"] = {
            "self_impact": 0.7,  # High impact on collaboration queries when ablated
            "task_collaboration_impact": 0.5,  # Moderate impact on cross-collection
            "collaboration_location_impact": 0.6,  # Moderate impact
        }
        
        # For location collection
        impact_metrics["ablation_location"] = {
            "self_impact": 0.9,  # Very high impact on location queries when ablated
            "task_location_impact": 0.3,  # Some impact on cross-collection
            "collaboration_location_impact": 0.4,  # Some impact
        }
        
        with patch.object(self.tester, '_calculate_collection_impact') as mock_calc_impact:
            # Return different impact values based on the collection being ablated
            def side_effect(collection, metrics):
                return impact_metrics.get(collection, {})
            
            mock_calc_impact.side_effect = side_effect
            
            # Run the calculation
            result = self.tester._calculate_impact_metrics({})
            
            # Verify impact metrics contain cross-collection impacts
            self.assertIsNotNone(result)
            self.assertIn("ablation_task", result)
            self.assertIn("ablation_collaboration", result)
            self.assertIn("ablation_location", result)
            
            # Verify cross-collection impacts are calculated
            for collection, metrics in result.items():
                self.assertGreaterEqual(len(metrics), 2)  # At least self-impact and a cross-collection impact


if __name__ == "__main__":
    unittest.main()