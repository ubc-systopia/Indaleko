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
        # Create a mock database configuration
        self.db_config_mock = MagicMock()
        self.db_mock = MagicMock()
        self.collection_mock = MagicMock()
        
        # Setup the database mock
        self.db_config_mock.get_arangodb.return_value = self.db_mock
        self.db_mock.has_collection.return_value = True
        self.db_mock.collection.return_value = self.collection_mock
        
        # Setup collection mock for inserts
        self.collection_mock.insert.return_value = {"_key": "test_key"}
        
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
    
    @patch('db.db_config.IndalekoDBConfig')
    def test_record_with_references(self, mock_db_config_class):
        """Test recording data with references."""
        # Set up the mock
        mock_db_config_class.return_value = self.db_config_mock
        
        # Create a test recorder class
        class TestRecorder(EnhancedActivityRecorder):
            COLLECTION_NAME = "TestActivity"
            TRUTH_COLLECTION = "TestTruthData"
            ActivityClass = TestActivityModel
        
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
        result = recorder.record_with_references(test_data, references)
        
        # Check that the record was successful
        self.assertTrue(result)
        
        # Check that the collection insert was called with the expected data
        call_args = self.collection_mock.insert.call_args[0][0]
        self.assertIn("references", call_args)
        self.assertIn("created_in", call_args["references"])
        self.assertIn(str(self.meeting_id), call_args["references"]["created_in"])
        
        # Check that the relationship was added to the registry
        refs = self.registry.get_entity_references(self.task_id, "created_in")
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].entity_id, self.meeting_id)
        self.assertEqual(refs[0].collection_name, self.collaboration_collection)
    
    @patch('db.db_config.IndalekoDBConfig')
    def test_record_batch_with_references(self, mock_db_config_class):
        """Test recording a batch of data with references."""
        # Set up the mock
        mock_db_config_class.return_value = self.db_config_mock
        
        # Mock batch insert
        self.collection_mock.insert_many.return_value = [{"_key": "key1"}, {"_key": "key2"}]
        
        # Create a test recorder class
        class TestRecorder(EnhancedActivityRecorder):
            COLLECTION_NAME = "TestActivity"
            TRUTH_COLLECTION = "TestTruthData"
            ActivityClass = TestActivityModel
        
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
        result = recorder.record_batch_with_references(test_batch, references_batch)
        
        # Check that the record was successful
        self.assertTrue(result)
        
        # Check that the collection insert_many was called
        self.collection_mock.insert_many.assert_called_once()
        
        # Check that the references were added
        call_args = self.collection_mock.insert_many.call_args[0][0]
        self.assertEqual(len(call_args), 2)
        
        # Check first record
        self.assertIn("references", call_args[0])
        self.assertIn("created_in", call_args[0]["references"])
        self.assertIn(str(self.meeting_id), call_args[0]["references"]["created_in"])
        
        # Check second record
        self.assertIn("references", call_args[1])
        self.assertIn("related_to", call_args[1]["references"])
        self.assertIn(str(self.task_id), call_args[1]["references"]["related_to"])


if __name__ == "__main__":
    unittest.main()