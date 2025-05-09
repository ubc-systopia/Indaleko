"""Example demonstrating relationship patterns with enhanced recorders."""

import logging
import sys
from uuid import UUID

from db.db_config import IndalekoDBConfig

from ..models.task_activity import TaskActivity
from ..models.collaboration_activity import CollaborationActivity
from ..models.location_activity import LocationActivity
from ..models.relationship_patterns import (
    TaskCollaborationPattern,
    LocationCollaborationPattern
)
from ..recorders.enhanced_base import EnhancedActivityRecorder
from ..registry import SharedEntityRegistry


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


def run_example():
    """Run the relationship patterns example."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    
    # Create shared entity registry
    registry = SharedEntityRegistry()
    
    # Create recorders with the shared registry
    task_recorder = EnhancedTaskRecorder(registry)
    collaboration_recorder = EnhancedCollaborationRecorder(registry)
    location_recorder = EnhancedLocationRecorder(registry)
    
    # Create relationship pattern generators
    task_collab_pattern = TaskCollaborationPattern(registry)
    location_collab_pattern = LocationCollaborationPattern(registry)
    
    # Example 1: Generate meeting with tasks
    logger.info("Generating meeting with tasks")
    meeting, tasks = task_collab_pattern.generate_meeting_with_tasks()
    
    # Record the meeting
    logger.info("Recording meeting")
    collaboration_recorder.record(meeting)
    
    # Record the tasks
    logger.info(f"Recording {len(tasks)} tasks")
    for task in tasks:
        task_recorder.record(task)
    
    # Example 2: Generate task with related meetings
    logger.info("Generating task with related meetings")
    task, meetings = task_collab_pattern.generate_task_with_related_meetings()
    
    # Record the task
    logger.info("Recording task")
    task_recorder.record(task)
    
    # Record the meetings
    logger.info(f"Recording {len(meetings)} related meetings")
    for meeting in meetings:
        collaboration_recorder.record(meeting)
    
    # Example 3: Generate meeting at location
    logger.info("Generating meeting at location")
    location, meeting = location_collab_pattern.generate_meeting_at_location()
    
    # Record the location
    logger.info("Recording location")
    location_recorder.record(location)
    
    # Record the meeting
    logger.info("Recording meeting at location")
    collaboration_recorder.record(meeting)
    
    # Generate AQL query examples that join these collections
    logger.info("\nExample AQL Query: Tasks assigned in a specific meeting")
    task_meeting_query = """
    FOR meeting IN CollaborationActivity
        FILTER meeting.title == "Planning Meeting"
        FOR task IN TaskActivity
            FILTER task.references != null AND task.references.created_in != null
            FILTER meeting._key IN task.references.created_in
            RETURN {
                meeting_title: meeting.title,
                meeting_time: meeting.timestamp,
                task_title: task.title,
                task_status: task.status,
                task_assignee: task.assignee
            }
    """
    logger.info(task_meeting_query)
    
    logger.info("\nExample AQL Query: Meetings at a specific location")
    location_meeting_query = """
    FOR location IN LocationActivity
        FILTER location.name == "Board Room"
        FOR meeting IN CollaborationActivity
            FILTER meeting.references != null AND meeting.references.located_at != null
            FILTER location._key IN meeting.references.located_at
            RETURN {
                location_name: location.name,
                location_type: location.type,
                meeting_title: meeting.title,
                meeting_time: meeting.timestamp,
                participant_count: LENGTH(meeting.participants)
            }
    """
    logger.info(location_meeting_query)
    
    logger.info("\nExample AQL Query: Tasks discussed in meetings at a specific location")
    task_location_query = """
    FOR location IN LocationActivity
        FILTER location.type == "office"
        FOR meeting IN CollaborationActivity
            FILTER meeting.references != null AND meeting.references.located_at != null
            FILTER location._key IN meeting.references.located_at
            FOR task IN TaskActivity
                FILTER task.references != null AND task.references.discussed_in != null
                FILTER meeting._key IN task.references.discussed_in
                RETURN {
                    location_name: location.name,
                    meeting_title: meeting.title,
                    task_title: task.title,
                    task_status: task.status
                }
    """
    logger.info(task_location_query)
    
    # Execute one of the queries as an example
    logger.info("\nExecuting query to find tasks assigned in meetings")
    db = IndalekoDBConfig().get_arangodb()
    aql_query = """
    FOR meeting IN CollaborationActivity
        FILTER meeting.references != null AND meeting.references.has_tasks != null
        FOR task_id IN meeting.references.has_tasks
            FOR task IN TaskActivity
                FILTER task._key == task_id
                RETURN {
                    meeting: meeting.title,
                    task: task.title,
                    assignee: task.assignee,
                    status: task.status
                }
    """
    
    try:
        cursor = db.aql.execute(aql_query)
        results = [doc for doc in cursor]
        logger.info(f"Found {len(results)} tasks assigned in meetings:")
        for result in results:
            logger.info(f"  - Task '{result['task']}' ({result['status']}) assigned to {result['assignee']} in meeting '{result['meeting']}'")
    except Exception as e:
        logger.error(f"Error executing query: {e}")
    
    logger.info("Relationship patterns example completed successfully")


if __name__ == "__main__":
    run_example()