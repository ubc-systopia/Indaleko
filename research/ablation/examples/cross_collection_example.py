"""Example demonstrating cross-collection references using the SharedEntityRegistry."""

import logging
import sys
from uuid import UUID

from db.db_config import IndalekoDBConfig

from ..collectors.task_collector import TaskActivityCollector
from ..collectors.collaboration_collector import CollaborationActivityCollector
from ..models.task_activity import TaskActivity
from ..models.collaboration_activity import CollaborationActivity
from ..recorders.enhanced_base import EnhancedActivityRecorder
from ..registry import SharedEntityRegistry


# Create enhanced recorders for task and collaboration activities
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


def run_example():
    """Run the cross-collection reference example."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    
    # Create shared entity registry
    registry = SharedEntityRegistry()
    
    # Create collectors
    task_collector = TaskActivityCollector()
    collaboration_collector = CollaborationActivityCollector()
    
    # Create enhanced recorders with the shared registry
    task_recorder = EnhancedTaskRecorder(registry)
    collaboration_recorder = EnhancedCollaborationRecorder(registry)
    
    # Generate task and collaboration activities
    logger.info("Generating task and collaboration activities")
    tasks = task_collector.generate_batch(5)
    meetings = collaboration_collector.generate_batch(3)
    
    # Record the task and meeting activities first (without references)
    logger.info("Recording baseline task and collaboration activities")
    task_recorder.record_batch(tasks)
    collaboration_recorder.record_batch(meetings)
    
    # Now create cross-collection references
    
    # 1. Tasks created during meetings (task -> meeting references)
    logger.info("Creating 'created_in' references from tasks to meetings")
    for i, task in enumerate(tasks):
        # Assign each task to a meeting (round-robin style)
        meeting_idx = i % len(meetings)
        meeting = meetings[meeting_idx]
        
        # Extract entity IDs
        task_id = UUID(task.get("id", ""))
        meeting_id = UUID(meeting.get("id", ""))
        
        # Register entities in the registry (if not already registered)
        registry.register_entity("task", task.get("title", ""), "TaskActivity")
        registry.register_entity("meeting", meeting.get("title", ""), "CollaborationActivity")
        
        # Add the relationship
        task_data = task.copy()
        task_references = {
            "created_in": [meeting_id]
        }
        
        # Re-record the task with the reference
        task_recorder.record_with_references(task_data, task_references)
        logger.info(f"Added 'created_in' reference from task '{task.get('title')}' to meeting '{meeting.get('title')}'")
    
    # 2. Meetings with task assignments (meeting -> task references)
    logger.info("Creating 'has_task' references from meetings to tasks")
    for i, meeting in enumerate(meetings):
        # Assign multiple tasks to each meeting
        assigned_tasks = []
        for j in range(2):  # Assign 2 tasks per meeting
            task_idx = (i * 2 + j) % len(tasks)
            assigned_tasks.append(tasks[task_idx])
        
        # Extract entity IDs
        meeting_id = UUID(meeting.get("id", ""))
        task_ids = [UUID(task.get("id", "")) for task in assigned_tasks]
        
        # Add the relationships
        meeting_data = meeting.copy()
        meeting_references = {
            "has_task": task_ids
        }
        
        # Re-record the meeting with the reference
        collaboration_recorder.record_with_references(meeting_data, meeting_references)
        logger.info(f"Added 'has_task' references from meeting '{meeting.get('title')}' to {len(task_ids)} tasks")
    
    # Print relationship summary
    logger.info("\nRelationship Summary:")
    for task in tasks:
        task_id = UUID(task.get("id", ""))
        task_title = task.get("title", "")
        
        # Get all meetings this task was created in
        meeting_refs = registry.get_entity_references(task_id, "created_in")
        if meeting_refs:
            logger.info(f"Task '{task_title}' was created in {len(meeting_refs)} meetings:")
            for ref in meeting_refs:
                # Get the meeting document from the database
                db = IndalekoDBConfig().get_arangodb()
                meeting_doc = db.collection("CollaborationActivity").get(str(ref.entity_id))
                if meeting_doc:
                    logger.info(f"  - Meeting: {meeting_doc.get('title', 'Unknown')}")
    
    for meeting in meetings:
        meeting_id = UUID(meeting.get("id", ""))
        meeting_title = meeting.get("title", "")
        
        # Get all tasks assigned in this meeting
        task_refs = registry.get_entity_references(meeting_id, "has_task")
        if task_refs:
            logger.info(f"Meeting '{meeting_title}' has {len(task_refs)} tasks:")
            for ref in task_refs:
                # Get the task document from the database
                db = IndalekoDBConfig().get_arangodb()
                task_doc = db.collection("TaskActivity").get(str(ref.entity_id))
                if task_doc:
                    logger.info(f"  - Task: {task_doc.get('title', 'Unknown')}")
    
    # Generate AQL query that joins tasks and meetings
    logger.info("\nExample AQL Query with JOIN:")
    aql_query = """
    FOR task IN TaskActivity
        FILTER task.references != null AND task.references.created_in != null
        FOR meeting_id IN task.references.created_in
            FOR meeting IN CollaborationActivity
                FILTER meeting._key == meeting_id
                RETURN {
                    task_title: task.title,
                    task_status: task.status,
                    meeting_title: meeting.title,
                    meeting_date: meeting.event_date
                }
    """
    logger.info(aql_query)
    
    logger.info("Cross-collection reference example completed successfully")


if __name__ == "__main__":
    run_example()