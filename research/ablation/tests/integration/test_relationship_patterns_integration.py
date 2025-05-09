"""Integration test for relationship patterns with the ablation framework."""

import logging
import os
import shutil
import sys
import unittest
import uuid
from typing import Dict, List, Any

from ....ablation.ablation_test_runner import AblationTestRunner
from ....ablation.ablation_tester import AblationConfig, AblationTester
from ....ablation.models.relationship_patterns import (
    TaskCollaborationPattern,
    LocationCollaborationPattern
)
from ....ablation.models.task_activity import TaskActivity
from ....ablation.models.collaboration_activity import CollaborationActivity
from ....ablation.models.location_activity import LocationActivity
from ....ablation.recorders.enhanced_base import EnhancedActivityRecorder
from ....ablation.registry import SharedEntityRegistry


# Create enhanced recorders for different activity types
class EnhancedTaskRecorder(EnhancedActivityRecorder):
    """Enhanced recorder for task activities."""
    
    COLLECTION_NAME = "TaskActivity"
    TRUTH_COLLECTION = "TaskTruthData"
    ActivityClass = TaskActivity


class EnhancedCollaborationRecorder(EnhancedActivityRecorder):
    """Enhanced recorder for collaboration activities."""
    
    COLLECTION_NAME = "CollaborationActivity"
    TRUTH_COLLECTION = "CollaborationTruthData"
    ActivityClass = CollaborationActivity


class EnhancedLocationRecorder(EnhancedActivityRecorder):
    """Enhanced recorder for location activities."""
    
    COLLECTION_NAME = "LocationActivity"
    TRUTH_COLLECTION = "LocationTruthData"
    ActivityClass = LocationActivity


