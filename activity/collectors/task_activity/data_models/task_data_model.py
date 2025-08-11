"""
This module defines the data model for task activities.

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
import sys

from datetime import datetime
from enum import Enum

from pydantic import Field, field_validator, model_validator


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel


# pylint: enable=wrong-import-position


class TaskStatus(str, Enum):
    """Status of a task in a task manager."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DEFERRED = "deferred"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Priority of a task in a task manager."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskData(IndalekoBaseModel):
    """
    Data model for task activities.

    This model represents a task in a task management system, capturing
    details about the task's properties, status, and relationships.
    """

    # Core task properties
    task_id: str = Field(..., description="Unique identifier for the task")
    title: str = Field(..., description="Title or name of the task")
    description: str | None = Field(
        None,
        description="Detailed description of the task",
    )
    status: TaskStatus = Field(
        TaskStatus.NOT_STARTED,
        description="Current status of the task",
    )
    priority: TaskPriority = Field(
        TaskPriority.NONE,
        description="Priority level of the task",
    )

    # Task timestamps
    created_time: datetime = Field(..., description="When the task was created")
    due_time: datetime | None = Field(
        None,
        description="When the task is due (if applicable)",
    )
    completed_time: datetime | None = Field(
        None,
        description="When the task was completed (if applicable)",
    )

    # Task categorization
    category: str | None = Field(
        None,
        description="Category or project the task belongs to",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags associated with the task",
    )

    # Task relationships
    parent_id: str | None = Field(
        None,
        description="ID of parent task (if this is a subtask)",
    )
    subtask_ids: list[str] = Field(
        default_factory=list,
        description="IDs of subtasks under this task",
    )
    assignee: str | None = Field(None, description="Person assigned to the task")

    # Source information
    source_app: str = Field(
        ...,
        description="Application or service that generated this task",
    )

    # Activity timestamp (when the activity was recorded)
    Timestamp: datetime = Field(..., description="When this activity was recorded")

    @field_validator("completed_time")
    @classmethod
    def validate_completed_time(cls, value: datetime | None, values):
        """Ensure completed_time is only set when status is COMPLETED."""
        if value is not None and "status" in values.data and values.data["status"] != TaskStatus.COMPLETED:
            raise ValueError("Completed time can only be set when status is COMPLETED")
        return value

    @model_validator(mode="after")
    def validate_timestamps(self):
        """Ensure timestamps are in logical order."""
        if self.due_time is not None and self.due_time < self.created_time:
            raise ValueError("Due time cannot be before created time")

        if self.completed_time is not None:
            if self.completed_time < self.created_time:
                raise ValueError("Completed time cannot be before created time")

            if self.due_time is not None and self.completed_time > self.due_time:
                # This is allowed but might warrant a warning
                pass

        return self

    class Config:
        """Configuration and example data for the task data model."""

        json_schema_extra = {
            "example": {
                "task_id": "task-123456",
                "title": "Complete Indaleko Documentation",
                "description": "Finish writing documentation for the Indaleko project",
                "status": "in_progress",
                "priority": "high",
                "created_time": "2024-04-01T09:00:00Z",
                "due_time": "2024-04-15T17:00:00Z",
                "completed_time": None,
                "category": "Documentation",
                "tags": ["indaleko", "docs", "urgent"],
                "parent_id": "project-789",
                "subtask_ids": ["task-456", "task-789"],
                "assignee": "john.doe@example.com",
                "source_app": "Trello",
                "Timestamp": "2024-04-10T14:30:00Z",
            },
        }


class TaskActivityData(IndalekoBaseModel):
    """
    Data model for task activity events.

    This model captures activities related to tasks, such as task creation,
    completion, or updates.
    """

    # The task data
    task: TaskData = Field(
        ...,
        description="The task data associated with this activity",
    )

    # Action that generated this activity
    action: str = Field(
        ...,
        description="Action that generated this activity (created, updated, completed, etc.)",
    )

    # Previous state for updates (optional)
    previous_state: dict | None = Field(
        None,
        description="Previous state of the task (for updates)",
    )

    # Activity timestamp (when the activity was recorded)
    Timestamp: datetime = Field(..., description="When this activity was recorded")

    # Record associated with this activity
    Record: IndalekoRecordDataModel = Field(
        ...,
        title="Record",
        description="The record for the activity data.",
    )

    # Semantic attributes for this activity
    SemanticAttributes: list[IndalekoSemanticAttributeDataModel] = Field(
        ...,
        title="SemanticAttributes",
        description="The semantic attributes captured by the activity data provider.",
    )

    class Config:
        """Configuration and example data for the task activity data model."""

        json_schema_extra = {
            "example": {
                "task": TaskData.Config.json_schema_extra["example"],
                "action": "created",
                "previous_state": None,
                "Timestamp": "2024-04-10T14:30:00Z",
                "Record": IndalekoRecordDataModel.get_json_example(),
                "SemanticAttributes": [
                    IndalekoSemanticAttributeDataModel.get_json_example(),
                ],
            },
        }


def main() -> None:
    """This allows testing the data models."""
    TaskData.test_model_main()

    TaskActivityData.test_model_main()


if __name__ == "__main__":
    main()
