"""
Dropbox Storage Activity Recorder for Indaleko.

This module provides a recorder for Dropbox storage activities that
stores the activities collected by the Dropbox storage activity collector.

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
import socket
import sys
import uuid

from datetime import timedelta
from typing import Any


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.storage.data_models.storage_activity_data_model import (
    DropboxStorageActivityData,
    StorageActivityMetadata,
    StorageProviderType,
)
from activity.collectors.storage.dropbox.dropbox_collector import (
    DropboxStorageActivityCollector,
)
from activity.collectors.storage.semantic_attributes import (
    StorageActivityAttributes,
    get_semantic_attributes_for_activity,
)
from activity.recorders.storage.base import StorageActivityRecorder
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel


# pylint: enable=wrong-import-position


class DropboxStorageActivityRecorder(StorageActivityRecorder):
    """
    Recorder for Dropbox storage activities.

    This recorder extends the base storage activity recorder and adds Dropbox-specific
    functionality for storing and querying Dropbox file system activities.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Dropbox storage activity recorder.

        Args:
            collector: Optional DropboxStorageActivityCollector instance to use
            collection_name: Optional custom collection name
            db_config_path: Optional path to database configuration
            register_service: Whether to register with the service manager
            auto_connect: Whether to connect to the database automatically
            debug: Whether to enable debug mode
        """
        # Set Dropbox-specific defaults
        kwargs["name"] = kwargs.get("name", "Dropbox Storage Activity Recorder")
        kwargs["recorder_id"] = kwargs.get(
            "recorder_id",
            uuid.UUID("9c51f8a7-4b3e-5d2f-8c6b-e7f9d0c4a3b2"),
        )
        kwargs["provider_type"] = StorageProviderType.DROPBOX
        kwargs["description"] = kwargs.get(
            "description",
            "Records storage activities from Dropbox",
        )
        kwargs["collection_name"] = kwargs.get(
            "collection_name",
            "DropboxStorageActivity",
        )

        # Get or create Dropbox collector
        collector = kwargs.get("collector")
        if collector is None:
            # If no collector is provided, create one with default settings
            collector = DropboxStorageActivityCollector(
                auto_start=False,  # Don't start automatically here
            )
            kwargs["collector"] = collector
        elif not isinstance(collector, DropboxStorageActivityCollector):
            raise ValueError(
                "collector must be an instance of DropboxStorageActivityCollector",
            )

        # Call parent initializer
        super().__init__(**kwargs)

        # Dropbox-specific setup
        self._dropbox_collector = collector

        # Add Dropbox-specific metadata if available
        if hasattr(self._dropbox_collector, "_user_info") and self._dropbox_collector._user_info:
            email = getattr(self._dropbox_collector._user_info, "email", "unknown")
            account_id = getattr(
                self._dropbox_collector._user_info,
                "account_id",
                "unknown",
            )

            self._metadata = StorageActivityMetadata(
                provider_type=StorageProviderType.DROPBOX,
                provider_name=self._name,
                source_machine=socket.gethostname(),
                storage_location=f"Dropbox:{email}",
            )

    def collect_and_store_activities(
        self,
        start_monitoring: bool = True,
    ) -> list[uuid.UUID]:
        """
        Collect and store Dropbox activities in one operation.

        Args:
            start_monitoring: Whether to start monitoring if not already active

        Returns:
            List of activity UUIDs that were stored
        """
        # Start monitoring if requested and not already active
        if start_monitoring and not self._dropbox_collector._active:
            self._dropbox_collector.start_monitoring()

        # Get current activities from the collector
        activities = self._dropbox_collector.get_activities()

        # Store activities and return their IDs
        return self.store_activities(activities)

    def stop_monitoring(self) -> None:
        """Stop monitoring Dropbox activities."""
        if self._dropbox_collector._active:
            self._dropbox_collector.stop_monitoring()

    def get_activities_by_dropbox_id(
        self,
        dropbox_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """
        Get activities for a specific Dropbox file ID.

        Args:
            dropbox_id: The Dropbox file ID to get activities for
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of activity documents for the file ID
        """
        # Query the database
        query = """
            FOR doc IN @@collection
            FILTER doc.Record.Data.dropbox_file_id == @dropbox_id
            SORT doc.Record.Data.timestamp DESC
            LIMIT @offset, @limit
            RETURN doc
        """

        # Execute query
        cursor = self._db._arangodb.aql.execute(
            query,
            bind_vars={
                "@collection": self._collection_name,
                "dropbox_id": dropbox_id,
                "offset": offset,
                "limit": limit,
            },
        )

        # Return results
        return [doc for doc in cursor]

    def get_activities_by_revision(
        self,
        revision: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """
        Get activities for a specific file revision.

        Args:
            revision: The file revision to get activities for
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of activity documents for the file revision
        """
        # Query the database
        query = """
            FOR doc IN @@collection
            FILTER doc.Record.Data.revision == @revision
            SORT doc.Record.Data.timestamp DESC
            LIMIT @offset, @limit
            RETURN doc
        """

        # Execute query
        cursor = self._db._arangodb.aql.execute(
            query,
            bind_vars={
                "@collection": self._collection_name,
                "revision": revision,
                "offset": offset,
                "limit": limit,
            },
        )

        # Return results
        return [doc for doc in cursor]

    def get_activities_by_shared_folder(
        self,
        shared_folder_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """
        Get activities for files in a specific shared folder.

        Args:
            shared_folder_id: The shared folder ID to get activities for
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of activity documents for files in the shared folder
        """
        # Query the database
        query = """
            FOR doc IN @@collection
            FILTER doc.Record.Data.shared_folder_id == @shared_folder_id
            SORT doc.Record.Data.timestamp DESC
            LIMIT @offset, @limit
            RETURN doc
        """

        # Execute query
        cursor = self._db._arangodb.aql.execute(
            query,
            bind_vars={
                "@collection": self._collection_name,
                "shared_folder_id": shared_folder_id,
                "offset": offset,
                "limit": limit,
            },
        )

        # Return results
        return [doc for doc in cursor]

    def get_shared_activities(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """
        Get all activities for shared files.

        Args:
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of activity documents for shared files
        """
        # Query the database
        query = """
            FOR doc IN @@collection
            FILTER doc.Record.Data.shared_folder_id != null
            SORT doc.Record.Data.timestamp DESC
            LIMIT @offset, @limit
            RETURN doc
        """

        # Execute query
        cursor = self._db._arangodb.aql.execute(
            query,
            bind_vars={
                "@collection": self._collection_name,
                "offset": offset,
                "limit": limit,
            },
        )

        # Return results
        return [doc for doc in cursor]

    def get_dropbox_specific_statistics(self) -> dict[str, Any]:
        """
        Get Dropbox-specific statistics about the activities.

        Returns:
            Dictionary of Dropbox-specific statistics
        """
        # Get basic statistics from parent class
        stats = self.get_activity_statistics()

        # Add Dropbox-specific statistics

        # Query for count by file revision
        revision_query = """
            FOR doc IN @@collection
            FILTER doc.Record.Data.revision != null
            COLLECT revision = doc.Record.Data.revision WITH COUNT INTO count
            SORT count DESC
            LIMIT 10
            RETURN { revision, count }
        """

        # Query for count by shared folder
        shared_query = """
            FOR doc IN @@collection
            FILTER doc.Record.Data.shared_folder_id != null
            COLLECT shared_folder = doc.Record.Data.shared_folder_id WITH COUNT INTO count
            SORT count DESC
            LIMIT 10
            RETURN { shared_folder, count }
        """

        # Query for count of shared vs. non-shared files
        sharing_query = """
            LET shared = (
                FOR doc IN @@collection
                FILTER doc.Record.Data.shared_folder_id != null
                COLLECT WITH COUNT INTO count
                RETURN count
            )[0]

            LET not_shared = (
                FOR doc IN @@collection
                FILTER doc.Record.Data.shared_folder_id == null
                COLLECT WITH COUNT INTO count
                RETURN count
            )[0]

            RETURN { shared, not_shared }
        """

        # Execute Dropbox-specific queries
        try:
            revision_cursor = self._db._arangodb.aql.execute(
                revision_query,
                bind_vars={"@collection": self._collection_name},
            )
            shared_cursor = self._db._arangodb.aql.execute(
                shared_query,
                bind_vars={"@collection": self._collection_name},
            )
            sharing_cursor = self._db._arangodb.aql.execute(
                sharing_query,
                bind_vars={"@collection": self._collection_name},
            )

            # Add to statistics
            stats["top_revisions"] = {item["revision"]: item["count"] for item in revision_cursor}
            stats["top_shared_folders"] = {item["shared_folder"]: item["count"] for item in shared_cursor}

            sharing_stats = next(sharing_cursor, {"shared": 0, "not_shared": 0})
            stats["sharing"] = sharing_stats

            # Calculate sharing percentage if there are activities
            total = sharing_stats.get("shared", 0) + sharing_stats.get("not_shared", 0)
            if total > 0:
                stats["sharing_percentage"] = (sharing_stats.get("shared", 0) / total) * 100
            else:
                stats["sharing_percentage"] = 0

        except Exception as e:
            self._logger.error(f"Error generating Dropbox statistics: {e}")

        # Add information about monitoring state
        stats["monitoring_active"] = self._dropbox_collector._active

        return stats

    def _build_dropbox_activity_document(
        self,
        activity_data: DropboxStorageActivityData,
        semantic_attributes: list[IndalekoSemanticAttributeDataModel] | None = None,
    ) -> dict:
        """
        Build a document for storing a Dropbox activity in the database.

        Args:
            activity_data: The Dropbox activity data to store
            semantic_attributes: Optional list of semantic attributes

        Returns:
            Document for the database
        """
        # Ensure we have semantic attributes specific to Dropbox
        if semantic_attributes is None:
            # Get common storage activity attributes
            semantic_attributes = get_semantic_attributes_for_activity(
                activity_data.model_dump(),
            )

            # Add Dropbox-specific attributes if needed
            dropbox_attribute = IndalekoSemanticAttributeDataModel(
                Identifier=str(StorageActivityAttributes.STORAGE_DROPBOX.value),
                Label="Dropbox Storage Activity",
                Description="Storage activity from Dropbox",
            )

            # Check if Dropbox attribute is already present
            dropbox_attribute_present = False
            for attr in semantic_attributes:
                if attr.Identifier == str(
                    StorageActivityAttributes.STORAGE_DROPBOX.value,
                ):
                    dropbox_attribute_present = True
                    break

            if not dropbox_attribute_present:
                semantic_attributes.append(dropbox_attribute)

            # Add sharing attribute if this is a shared file
            if activity_data.shared_folder_id:
                sharing_attribute = IndalekoSemanticAttributeDataModel(
                    Identifier=str(StorageActivityAttributes.STORAGE_SHARED.value),
                    Label="Shared Storage",
                    Description="Activity involves shared storage",
                )

                # Check if sharing attribute is already present
                sharing_attribute_present = False
                for attr in semantic_attributes:
                    if attr.Identifier == str(
                        StorageActivityAttributes.STORAGE_SHARED.value,
                    ):
                        sharing_attribute_present = True
                        break

                if not sharing_attribute_present:
                    semantic_attributes.append(sharing_attribute)

        # Use the parent class method to build the document
        return super().build_activity_document(activity_data, semantic_attributes)

    def store_activity(
        self,
        activity_data: DropboxStorageActivityData | dict,
    ) -> uuid.UUID:
        """
        Store a Dropbox activity in the database.

        Args:
            activity_data: Dropbox activity data to store

        Returns:
            UUID of the stored activity
        """
        # Convert dict to DropboxStorageActivityData if needed
        if isinstance(activity_data, dict):
            # Create DropboxStorageActivityData from dict
            activity_data = DropboxStorageActivityData(**activity_data)

        # Build document with Dropbox-specific attributes
        document = self._build_dropbox_activity_document(activity_data)

        # Store in database
        result = self._collection.add_document(document)

        return activity_data.activity_id

    # Override parent class methods as needed

    def get_recorder_characteristics(self) -> list[ActivityDataCharacteristics]:
        """Get the characteristics of this recorder."""
        return [
            ActivityDataCharacteristics.ACTIVITY_DATA_SYSTEM_ACTIVITY,
            ActivityDataCharacteristics.ACTIVITY_DATA_FILE_ACTIVITY,
            ActivityDataCharacteristics.ACTIVITY_DATA_CLOUD_STORAGE,
        ]

    def get_json_schema(self) -> dict:
        """
        Get the JSON schema for this recorder's data.

        Returns:
            The JSON schema
        """
        return DropboxStorageActivityData.model_json_schema()

    def cache_duration(self) -> timedelta:
        """
        Get the cache duration for this recorder's data.

        Dropbox activities are less frequent than local file operations,
        so we can use a longer cache duration.

        Returns:
            The cache duration
        """
        return timedelta(hours=2)


# Example usage in __main__
if __name__ == "__main__":
    # Configure logging
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create collector with default settings
    collector = DropboxStorageActivityCollector(auto_start=True, debug=True)

    # Create recorder that uses the collector
    recorder = DropboxStorageActivityRecorder(collector=collector, debug=True)

    # Collect and store some activities
    try:
        # Wait for some activities to be collected
        import time

        print("Monitoring Dropbox activities for 5 minutes...")
        time.sleep(300)  # 5 minutes

        # Store collected activities
        activity_ids = recorder.collect_and_store_activities()
        print(f"Stored {len(activity_ids)} activities")

        # Get statistics
        stats = recorder.get_dropbox_specific_statistics()
        print("Activity statistics:")
        for key, value in stats.items():
            # Skip complex values for cleaner output
            if isinstance(value, dict) and len(value) > 5:
                print(f"  {key}: {len(value)} items")
            else:
                print(f"  {key}: {value}")

    finally:
        # Stop monitoring
        recorder.stop_monitoring()
