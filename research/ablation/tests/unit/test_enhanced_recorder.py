"""Unit tests for the EnhancedActivityRecorder."""

import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID

from pydantic import BaseModel

from ...recorders.enhanced_base import EnhancedActivityRecorder
from ...registry import SharedEntityRegistry


class TestActivityModel(BaseModel):
    """Test activity model for the EnhancedActivityRecorder."""
    
    id: str
    title: str
    description: str


class TestEnhancedActivityRecorder(unittest.TestCase):
    """Test cases for the EnhancedActivityRecorder."""
    
    def setUp(self):
        """Set up test cases."""
        # Create a registry
        self.registry = SharedEntityRegistry()
        
        # Define test collections
        self.task_collection = "TaskActivity"
        self.collaboration_collection = "CollaborationActivity"
        
        # Register test entities
        self.task_id = self.registry.register_entity(
            "task", "Complete project report", self.task_collection
        )
        self.meeting_id = self.registry.register_entity(
            "meeting", "Weekly team sync", self.collaboration_collection
        )
    
    def test_record_with_references(self):
        """Test recording data with references."""
        # Create a test recorder class that avoids database connection
        class TestRecorder(EnhancedActivityRecorder):
            COLLECTION_NAME = "TestActivity"
            TRUTH_COLLECTION = "TestTruthData"
            ActivityClass = TestActivityModel
            
            def __init__(self, entity_registry=None):
                # Skip the parent __init__ to avoid database connection
                self.logger = MagicMock()
                self.db_config = MagicMock()
                self.db = MagicMock()
                # Mock the collection
                collection_mock = MagicMock()
                collection_mock.insert.return_value = {"_key": "test_key"}
                self.db.collection.return_value = collection_mock
                # Use provided registry or create new one
                self.entity_registry = entity_registry or SharedEntityRegistry()
        
        # Create the recorder
        recorder = TestRecorder(self.registry)
        
        # Create test data
        test_data = {
            "id": str(self.task_id),
            "title": "Test Task",
            "description": "This is a test task"
        }
        
        # Add references
        references = {
            "created_in": [self.meeting_id]
        }
        
        # Record the data with references
        with patch('json.loads', return_value=test_data.copy()):
            with patch('json.dumps', return_value='{"mocked": "json"}'):
                result = recorder.record_with_references(test_data, references)
        
        # Check that the record call was made
        self.assertTrue(recorder.db.collection.called)
        
        # Check that the relationship was added to the registry
        refs = self.registry.get_entity_references(self.task_id, "created_in")
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].entity_id, self.meeting_id)
        self.assertEqual(refs[0].collection_name, self.collaboration_collection)
    
    def test_record_batch_with_references(self):
        """Test recording a batch of data with references."""
        # Create a test recorder class that avoids database connection
        class TestRecorder(EnhancedActivityRecorder):
            COLLECTION_NAME = "TestActivity"
            TRUTH_COLLECTION = "TestTruthData"
            ActivityClass = TestActivityModel
            
            def __init__(self, entity_registry=None):
                # Skip the parent __init__ to avoid database connection
                self.logger = MagicMock()
                self.db_config = MagicMock()
                self.db = MagicMock()
                # Mock the collection
                collection_mock = MagicMock()
                collection_mock.insert.return_value = {"_key": "test_key"}
                collection_mock.insert_many.return_value = [{"_key": "key1"}, {"_key": "key2"}]
                self.db.collection.return_value = collection_mock
                # Use provided registry or create new one
                self.entity_registry = entity_registry or SharedEntityRegistry()
        
        # Create the recorder
        recorder = TestRecorder(self.registry)
        
        # Create test data batch
        test_batch = [
            {
                "id": str(self.task_id),
                "title": "Task 1",
                "description": "This is task 1"
            },
            {
                "id": "00000000-0000-0000-0000-000000000002",
                "title": "Task 2",
                "description": "This is task 2"
            }
        ]
        
        # Add references batch
        references_batch = [
            {
                "created_in": [self.meeting_id]
            },
            {
                "related_to": [self.task_id]
            }
        ]
        
        # Record the batch with references
        with patch('json.loads', side_effect=lambda x: test_batch[0].copy() if '1' in x else test_batch[1].copy()):
            with patch('json.dumps', return_value='{"mocked": "json"}'):
                # Mock ActivityClass validation in record_batch
                with patch.object(recorder, 'ActivityClass', side_effect=lambda **kwargs: MagicMock(model_dump_json=lambda: '{}')):
                    result = recorder.record_batch_with_references(test_batch, references_batch)
        
        # Check that the collection insert_many was called
        self.assertTrue(recorder.db.collection.called)
        
        # Check that the relationship was added to the registry
        created_in_refs = self.registry.get_entity_references(self.task_id, "created_in")
        self.assertEqual(len(created_in_refs), 1)
        self.assertEqual(created_in_refs[0].entity_id, self.meeting_id)


if __name__ == "__main__":
    unittest.main()