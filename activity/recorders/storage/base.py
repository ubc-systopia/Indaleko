"""
Base class for storage activity recorders in Indaleko.

This module provides a standardized base class for implementing storage activity
recorders across different storage providers (NTFS, Dropbox, OneDrive, etc.).

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
import uuid
import json
import socket
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union, Type, Set, Tuple, cast

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.recorders.base import RecorderBase
from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.storage.base import StorageActivityCollector
from activity.collectors.storage.data_models.storage_activity_data_model \
    import (
        BaseStorageActivityData,
        StorageActivityType,
        StorageProviderType,
        StorageActivityMetadata,
        StorageActivityData
    )
from activity.collectors.storage.semantic_attributes import (
    get_storage_activity_semantic_attributes,
    get_semantic_attributes_for_activity,
    StorageActivityAttributes
)
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from data_models.timestamp import IndalekoTimestampDataModel
from Indaleko import Indaleko
from activity.recorders.registration_service \
    import IndalekoActivityDataRegistrationService
# pylint: enable=wrong-import-position


class StorageActivityRecorder(RecorderBase):
    """
    Base class for all storage activity recorders.

    This class provides common functionality for recording storage activities
    across different storage providers. Specific providers should extend this
    class and implement the provider-specific logic.
    """

    def __init__(self, **kwargs):
        """
        Initialize the storage activity recorder.

        Args:
            name: Name of the recorder
            recorder_id: UUID of the recorder
            collection_name: Name of the collection to store activities in
            collector: StorageActivityCollector instance to use
            provider_type: Type of storage provider
            db_config_path: Path to database configuration file
            version: Version of the recorder
            description: Description of the recorder
            register_service: Whether to register with the service manager
        """
        # Basic configuration
        self._name = kwargs.get("name", "Storage Activity Recorder")
        self._recorder_id = kwargs.get(
            "recorder_id", uuid.UUID("7f52e6a9-1d23-45cb-8f9a-d2a7b6c89e34")
        )
        self._version = kwargs.get("version", "1.0.0")
        self._description = kwargs.get(
            "description", "Records storage activities"
        )
        self._provider_type = kwargs.get(
            "provider_type",
            StorageProviderType.OTHER)

        # Storage configuration
        self._collection_name = kwargs.get(
            "collection_name",
            "StorageActivity"
        )
        self._db_config_path = kwargs.get(
            "db_config_path",
            None
        )

        # Get or create collector
        self._collector = kwargs.get("collector", None)
        self._debug = kwargs.get("debug", False)

        # Database connection
        self._db = None
        self._collection = None

        # Connect to database if auto_connect is True
        if kwargs.get("auto_connect", True):
            self._connect_to_db()

        # Register with activity service manager if specified
        self._register_enabled = kwargs.get("register_service", True)
        if self._register_enabled:
            self._register_with_service_manager()

        # Setup logging
        self._logger = logging.getLogger(f"{self._name}")

    def _connect_to_db(self):
        """Connect to the Indaleko database."""
        # Create IndalekoDBConfig instance to connect to database
        from db.db_config import IndalekoDBConfig
        db_config = IndalekoDBConfig(config_file=self._db_config_path if self._db_config_path else None)
        
        # Start the database connection
        db_config.start()
        
        # Store reference to the database
        self._db = db_config
        
        # Get or create collection
        # Try to get the collection from the central registry
        from db.i_collections import IndalekoCollections

        try:
            # Check if collection exists in registry
            collection_obj = IndalekoCollections.get_collection(self._collection_name)
            self._collection = collection_obj.collection
            self._logger.info(f"Using existing collection {self._collection_name}")
        except ValueError:
            # If not in registry, use dynamic registration service
            self._logger.info(f"Collection {self._collection_name} not found in registry")

            # Get or create the registration service for activity data
            from activity.registration_service import ActivityRegistrationService
            registration_service = ActivityRegistrationService()

            # Register this collection with a generated UUID for consistency
            import hashlib
            # Generate deterministic UUID from collection name
            name_hash = hashlib.md5(self._collection_name.encode()).hexdigest()
            provider_id = str(uuid.UUID(name_hash))

            # Create provider collection
            provider_collection = registration_service.lookup_provider_collection(provider_id)
            if provider_collection is None:
                self._logger.info(f"Creating collection for {self._collection_name} via registration service")
                provider_collection = registration_service.create_provider_collection(
                    identifier=provider_id,
                    schema=None,  # No schema validation for now
                    edge=False
                )

            self._collection = provider_collection.collection

    def build_activity_document(
        self,
        activity_data: BaseStorageActivityData,
        semantic_attributes: Optional[List[IndalekoSemanticAttributeDataModel]] = None
    ) -> Dict:
        """
        Build a document for storing an activity in the database.

        Args:
            activity_data: The activity data to store
            semantic_attributes: Optional list of semantic attributes

        Returns:
            Document for the database
        """
        # Ensure we have semantic attributes
        if semantic_attributes is None:
            semantic_attributes = get_semantic_attributes_for_activity(
                activity_data.model_dump()
            )

        # Create a timestamp if not provided
        timestamp = IndalekoTimestampDataModel()

        # Create source identifier
        source_id = IndalekoSourceIdentifierDataModel(
            SourceID=str(self._recorder_id),
            SourceIdName=self._name,
            SourceDescription=self._description,
            SourceVersion=self._version
        )

        # Create the record
        record = IndalekoRecordDataModel(
            RecordType="StorageActivity",
            Data=activity_data.model_dump(),
            SourceId=source_id,
            Timestamp=timestamp,
            SemanticAttributes=semantic_attributes,
            RecordId=activity_data.activity_id
        )

        return record.model_dump()

    def store_activity(
        self,
        activity_data: Union[BaseStorageActivityData, Dict]
    ) -> uuid.UUID:
        """
        Store an activity in the database.

        Args:
            activity_data: Activity data to store

        Returns:
            UUID of the stored activity
        """
        # Convert dict to BaseStorageActivityData if needed
        if isinstance(activity_data, dict):
            # Determine the correct model class based on provider_type
            provider_type = activity_data.get("provider_type")
            model_class = self._get_model_class_for_provider_type(provider_type)
            activity_data = model_class(**activity_data)

        # Get semantic attributes
        semantic_attributes = get_semantic_attributes_for_activity(
            activity_data.model_dump()
        )

        # Build the document
        document = self.build_activity_document(
            activity_data,
            semantic_attributes
        )

        # Store in database
        result = self._collection.add_document(document)

        return activity_data.activity_id

    def store_activities(
        self,
        activities: List[Union[BaseStorageActivityData, Dict]]
    ) -> List[uuid.UUID]:
        """
        Store multiple activities in the database.

        Args:
            activities: List of activities to store

        Returns:
            List of UUIDs of the stored activities
        """
        activity_ids = []

        # Store each activity
        for activity_data in activities:
            activity_id = self.store_activity(activity_data)
            activity_ids.append(activity_id)

        return activity_ids

    def query_activities(
        self,
        query_filter: Optional[Dict] = None,
        sort_by: Optional[str] = "timestamp",
        sort_direction: str = "desc",
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Query activities from the database.

        Args:
            query_filter: Dictionary of filters to apply
            sort_by: Field to sort by
            sort_direction: Sort direction ('asc' or 'desc')
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of activity documents
        """
        # Convert query_filter to AQL filter string
        filter_str = ""
        bind_vars = {}

        if query_filter:
            filter_conditions = []
            bind_idx = 1

            for key, value in query_filter.items():
                bind_name = f"val{bind_idx}"
                filter_conditions.append(f"doc.Record.Data.{key} == @{bind_name}")
                bind_vars[bind_name] = value
                bind_idx += 1

            if filter_conditions:
                filter_str = "FILTER " + " AND ".join(filter_conditions)

        # Create AQL query
        query = f"""
            FOR doc IN @@collection
            {filter_str}
            SORT doc.Record.Data.{sort_by} {sort_direction}
            LIMIT {offset}, {limit}
            RETURN doc
        """

        # Add collection to bind variables
        bind_vars["@collection"] = self._collection_name

        # Execute query
        cursor = self._db.db.aql.execute(query, bind_vars=bind_vars)

        # Return results
        return [doc for doc in cursor]

    def get_activity_by_id(self, activity_id: Union[uuid.UUID, str]) -> Optional[Dict]:
        """
        Get an activity by its ID.

        Args:
            activity_id: The activity ID to look for

        Returns:
            The activity document if found, None otherwise
        """
        # Convert to string if needed
        if isinstance(activity_id, uuid.UUID):
            activity_id = str(activity_id)

        # Query the database
        query = """
            FOR doc IN @@collection
            FILTER doc.Record.Data.activity_id == @activity_id
            RETURN doc
        """

        # Execute query
        cursor = self._db.db.aql.execute(
            query,
            bind_vars={
                "@collection": self._collection_name,
                "activity_id": activity_id
            }
        )

        # Return the first result, or None if no results
        try:
            return next(cursor)
        except StopIteration:
            return None

    def get_activities_by_type(
        self,
        activity_type: Union[StorageActivityType, str],
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get activities of a specific type.

        Args:
            activity_type: Type of activities to get
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of activity documents of the specified type
        """
        # Convert to string if needed
        if isinstance(activity_type, StorageActivityType):
            activity_type = activity_type.value

        # Query the database
        query = """
            FOR doc IN @@collection
            FILTER doc.Record.Data.activity_type == @activity_type
            SORT doc.Record.Data.timestamp DESC
            LIMIT @offset, @limit
            RETURN doc
        """

        # Execute query
        cursor = self._db.db.aql.execute(
            query,
            bind_vars={
                "@collection": self._collection_name,
                "activity_type": activity_type,
                "offset": offset,
                "limit": limit
            }
        )

        # Return results
        return [doc for doc in cursor]

    def get_activities_by_time_range(
        self,
        start_time: Union[datetime, str],
        end_time: Union[datetime, str],
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get activities within a time range.

        Args:
            start_time: Start of the time range
            end_time: End of the time range
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of activity documents within the time range
        """
        # Convert datetime objects to strings if needed
        if isinstance(start_time, datetime):
            start_time = start_time.isoformat()
        if isinstance(end_time, datetime):
            end_time = end_time.isoformat()

        # Query the database
        query = """
            FOR doc IN @@collection
            FILTER doc.Record.Data.timestamp >= @start_time AND doc.Record.Data.timestamp <= @end_time
            SORT doc.Record.Data.timestamp DESC
            LIMIT @offset, @limit
            RETURN doc
        """

        # Execute query
        cursor = self._db.db.aql.execute(
            query,
            bind_vars={
                "@collection": self._collection_name,
                "start_time": start_time,
                "end_time": end_time,
                "offset": offset,
                "limit": limit
            }
        )

        # Return results
        return [doc for doc in cursor]

    def get_activities_by_path(
        self,
        file_path: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get activities for a specific file path.

        Args:
            file_path: The file path to look for
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of activity documents for the file
        """
        # Query the database
        query = """
            FOR doc IN @@collection
            FILTER doc.Record.Data.file_path == @file_path OR
                  (doc.Record.Data.file_path != null AND LIKE(doc.Record.Data.file_path, @file_name, true))
            SORT doc.Record.Data.timestamp DESC
            LIMIT @offset, @limit
            RETURN doc
        """

        # Execute query
        cursor = self._db.db.aql.execute(
            query,
            bind_vars={
                "@collection": self._collection_name,
                "file_path": file_path,
                "file_name": f"%{os.path.basename(file_path)}",
                "offset": offset,
                "limit": limit
            }
        )

        # Return results
        return [doc for doc in cursor]

    def get_activity_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the activities in the database.

        Returns:
            Dictionary of statistics
        """
        # Query for count by activity type
        type_query = """
            FOR doc IN @@collection
            COLLECT type = doc.Record.Data.activity_type WITH COUNT INTO count
            RETURN { type, count }
        """

        # Query for count by provider type
        provider_query = """
            FOR doc IN @@collection
            COLLECT provider = doc.Record.Data.provider_type WITH COUNT INTO count
            RETURN { provider, count }
        """

        # Query for count by item type
        item_query = """
            FOR doc IN @@collection
            COLLECT item_type = doc.Record.Data.item_type WITH COUNT INTO count
            RETURN { item_type, count }
        """

        # Query for count by date
        date_query = """
            FOR doc IN @@collection
            LET date = SUBSTRING(doc.Record.Data.timestamp, 0, 10)
            COLLECT d = date WITH COUNT INTO count
            SORT d
            RETURN { date: d, count }
        """

        # Query for total count
        count_query = """
            RETURN LENGTH(@@collection)
        """

        # Execute queries
        type_cursor = self._db.db.aql.execute(
            type_query,
            bind_vars={"@collection": self._collection_name}
        )
        provider_cursor = self._db.db.aql.execute(
            provider_query,
            bind_vars={"@collection": self._collection_name}
        )
        item_cursor = self._db.db.aql.execute(
            item_query,
            bind_vars={"@collection": self._collection_name}
        )
        date_cursor = self._db.db.aql.execute(
            date_query,
            bind_vars={"@collection": self._collection_name}
        )
        count_cursor = self._db.db.aql.execute(
            count_query,
            bind_vars={"@collection": self._collection_name}
        )

        # Build statistics dictionary
        statistics = {
            "total_count": next(count_cursor),
            "by_type": {item["type"]: item["count"] for item in type_cursor},
            "by_provider": {item["provider"]: item["count"] for item in provider_cursor},
            "by_item_type": {item["item_type"]: item["count"] for item in item_cursor},
            "by_date": [
                {"date": item["date"], "count": item["count"]}
                for item in date_cursor
            ]
        }

        return statistics

    def _get_model_class_for_provider_type(self, provider_type: Union[StorageProviderType, str]) -> Type[BaseStorageActivityData]:
        """
        Get the appropriate model class for a provider type.

        Args:
            provider_type: Provider type to get model class for

        Returns:
            Model class for the provider type
        """
        from activity.collectors.storage.data_models.storage_activity_data_model import (
            NtfsStorageActivityData,
            DropboxStorageActivityData,
            OneDriveStorageActivityData,
            GoogleDriveStorageActivityData
        )

        # Convert string to enum if needed
        if isinstance(provider_type, str):
            try:
                provider_type = StorageProviderType(provider_type)
            except ValueError:
                provider_type = StorageProviderType.OTHER

        # Map provider types to model classes
        provider_type_to_model = {
            StorageProviderType.LOCAL_NTFS: NtfsStorageActivityData,
            StorageProviderType.DROPBOX: DropboxStorageActivityData,
            StorageProviderType.ONEDRIVE: OneDriveStorageActivityData,
            StorageProviderType.GOOGLE_DRIVE: GoogleDriveStorageActivityData,
        }

        # Return appropriate model class or fallback to base class
        return provider_type_to_model.get(provider_type, BaseStorageActivityData)

    def _register_with_service_manager(self) -> None:
        """Register with the activity service manager."""
        try:
            # Get semantic attributes for storage activity
            attributes = get_storage_activity_semantic_attributes()
            semantic_attribute_ids = [str(attr.Identifier) for attr in attributes]

            # Create source identifier for the record
            source_identifier = IndalekoSourceIdentifierDataModel(
                SourceID=str(self._recorder_id),
                SourceIdName=self._name,
                SourceDescription=self._description,
                SourceVersion=self._version
            )

            # Create record data model
            record = IndalekoRecordDataModel(
                SourceId=source_identifier,
                Timestamp=datetime.now(timezone.utc),
                Data={}
            )

            # Prepare registration data
            registration_kwargs = {
                "Identifier": str(self._recorder_id),
                "Name": self._name,
                "Description": self._description,
                "Version": self._version,
                "Record": record,
                "DataProvider": f"{self._provider_type} Storage Activity",
                "DataProviderType": "Activity",
                "DataProviderSubType": "Storage",
                "DataProviderURL": "",
                "DataProviderCollectionName": self._collection_name,
                "DataFormat": "JSON",
                "DataFormatVersion": "1.0",
                "DataAccess": "Read",
                "DataAccessURL": "",
                "CreateCollection": True,
                "SourceIdentifiers": [
                    str(StorageActivityAttributes.STORAGE_ACTIVITY.value),
                ],
                "SchemaIdentifiers": semantic_attribute_ids,
                "Tags": ["storage", "activity", str(self._provider_type)]
            }

            # Register with service manager
            try:
                service = IndalekoActivityDataRegistrationService()
                service.register_provider(**registration_kwargs)

                self._logger.info(f"Registered storage activity recorder with service manager: {self._recorder_id}")
            except Exception as e:
                self._logger.error(f"Error registering with service manager: {e}")

        except Exception as e:
            self._logger.error(f"Error creating registration data: {e}")

    # Implement RecorderBase abstract methods
    def get_recorder_characteristics(self) -> List[ActivityDataCharacteristics]:
        """Get the characteristics of this recorder."""
        return [
            ActivityDataCharacteristics.ACTIVITY_DATA_SYSTEM_ACTIVITY,
            ActivityDataCharacteristics.ACTIVITY_DATA_FILE_ACTIVITY
        ]

    def get_recorder_name(self) -> str:
        """Get the name of the recorder."""
        return self._name

    def get_collector_class_model(self) -> Dict[str, Type]:
        """Get the class models for the collector(s) used by this recorder."""
        from activity.collectors.storage.data_models.storage_activity_data_model import (
            BaseStorageActivityData,
            NtfsStorageActivityData,
            CloudStorageActivityData,
            DropboxStorageActivityData,
            OneDriveStorageActivityData,
            GoogleDriveStorageActivityData,
            StorageActivityType,
            StorageProviderType,
            StorageItemType
        )

        return {
            "StorageActivityCollector": StorageActivityCollector,
            "BaseStorageActivityData": BaseStorageActivityData,
            "NtfsStorageActivityData": NtfsStorageActivityData,
            "CloudStorageActivityData": CloudStorageActivityData,
            "DropboxStorageActivityData": DropboxStorageActivityData,
            "OneDriveStorageActivityData": OneDriveStorageActivityData,
            "GoogleDriveStorageActivityData": GoogleDriveStorageActivityData,
            "StorageActivityType": StorageActivityType,
            "StorageProviderType": StorageProviderType,
            "StorageItemType": StorageItemType
        }

    def get_recorder_id(self) -> uuid.UUID:
        """Get the ID of the recorder."""
        return self._recorder_id

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
        Get the cache duration for this recorder's data.

        Returns:
            The cache duration
        """
        return timedelta(hours=1)

    def get_description(self) -> str:
        """
        Get a description of this recorder.

        Returns:
            The recorder description
        """
        return self._description

    def get_json_schema(self) -> dict:
        """
        Get the JSON schema for this recorder's data.

        Returns:
            The JSON schema
        """
        return StorageActivityData.model_json_schema()

    def process_data(self, data: Any) -> Dict[str, Any]:
        """
        Process the collected data.

        Args:
            data: Raw data to process

        Returns:
            Processed data
        """
        # If data is already a dictionary, just return it
        if isinstance(data, dict):
            # Ensure any datetime fields are timezone-aware
            return self._ensure_timezone_for_dict(data)

        # If data is a StorageActivityData, convert to dict
        if isinstance(data, StorageActivityData):
            return data.model_dump()

        # If data is a list of BaseStorageActivityData, convert to StorageActivityData
        if isinstance(data, list) and all(isinstance(item, BaseStorageActivityData) for item in data):
            metadata = getattr(self._collector, "_metadata", None) if self._collector else StorageActivityMetadata(
                provider_type=self._provider_type,
                provider_name=self._name,
                source_machine=socket.gethostname()
            )
            activity_data = StorageActivityData(
                metadata=metadata,
                activities=data,
                Timestamp=IndalekoTimestampDataModel()
            )
            return activity_data.model_dump()

        # If data is a single BaseStorageActivityData, wrap it
        if isinstance(data, BaseStorageActivityData):
            return {
                "activity": data.model_dump(),
                "timestamp": IndalekoTimestampDataModel().model_dump()
            }

        # Unknown data type, just convert to JSON
        return {"data": json.dumps(data)}
        
    def _ensure_timezone_for_dict(self, data: Dict) -> Dict:
        """
        Recursively ensure all datetime fields in a dictionary have timezone info.
        
        Args:
            data: Dictionary to process
            
        Returns:
            Dictionary with timezone-aware datetime fields
        """
        if not isinstance(data, dict):
            return data
            
        result = {}
        for key, value in data.items():
            if isinstance(value, datetime) and not value.tzinfo:
                # Add timezone to datetime objects
                result[key] = value.replace(tzinfo=timezone.utc)
            elif isinstance(value, dict):
                # Recursively process nested dictionaries
                result[key] = self._ensure_timezone_for_dict(value)
            elif isinstance(value, list):
                # Recursively process lists
                result[key] = [
                    self._ensure_timezone_for_dict(item) if isinstance(item, dict) 
                    else (item.replace(tzinfo=timezone.utc) if isinstance(item, datetime) and not item.tzinfo else item)
                    for item in value
                ]
            else:
                result[key] = value
        
        return result

    def store_data(self, data: Dict[str, Any]) -> None:
        """
        Store the processed data.

        Args:
            data: Data to store
        """
        # If data has an "activities" list, store each activity
        if "activities" in data:
            activities = data["activities"]
            if isinstance(activities, list):
                self.store_activities(activities)
                return

        # If data has an "activity" dict, store it
        if "activity" in data:
            activity = data["activity"]
            if isinstance(activity, dict):
                self.store_activity(activity)
                return

        # Otherwise, try to store the data directly
        try:
            self.store_activity(data)
        except Exception as e:
            self._logger.error(f"Failed to store data: {e}")

    def update_data(self) -> None:
        """Update the data in the database."""
        # This recorder doesn't implement data updates
        pass

    def get_latest_db_update(self) -> Dict[str, Any]:
        """
        Get the latest data update from the database.

        Returns:
            The latest update information
        """
        # Query for the most recent activity
        query = """
            FOR doc IN @@collection
            SORT doc.Record.Data.timestamp DESC
            LIMIT 1
            RETURN doc
        """

        # Execute query
        cursor = self._db.db.aql.execute(
            query,
            bind_vars={"@collection": self._collection_name}
        )

        # Return the first result, or empty dict if no results
        try:
            return next(cursor)
        except StopIteration:
            return {}
