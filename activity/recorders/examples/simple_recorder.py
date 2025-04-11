"""
Simple example recorder implementation using the TemplateRecorder class.

This example shows how to create a minimal recorder using the template class.

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
import logging
import datetime
from typing import Dict, List, Any, Type

# Set up path for Indaleko imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.recorders.template import TemplateRecorder
from activity.characteristics import ActivityDataCharacteristics
from data_models.i_uuid import IndalekoUUIDDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
# pylint: enable=wrong-import-position


class SimpleActivity:
    """Simple activity data class for example purposes."""
    
    def __init__(self, name, activity_type, timestamp=None, details=None):
        """Initialize a simple activity."""
        self.name = name
        self.activity_type = activity_type
        self.timestamp = timestamp or datetime.datetime.now(datetime.timezone.utc)
        self.details = details or {}
        self.activity_id = uuid.uuid4()
    
    def model_dump(self):
        """Convert to dictionary."""
        return {
            "activity_id": str(self.activity_id),
            "name": self.name,
            "activity_type": self.activity_type,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }


class SimpleCollector:
    """Simple collector class for example purposes."""
    
    def __init__(self):
        """Initialize the collector."""
        self.version = "1.0.0"
        self.name = "Simple Activity Collector"
    
    def collect_data(self):
        """Collect some sample data."""
        activities = [
            SimpleActivity(
                name="Sample Activity 1",
                activity_type="login",
                details={"source": "web", "device": "laptop"}
            ),
            SimpleActivity(
                name="Sample Activity 2",
                activity_type="file_access",
                details={"file": "document.txt", "action": "read"}
            ),
            SimpleActivity(
                name="Sample Activity 3",
                activity_type="logout",
                details={"source": "web", "device": "laptop"}
            )
        ]
        return activities


class SimpleActivityRecorder(TemplateRecorder):
    """
    Simple example activity recorder using the template.
    
    This recorder shows how to create a minimal implementation
    using the TemplateRecorder base class.
    """
    
    # Define some UUIDs for our semantic attributes
    ACTIVITY_NAME_UUID = uuid.UUID("71a3b5c7-d8e9-4f0a-b1c2-d3e4f5a6b7c8")
    ACTIVITY_TYPE_UUID = uuid.UUID("82b4c6d8-e9f0-a1b2-c3d4-e5f6a7b8c9d0")
    
    def __init__(self, **kwargs):
        """Initialize the simple activity recorder."""
        # Set defaults specific to this recorder
        kwargs.setdefault("name", "Simple Activity Recorder")
        kwargs.setdefault("recorder_id", uuid.UUID("91c5d7e9-f0a1-b2c3-d4e5-f6a7b8c9d0e1"))
        kwargs.setdefault("version", "1.0.0")
        kwargs.setdefault("activity_type", "user activity")
        kwargs.setdefault("collection_name", "SimpleActivities")
        
        # Set characteristics
        kwargs.setdefault("characteristics", [
            ActivityDataCharacteristics.ACTIVITY_DATA_ACTIVITY,
            ActivityDataCharacteristics.ACTIVITY_DATA_USER_ACTIVITY
        ])
        
        # Set tags
        kwargs.setdefault("tags", ["activity", "user", "simple", "example"])
        
        # Initialize the template recorder
        super().__init__(**kwargs)
        
        # Set up the collector
        self.collector = SimpleCollector()
    
    def collect_and_process_data(self) -> List[Any]:
        """
        Collect and process data from the source.
        
        Returns:
            List of processed SimpleActivity objects
        """
        # Use the collector to get data
        return self.collector.collect_data()
    
    def get_collector_class_model(self) -> Dict[str, Type]:
        """Get the class models for the collector(s) used by this recorder."""
        return {
            "SimpleCollector": SimpleCollector,
            "SimpleActivity": SimpleActivity
        }
    
    def get_json_schema(self) -> dict:
        """Get the JSON schema for this recorder's data."""
        return {
            "type": "object",
            "properties": {
                "activity_id": {"type": "string", "format": "uuid"},
                "name": {"type": "string"},
                "activity_type": {"type": "string"},
                "timestamp": {"type": "string", "format": "date-time"},
                "details": {"type": "object"}
            },
            "required": ["activity_id", "name", "activity_type", "timestamp"]
        }
    
    def get_semantic_attributes(self, activity_data: SimpleActivity) -> List[IndalekoSemanticAttributeDataModel]:
        """
        Get semantic attributes for the activity data.
        
        Args:
            activity_data: SimpleActivity object
            
        Returns:
            List of semantic attributes
        """
        attributes = []
        
        # Add name attribute
        attributes.append(IndalekoSemanticAttributeDataModel(
            Identifier=IndalekoUUIDDataModel(
                Identifier=self.ACTIVITY_NAME_UUID,
                Label="Activity Name"
            ),
            Value=activity_data.name
        ))
        
        # Add activity type attribute
        attributes.append(IndalekoSemanticAttributeDataModel(
            Identifier=IndalekoUUIDDataModel(
                Identifier=self.ACTIVITY_TYPE_UUID,
                Label="Activity Type"
            ),
            Value=activity_data.activity_type
        ))
        
        return attributes
    
    def _get_source_identifier_tags(self) -> tuple[list[str], list[str]]:
        """
        Get source identifier UUIDs and schema identifier UUIDs.
        
        Returns:
            Tuple of (source_ids, schema_ids)
        """
        source_ids = [
            str(ActivityDataCharacteristics.ACTIVITY_DATA_ACTIVITY.value),
            str(ActivityDataCharacteristics.ACTIVITY_DATA_USER_ACTIVITY.value)
        ]
        
        schema_ids = [
            str(self.ACTIVITY_NAME_UUID),
            str(self.ACTIVITY_TYPE_UUID)
        ]
        
        return source_ids, schema_ids


def main():
    """Test the simple activity recorder."""
    # Set up logging
    logging.basicConfig(level=logging.INFO,
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create a recorder with auto_connect disabled for testing
    recorder = SimpleActivityRecorder(auto_connect=False, register_service=False)
    
    # Show information about the recorder
    print(f"Recorder ID: {recorder.get_recorder_id()}")
    print(f"Recorder Name: {recorder.get_recorder_name()}")
    print(f"Recorder Description: {recorder.get_description()}")
    print(f"Collection Name: {recorder._collection_name}")
    
    # Show the JSON schema
    print("\nJSON Schema:")
    print(recorder.get_json_schema())
    
    # Collect and process data (if database connection is available)
    try:
        activities = recorder.collect_and_process_data()
        print(f"\nCollected {len(activities)} activities:")
        for activity in activities:
            print(f"  - {activity.name} ({activity.activity_type})")
            
        # To actually store in database, uncomment these lines
        # recorder._connect_to_db()
        # recorder.update_data()
    except Exception as e:
        print(f"Error collecting data: {e}")


if __name__ == "__main__":
    main()