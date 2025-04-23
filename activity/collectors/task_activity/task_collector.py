"""
This module implements a task activity collector for Indaleko.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import os
import random
import sys
import uuid
from datetime import UTC, datetime, timedelta

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.base import CollectorBase
from activity.collectors.task_activity.data_models.task_data_model import (
    TaskActivityData,
    TaskData,
    TaskPriority,
    TaskStatus,
)

# pylint: enable=wrong-import-position


class TaskActivityCollector(CollectorBase):
    """
    Task activity data collector for Indaleko.

    This collector generates simulated task activity data for testing and demo purposes.
    In a real implementation, this would connect to a task management service's API.
    """

    def __init__(self, **kwargs):
        """Initialize the task activity collector"""
        self._name = kwargs.get("name", "Task Activity Collector")
        self._provider_id = kwargs.get(
            "provider_id", uuid.UUID("5a63b8d2-97f1-4e21-a589-6c47fd0e902c"),
        )
        self._version = kwargs.get("version", "1.0.0")
        self._description = kwargs.get(
            "description", "Collects task activities from task management services",
        )

        # Initialize data store for simulated tasks
        self._tasks = {}
        self._task_history = {}

        # Optional config
        self._source_app = kwargs.get("source_app", "SimulatedTaskManager")

        # Create initial test data if not disabled
        if not kwargs.get("disable_test_data", False):
            self._create_test_data()

    def _create_test_data(self):
        """Create simulated test data"""
        # Generate a few tasks with different statuses
        task_templates = [
            {
                "title": "Update project documentation",
                "description": "Add latest features to the project documentation",
                "status": TaskStatus.IN_PROGRESS,
                "priority": TaskPriority.MEDIUM,
                "category": "Documentation",
                "tags": ["docs", "update"],
                "created_time": datetime.now(UTC) - timedelta(days=3),
                "due_time": datetime.now(UTC) + timedelta(days=2),
            },
            {
                "title": "Fix bug in authentication module",
                "description": "Users report intermittent login failures",
                "status": TaskStatus.NOT_STARTED,
                "priority": TaskPriority.HIGH,
                "category": "Bugs",
                "tags": ["bugfix", "authentication", "urgent"],
                "created_time": datetime.now(UTC) - timedelta(days=1),
                "due_time": datetime.now(UTC) + timedelta(days=1),
            },
            {
                "title": "Refactor database queries",
                "description": "Optimize performance of main dashboard queries",
                "status": TaskStatus.COMPLETED,
                "priority": TaskPriority.HIGH,
                "category": "Performance",
                "tags": ["optimization", "database"],
                "created_time": datetime.now(UTC) - timedelta(days=5),
                "due_time": datetime.now(UTC) - timedelta(days=1),
                "completed_time": datetime.now(UTC) - timedelta(hours=12),
            },
            {
                "title": "Upgrade dependencies",
                "description": "Update all dependencies to latest versions",
                "status": TaskStatus.DEFERRED,
                "priority": TaskPriority.LOW,
                "category": "Maintenance",
                "tags": ["dependencies", "update"],
                "created_time": datetime.now(UTC) - timedelta(days=10),
                "due_time": None,
            },
        ]

        # Create the tasks
        for template in task_templates:
            task_id = f"task-{uuid.uuid4().hex[:8]}"

            # Create base task data
            task_data = TaskData(
                task_id=task_id,
                title=template["title"],
                description=template["description"],
                status=template["status"],
                priority=template["priority"],
                created_time=template["created_time"],
                due_time=template.get("due_time"),
                completed_time=template.get("completed_time"),
                category=template["category"],
                tags=template["tags"],
                parent_id=None,
                subtask_ids=[],
                assignee=None,
                source_app=self._source_app,
                Timestamp=template["created_time"],
            )

            # Store the task
            self._tasks[task_id] = task_data

            # Add task creation to history
            self._task_history[task_id] = [
                {
                    "action": "created",
                    "timestamp": template["created_time"],
                    "task_data": task_data.model_dump(),
                },
            ]

            # Add task completion to history if completed
            if (
                template["status"] == TaskStatus.COMPLETED
                and "completed_time" in template
            ):
                self._task_history[task_id].append(
                    {
                        "action": "completed",
                        "timestamp": template["completed_time"],
                        "previous_state": {"status": TaskStatus.IN_PROGRESS},
                        "task_data": task_data.model_dump(),
                    },
                )

    def get_task_by_id(self, task_id: str) -> TaskData | None:
        """
        Get a task by its ID.

        Args:
            task_id: The ID of the task to retrieve

        Returns:
            The task data if found, None otherwise
        """
        return self._tasks.get(task_id)

    def get_tasks(self, filters: dict | None = None) -> list[TaskData]:
        """
        Get tasks, optionally filtered.

        Args:
            filters: Dictionary of filters to apply

        Returns:
            List of tasks matching the filters
        """
        if not filters:
            return list(self._tasks.values())

        results = []
        for task in self._tasks.values():
            match = True
            for key, value in filters.items():
                if hasattr(task, key) and getattr(task, key) != value:
                    match = False
                    break
            if match:
                results.append(task)

        return results

    def get_task_history(self, task_id: str) -> list[dict]:
        """
        Get the history of activities for a task.

        Args:
            task_id: The ID of the task

        Returns:
            List of historical activities for the task
        """
        return self._task_history.get(task_id, [])

    def create_task(self, task_data: dict) -> TaskData:
        """
        Create a new task.

        Args:
            task_data: Dictionary with task data

        Returns:
            The created task
        """
        # Generate task ID if not provided
        if "task_id" not in task_data:
            task_data["task_id"] = f"task-{uuid.uuid4().hex[:8]}"

        # Set creation time if not provided
        if "created_time" not in task_data:
            task_data["created_time"] = datetime.now(UTC)

        # Set source app
        task_data["source_app"] = self._source_app

        # Set timestamp
        task_data["Timestamp"] = datetime.now(UTC)

        # Create TaskData object
        task = TaskData(**task_data)

        # Store the task
        self._tasks[task.task_id] = task

        # Add to history
        self._task_history[task.task_id] = [
            {
                "action": "created",
                "timestamp": task.created_time,
                "task_data": task.model_dump(),
            },
        ]

        return task

    def update_task(self, task_id: str, updates: dict) -> TaskData | None:
        """
        Update an existing task.

        Args:
            task_id: The ID of the task to update
            updates: Dictionary with updates to apply

        Returns:
            The updated task if found, None otherwise
        """
        if task_id not in self._tasks:
            return None

        # Get current task
        current_task = self._tasks[task_id]
        previous_state = current_task.model_dump()

        # Create updated task data
        update_data = current_task.model_dump()
        update_data.update(updates)
        update_data["Timestamp"] = datetime.now(UTC)

        # Special handling for completion
        if "status" in updates and updates["status"] == TaskStatus.COMPLETED:
            if "completed_time" not in updates:
                update_data["completed_time"] = datetime.now(UTC)

        # Create updated task
        updated_task = TaskData(**update_data)

        # Store updated task
        self._tasks[task_id] = updated_task

        # Add to history
        self._task_history[task_id].append(
            {
                "action": "updated",
                "timestamp": updated_task.Timestamp,
                "previous_state": {
                    k: previous_state[k] for k in updates if k in previous_state
                },
                "task_data": updated_task.model_dump(),
            },
        )

        return updated_task

    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task.

        Args:
            task_id: The ID of the task to delete

        Returns:
            True if the task was deleted, False otherwise
        """
        if task_id not in self._tasks:
            return False

        # Get task before deletion
        task = self._tasks[task_id]

        # Remove from tasks dictionary
        del self._tasks[task_id]

        # Add to history
        if task_id in self._task_history:
            self._task_history[task_id].append(
                {
                    "action": "deleted",
                    "timestamp": datetime.now(UTC),
                    "task_data": task.model_dump(),
                },
            )

        return True

    def get_recent_activities(self, limit: int = 10) -> list[dict]:
        """
        Get recent task activities.

        Args:
            limit: Maximum number of activities to return

        Returns:
            List of recent activities
        """
        activities = []

        # Gather all activities from all tasks
        for task_id, history in self._task_history.items():
            for activity in history:
                activities.append({"task_id": task_id, **activity})

        # Sort by timestamp (newest first)
        activities.sort(key=lambda x: x["timestamp"], reverse=True)

        # Return limited number
        return activities[:limit]

    def create_random_task(self) -> TaskData:
        """
        Create a random task for testing.

        Returns:
            The generated task
        """
        titles = [
            "Review code for PR #123",
            "Implement new feature X",
            "Design user interface for dashboard",
            "Update API documentation",
            "Set up CI/CD pipeline",
            "Refactor legacy code module",
            "Fix bug in login system",
            "Create user onboarding workflow",
            "Optimize database queries",
            "Write unit tests for module Y",
        ]

        categories = [
            "Development",
            "Design",
            "Documentation",
            "Testing",
            "DevOps",
            "Bugs",
            "Performance",
            "Features",
            "Maintenance",
        ]

        tags_list = [
            ["code", "review", "pr"],
            ["feature", "implementation"],
            ["design", "ui", "dashboard"],
            ["docs", "api"],
            ["devops", "pipeline", "ci-cd"],
            ["refactor", "legacy"],
            ["bug", "login", "security"],
            ["onboarding", "user-experience"],
            ["database", "optimization"],
            ["testing", "unit-tests"],
        ]

        # Select random elements
        title_idx = random.randint(0, len(titles) - 1)

        # Create task data
        task_data = {
            "title": titles[title_idx],
            "description": f"This is a randomly generated task: {titles[title_idx]}",
            "status": random.choice(list(TaskStatus)),
            "priority": random.choice(list(TaskPriority)),
            "category": random.choice(categories),
            "tags": random.choice(tags_list),
            "created_time": datetime.now(UTC)
            - timedelta(days=random.randint(0, 10)),
        }

        # Add due date (50% chance)
        if random.random() > 0.5:
            task_data["due_time"] = datetime.now(UTC) + timedelta(
                days=random.randint(1, 14),
            )

        # If task is completed, add completion time
        if task_data["status"] == TaskStatus.COMPLETED:
            task_data["completed_time"] = datetime.now(UTC) - timedelta(
                hours=random.randint(1, 48),
            )

        # Create and return task
        return self.create_task(task_data)

    # Collector interface methods
    def get_collector_characteristics(self) -> list[ActivityDataCharacteristics]:
        """Get the characteristics of the collector"""
        return [
            ActivityDataCharacteristics.ACTIVITY_DATA_USER_ACTIVITY,
            ActivityDataCharacteristics.ACTIVITY_DATA_TASK_MANAGEMENT,
        ]

    def get_collectorr_name(self) -> str:
        """Get the name of the collector"""
        return self._name

    def get_provider_id(self) -> uuid.UUID:
        """Get the ID of the collector"""
        return self._provider_id

    def retrieve_data(self, data_id: str) -> dict:
        """
        Retrieve data for a specific ID.

        Args:
            data_id: The ID to retrieve data for

        Returns:
            The requested data
        """
        task = self.get_task_by_id(data_id)
        if task:
            return task.model_dump()
        return {}

    def retrieve_temporal_data(
        self,
        reference_time: datetime,
        prior_time_window: timedelta,
        subsequent_time_window: timedelta,
        max_entries: int = 0,
    ) -> list[dict]:
        """
        Retrieve data within a time window.

        Args:
            reference_time: The reference time
            prior_time_window: Time window before reference
            subsequent_time_window: Time window after reference
            max_entries: Maximum number of entries to return

        Returns:
            List of data within the time window
        """
        start_time = reference_time - prior_time_window
        end_time = reference_time + subsequent_time_window

        # Get all activities
        all_activities = []
        for task_id, history in self._task_history.items():
            for activity in history:
                if start_time <= activity["timestamp"] <= end_time:
                    all_activities.append({"task_id": task_id, **activity})

        # Sort by timestamp
        all_activities.sort(key=lambda x: x["timestamp"])

        # Apply limit if specified
        if max_entries > 0:
            all_activities = all_activities[:max_entries]

        return all_activities

    def get_cursor(self, activity_context: uuid.UUID) -> uuid.UUID:
        """
        Get a cursor for the provided activity context.

        Args:
            activity_context: The activity context

        Returns:
            A cursor UUID
        """
        # In this simple implementation, just return a new UUID
        return uuid.uuid4()

    def cache_duration(self) -> timedelta:
        """
        Get the cache duration for this collector's data.

        Returns:
            The cache duration
        """
        return timedelta(minutes=5)

    def get_description(self) -> str:
        """
        Get a description of this collector.

        Returns:
            The collector description
        """
        return self._description

    def get_json_schema(self) -> dict:
        """
        Get the JSON schema for this collector's data.

        Returns:
            The JSON schema
        """
        return TaskActivityData.model_json_schema()


