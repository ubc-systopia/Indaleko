"""Test suite for the CloudStorageActivityGeneratorTool.

This module tests the functionality of the CloudStorageActivityGeneratorTool,
ensuring it generates valid cloud storage activities and files.
"""

import os
import sys
import unittest
import uuid
import random
from typing import Dict, Any
from datetime import datetime, timezone, timedelta

# Setup path for imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import the generator tools
from tools.data_generator_enhanced.agents.data_gen.tools.cloud_storage_generator import (
    CloudStorageActivityGeneratorTool, 
    CloudStorageWorkflowGenerator, 
    CloudStorageFileType,
    CloudStorageActivityGenerator,
    StorageActivityType,
    StorageItemType,
    StorageProviderType
)
from tools.data_generator_enhanced.agents.data_gen.tools.calendar_event_generator import (
    CalendarEventGeneratorTool
)

# Import database-related modules
try:
    from db.db_config import IndalekoDBConfig
    from db.db_collections import IndalekoDBCollections
    HAS_DB = True
except ImportError:
    HAS_DB = False


class TestCloudStorageGenerator(unittest.TestCase):
    """Test cases for the CloudStorageActivityGeneratorTool."""

    def setUp(self):
        """Set up the test environment."""
        # Initialize the generator with a fixed seed for reproducibility
        self.generator = CloudStorageActivityGeneratorTool()
        self.seed = 42
        random.seed(self.seed)
        
        # Create test data
        self.user_email = "test.user@example.com"
        self.user_name = "Test User"
        
        # Time range for activities (90 days in the past to now)
        self.now = datetime.now(timezone.utc)
        self.start_time = self.now - timedelta(days=90)
        self.end_time = self.now
        
        # Generate sample data
        self.gdrive_result = self.generator.execute({
            "count": 20,
            "criteria": {
                "user_email": self.user_email,
                "provider_type": "google_drive",
                "start_time": self.start_time,
                "end_time": self.end_time
            }
        })
        
        self.dropbox_result = self.generator.execute({
            "count": 20,
            "criteria": {
                "user_email": self.user_email,
                "provider_type": "dropbox",
                "start_time": self.start_time,
                "end_time": self.end_time
            }
        })
        
        # Set up database connection if available
        if HAS_DB:
            try:
                self.db_config = IndalekoDBConfig()
                self.db = self.db_config.db
                self.HAS_ACTIVE_DB = self.db_config.db is not None
            except Exception as e:
                print(f"Database connection failed: {e}")
                self.HAS_ACTIVE_DB = False
        else:
            self.HAS_ACTIVE_DB = False
    
    def test_generator_initialization(self):
        """Test that the generator initializes correctly."""
        self.assertIsNotNone(self.generator)
        self.assertIsInstance(self.generator, CloudStorageActivityGeneratorTool)
        self.assertIsInstance(self.generator.generator, CloudStorageActivityGenerator)
    
    def test_gdrive_generation(self):
        """Test that Google Drive activities are generated correctly."""
        # Check results
        self.assertIn("activities", self.gdrive_result)
        self.assertIn("files", self.gdrive_result)
        self.assertIn("provider_type", self.gdrive_result)
        
        # Check that activities were generated
        activities = self.gdrive_result["activities"]
        self.assertGreaterEqual(len(activities), 1)
        
        # Check that files were generated
        files = self.gdrive_result["files"]
        self.assertGreaterEqual(len(files), 1)
        
        # Check the provider type
        self.assertEqual(self.gdrive_result["provider_type"], StorageProviderType.GOOGLE_DRIVE)
        
        # Check the structure of each activity
        for activity in activities:
            # Basic fields
            self.assertIn("activity_id", activity)
            self.assertIn("timestamp", activity)
            self.assertIn("activity_type", activity)
            self.assertIn("item_type", activity)
            self.assertIn("file_name", activity)
            self.assertIn("file_path", activity)
            self.assertIn("provider_type", activity)
            self.assertIn("provider_id", activity)
            
            # Cloud storage fields
            self.assertIn("cloud_item_id", activity)
            self.assertIn("mime_type", activity)
            
            # Specific Google Drive fields
            self.assertIn("drive_id", activity)
            
            # Semantic attributes
            self.assertIn("SemanticAttributes", activity)
            self.assertGreater(len(activity["SemanticAttributes"]), 0)
            
            # Verify timestamp is within range
            timestamp = activity["timestamp"]
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            self.assertGreaterEqual(timestamp, self.start_time)
            self.assertLessEqual(timestamp, self.end_time)
            
            # Check semantic attributes structure
            for attr in activity["SemanticAttributes"]:
                self.assertIn("Identifier", attr)
                self.assertIn("Identifier", attr["Identifier"])
                self.assertIn("Label", attr["Identifier"])
    
    def test_dropbox_generation(self):
        """Test that Dropbox activities are generated correctly."""
        # Check results
        self.assertIn("activities", self.dropbox_result)
        self.assertIn("files", self.dropbox_result)
        self.assertIn("provider_type", self.dropbox_result)
        
        # Check that activities were generated
        activities = self.dropbox_result["activities"]
        self.assertGreaterEqual(len(activities), 1)
        
        # Check that files were generated
        files = self.dropbox_result["files"]
        self.assertGreaterEqual(len(files), 1)
        
        # Check the provider type
        self.assertEqual(self.dropbox_result["provider_type"], StorageProviderType.DROPBOX)
        
        # Check the structure of each activity
        for activity in activities:
            # Basic fields
            self.assertIn("activity_id", activity)
            self.assertIn("timestamp", activity)
            self.assertIn("activity_type", activity)
            self.assertIn("item_type", activity)
            self.assertIn("file_name", activity)
            self.assertIn("file_path", activity)
            self.assertIn("provider_type", activity)
            self.assertIn("provider_id", activity)
            
            # Cloud storage fields
            self.assertIn("cloud_item_id", activity)
            self.assertIn("mime_type", activity)
            
            # Specific Dropbox fields
            self.assertIn("dropbox_file_id", activity)
            self.assertIn("revision", activity)
            
            # Semantic attributes
            self.assertIn("SemanticAttributes", activity)
            self.assertGreater(len(activity["SemanticAttributes"]), 0)
            
            # Verify timestamp is within range
            timestamp = activity["timestamp"]
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            self.assertGreaterEqual(timestamp, self.start_time)
            self.assertLessEqual(timestamp, self.end_time)
    
    def test_activity_types(self):
        """Test that various activity types are generated."""
        activities = self.gdrive_result["activities"]
        
        # Collect all activity types
        activity_types = set(a["activity_type"] for a in activities)
        
        # We should have at least a few different activity types
        self.assertGreater(len(activity_types), 1)
        
        # CREATE should be one of them
        self.assertIn(StorageActivityType.CREATE, activity_types)
    
    def test_file_structure(self):
        """Test that files have a proper hierarchical structure."""
        files = self.gdrive_result["files"]
        
        # Find folders
        folders = [f for f in files if f["is_directory"]]
        
        # There should be at least one folder
        self.assertGreater(len(folders), 0)
        
        # Files should have parent IDs
        non_root_files = [f for f in files if not f["is_directory"] and "cloud_parent_id" in f]
        self.assertGreater(len(non_root_files), 0)
        
        # Verify parent-child relationships
        for file in non_root_files:
            parent_id = file["cloud_parent_id"]
            # Find the parent folder
            parent_found = False
            for folder in folders:
                if folder["cloud_item_id"] == parent_id:
                    parent_found = True
                    self.assertIn(file["cloud_item_id"], folder["children"])
                    break
            self.assertTrue(parent_found, f"Parent folder {parent_id} not found for file {file['file_name']}")
    
    def test_temporal_consistency(self):
        """Test that activities have temporal consistency."""
        activities = self.gdrive_result["activities"]
        
        # Sort activities by timestamp
        sorted_activities = sorted(activities, key=lambda a: a["timestamp"] if isinstance(a["timestamp"], datetime) else datetime.fromisoformat(a["timestamp"]))
        
        # Group activities by file
        file_activities = {}
        for activity in sorted_activities:
            file_id = activity["file_id"]
            if file_id not in file_activities:
                file_activities[file_id] = []
            file_activities[file_id].append(activity)
        
        # Check each file's activity sequence
        for file_id, activities in file_activities.items():
            if len(activities) <= 1:
                continue
            
            # First activity should be CREATE
            first_activity = activities[0]
            self.assertEqual(
                first_activity["activity_type"], 
                StorageActivityType.CREATE,
                f"First activity for file {file_id} is not CREATE"
            )
            
            # Check that each activity's timestamp is after the previous one
            for i in range(1, len(activities)):
                prev_time = activities[i-1]["timestamp"] if isinstance(activities[i-1]["timestamp"], datetime) else datetime.fromisoformat(activities[i-1]["timestamp"])
                curr_time = activities[i]["timestamp"] if isinstance(activities[i]["timestamp"], datetime) else datetime.fromisoformat(activities[i]["timestamp"])
                
                self.assertGreaterEqual(
                    curr_time, 
                    prev_time,
                    f"Activity {activities[i]['activity_id']} has timestamp before previous activity"
                )
    
    def test_calendar_integration(self):
        """Test integration with calendar events."""
        # First generate some calendar events
        calendar_generator = CalendarEventGeneratorTool()
        calendar_result = calendar_generator.execute({
            "count": 5,
            "criteria": {
                "user_email": self.user_email,
                "user_name": self.user_name,
                "start_time": self.start_time,
                "end_time": self.end_time
            }
        })
        
        # Generate cloud storage activities with calendar integration
        result = self.generator.execute({
            "count": 20,
            "criteria": {
                "user_email": self.user_email,
                "provider_type": "google_drive",
                "start_time": self.start_time,
                "end_time": self.end_time,
                "calendar_events": calendar_result["events"]
            }
        })
        
        # Check if we have some activities with calendar event references
        activities = result["activities"]
        calendar_related = False
        
        for activity in activities:
            if "attributes" in activity and "related_calendar_event" in activity["attributes"]:
                calendar_related = True
                # Verify this is a valid event ID from our calendar events
                event_id = activity["attributes"]["related_calendar_event"]
                self.assertTrue(
                    any(e["event_id"] == event_id for e in calendar_result["events"]),
                    f"Activity references unknown calendar event ID: {event_id}"
                )
                
                # The activity should have happened during the calendar event
                event = next(e for e in calendar_result["events"] if e["event_id"] == event_id)
                
                # Parse timestamps
                activity_time = activity["timestamp"] if isinstance(activity["timestamp"], datetime) else datetime.fromisoformat(activity["timestamp"])
                event_start = event["start_time"] if isinstance(event["start_time"], datetime) else datetime.fromisoformat(event["start_time"])
                event_end = event["end_time"] if isinstance(event["end_time"], datetime) else datetime.fromisoformat(event["end_time"])
                
                # The activity should be temporally related to the event
                # (We allow a small buffer before and after for practical reasons)
                buffer = timedelta(minutes=15)
                self.assertTrue(
                    event_start - buffer <= activity_time <= event_end + buffer,
                    f"Activity time {activity_time} is outside event time range {event_start} - {event_end}"
                )
                
        # We might not have any calendar-related activities due to random sampling
        # So this test is informational rather than strictly required
        if not calendar_related:
            print("No calendar-related activities were generated in this test run")
    
    @unittest.skipIf(not HAS_DB, "Database modules not available")
    def test_db_integration(self):
        """Test that generated activities can be stored in the database."""
        if not hasattr(self, 'db') or not self.HAS_ACTIVE_DB:
            self.skipTest("No active database connection available")
        
        print("Database connection verified. Running database integration test...")
        
        # Check if collection exists
        collection_name = "CloudStorageActivities"
        if not self.db.has_collection(collection_name):
            self.db.create_collection(collection_name)
        
        collection = self.db.collection(collection_name)
        
        # Get the first activity
        activity = self.gdrive_result["activities"][0]
        
        # Make a copy with only the essential fields for database testing
        db_activity = {
            "activity_id": activity["activity_id"],
            "timestamp": activity["timestamp"] if isinstance(activity["timestamp"], str) else activity["timestamp"].isoformat(),
            "activity_type": activity["activity_type"],
            "item_type": activity["item_type"],
            "file_name": activity["file_name"],
            "provider_type": activity["provider_type"]
        }
        
        try:
            # Try to insert the activity into the database
            document = collection.insert(db_activity)
            self.assertIsNotNone(document)
            print(f"Successfully inserted activity into database: {document}")
            
            # Clean up after test
            collection.delete(document)
            print("Successfully deleted test activity from database")
        except Exception as e:
            self.fail(f"Database integration test failed: {e}")


if __name__ == "__main__":
    unittest.main()