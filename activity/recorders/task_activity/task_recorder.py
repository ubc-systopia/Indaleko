"""
This module implements a task activity recorder for Indaleko.

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

import json
import logging
import os
import sys
import uuid
from datetime import UTC, datetime
from typing import Any

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.task_activity.data_models.task_data_model import (
    TaskActivityData,
    TaskData,
    TaskStatus,
)
from activity.collectors.task_activity.semantic_attributes import (
    ACTIVITY_DATA_TASK_ASSIGNEE,
    ACTIVITY_DATA_TASK_CATEGORY,
    ACTIVITY_DATA_TASK_COMPLETED_TIME,
    ACTIVITY_DATA_TASK_CREATED_TIME,
    ACTIVITY_DATA_TASK_DESCRIPTION,
    ACTIVITY_DATA_TASK_DUE_TIME,
    ACTIVITY_DATA_TASK_ID,
    ACTIVITY_DATA_TASK_PARENT_ID,
    ACTIVITY_DATA_TASK_PRIORITY,
    ACTIVITY_DATA_TASK_SOURCE_APP,
    ACTIVITY_DATA_TASK_STATUS,
    ACTIVITY_DATA_TASK_SUBTASKS,
    ACTIVITY_DATA_TASK_TAGS,
    ACTIVITY_DATA_TASK_TITLE,
)
from activity.collectors.task_activity.task_collector import TaskActivityCollector
from activity.data_model.activity import IndalekoActivityDataModel
from activity.recorders.base import RecorderBase
from activity.recorders.registration_service import (
    IndalekoActivityDataRegistrationService,
)
from data_models.i_uuid import IndalekoUUIDDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from db import IndalekoCollection, IndalekoDBConfig

# pylint: disable=wrong-import-position
from Indaleko import Indaleko

# pylint: enable=wrong-import-position


class TaskActivityRecorder(RecorderBase):
    """
    Task activity data recorder for Indaleko.

    This recorder processes task activity data and stores it in the Indaleko database.
    """

    source_data = {
        "Identifier": uuid.UUID("8e7a6c4d-5f2b-9e8d-3c1a-7b0f6d2e5c9a"),
        "Version": "1.0.0",
        "Description": "Task Activity Recorder",
    }

    semantic_attributes_mapping = {
        "task_id": ACTIVITY_DATA_TASK_ID,
        "title": ACTIVITY_DATA_TASK_TITLE,
        "description": ACTIVITY_DATA_TASK_DESCRIPTION,
        "status": ACTIVITY_DATA_TASK_STATUS,
        "priority": ACTIVITY_DATA_TASK_PRIORITY,
        "created_time": ACTIVITY_DATA_TASK_CREATED_TIME,
        "due_time": ACTIVITY_DATA_TASK_DUE_TIME,
        "completed_time": ACTIVITY_DATA_TASK_COMPLETED_TIME,
        "category": ACTIVITY_DATA_TASK_CATEGORY,
        "tags": ACTIVITY_DATA_TASK_TAGS,
        "parent_id": ACTIVITY_DATA_TASK_PARENT_ID,
        "subtask_ids": ACTIVITY_DATA_TASK_SUBTASKS,
        "assignee": ACTIVITY_DATA_TASK_ASSIGNEE,
        "source_app": ACTIVITY_DATA_TASK_SOURCE_APP,
    }

    def __init__(self, **kwargs):
        """Initialize the task activity recorder"""
        # Initialize database connection
        self.db_config = IndalekoDBConfig()
        assert self.db_config is not None, "Failed to get the database configuration"

        # Initialize source identifier
        source_identifier = IndalekoSourceIdentifierDataModel(
            Identifier=self.source_data["Identifier"],
            Version=self.source_data["Version"],
            Description=self.source_data["Description"],
        )

        # Initialize record kwargs
        record_kwargs = {
            "Identifier": str(self.source_data["Identifier"]),
            "Version": self.source_data["Version"],
            "Description": self.source_data["Description"],
            "Record": IndalekoRecordDataModel(
                SourceIdentifier=source_identifier,
                Timestamp=datetime.now(UTC),
                Attributes={},
                Data="",
            ),
        }

        # Register with the provider registrar
        self.provider_registrar = IndalekoActivityDataRegistrationService()
        assert (
            self.provider_registrar is not None
        ), "Failed to get the provider registrar"

        collector_data = self.provider_registrar.lookup_provider_by_identifier(
            str(self.source_data["Identifier"]),
        )
        if collector_data is None:
            ic("Registering the provider")
            collector_data, collection = self.provider_registrar.register_provider(
                **record_kwargs,
            )
        else:
            ic("Provider already registered")
            collection = IndalekoActivityDataRegistrationService.lookup_activity_provider_collection(
                str(self.source_data["Identifier"]),
            )

        ic(collector_data)
        ic(collection)
        self.collector_data = collector_data
        self.collection = collection

        # Initialize collector
        # In a real implementation, this would connect to an actual task management service
        # For this demo, we use the simulated collector
        self.collector = kwargs.get("collector", TaskActivityCollector())

        # Set up logging
        self.logger = logging.getLogger("TaskActivityRecorder")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def get_recorder_name(self) -> str:
        """Get the name of the recorder"""
        return "task_activity_recorder"

    def get_recorder_id(self) -> uuid.UUID:
        """Get the ID of the recorder"""
        return self.source_data["Identifier"]

    def get_recorder_characteristics(self) -> list[ActivityDataCharacteristics]:
        """Get the characteristics of the recorder"""
        return self.collector.get_collector_characteristics()

    def get_collector_class_model(self) -> dict[str, type]:
        """Get the class model for the collector"""
        return {"TaskData": TaskData, "TaskActivityData": TaskActivityData}

    def get_description(self) -> str:
        """Get the description of the recorder"""
        return self.source_data["Description"]

    def process_data(self, data: Any) -> dict[str, Any]:
        """
        Process the data from the collector.

        Args:
            data: Data to process

        Returns:
            Processed data
        """
        return data

    def create_semantic_attributes(
        self, task_data: TaskData,
    ) -> list[IndalekoSemanticAttributeDataModel]:
        """
        Create semantic attributes from task data.

        Args:
            task_data: The task data to convert

        Returns:
            List of semantic attributes
        """
        semantic_attributes = []

        # Convert task data to dictionary
        task_dict = task_data.model_dump()

        # Create a semantic attribute for each field
        for field_name, uuid_value in self.semantic_attributes_mapping.items():
            if field_name in task_dict and task_dict[field_name] is not None:
                value = task_dict[field_name]

                # Convert special types
                if isinstance(value, datetime):
                    value = value.isoformat()
                elif isinstance(value, list):
                    value = json.dumps(value)
                elif isinstance(value, (TaskStatus, TaskPriority)):
                    value = value.value

                # Create the semantic attribute
                semantic_attributes.append(
                    IndalekoSemanticAttributeDataModel(
                        Identifier=IndalekoUUIDDataModel(
                            Identifier=uuid_value, Version="1", Description=field_name,
                        ),
                        Data=str(value),
                    ),
                )

        return semantic_attributes

    def build_task_activity_document(
        self,
        task_data: TaskData,
        action: str,
        previous_state: dict | None = None,
        semantic_attributes: list[IndalekoSemanticAttributeDataModel] | None = None,
    ) -> dict:
        """
        Build a document for storing in the database.

        Args:
            task_data: The task data
            action: The action performed
            previous_state: The previous state (for updates)
            semantic_attributes: The semantic attributes

        Returns:
            Document for storage
        """
        if semantic_attributes is None:
            semantic_attributes = self.create_semantic_attributes(task_data)

        # Prepare the activity data
        activity_data = {
            "task": task_data.model_dump(),
            "action": action,
            "previous_state": previous_state,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Create the record
        record = IndalekoRecordDataModel(
            SourceIdentifier=self.source_data,
            Timestamp=datetime.now(UTC),
            Data=Indaleko.encode_binary_data(activity_data),
        )

        # Create the activity data model
        activity_data_args = {
            "Record": record,
            "Timestamp": datetime.now(UTC),
            "SemanticAttributes": semantic_attributes,
        }

        activity_data = IndalekoActivityDataModel(**activity_data_args)

        # Convert to dictionary
        return json.loads(
            activity_data.model_dump_json(exclude_none=True, exclude_unset=True),
        )

    def store_task_activity(
        self, task_data: TaskData, action: str, previous_state: dict | None = None,
    ) -> dict:
        """
        Store a task activity in the database.

        Args:
            task_data: The task data
            action: The action performed
            previous_state: The previous state (for updates)

        Returns:
            The stored document
        """
        # Create semantic attributes
        semantic_attributes = self.create_semantic_attributes(task_data)

        # Build document
        doc = self.build_task_activity_document(
            task_data=task_data,
            action=action,
            previous_state=previous_state,
            semantic_attributes=semantic_attributes,
        )

        # Insert into collection
        self.collection.insert(doc)

        return doc

    def get_latest_db_update(self, task_id: str | None = None) -> dict:
        """
        Get the latest update from the database.

        Args:
            task_id: Optional task ID to filter by

        Returns:
            The latest update
        """
        assert isinstance(
            self.collection, IndalekoCollection,
        ), f"collection is not an IndalekoCollection {type(self.collection)}"

        if task_id:
            # Query with task ID filter
            query = """
                FOR doc IN @@collection
                    FILTER doc.Record.Data LIKE @task_id
                    SORT doc.Timestamp DESC
                    LIMIT 1
                    RETURN doc
            """
            bind_vars = {"@collection": self.collection.name, "task_id": f"%{task_id}%"}
        else:
            # Query without filter
            query = """
                FOR doc IN @@collection
                    SORT doc.Timestamp DESC
                    LIMIT 1
                    RETURN doc
            """
            bind_vars = {"@collection": self.collection.name}

        results = IndalekoDBConfig()._arangodb.aql.execute(query, bind_vars=bind_vars)
        entries = [entry for entry in results]

        if len(entries) == 0:
            return None

        assert len(entries) == 1, f"Too many results {len(entries)}"
        return entries[0]

    def get_task_history(self, task_id: str, limit: int = 10) -> list[dict]:
        """
        Get the history of a task from the database.

        Args:
            task_id: The task ID
            limit: Maximum number of entries to return

        Returns:
            List of historical entries for the task
        """
        assert isinstance(
            self.collection, IndalekoCollection,
        ), f"collection is not an IndalekoCollection {type(self.collection)}"

        query = """
            FOR doc IN @@collection
                FILTER doc.Record.Data LIKE @task_id
                SORT doc.Timestamp DESC
                LIMIT @limit
                RETURN doc
        """
        bind_vars = {
            "@collection": self.collection.name,
            "task_id": f"%{task_id}%",
            "limit": limit,
        }

        results = IndalekoDBConfig()._arangodb.aql.execute(query, bind_vars=bind_vars)
        return [entry for entry in results]

    def sync_all_tasks(self) -> int:
        """
        Sync all tasks from the collector to the database.

        Returns:
            Number of tasks synced
        """
        # Get all tasks from collector
        tasks = self.collector.get_tasks()

        # Store each task
        count = 0
        for task in tasks:
            self.store_task_activity(task, "synced")
            count += 1

        return count

    def sync_recent_activities(self, limit: int = 10) -> int:
        """
        Sync recent activities from the collector to the database.

        Args:
            limit: Maximum number of activities to sync

        Returns:
            Number of activities synced
        """
        # Get recent activities from collector
        activities = self.collector.get_recent_activities(limit)

        # Store each activity
        count = 0
        for activity in activities:
            task_id = activity["task_id"]
            action = activity["action"]

            # Get task data
            task_data = self.collector.get_task_by_id(task_id)
            if task_data:
                previous_state = activity.get("previous_state")

                # Store activity
                self.store_task_activity(task_data, action, previous_state)
                count += 1

        return count

    def update_data(self) -> int:
        """
        Update data in the database by syncing recent activities.

        Returns:
            Number of activities synced
        """
        return self.sync_recent_activities()


def main():
    """Main function for testing the recorder"""
    # Create collector and recorder
    collector = TaskActivityCollector()
    recorder = TaskActivityRecorder(collector=collector)

    # Print recorder info
    ic("Recorder Name:", recorder.get_recorder_name())
    ic("Recorder ID:", recorder.get_recorder_id())
    ic("Recorder Characteristics:", recorder.get_recorder_characteristics())

    # Get existing tasks from collector
    tasks = collector.get_tasks()
    ic(f"Found {len(tasks)} tasks")

    # Create a new random task
    new_task = collector.create_random_task()
    ic(f"Created new task: {new_task.task_id} - {new_task.title}")

    # Store the new task
    doc = recorder.store_task_activity(new_task, "created")
    ic("Stored new task in database")

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
            doc = recorder.store_task_activity(
                updated_task, "updated", {"status": task_to_update.status},
            )
            ic("Stored updated task in database")

    # Sync all tasks
    count = recorder.sync_all_tasks()
    ic(f"Synced {count} tasks to database")

    # Get latest update from database
    latest = recorder.get_latest_db_update()
    if latest:
        ic("Latest update from database:", latest["Timestamp"])

    # Get task history
    if new_task:
        history = recorder.get_task_history(new_task.task_id)
        ic(f"Task history for {new_task.task_id}: {len(history)} entries")


if __name__ == "__main__":
    main()
