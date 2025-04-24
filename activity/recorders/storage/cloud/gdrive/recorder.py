"""
Google Drive Storage Activity Recorder for Indaleko.

This module provides a recorder for Google Drive storage activities that
stores the activities collected by the Google Drive storage activity collector.

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

import logging
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
from activity.collectors.storage.cloud.data_models.gdrive_activity_model import (
    GDriveActivityData,
    GDriveFileType,
)
from activity.collectors.storage.cloud.gdrive_activity_collector import (
    GoogleDriveActivityCollector,
)
from activity.collectors.storage.data_models.storage_activity_data_model import (
    GoogleDriveStorageActivityData,
    StorageActivityMetadata,
    StorageProviderType,
)
from activity.collectors.storage.semantic_attributes import (
    StorageActivityAttributes,
    get_semantic_attributes_for_activity,
)
from activity.recorders.storage.base import StorageActivityRecorder
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel

# pylint: enable=wrong-import-position


class GoogleDriveActivityRecorder(StorageActivityRecorder):
    """
    Recorder for Google Drive storage activities.

    This recorder extends the base storage activity recorder and adds Google Drive-specific
    functionality for storing and querying Google Drive file system activities.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Google Drive storage activity recorder.

        Args:
            collector: Optional GoogleDriveActivityCollector instance to use
            collection_name: Optional custom collection name
            db_config_path: Optional path to database configuration
            register_service: Whether to register with the service manager
            auto_connect: Whether to connect to the database automatically
            debug: Whether to enable debug mode
        """
        # Setup logging early
        self._debug = kwargs.get("debug", False)
        self._logger = logging.getLogger(__name__)
        if self._debug:
            self._logger.setLevel(logging.DEBUG)

        # Set Google Drive-specific defaults
        kwargs["name"] = kwargs.get("name", "Google Drive Storage Activity Recorder")
        kwargs["recorder_id"] = kwargs.get(
            "recorder_id",
            uuid.UUID("4e8d9f2a-5c6b-7d8e-9f0a-1b2c3d4e5f6a"),
        )
        kwargs["provider_type"] = StorageProviderType.GOOGLE_DRIVE
        kwargs["description"] = kwargs.get(
            "description",
            "Records storage activities from Google Drive",
        )
        kwargs["collection_name"] = kwargs.get(
            "collection_name",
            "GoogleDriveStorageActivity",
        )

        # Get or create Google Drive collector
        collector = kwargs.get("collector")
        if collector is None:
            # If no collector is provided, create one with default settings
            collector = GoogleDriveActivityCollector(
                auto_start=False,  # Don't start automatically here
            )
            kwargs["collector"] = collector
        elif not isinstance(collector, GoogleDriveActivityCollector):
            raise ValueError(
                "collector must be an instance of GoogleDriveActivityCollector",
            )

        # Get default config directory for database
        default_config_dir = os.path.join(
            os.environ.get("INDALEKO_ROOT", "."),
            "config",
        )
        default_db_config_path = os.path.join(default_config_dir, "db_config.json")

        # Set default DB config path if not provided
        if "db_config_path" not in kwargs or kwargs["db_config_path"] is None:
            kwargs["db_config_path"] = default_db_config_path
            self._logger.info(f"Using default DB config path: {default_db_config_path}")

        # Call parent initializer
        super().__init__(**kwargs)

        # Google Drive-specific setup
        self._gdrive_collector = collector

        # Add basic metadata
        self._metadata = StorageActivityMetadata(
            provider_type=StorageProviderType.GOOGLE_DRIVE,
            provider_name=self._name,
            source_machine=socket.gethostname(),
            storage_location="Google Drive",
        )

    def collect_and_store_activities(self) -> list[uuid.UUID]:
        """
        Collect and store Google Drive activities in one operation.

        Returns:
            List of activity UUIDs that were stored
        """
        # Run the collector
        self._gdrive_collector.collect_data()

        # Get current activities from the collector
        activities = self._gdrive_collector.activities

        # Convert to storage activities
        storage_activities = [activity.to_storage_activity() for activity in activities]

        # Store activities and return their IDs
        return self.store_activities(storage_activities)

    def _build_gdrive_activity_document(
        self,
        activity_data: GoogleDriveStorageActivityData | GDriveActivityData,
        semantic_attributes: list[IndalekoSemanticAttributeDataModel] | None = None,
    ) -> dict:
        """
        Build a document for storing a Google Drive activity in the database.

        Args:
            activity_data: The Google Drive activity data to store
            semantic_attributes: Optional list of semantic attributes

        Returns:
            Document for the database
        """
        # Ensure we have semantic attributes specific to Google Drive
        if semantic_attributes is None:
            # Get common storage activity attributes
            semantic_attributes = get_semantic_attributes_for_activity(
                activity_data.model_dump(),
            )

            # Add Google Drive-specific attributes if needed
            gdrive_attribute = IndalekoSemanticAttributeDataModel(
                Identifier=str(StorageActivityAttributes.STORAGE_GOOGLE_DRIVE.value),
                Label="Google Drive Storage Activity",
                Description="Storage activity from Google Drive",
            )

            # Check if Google Drive attribute is already present
            gdrive_attribute_present = False
            for attr in semantic_attributes:
                if attr.Identifier == str(
                    StorageActivityAttributes.STORAGE_GOOGLE_DRIVE.value,
                ):
                    gdrive_attribute_present = True
                    break

            if not gdrive_attribute_present:
                semantic_attributes.append(gdrive_attribute)

            # Add sharing attribute if this is a shared file
            if hasattr(activity_data, "shared") and activity_data.shared:
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

            # Add Drive app type attribute if available
            if hasattr(activity_data, "file_type"):
                file_type = getattr(activity_data, "file_type", None)
                if file_type and file_type != GDriveFileType.UNKNOWN:
                    app_attribute = IndalekoSemanticAttributeDataModel(
                        Identifier=str(
                            uuid.uuid5(
                                uuid.UUID("4e8d9f2a-5c6b-7d8e-9f0a-1b2c3d4e5f6a"),
                                f"google_drive_app_{file_type}",
                            ),
                        ),
                        Label=f"Google Drive {file_type.name}",
                        Description=f"Activity involves a Google Drive {file_type.name}",
                    )
                    semantic_attributes.append(app_attribute)

        # Convert GDriveActivityData to GoogleDriveStorageActivityData if needed
        if isinstance(activity_data, GDriveActivityData):
            activity_data = activity_data.to_storage_activity()

        # Use the parent class method to build the document
        return super().build_activity_document(activity_data, semantic_attributes)

    def store_activity(
        self,
        activity_data: GoogleDriveStorageActivityData | GDriveActivityData | dict,
    ) -> uuid.UUID:
        """
        Store a Google Drive activity in the database.

        Args:
            activity_data: Google Drive activity data to store

        Returns:
            UUID of the stored activity
        """
        # Convert dict to appropriate model if needed
        if isinstance(activity_data, dict):
            # Check if it has GDriveActivityData-specific fields
            if "activity_type" in activity_data and "file" in activity_data:
                activity_data = GDriveActivityData(**activity_data)
            else:
                # Create GoogleDriveStorageActivityData from dict
                activity_data = GoogleDriveStorageActivityData(**activity_data)

        # Convert GDriveActivityData to GoogleDriveStorageActivityData if needed
        if isinstance(activity_data, GDriveActivityData):
            activity_data = activity_data.to_storage_activity()

        # Build document with Google Drive-specific attributes
        document = self._build_gdrive_activity_document(activity_data)

        # Store in database
        result = self._collection.add_document(document)

        return activity_data.activity_id

    def get_activities_by_drive_id(
        self,
        drive_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """
        Get activities for a specific Google Drive file ID.

        Args:
            drive_id: The Google Drive file ID to get activities for
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of activity documents for the file ID
        """
        # Query the database
        query = """
            FOR doc IN @@collection
            FILTER doc.Record.Data.file_id == @drive_id
            SORT doc.Record.Data.timestamp DESC
            LIMIT @offset, @limit
            RETURN doc
        """

        # Execute query
        cursor = self._db._arangodb.aql.execute(
            query,
            bind_vars={
                "@collection": self._collection_name,
                "drive_id": drive_id,
                "offset": offset,
                "limit": limit,
            },
        )

        # Return results
        return [doc for doc in cursor]

    def get_activities_by_mime_type(
        self,
        mime_type: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """
        Get activities for files with a specific MIME type.

        Args:
            mime_type: The MIME type to get activities for
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of activity documents for the MIME type
        """
        # Query the database
        query = """
            FOR doc IN @@collection
            FILTER doc.Record.Data.mime_type == @mime_type
            SORT doc.Record.Data.timestamp DESC
            LIMIT @offset, @limit
            RETURN doc
        """

        # Execute query
        cursor = self._db._arangodb.aql.execute(
            query,
            bind_vars={
                "@collection": self._collection_name,
                "mime_type": mime_type,
                "offset": offset,
                "limit": limit,
            },
        )

        # Return results
        return [doc for doc in cursor]

    def get_activities_by_folder(
        self,
        folder_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """
        Get activities for files in a specific folder.

        Args:
            folder_id: The folder ID to get activities for
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of activity documents for files in the folder
        """
        # Query the database
        query = """
            FOR doc IN @@collection
            FILTER doc.Record.Data.parent_folder_id == @folder_id
            SORT doc.Record.Data.timestamp DESC
            LIMIT @offset, @limit
            RETURN doc
        """

        # Execute query
        cursor = self._db._arangodb.aql.execute(
            query,
            bind_vars={
                "@collection": self._collection_name,
                "folder_id": folder_id,
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
            FILTER doc.Record.Data.shared == true
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

    def get_google_drive_specific_statistics(self) -> dict[str, Any]:
        """
        Get Google Drive-specific statistics about the activities.

        Returns:
            Dictionary of Google Drive-specific statistics
        """
        # Get basic statistics from parent class
        stats = self.get_activity_statistics()

        # Add Google Drive-specific statistics

        # Query for count by file type (document, spreadsheet, etc.)
        file_type_query = """
            FOR doc IN @@collection
            FILTER doc.Record.Data.file_type != null
            COLLECT file_type = doc.Record.Data.file_type WITH COUNT INTO count
            SORT count DESC
            LIMIT 10
            RETURN { file_type, count }
        """

        # Query for count by sharing status
        sharing_query = """
            LET shared = (
                FOR doc IN @@collection
                FILTER doc.Record.Data.shared == true
                COLLECT WITH COUNT INTO count
                RETURN count
            )[0]

            LET not_shared = (
                FOR doc IN @@collection
                FILTER doc.Record.Data.shared != true
                COLLECT WITH COUNT INTO count
                RETURN count
            )[0]

            RETURN { shared, not_shared }
        """

        # Query for count by app/mime type
        app_query = """
            FOR doc IN @@collection
            FILTER doc.Record.Data.mime_type != null
            COLLECT mime_type = doc.Record.Data.mime_type WITH COUNT INTO count
            SORT count DESC
            LIMIT 10
            RETURN { mime_type, count }
        """

        # Execute Google Drive-specific queries
        try:
            file_type_cursor = self._db._arangodb.aql.execute(
                file_type_query,
                bind_vars={"@collection": self._collection_name},
            )
            sharing_cursor = self._db._arangodb.aql.execute(
                sharing_query,
                bind_vars={"@collection": self._collection_name},
            )
            app_cursor = self._db._arangodb.aql.execute(
                app_query,
                bind_vars={"@collection": self._collection_name},
            )

            # Add to statistics
            stats["top_file_types"] = {item["file_type"]: item["count"] for item in file_type_cursor}
            stats["top_mime_types"] = {item["mime_type"]: item["count"] for item in app_cursor}

            sharing_stats = next(sharing_cursor, {"shared": 0, "not_shared": 0})
            stats["sharing"] = sharing_stats

            # Calculate sharing percentage if there are activities
            total = sharing_stats.get("shared", 0) + sharing_stats.get("not_shared", 0)
            if total > 0:
                stats["sharing_percentage"] = (sharing_stats.get("shared", 0) / total) * 100
            else:
                stats["sharing_percentage"] = 0

        except Exception as e:
            self._logger.error(f"Error generating Google Drive statistics: {e}")

        return stats

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
        return GoogleDriveStorageActivityData.model_json_schema()

    def cache_duration(self) -> timedelta:
        """
        Get the cache duration for this recorder's data.

        Google Drive activities are less frequent than local file operations,
        so we can use a longer cache duration.

        Returns:
            The cache duration
        """
        return timedelta(hours=2)

    def _register_with_service_manager(self) -> None:
        """Register with the activity service manager."""
        # Only register if we have a db connection
        if not hasattr(self, "_db") or self._db is None:
            self._logger.info(
                "Skipping registration with service manager since no database connection is active",
            )
            return

        # Let the parent class method handle registration
        try:
            super()._register_with_service_manager()
        except Exception as e:
            self._logger.error(f"Error registering with service manager: {e}")
            # Continue even if registration fails


# Example usage in __main__
if __name__ == "__main__":
    # Configure logging
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create collector with default settings
    collector = GoogleDriveActivityCollector(debug=True)

    # Create recorder that uses the collector
    recorder = GoogleDriveActivityRecorder(collector=collector, debug=True)

    # Collect and store activities
    try:
        # Collect data
        print("Collecting Google Drive activities...")
        collector.collect_data()

        # Store collected activities
        storage_activities = [activity.to_storage_activity() for activity in collector.activities]
        activity_ids = recorder.store_activities(storage_activities)
        print(f"Stored {len(activity_ids)} activities")

        # Get statistics
        stats = recorder.get_google_drive_specific_statistics()
        print("Activity statistics:")
        for key, value in stats.items():
            # Skip complex values for cleaner output
            if isinstance(value, dict) and len(value) > 5:
                print(f"  {key}: {len(value)} items")
            else:
                print(f"  {key}: {value}")

    except Exception as e:
        print(f"Error: {e}")
