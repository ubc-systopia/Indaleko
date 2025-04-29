# Task Activity Generator for Indaleko

## Overview

The Task Activity Generator is a component for the Indaleko system that collects and processes data about task-related activities. It follows Indaleko's collector/recorder architecture pattern, where:

- **Collector**: Gathers raw data about tasks and task activities (creation, updates, completion, etc.)
- **Recorder**: Processes and stores the task activity data in the Indaleko database with appropriate semantic attributes

This component can be used to track task management activities from various sources, providing insights into work patterns, task completion rates, and productivity metrics.

## Architecture

The Task Activity Generator consists of:

1. **Data Models**:
   - `TaskData`: Represents a task with properties like ID, title, status, priority, etc.
   - `TaskActivityData`: Represents an activity event related to a task, such as creation, update, or completion

2. **Collector**:
   - `TaskActivityCollector`: Collects task activity data from various sources
   - For the demo implementation, generates simulated task data
   - In a real implementation, would connect to task management services (Trello, Asana, Jira, etc.)

3. **Recorder**:
   - `TaskActivityRecorder`: Processes task activity data and stores it in the Indaleko database
   - Handles the mapping of task properties to semantic attributes
   - Manages database operations for storing and retrieving task activities

4. **Semantic Attributes**:
   - Defined in `semantic_attributes.py`
   - Includes UUIDs for all task properties and metadata
   - Used for indexing and searching task activities

## Features

- Task creation, updates, and completion tracking
- Rich metadata capture (priorities, due dates, categories, tags)
- Task relationship tracking (parent/child tasks)
- Historical activity tracking
- Semantic attribute mapping for efficient querying
- Simulated data generation for testing and demos

## Usage

### Basic Usage

```python
from activity.collectors.task_activity.task_collector import TaskActivityCollector
from activity.recorders.task_activity.task_recorder import TaskActivityRecorder

# Initialize components
collector = TaskActivityCollector()
recorder = TaskActivityRecorder(collector=collector)

# Create a new task
task_data = {
    "title": "Implement feature X",
    "description": "Add the new X feature to the application",
    "status": "not_started",
    "priority": "high",
    "category": "Development",
    "tags": ["feature", "important"]
}
new_task = collector.create_task(task_data)

# Store the task activity in the database
recorder.store_task_activity(new_task, "created")

# Update the task
updated_task = collector.update_task(
    new_task.task_id,
    {"status": "in_progress"}
)

# Store the update activity
recorder.store_task_activity(
    updated_task,
    "updated",
    {"status": "not_started"}
)

# Mark the task as completed
completed_task = collector.update_task(
    new_task.task_id,
    {"status": "completed"}
)

# Store the completion activity
recorder.store_task_activity(
    completed_task,
    "completed",
    {"status": "in_progress"}
)

# Retrieve task history
history = recorder.get_task_history(new_task.task_id)
```

### Syncing All Tasks

```python
# Sync all tasks from the collector to the database
count = recorder.sync_all_tasks()
print(f"Synced {count} tasks to the database")
```

### Data Generation for Testing

```python
# Generate a random task
random_task = collector.create_random_task()
print(f"Generated task: {random_task.title} (Priority: {random_task.priority})")
```

## Semantic Attributes

The following semantic attributes are used to index task activity data:

- Task Properties:
  - `ACTIVITY_DATA_TASK_ID`: Unique identifier for the task
  - `ACTIVITY_DATA_TASK_TITLE`: Title or name of the task
  - `ACTIVITY_DATA_TASK_DESCRIPTION`: Detailed description of the task
  - `ACTIVITY_DATA_TASK_STATUS`: Current status of the task
  - `ACTIVITY_DATA_TASK_PRIORITY`: Priority level of the task

- Task Timestamps:
  - `ACTIVITY_DATA_TASK_CREATED_TIME`: When the task was created
  - `ACTIVITY_DATA_TASK_DUE_TIME`: When the task is due
  - `ACTIVITY_DATA_TASK_COMPLETED_TIME`: When the task was completed

- Task Categorization:
  - `ACTIVITY_DATA_TASK_CATEGORY`: Category or project the task belongs to
  - `ACTIVITY_DATA_TASK_TAGS`: Tags associated with the task

- Task Relationships:
  - `ACTIVITY_DATA_TASK_PARENT_ID`: ID of parent task
  - `ACTIVITY_DATA_TASK_SUBTASKS`: IDs of subtasks
  - `ACTIVITY_DATA_TASK_ASSIGNEE`: Person assigned to the task

- Task App Info:
  - `ACTIVITY_DATA_TASK_SOURCE_APP`: Application or service that generated the task

## Extending for Real Services

To extend this component for real task management services:

1. Create a new collector class that inherits from `TaskActivityCollector`
2. Implement the service-specific API connection logic
3. Override the data collection methods to fetch from the real service
4. Create a specific data model if needed for service-specific fields

Example:

```python
class TrelloTaskCollector(TaskActivityCollector):
    def __init__(self, api_key, token, **kwargs):
        super().__init__(**kwargs)
        self.client = TrelloClient(api_key=api_key, token=token)

    def get_tasks(self, filters=None):
        # Implement Trello-specific logic to fetch cards as tasks
        # ...
```

## Future Enhancements

- Real-time activity monitoring
- Integration with popular task management services
- Task analytics and reporting
- User activity correlation
- Context-aware task suggestions
