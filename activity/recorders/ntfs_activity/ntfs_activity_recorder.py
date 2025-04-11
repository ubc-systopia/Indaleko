"""
NTFS activity recorder for Indaleko.

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
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union, Tuple, Set, Type

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.recorders.base import RecorderBase
from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.ntfs_activity.data_models.ntfs_activity_data_model import (
    FileActivityType,
    NtfsFileActivityData,
    EmailAttachmentActivityData,
    NtfsActivityData,
    NtfsActivityMetadata
)
from activity.collectors.ntfs_activity.ntfs_activity_collector import NtfsActivityCollector
from activity.collectors.ntfs_activity.semantic_attributes import (
    get_ntfs_activity_semantic_attributes,
    get_semantic_attributes_for_activity,
    NtfsActivityAttributes
)
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from data_models.provenance_data import IndalekoProvenanceData
from data_models.timestamp import IndalekoTimestamp
from db.collection import IndalekoCollection
from Indaleko import Indaleko
# pylint: enable=wrong-import-position


class NtfsActivityRecorder(RecorderBase):
    """
    Recorder for NTFS file system activities.
    
    This recorder stores file system activities from the NTFS USN Journal
    in the Indaleko database for later querying and analysis.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize the NTFS activity recorder.
        
        Args:
            collection_name: Name of the collection to store activities in
            collector: NtfsActivityCollector instance to use
            db_config_path: Path to database configuration file
        """
        # Basic configuration
        self._name = kwargs.get("name", "NTFS Activity Recorder")
        self._recorder_id = kwargs.get(
            "recorder_id", uuid.UUID("8f93a761-42e0-4c1d-b6a9-3c2d9e87f5b3")
        )
        self._version = kwargs.get("version", "1.0.0")
        self._description = kwargs.get(
            "description", "Records file system activities from the NTFS USN Journal"
        )
        
        # Storage configuration
        self._collection_name = kwargs.get("collection_name", "NtfsActivity")
        self._db_config_path = kwargs.get("db_config_path", None)
        
        # Get or create collector
        self._collector = kwargs.get("collector", None)
        if not self._collector:
            try:
                collector_kwargs = kwargs.get("collector_kwargs", {})
                self._collector = NtfsActivityCollector(**collector_kwargs)
            except ImportError as e:
                raise ImportError(
                    "NtfsActivityCollector could not be imported. "
                    "Make sure you're running on Windows."
                ) from e
        
        # Database connection
        self._db = None
        self._collection = None
        
        # Connect to database if auto_connect is True
        if kwargs.get("auto_connect", True):
            self._connect_to_db()
        
        # Enable storage updates if specified
        self._update_storage_objects = kwargs.get("update_storage_objects", False)
        self._storage_recorder = None
        if self._update_storage_objects:
            self._initialize_storage_recorder()
        
        # Setup logging
        self._logger = logging.getLogger("NtfsActivityRecorder")
    
    def _connect_to_db(self):
        """Connect to the Indaleko database."""
        # Create Indaleko instance and connect to database
        self._db = Indaleko()
        
        # If db_config_path is provided, use it
        if self._db_config_path:
            self._db.db_config_path = self._db_config_path
            
        # Connect to database
        self._db.connect()
        
        # Get or create collection
        if self._collection_name in self._db.get_collections():
            self._collection = self._db.get_collection(self._collection_name)
        else:
            self._collection = self._db.create_collection(
                self._collection_name,
                description="NTFS USN Journal activity data"
            )
    
    def _initialize_storage_recorder(self):
        """Initialize the storage recorder for dynamic updates."""
        try:
            # Import here to avoid circular imports
            from storage.recorders.local.windows.recorder import WindowsLocalRecorder
            
            # Create the storage recorder
            self._storage_recorder = WindowsLocalRecorder(
                collection_name="WindowsObjects",
                db_config_path=self._db_config_path
            )
        except ImportError as e:
            self._logger.warning(f"Could not initialize storage recorder: {e}")
            self._update_storage_objects = False
    
    def build_activity_document(
        self,
        activity_data: NtfsFileActivityData,
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
        timestamp = IndalekoTimestamp()
        
        # Create source identifier
        source_id = IndalekoSourceIdentifierDataModel(
            SourceID=str(self._recorder_id),
            SourceIdName=self._name,
            SourceDescription=self._description,
            SourceVersion=self._version
        )
        
        # Create the record
        record = IndalekoRecordDataModel(
            RecordType="NTFS_Activity",
            Data=activity_data.model_dump(),
            SourceId=source_id,
            Timestamp=timestamp,
            SemanticAttributes=semantic_attributes,
            RecordId=activity_data.activity_id
        )
        
        return record.model_dump()
    
    def store_activity(
        self, 
        activity_data: Union[NtfsFileActivityData, Dict],
        update_storage: bool = None
    ) -> uuid.UUID:
        """
        Store an activity in the database.
        
        Args:
            activity_data: Activity data to store
            update_storage: Whether to update storage objects
            
        Returns:
            UUID of the stored activity
        """
        # Convert dict to NtfsFileActivityData if needed
        if isinstance(activity_data, dict):
            if "email_source" in activity_data:
                activity_data = EmailAttachmentActivityData(**activity_data)
            else:
                activity_data = NtfsFileActivityData(**activity_data)
        
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
        
        # Update storage object if requested
        if (update_storage is True or 
            (update_storage is None and self._update_storage_objects)):
            self._update_storage_object(activity_data)
        
        return activity_data.activity_id
    
    def store_activities(
        self, 
        activities: List[Union[NtfsFileActivityData, Dict]],
        update_storage: bool = None
    ) -> List[uuid.UUID]:
        """
        Store multiple activities in the database.
        
        Args:
            activities: List of activities to store
            update_storage: Whether to update storage objects
            
        Returns:
            List of UUIDs of the stored activities
        """
        activity_ids = []
        
        # Store each activity
        for activity_data in activities:
            activity_id = self.store_activity(
                activity_data, 
                update_storage=update_storage
            )
            activity_ids.append(activity_id)
        
        return activity_ids
    
    def _update_storage_object(self, activity_data: NtfsFileActivityData):
        """
        Update a storage object based on the activity.
        
        Args:
            activity_data: The activity data to use for the update
        """
        if not self._storage_recorder:
            return
        
        try:
            # Only update for create, modify, delete and rename activities
            if activity_data.activity_type not in [
                FileActivityType.CREATE,
                FileActivityType.MODIFY,
                FileActivityType.DELETE,
                FileActivityType.RENAME
            ]:
                return
            
            # Get the file path
            file_path = activity_data.file_path
            if not file_path:
                return
            
            # Delegate to the storage recorder to handle the update
            self._storage_recorder.update_object_from_activity(
                file_path,
                activity_data.activity_type,
                activity_data.timestamp,
                {
                    "activity_id": str(activity_data.activity_id),
                    "process_name": activity_data.process_name,
                    "process_id": activity_data.process_id
                }
            )
        except Exception as e:
            self._logger.error(f"Error updating storage object: {e}")
    
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
    
    def get_activities_by_file_path(
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
    
    def get_activities_by_process(
        self,
        process_name: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get activities initiated by a specific process.
        
        Args:
            process_name: Process name to look for
            limit: Maximum number of results to return
            offset: Number of results to skip
            
        Returns:
            List of activity documents by the process
        """
        # Query the database
        query = """
            FOR doc IN @@collection
            FILTER doc.Record.Data.process_name != null AND LIKE(doc.Record.Data.process_name, @process_name, true)
            SORT doc.Record.Data.timestamp DESC
            LIMIT @offset, @limit
            RETURN doc
        """
        
        # Execute query
        cursor = self._db.db.aql.execute(
            query,
            bind_vars={
                "@collection": self._collection_name,
                "process_name": f"%{process_name}%",
                "offset": offset,
                "limit": limit
            }
        )
        
        # Return results
        return [doc for doc in cursor]
    
    def get_email_attachment_activities(
        self,
        min_confidence: float = 0.5,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get activities identified as email attachments.
        
        Args:
            min_confidence: Minimum confidence score
            limit: Maximum number of results to return
            offset: Number of results to skip
            
        Returns:
            List of email attachment activity documents
        """
        # Query the database
        query = """
            FOR doc IN @@collection
            FILTER doc.Record.Data.confidence_score >= @min_confidence
            SORT doc.Record.Data.timestamp DESC
            LIMIT @offset, @limit
            RETURN doc
        """
        
        # Execute query
        cursor = self._db.db.aql.execute(
            query,
            bind_vars={
                "@collection": self._collection_name,
                "min_confidence": min_confidence,
                "offset": offset,
                "limit": limit
            }
        )
        
        # Return results
        return [doc for doc in cursor]
    
    def get_activities_by_type(
        self,
        activity_type: Union[FileActivityType, str],
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
        if isinstance(activity_type, FileActivityType):
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
        
        # Query for count by directory vs file
        dir_query = """
            FOR doc IN @@collection
            COLLECT is_dir = doc.Record.Data.is_directory WITH COUNT INTO count
            RETURN { is_dir, count }
        """
        
        # Query for count by process name
        process_query = """
            FOR doc IN @@collection
            FILTER doc.Record.Data.process_name != null
            COLLECT process = doc.Record.Data.process_name WITH COUNT INTO count
            SORT count DESC
            LIMIT 10
            RETURN { process, count }
        """
        
        # Query for count by volume
        volume_query = """
            FOR doc IN @@collection
            COLLECT volume = doc.Record.Data.volume_name WITH COUNT INTO count
            RETURN { volume, count }
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
        dir_cursor = self._db.db.aql.execute(
            dir_query,
            bind_vars={"@collection": self._collection_name}
        )
        process_cursor = self._db.db.aql.execute(
            process_query,
            bind_vars={"@collection": self._collection_name}
        )
        volume_cursor = self._db.db.aql.execute(
            volume_query,
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
            "by_dir_file": {
                "directory" if item["is_dir"] else "file": item["count"] 
                for item in dir_cursor
            },
            "by_process": [
                {"process": item["process"], "count": item["count"]} 
                for item in process_cursor
            ],
            "by_volume": {item["volume"]: item["count"] for item in volume_cursor},
            "by_date": [
                {"date": item["date"], "count": item["count"]} 
                for item in date_cursor
            ]
        }
        
        return statistics
    
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
        return {
            "NtfsActivityCollector": NtfsActivityCollector,
            "NtfsFileActivityData": NtfsFileActivityData,
            "EmailAttachmentActivityData": EmailAttachmentActivityData,
            "NtfsActivityData": NtfsActivityData,
            "NtfsActivityMetadata": NtfsActivityMetadata,
            "FileActivityType": FileActivityType
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
        return NtfsActivityData.model_json_schema()
    
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
            return data
        
        # If data is a NtfsActivityData, convert to dict
        if isinstance(data, NtfsActivityData):
            return data.model_dump()
        
        # If data is a list of NtfsFileActivityData, convert to NtfsActivityData
        if isinstance(data, list) and all(isinstance(item, NtfsFileActivityData) for item in data):
            metadata = self._collector._metadata if self._collector else NtfsActivityMetadata(
                source_machine=socket.gethostname()
            )
            activity_data = NtfsActivityData(
                metadata=metadata,
                activities=data,
                Timestamp=IndalekoTimestamp()
            )
            return activity_data.model_dump()
        
        # If data is a single NtfsFileActivityData, wrap it
        if isinstance(data, NtfsFileActivityData):
            return {
                "activity": data.model_dump(),
                "timestamp": IndalekoTimestamp().model_dump()
            }
        
        # Unknown data type, just convert to JSON
        return {"data": json.dumps(data)}
    
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
        # since the USN Journal is append-only
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


def main():
    """Main function for testing the recorder."""
    logging.basicConfig(level=logging.INFO)
    
    # Check if running on Windows
    if platform.system() != "Windows":
        print("This recorder only works on Windows")
        return
    
    try:
        # Create a collector with simulated data for testing
        collector = NtfsActivityCollector(auto_start=False)
        
        # Create some test activities
        test_activities = []
        for i in range(10):
            activity = NtfsFileActivityData(
                usn=1000 + i,
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=i),
                file_reference_number=f"1234567890{i}",
                parent_file_reference_number="9876543210",
                activity_type=FileActivityType.CREATE if i % 3 == 0 else 
                             FileActivityType.MODIFY if i % 3 == 1 else 
                             FileActivityType.DELETE,
                reason_flags=win32file.USN_REASON_FILE_CREATE if i % 3 == 0 else 
                             win32file.USN_REASON_DATA_OVERWRITE if i % 3 == 1 else 
                             win32file.USN_REASON_FILE_DELETE,
                file_name=f"test_file_{i}.txt",
                file_path=f"C:\\test\\test_file_{i}.txt",
                volume_name="C:",
                process_id=1234 + i,
                process_name="test_process.exe",
                is_directory=False
            )
            test_activities.append(activity)
        
        # Also add an email attachment activity
        email_attachment = EmailAttachmentActivityData(
            usn=2000,
            timestamp=datetime.now(timezone.utc),
            file_reference_number="9876543219",
            parent_file_reference_number="9876543210",
            activity_type=FileActivityType.CREATE,
            reason_flags=win32file.USN_REASON_FILE_CREATE,
            file_name="test_attachment.docx",
            file_path="C:\\Users\\Test\\Downloads\\test_attachment.docx",
            volume_name="C:",
            process_id=5678,
            process_name="outlook.exe",
            is_directory=False,
            email_source="test@example.com",
            email_subject="Test Email with Attachment",
            email_timestamp=datetime.now(timezone.utc) - timedelta(minutes=1),
            attachment_original_name="original_name.docx",
            confidence_score=0.95,
            matching_signals=["outlook_process", "filename_pattern"]
        )
        test_activities.append(email_attachment)
        
        # Set the activities on the collector
        collector._activities = test_activities
        
        # Create a recorder
        recorder = NtfsActivityRecorder(
            collector=collector,
            auto_connect=True  # Connect to the database
        )
        
        print(f"Connected to database, using collection: {recorder._collection_name}")
        
        # Store the activities
        print(f"Storing {len(test_activities)} activities...")
        activity_ids = recorder.store_activities(test_activities)
        print(f"Stored {len(activity_ids)} activities")
        
        # Query the activities
        print("\nQuerying activities by type...")
        create_activities = recorder.get_activities_by_type(FileActivityType.CREATE)
        print(f"Found {len(create_activities)} CREATE activities")
        
        # Query email attachment activities
        print("\nQuerying email attachment activities...")
        email_activities = recorder.get_email_attachment_activities()
        print(f"Found {len(email_activities)} email attachment activities")
        
        # Get statistics
        print("\nGetting activity statistics...")
        stats = recorder.get_activity_statistics()
        print(f"Total activities: {stats['total_count']}")
        print("Activities by type:")
        for activity_type, count in stats.get("by_type", {}).items():
            print(f"  {activity_type}: {count}")
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    import platform  # Required for checking system
    
    # Import win32file for USN constants
    try:
        import win32file
    except ImportError:
        # This will only be used for type hints in non-Windows environments
        class win32file:
            USN_REASON_FILE_CREATE = 0x00000100
            USN_REASON_FILE_DELETE = 0x00000200
            USN_REASON_DATA_OVERWRITE = 0x00000001
    
    main()