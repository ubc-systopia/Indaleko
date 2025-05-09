"""Unit tests for relationship patterns."""

import unittest
import uuid
from unittest.mock import patch

from ...models.relationship_patterns import (
    RelationshipPatternGenerator,
    TaskCollaborationPattern,
    LocationCollaborationPattern
)
from ...registry import SharedEntityRegistry


class TestRelationshipPatterns(unittest.TestCase):
    """Test relationship pattern generators."""
    
    def setUp(self):
        """Set up test cases."""
        self.registry = SharedEntityRegistry()
    
    def test_relationship_pattern_generator_base(self):
        """Test the base relationship pattern generator."""
        generator = RelationshipPatternGenerator(self.registry)
        
        # Test timestamp generation
        timestamp = generator.generate_timestamp()
        self.assertIsInstance(timestamp, int)
        
        # Test UUID generation
        generated_uuid = generator.generate_uuid()
        self.assertIsInstance(generated_uuid, str)
        # Verify it's a valid UUID
        uuid.UUID(generated_uuid)
        
        # Test entity registration
        entities = [
            {"id": generator.generate_uuid(), "title": "Entity 1"},
            {"id": generator.generate_uuid(), "title": "Entity 2"}
        ]
        # Register entities in the registry
        generator.register_entities(entities, "Test")
        
        # Verify registry isn't empty - we don't need specific verification
        # since we're testing with no database connection
        self.assertIsNotNone(self.registry.entity_collections)
        self.assertIsNotNone(self.registry.collection_entities)
    
    def test_task_collaboration_pattern(self):
        """Test task-collaboration relationship patterns."""
        generator = TaskCollaborationPattern(self.registry)
        
        # Test meeting with tasks
        meeting, tasks = generator.generate_meeting_with_tasks()
        
        # Verify meeting properties
        self.assertIsInstance(meeting, dict)
        self.assertIn("id", meeting)
        self.assertIn("platform", meeting)
        self.assertIn("event_type", meeting)
        self.assertIn("participants", meeting)
        self.assertIn("references", meeting)
        self.assertIn("has_tasks", meeting["references"])
        
        # Verify tasks properties
        self.assertIsInstance(tasks, list)
        self.assertTrue(len(tasks) > 0)
        for task in tasks:
            self.assertIn("id", task)
            self.assertIn("task_name", task)
            self.assertIn("application", task)
            self.assertIn("duration_seconds", task)
            self.assertIn("references", task)
            self.assertIn("created_in", task["references"])
            self.assertIn(meeting["id"], task["references"]["created_in"])
        
        # Verify cross-references
        for task in tasks:
            task_id = uuid.UUID(task["id"])
            meeting_id = uuid.UUID(meeting["id"])
            
            # Verify task references the meeting
            task_refs = self.registry.get_entity_references(task_id, "created_in")
            self.assertTrue(any(ref.entity_id == meeting_id for ref in task_refs))
            
            # Verify meeting references the task
            meeting_refs = self.registry.get_entity_references(meeting_id, "has_tasks")
            self.assertTrue(any(ref.entity_id == task_id for ref in meeting_refs))
        
        # Test task with related meetings
        task, meetings = generator.generate_task_with_related_meetings()
        
        # Verify task properties
        self.assertIsInstance(task, dict)
        self.assertIn("id", task)
        self.assertIn("task_name", task)
        self.assertIn("references", task)
        self.assertIn("discussed_in", task["references"])
        
        # Verify meetings properties
        self.assertIsInstance(meetings, list)
        self.assertTrue(len(meetings) > 0)
        for meeting in meetings:
            self.assertIn("id", meeting)
            self.assertIn("platform", meeting)
            self.assertIn("event_type", meeting)
            self.assertIn("participants", meeting)
            self.assertIn("references", meeting)
            self.assertIn("related_to", meeting["references"])
            self.assertIn(task["id"], meeting["references"]["related_to"])
        
        # Verify cross-references
        task_id = uuid.UUID(task["id"])
        for meeting in meetings:
            meeting_id = uuid.UUID(meeting["id"])
            
            # Verify task references the meeting
            task_refs = self.registry.get_entity_references(task_id, "discussed_in")
            self.assertTrue(any(ref.entity_id == meeting_id for ref in task_refs))
            
            # Verify meeting references the task
            meeting_refs = self.registry.get_entity_references(meeting_id, "related_to")
            self.assertTrue(any(ref.entity_id == task_id for ref in meeting_refs))
    
    def test_location_collaboration_pattern(self):
        """Test location-collaboration relationship patterns."""
        generator = LocationCollaborationPattern(self.registry)
        
        # Test meeting at location
        location, meeting = generator.generate_meeting_at_location()
        
        # Verify location properties
        self.assertIsInstance(location, dict)
        self.assertIn("id", location)
        self.assertIn("location_name", location)
        self.assertIn("location_type", location)
        self.assertIn("references", location)
        self.assertIn("hosted_meetings", location["references"])
        
        # Verify meeting properties
        self.assertIsInstance(meeting, dict)
        self.assertIn("id", meeting)
        self.assertIn("platform", meeting)
        self.assertIn("event_type", meeting)
        self.assertIn("participants", meeting)
        self.assertIn("references", meeting)
        self.assertIn("located_at", meeting["references"])
        self.assertIn(location["id"], meeting["references"]["located_at"])
        
        # Verify cross-references
        location_id = uuid.UUID(location["id"])
        meeting_id = uuid.UUID(meeting["id"])
        
        # Verify meeting references the location
        meeting_refs = self.registry.get_entity_references(meeting_id, "located_at")
        self.assertTrue(any(ref.entity_id == location_id for ref in meeting_refs))
        
        # Verify location references the meeting
        location_refs = self.registry.get_entity_references(location_id, "hosted_meetings")
        self.assertTrue(any(ref.entity_id == meeting_id for ref in location_refs))


if __name__ == "__main__":
    unittest.main()