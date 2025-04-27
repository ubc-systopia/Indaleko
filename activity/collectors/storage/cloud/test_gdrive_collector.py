#!/usr/bin/env python3
"""
Test script for Google Drive Activity Collector and Recorder.

This script tests the Google Drive Activity Collector and Recorder without requiring
actual Google Drive credentials.

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
import unittest
import uuid

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch


# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import the collector class
from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.storage.cloud.data_models.gdrive_activity_model import (
    GDriveActivityData,
    GDriveActivityType,
    GDriveFileInfo,
    GDriveFileType,
    GDriveUserInfo,
)
from activity.collectors.storage.cloud.gdrive_activity_collector import (
    GoogleDriveActivityCollector,
)


# Import paths may be different when running tests directly vs through a module
try:
    from activity.recorders.storage.cloud.gdrive.recorder import (
        GoogleDriveActivityRecorder,
    )
except ImportError:
    # This is fine during initial development - recorder may not exist yet
    pass


class TestGoogleDriveCollector(unittest.TestCase):
    """Test class for GoogleDriveActivityCollector."""

    @patch(
        "activity.collectors.storage.cloud.gdrive_activity_collector.GoogleDriveActivityCollector._authenticate",
    )
    @patch(
        "activity.collectors.storage.cloud.gdrive_activity_collector.GoogleDriveActivityCollector._init_apis",
    )
    @patch(
        "activity.collectors.storage.cloud.gdrive_activity_collector.GoogleDriveActivityCollector._load_config",
    )
    def setUp(self, mock_load_config, mock_init_apis, mock_authenticate):
        """Set up test environment."""
        # Mock authentication and API initialization
        mock_authenticate.return_value = None
        mock_init_apis.return_value = None

        # Mock config loading
        mock_load_config.return_value = {
            "credentials_file": "test_credentials.json",
            "token_file": "test_token.json",
            "state_file": "test_state.json",
            "output_file": "test_output.jsonl",
            "direct_to_db": False,
            "db_config": {"use_default": True},
            "collection": {"max_results_per_page": 100, "max_pages_per_run": 10},
            "scheduling": {
                "interval_minutes": 15,
                "retry_delay_seconds": 60,
                "max_retries": 3,
            },
            "logging": {"log_file": "test_log.log", "log_level": "DEBUG"},
        }

        # Create a collector with test configuration
        self.collector = GoogleDriveActivityCollector(
            debug=True,
            config_path="test_config.json",
            credentials_file="test_credentials.json",
            token_file="test_token.json",
            state_file="test_state.json",
            output_file="test_output.jsonl",
        )

        # Set up mock state
        self.collector.state = {
            "last_run": "2025-04-21T00:00:00Z",
            "last_page_token": "test_page_token",
            "last_start_time": "2025-04-14T00:00:00Z",
            "activities_collected": 0,
            "total_activities_collected": 0,
            "errors": 0,
        }

        # Set up mock activities
        self.collector.activities = [
            GDriveActivityData(
                activity_id="test-activity-1",
                activity_type=GDriveActivityType.EDIT,
                timestamp="2025-04-15T10:00:00Z",
                user=GDriveUserInfo(
                    user_id="test-user-1",
                    email="test@example.com",
                    display_name="Test User",
                ),
                file=GDriveFileInfo(
                    file_id="test-file-1",
                    name="Test Document.docx",
                    mime_type="application/vnd.google-apps.document",
                    file_type=GDriveFileType.DOCUMENT,
                    parent_folder_id="test-folder-1",
                    parent_folder_name="Test Folder",
                ),
            ),
        ]

    def test_get_collector_name(self):
        """Test get_collector_name method."""
        self.assertEqual(
            self.collector.get_collector_name(),
            "Google Drive Activity Collector",
        )

    def test_get_provider_id(self):
        """Test get_provider_id method."""
        self.assertEqual(
            self.collector.get_provider_id(),
            uuid.UUID("3e7d8f29-7c73-41c5-b3d4-1a9b42567890"),
        )

    def test_get_collector_characteristics(self):
        """Test get_collector_characteristics method."""
        characteristics = self.collector.get_collector_characteristics()
        # Verify we get a list of characteristics
        self.assertIsInstance(characteristics, list)
        self.assertTrue(len(characteristics) > 0)

        # Check that each item is an ActivityDataCharacteristics object
        for char in characteristics:
            self.assertIsInstance(char, ActivityDataCharacteristics)

    def test_get_cursor(self):
        """Test get_cursor method."""
        # Get cursor with no activity context
        cursor = self.collector.get_cursor()
        self.assertIsInstance(cursor, uuid.UUID)

        # Get cursor with activity context
        activity_context = uuid.uuid4()
        cursor = self.collector.get_cursor(activity_context)
        self.assertIsInstance(cursor, uuid.UUID)

    def test_retrieve_data(self):
        """Test retrieve_data method."""
        # Try to retrieve a non-existent activity
        non_existent_id = uuid.uuid4()
        result = self.collector.retrieve_data(non_existent_id)
        self.assertEqual(result, {})

        # Add a mock activity and try to retrieve it
        activity_id = uuid.uuid4()
        self.collector.activities[0].activity_id = str(activity_id)
        result = self.collector.retrieve_data(activity_id)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["activity_id"], str(activity_id))

    def test_cache_duration(self):
        """Test cache_duration method."""
        duration = self.collector.cache_duration()
        self.assertIsInstance(duration, int)
        self.assertTrue(duration > 0)

    def test_get_description(self):
        """Test get_description method."""
        description = self.collector.get_description()
        self.assertIsInstance(description, str)
        self.assertTrue(len(description) > 0)

    def test_get_json_schema(self):
        """Test get_json_schema method."""
        schema = self.collector.get_json_schema()
        self.assertIsInstance(schema, dict)
        self.assertIn("properties", schema)

    def test_activity_conversion(self):
        """Test conversion from GDriveActivityData to GoogleDriveStorageActivityData."""
        if self.collector.activities:
            activity = self.collector.activities[0]
            storage_activity = activity.to_storage_activity()
            self.assertEqual(storage_activity.file_id, activity.file.file_id)
            self.assertEqual(storage_activity.file_name, activity.file.name)
            self.assertEqual(storage_activity.mime_type, activity.file.mime_type)


# Test the recorder if it's available
@unittest.skipIf(
    "GoogleDriveActivityRecorder" not in globals(),
    "Recorder class not available",
)
class TestGoogleDriveRecorder(unittest.TestCase):
    """Test class for GoogleDriveActivityRecorder."""

    @patch(
        "activity.collectors.storage.cloud.gdrive_activity_collector.GoogleDriveActivityCollector._authenticate",
    )
    @patch(
        "activity.collectors.storage.cloud.gdrive_activity_collector.GoogleDriveActivityCollector._init_apis",
    )
    @patch(
        "activity.collectors.storage.cloud.gdrive_activity_collector.GoogleDriveActivityCollector._load_config",
    )
    @patch(
        "activity.recorders.storage.cloud.gdrive.recorder.GoogleDriveActivityRecorder._connect_to_db",
    )
    @patch(
        "activity.recorders.storage.cloud.gdrive.recorder.GoogleDriveActivityRecorder._register_with_service_manager",
    )
    def setUp(
        self,
        mock_register,
        mock_connect,
        mock_load_config,
        mock_init_apis,
        mock_authenticate,
    ):
        """Set up test environment."""
        # Mock authentication and API initialization
        mock_authenticate.return_value = None
        mock_init_apis.return_value = None
        mock_connect.return_value = None
        mock_register.return_value = None

        # Mock config loading
        mock_load_config.return_value = {
            "credentials_file": "test_credentials.json",
            "token_file": "test_token.json",
            "state_file": "test_state.json",
            "output_file": "test_output.jsonl",
            "direct_to_db": False,
            "db_config": {"use_default": True},
            "collection": {"max_results_per_page": 100, "max_pages_per_run": 10},
        }

        # Create a collector with test configuration
        self.collector = GoogleDriveActivityCollector(
            debug=True,
            config_path="test_config.json",
            credentials_file="test_credentials.json",
            token_file="test_token.json",
            state_file="test_state.json",
            output_file="test_output.jsonl",
        )

        # Set up test activities
        self.collector.activities = [
            GDriveActivityData(
                activity_id=uuid.uuid4(),
                activity_type=GDriveActivityType.EDIT,
                timestamp=datetime.now(UTC),
                user=GDriveUserInfo(
                    user_id="test-user-1",
                    email="test@example.com",
                    display_name="Test User",
                ),
                file=GDriveFileInfo(
                    file_id="test-file-1",
                    name="Test Document.docx",
                    mime_type="application/vnd.google-apps.document",
                    file_type=GDriveFileType.DOCUMENT,
                    parent_folder_id="test-folder-1",
                    parent_folder_name="Test Folder",
                ),
            ),
        ]

        # Create a recorder with the test collector
        self.recorder = GoogleDriveActivityRecorder(
            collector=self.collector,
            debug=True,
            auto_connect=False,  # Disable actual DB connection
        )

        # Mock collection for tests
        self.recorder._collection = MagicMock()
        self.recorder._collection.add_document.return_value = {"_key": "test_key"}

    def test_recorder_initialization(self):
        """Test recorder initialization."""
        self.assertEqual(self.recorder._name, "Google Drive Storage Activity Recorder")
        self.assertEqual(self.recorder._provider_type, "google_drive")
        self.assertEqual(self.recorder._gdrive_collector, self.collector)

    @patch(
        "activity.recorders.storage.cloud.gdrive.recorder.get_semantic_attributes_for_activity",
    )
    def test_build_gdrive_activity_document(self, mock_get_attributes):
        """Test building a document for a Google Drive activity."""
        # Mock semantic attributes
        mock_get_attributes.return_value = []

        # Get first test activity
        activity = self.collector.activities[0]

        # Convert to storage activity
        storage_activity = activity.to_storage_activity()

        # Build document
        document = self.recorder._build_gdrive_activity_document(storage_activity)

        # Verify document structure
        self.assertIn("Record", document)
        self.assertIn("Data", document["Record"])
        self.assertEqual(document["Record"]["Data"]["file_id"], "test-file-1")
        self.assertEqual(document["Record"]["Data"]["file_name"], "Test Document.docx")

    @patch(
        "activity.recorders.storage.cloud.gdrive.recorder.GoogleDriveActivityRecorder._build_gdrive_activity_document",
    )
    def test_store_activity(self, mock_build_doc):
        """Test storing a Google Drive activity."""
        # Mock document building
        mock_build_doc.return_value = {"_key": "test_key", "Record": {"Data": {}}}

        # Get first test activity
        activity = self.collector.activities[0]

        # Convert to storage activity
        storage_activity = activity.to_storage_activity()

        # Store activity
        result = self.recorder.store_activity(storage_activity)

        # Verify result
        self.assertEqual(result, storage_activity.activity_id)

        # Verify document was added to collection
        self.recorder._collection.add_document.assert_called_once()

    def test_get_recorder_characteristics(self):
        """Test getting recorder characteristics."""
        characteristics = self.recorder.get_recorder_characteristics()
        self.assertIsInstance(characteristics, list)
        self.assertTrue(len(characteristics) >= 3)

    def test_get_json_schema(self):
        """Test getting JSON schema."""
        schema = self.recorder.get_json_schema()
        self.assertIsInstance(schema, dict)
        self.assertIn("properties", schema)

    def test_cache_duration(self):
        """Test cache duration."""
        duration = self.recorder.cache_duration()
        self.assertEqual(duration.total_seconds(), 7200)  # 2 hours


# Test the recorder if it's available
@unittest.skipIf(
    "GoogleDriveActivityRecorder" not in globals(),
    "Recorder class not available",
)
class TestGoogleDriveRecorder(unittest.TestCase):
    """Test class for GoogleDriveActivityRecorder."""

    @patch(
        "activity.collectors.storage.cloud.gdrive_activity_collector.GoogleDriveActivityCollector._authenticate",
    )
    @patch(
        "activity.collectors.storage.cloud.gdrive_activity_collector.GoogleDriveActivityCollector._init_apis",
    )
    @patch(
        "activity.collectors.storage.cloud.gdrive_activity_collector.GoogleDriveActivityCollector._load_config",
    )
    @patch(
        "activity.recorders.storage.cloud.gdrive.recorder.GoogleDriveActivityRecorder._connect_to_db",
    )
    @patch(
        "activity.recorders.storage.cloud.gdrive.recorder.GoogleDriveActivityRecorder._register_with_service_manager",
    )
    def setUp(
        self,
        mock_register,
        mock_connect,
        mock_load_config,
        mock_init_apis,
        mock_authenticate,
    ):
        """Set up test environment."""
        # Mock authentication and API initialization
        mock_authenticate.return_value = None
        mock_init_apis.return_value = None
        mock_connect.return_value = None
        mock_register.return_value = None

        # Mock config loading
        mock_load_config.return_value = {
            "credentials_file": "test_credentials.json",
            "token_file": "test_token.json",
            "state_file": "test_state.json",
            "output_file": "test_output.jsonl",
            "direct_to_db": False,
            "db_config": {"use_default": True},
            "collection": {"max_results_per_page": 100, "max_pages_per_run": 10},
        }

        # Create a collector with test configuration
        self.collector = GoogleDriveActivityCollector(
            debug=True,
            config_path="test_config.json",
            credentials_file="test_credentials.json",
            token_file="test_token.json",
            state_file="test_state.json",
            output_file="test_output.jsonl",
        )

        # Set up test activities
        self.collector.activities = [
            GDriveActivityData(
                activity_id=uuid.uuid4(),
                activity_type=GDriveActivityType.EDIT,
                timestamp=datetime.now(UTC),
                user=GDriveUserInfo(
                    user_id="test-user-1",
                    email="test@example.com",
                    display_name="Test User",
                ),
                file=GDriveFileInfo(
                    file_id="test-file-1",
                    name="Test Document.docx",
                    mime_type="application/vnd.google-apps.document",
                    file_type=GDriveFileType.DOCUMENT,
                    parent_folder_id="test-folder-1",
                    parent_folder_name="Test Folder",
                ),
            ),
        ]

        # Create a recorder with the test collector
        self.recorder = GoogleDriveActivityRecorder(
            collector=self.collector,
            debug=True,
            auto_connect=False,  # Disable actual DB connection
        )

        # Mock collection for tests
        self.recorder._collection = MagicMock()
        self.recorder._collection.add_document.return_value = {"_key": "test_key"}

    def test_recorder_initialization(self):
        """Test recorder initialization."""
        self.assertEqual(self.recorder._name, "Google Drive Storage Activity Recorder")
        self.assertEqual(self.recorder._provider_type, "google_drive")
        self.assertEqual(self.recorder._gdrive_collector, self.collector)

    @patch(
        "activity.recorders.storage.cloud.gdrive.recorder.get_semantic_attributes_for_activity",
    )
    def test_build_gdrive_activity_document(self, mock_get_attributes):
        """Test building a document for a Google Drive activity."""
        # Mock semantic attributes
        mock_get_attributes.return_value = []

        # Get first test activity
        activity = self.collector.activities[0]

        # Convert to storage activity
        storage_activity = activity.to_storage_activity()

        # Build document
        document = self.recorder._build_gdrive_activity_document(storage_activity)

        # Verify document structure
        self.assertIn("Record", document)
        self.assertIn("Data", document["Record"])
        self.assertEqual(document["Record"]["Data"]["file_id"], "test-file-1")
        self.assertEqual(document["Record"]["Data"]["file_name"], "Test Document.docx")

    @patch(
        "activity.recorders.storage.cloud.gdrive.recorder.GoogleDriveActivityRecorder._build_gdrive_activity_document",
    )
    def test_store_activity(self, mock_build_doc):
        """Test storing a Google Drive activity."""
        # Mock document building
        mock_build_doc.return_value = {"_key": "test_key", "Record": {"Data": {}}}

        # Get first test activity
        activity = self.collector.activities[0]

        # Convert to storage activity
        storage_activity = activity.to_storage_activity()

        # Store activity
        result = self.recorder.store_activity(storage_activity)

        # Verify result
        self.assertEqual(result, storage_activity.activity_id)

        # Verify document was added to collection
        self.recorder._collection.add_document.assert_called_once()

    def test_get_recorder_characteristics(self):
        """Test getting recorder characteristics."""
        characteristics = self.recorder.get_recorder_characteristics()
        self.assertIsInstance(characteristics, list)
        self.assertTrue(len(characteristics) >= 3)

    def test_get_json_schema(self):
        """Test getting JSON schema."""
        schema = self.recorder.get_json_schema()
        self.assertIsInstance(schema, dict)
        self.assertIn("properties", schema)

    def test_cache_duration(self):
        """Test cache duration."""
        duration = self.recorder.cache_duration()
        self.assertEqual(duration.total_seconds(), 7200)  # 2 hours


if __name__ == "__main__":
    unittest.main()