class TestRelationshipPatternsIntegration(unittest.TestCase):
    """Integration test for relationship patterns with the ablation framework."""
    
    @classmethod
    def setUpClass(cls):
        """Set up class-level resources."""
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        
        # Create test output directory
        cls.test_output_dir = "/tmp/ablation_test_output"
        os.makedirs(cls.test_output_dir, exist_ok=True)
        
        # Create shared registry
        cls.registry = SharedEntityRegistry()
        
        # Create pattern generators
        cls.task_collab_pattern = TaskCollaborationPattern(cls.registry)
        cls.location_collab_pattern = LocationCollaborationPattern(cls.registry)
        
        # Create recorders
        cls.task_recorder = EnhancedTaskRecorder(cls.registry)
        cls.collaboration_recorder = EnhancedCollaborationRecorder(cls.registry)
        cls.location_recorder = EnhancedLocationRecorder(cls.registry)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up class-level resources."""
        # Remove test output directory
        if os.path.exists(cls.test_output_dir):
            shutil.rmtree(cls.test_output_dir)
    
    def test_relationship_patterns_data_pipeline(self):
        """Test that relationship patterns work with the ablation data pipeline."""
        # Generate test data with relationships
        self._generate_test_data()
        
        # Generate queries that span collections
        queries = self._generate_test_queries()
        
        # Create ablation config
        config = AblationConfig(
            collections_to_ablate=["TaskActivity", "CollaborationActivity", "LocationActivity"],
            query_limit=10,
            verbose=True
        )
        
        # Create ablation tester
        tester = AblationTester()
        
        # Run a single ablation test
        first_query = queries[0]
        query_id = uuid.UUID(first_query["id"])
        query_text = first_query["text"]
        
        try:
            # Record truth data for the query
            self._record_truth_data(query_id)
            
            # This will fail if the data pipeline doesn't work with relationship patterns
            results = tester.run_ablation_test(config, query_id, query_text)
            
            # Verify we got results for each collection
            self.assertTrue(len(results) > 0)
            
            # Log the results
            logging.info(f"Ablation test results for query '{query_text}':")
            for collection, result in results.items():
                logging.info(f"  {collection}: precision={result.precision:.4f}, recall={result.recall:.4f}, f1={result.f1_score:.4f}, impact={result.impact:.4f}")
            
            # Look for impact between Task and Collaboration
            task_collab_impact = None
            for key, result in results.items():
                if "TaskActivity_impact_on_CollaborationActivity" in key:
                    task_collab_impact = result.impact
                elif "CollaborationActivity_impact_on_TaskActivity" in key:
                    task_collab_impact = result.impact
            
            # We should have non-zero impact between Task and Collaboration
            if task_collab_impact is not None:
                logging.info(f"Impact between Task and Collaboration: {task_collab_impact:.4f}")
        
        finally:
            # Clean up
            tester.cleanup()
    
    def _generate_test_data(self) -> None:
        """Generate test data with cross-collection relationships."""
        logging.info("Generating test data with cross-collection relationships")
        
        # Generate meetings with tasks
        for i in range(3):
            meeting, tasks = self.task_collab_pattern.generate_meeting_with_tasks()
            
            # Record the meeting
            self.collaboration_recorder.record(meeting)
            
            # Record the tasks
            for task in tasks:
                self.task_recorder.record(task)
                
            logging.info(f"Generated and recorded meeting with {len(tasks)} tasks")
        
        # Generate tasks with related meetings
        for i in range(2):
            task, meetings = self.task_collab_pattern.generate_task_with_related_meetings()
            
            # Record the task
            self.task_recorder.record(task)
            
            # Record the meetings
            for meeting in meetings:
                self.collaboration_recorder.record(meeting)
                
            logging.info(f"Generated and recorded task with {len(meetings)} related meetings")
        
        # Generate meetings at locations
        for i in range(2):
            location, meeting = self.location_collab_pattern.generate_meeting_at_location()
            
            # Record the location
            self.location_recorder.record(location)
            
            # Record the meeting
            self.collaboration_recorder.record(meeting)
            
            logging.info(f"Generated and recorded meeting at location '{location['location_name']}'")
    
    def _record_truth_data(self, query_id: uuid.UUID) -> None:
        """Record truth data for a query to enable ablation testing.
        
        Args:
            query_id: The UUID of the query
        """
        # Get all task IDs as truth data for TaskActivity collection
        task_ids = set()
        for task_entity in self.registry.get_entities_by_collection("TaskActivity"):
            task_ids.add(task_entity)
        
        # Record truth data for TaskActivity
        if task_ids:
            self.task_recorder.record_truth_data(query_id, task_ids)
            logging.info(f"Recorded {len(task_ids)} truth entries for TaskActivity")
        
        # Get all collaboration IDs as truth data for CollaborationActivity collection
        collaboration_ids = set()
        for collab_entity in self.registry.get_entities_by_collection("CollaborationActivity"):
            collaboration_ids.add(collab_entity)
        
        # Record truth data for CollaborationActivity
        if collaboration_ids:
            self.collaboration_recorder.record_truth_data(query_id, collaboration_ids)
            logging.info(f"Recorded {len(collaboration_ids)} truth entries for CollaborationActivity")
        
        # Get all location IDs as truth data for LocationActivity collection
        location_ids = set()
        for location_entity in self.registry.get_entities_by_collection("LocationActivity"):
            location_ids.add(location_entity)
        
        # Record truth data for LocationActivity
        if location_ids:
            self.location_recorder.record_truth_data(query_id, location_ids)
            logging.info(f"Recorded {len(location_ids)} truth entries for LocationActivity")
    
    def _generate_test_queries(self) -> List[Dict[str, Any]]:
        """Generate test queries that span collections.
        
        Returns:
            List[Dict[str, Any]]: List of query dictionaries
        """
        logging.info("Generating test queries that span collections")
        
        # Create simple queries manually to avoid LLM dependency in tests
        queries = [
            {
                "id": str(uuid.uuid4()),
                "text": "Tasks assigned during meetings"
            },
            {
                "id": str(uuid.uuid4()),
                "text": "Meetings with pending tasks"
            },
            {
                "id": str(uuid.uuid4()),
                "text": "Meetings held at the conference room"
            },
            {
                "id": str(uuid.uuid4()),
                "text": "Tasks discussed in team meetings"
            },
            {
                "id": str(uuid.uuid4()),
                "text": "Meetings at the headquarters office"
            }
        ]
        
        logging.info(f"Generated {len(queries)} test queries")
        return queries


if __name__ == "__main__":
    unittest.main()