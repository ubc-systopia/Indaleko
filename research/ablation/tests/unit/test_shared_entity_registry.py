"""Unit tests for the SharedEntityRegistry."""

import unittest
from uuid import UUID

from ...registry import SharedEntityRegistry, EntityReference
from ...utils.uuid_utils import generate_uuid_for_entity


class TestSharedEntityRegistry(unittest.TestCase):
    """Test cases for the SharedEntityRegistry."""
    
    def setUp(self):
        """Set up test cases."""
        self.registry = SharedEntityRegistry()
        
        # Define test collections
        self.task_collection = "TaskActivity"
        self.collaboration_collection = "CollaborationActivity"
        self.location_collection = "LocationActivity"
        
        # Register test entities
        self.task_id = self.registry.register_entity(
            "task", "Complete project report", self.task_collection
        )
        self.meeting_id = self.registry.register_entity(
            "meeting", "Weekly team sync", self.collaboration_collection
        )
        self.location_id = self.registry.register_entity(
            "location", "Conference room", self.location_collection
        )
    
    def test_register_entity(self):
        """Test entity registration."""
        # Verify entities are registered correctly
        self.assertIsInstance(self.task_id, UUID)
        self.assertIsInstance(self.meeting_id, UUID)
        self.assertIsInstance(self.location_id, UUID)
        
        # Verify entity lookup works
        retrieved_task_id = self.registry.get_entity_id("task", "Complete project report")
        self.assertEqual(retrieved_task_id, self.task_id)
        
        # Verify collection tracking
        task_collections = self.registry.get_collections_for_entity(self.task_id)
        self.assertEqual(len(task_collections), 1)
        self.assertIn(self.task_collection, task_collections)
    
    def test_add_relationship(self):
        """Test adding relationships between entities."""
        # Add relationships
        result = self.registry.add_relationship(
            self.task_id, self.meeting_id, "created_in"
        )
        self.assertTrue(result)
        
        result = self.registry.add_relationship(
            self.meeting_id, self.location_id, "located_at"
        )
        self.assertTrue(result)
        
        # Verify relationship types are tracked
        rel_types = self.registry.get_relationship_types(
            self.task_collection, self.collaboration_collection
        )
        self.assertIn("created_in", rel_types)
        
        rel_types = self.registry.get_relationship_types(
            self.collaboration_collection, self.location_collection
        )
        self.assertIn("located_at", rel_types)
    
    def test_get_entity_references(self):
        """Test retrieving entity references."""
        # Add relationships
        self.registry.add_relationship(
            self.task_id, self.meeting_id, "created_in"
        )
        self.registry.add_relationship(
            self.task_id, self.location_id, "located_at"
        )
        
        # Get all references
        all_refs = self.registry.get_entity_references(self.task_id)
        self.assertEqual(len(all_refs), 2)
        
        # Get filtered references
        meeting_refs = self.registry.get_entity_references(self.task_id, "created_in")
        self.assertEqual(len(meeting_refs), 1)
        self.assertEqual(meeting_refs[0].entity_id, self.meeting_id)
        self.assertEqual(meeting_refs[0].collection_name, self.collaboration_collection)
        
        location_refs = self.registry.get_entity_references(self.task_id, "located_at")
        self.assertEqual(len(location_refs), 1)
        self.assertEqual(location_refs[0].entity_id, self.location_id)
        self.assertEqual(location_refs[0].collection_name, self.location_collection)
    
    def test_get_entities_by_collection(self):
        """Test retrieving entities by collection."""
        # Register additional task
        second_task_id = self.registry.register_entity(
            "task", "Prepare presentation", self.task_collection
        )
        
        # Get all task entities
        task_entities = self.registry.get_entities_by_collection(self.task_collection)
        self.assertEqual(len(task_entities), 2)
        self.assertIn(self.task_id, task_entities)
        self.assertIn(second_task_id, task_entities)
        
        # Get filtered by type
        task_type_entities = self.registry.get_entities_by_collection(self.task_collection, "task")
        self.assertEqual(len(task_type_entities), 2)
        
        # Non-existent type
        nonexistent = self.registry.get_entities_by_collection(self.task_collection, "nonexistent")
        self.assertEqual(len(nonexistent), 0)


if __name__ == "__main__":
    unittest.main()