def main():
    """Main function for testing the collector"""
    collector = TaskActivityCollector()

    # Print collector info
    ic("Collector Name:", collector.get_collectorr_name())
    ic("Collector ID:", collector.get_provider_id())
    ic("Collector Characteristics:", collector.get_collector_characteristics())

    # Get existing tasks
    tasks = collector.get_tasks()
    ic(f"Found {len(tasks)} tasks:")
    for task in tasks:
        ic(f"- {task.task_id}: {task.title} ({task.status})")

    # Create a new random task
    new_task = collector.create_random_task()
    ic(f"Created new task: {new_task.task_id} - {new_task.title}")

    # Update a task
    if tasks:
        task_to_update = tasks[0]
        updated_task = collector.update_task(
            task_to_update.task_id,
            {
                "status": (
                    TaskStatus.COMPLETED
                    if task_to_update.status != TaskStatus.COMPLETED
                    else TaskStatus.IN_PROGRESS
                ),
            },
        )
        if updated_task:
            ic(f"Updated task {updated_task.task_id} status to {updated_task.status}")

    # Get recent activities
    activities = collector.get_recent_activities()
    ic(f"Recent activities ({len(activities)}):")
    for activity in activities:
        ic(
            f"- {activity['timestamp']}: {activity['action']} task {activity['task_id']}",
        )


if __name__ == "__main__":
    main()
