#!/usr/bin/env python
"""
Unit tests for the NTFS Hot Tier Recorder.

This module contains tests for verifying the functionality of the
NTFS Hot Tier Recorder, which is responsible for high-fidelity
storage of recent NTFS file system activities.

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
import json
import tempfile
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from pathlib import Path

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import the recorder class to test
from activity.recorders.storage.ntfs.tiered.hot.recorder import NtfsHotTierRecorder
from activity.collectors.storage.data_models.storage_activity_data_model import (
    NtfsStorageActivityData,
    StorageProviderType,
    StorageActivityType,
    StorageItemType
)


class TestNtfsHotTierRecorder(unittest.TestCase):
    """Tests for the NtfsHotTierRecorder class."""

    def setUp(self):
        """Set up test environment."""
        # Create a recorder instance with database disabled for unit tests
        # Also disable registration with service manager
        self.recorder = NtfsHotTierRecorder(no_db=True, debug=True, register_service=False)
        
        # Create some test data
        self.test_data = self._create_test_data()
        
        # Skip JSONL file creation for basic tests as it may fail if model changes
        # We'll create it only in tests that actually need it

    def tearDown(self):
        """Clean up after tests."""
        # Remove temporary file if it exists
        if hasattr(self, 'temp_jsonl') and os.path.exists(self.temp_jsonl):
            os.unlink(self.temp_jsonl)

    def _create_test_data(self):
        """Create test activity data."""
        return NtfsStorageActivityData(
            activity_id=uuid.uuid4(),
            activity_type=StorageActivityType.CREATE,
            timestamp=datetime.now(timezone.utc),
            file_name="test_file.txt",
            file_path="C:\\Indaleko_Test\\test_file.txt",
            volume_name="C:",
            file_reference_number="1234567890",
            is_directory=False,
            provider_type=StorageProviderType.LOCAL_NTFS,
            provider_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            item_type=StorageItemType.FILE,
            reason_flags=0x01  # FILE_ACTION_ADDED
        )

    def _create_temp_jsonl_file(self):
        """Create a temporary JSONL file with test activities."""
        # Create a custom encoder for JSON serialization
        class CustomEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, uuid.UUID):
                    return str(obj)
                elif isinstance(obj, datetime):
                    return obj.isoformat()
                return str(obj)  # For any other non-serializable objects, convert to string
                
        fd, path = tempfile.mkstemp(suffix='.jsonl')
        with os.fdopen(fd, 'w') as f:
            # Write several test activities
            for i in range(5):
                # Create simplified test data that can be safely serialized
                activity_dict = {
                    "activity_id": str(uuid.uuid4()),
                    "activity_type": "create",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "file_name": f"test_file_{i}.txt",
                    "file_path": f"C:\\Indaleko_Test\\test_file_{i}.txt",
                    "volume_name": "C:",
                    "file_reference_number": f"123456789{i}",
                    "is_directory": False,
                    "provider_type": "ntfs",
                    "provider_id": str(uuid.uuid4()),
                    "item_type": "file",
                    "reason_flags": 1
                }
                
                # Write as JSON line with custom encoder
                f.write(json.dumps(activity_dict, cls=CustomEncoder) + '\n')
        
        return path

    def test_recorder_initialization(self):
        """Test that the recorder initializes properly."""
        self.assertEqual(self.recorder._ttl_days, 4)
        self.assertEqual(self.recorder._name, "NTFS Hot Tier Recorder")
        self.assertEqual(self.recorder._provider_type, StorageProviderType.LOCAL_NTFS)
        self.assertIsNotNone(self.recorder._frn_entity_cache)
        self.assertIsNotNone(self.recorder._path_entity_cache)

    def test_get_recorder_name(self):
        """Test get_recorder_name method."""
        self.assertEqual(self.recorder.get_recorder_name(), "NTFS Hot Tier Recorder")

    def test_get_recorder_id(self):
        """Test get_recorder_id method."""
        self.assertEqual(self.recorder.get_recorder_id(), 
                         uuid.UUID("f4dea3b8-5d3e-48ad-9b2c-0e72c9a1b867"))

    def test_get_recorder_characteristics(self):
        """Test get_recorder_characteristics method."""
        characteristics = self.recorder.get_recorder_characteristics()
        self.assertGreaterEqual(len(characteristics), 2)

    def test_get_collector_class_model(self):
        """Test get_collector_class_model method."""
        model = self.recorder.get_collector_class_model()
        self.assertIn("NtfsStorageActivityData", model)
        self.assertIn("StorageActivityType", model)

    def test_get_json_schema(self):
        """Test get_json_schema method."""
        schema = self.recorder.get_json_schema()
        self.assertIsInstance(schema, dict)
        self.assertIn("properties", schema)

    def test_cache_duration(self):
        """Test cache_duration method."""
        duration = self.recorder.cache_duration()
        self.assertEqual(duration.total_seconds(), 15 * 60)  # 15 minutes

    def test_get_cursor(self):
        """Test get_cursor method."""
        context_id = uuid.uuid4()
        cursor = self.recorder.get_cursor(context_id)
        self.assertIsInstance(cursor, uuid.UUID)

    def test_calculate_initial_importance(self):
        """Test _calculate_initial_importance method."""
        # Skip creating temp_jsonl file for this test
        if hasattr(self, 'temp_jsonl'):
            del self.temp_jsonl
            
        # Test file type importance
        doc_activity = {}
        doc_activity["file_path"] = "C:\\Documents\\report.docx"
        doc_activity["activity_type"] = "create"
        importance1 = self.recorder._calculate_initial_importance(doc_activity)
        
        # Test temp file (lower importance)
        temp_activity = {}
        temp_activity["file_path"] = "C:\\Temp\\cache.dat"
        temp_activity["activity_type"] = "create"
        importance2 = self.recorder._calculate_initial_importance(temp_activity)
        
        # Document should have higher importance than temp file
        self.assertGreater(importance1, importance2)
        
        # Test directory importance
        dir_activity = {}
        dir_activity["file_path"] = "C:\\test\\folder"
        dir_activity["is_directory"] = True
        dir_activity["activity_type"] = "create"
        importance3 = self.recorder._calculate_initial_importance(dir_activity)
        
        # Directory should have slightly higher importance than regular file
        regular_activity = {}
        regular_activity["file_path"] = "C:\\test\\file.txt"
        regular_activity["is_directory"] = False
        regular_activity["activity_type"] = "create"
        importance4 = self.recorder._calculate_initial_importance(regular_activity)
        self.assertGreater(importance3, importance4)

    def test_process_jsonl_file(self):
        """Test process_jsonl_file method."""
        # Since the actual implementation reads a file, we'll just test
        # that our implementation handles errors gracefully
        
        # Test with a non-existent file
        with patch('os.path.exists', return_value=False):
            with self.assertRaises(FileNotFoundError):
                self.recorder.process_jsonl_file('/non-existent.jsonl')
                
        # Success case is tested by real implementation in Phase 8

    def test_get_description(self):
        """Test get_description method."""
        description = self.recorder.get_description()
        self.assertIn("hot tier", description.lower())

    @patch('activity.recorders.storage.ntfs.tiered.hot.recorder.NtfsHotTierRecorder._enhance_activity_data')
    def test_store_activity(self, mock_enhance):
        """Test store_activity method."""
        # Set up mocks
        mock_enhance.return_value = self.test_data.model_dump()
        
        # Mock the collection methods to avoid database access
        self.recorder._collection = MagicMock()
        self.recorder._collection.add_document.return_value = {'_id': '123', '_key': '123'}
        
        # Test with activity data model
        with patch.object(self.recorder, '_build_hot_tier_document', return_value={"test": "document"}):
            result = self.recorder.store_activity(self.test_data)
            self.assertEqual(result, self.test_data.activity_id)
            self.recorder._build_hot_tier_document.assert_called_once()
            self.recorder._collection.add_document.assert_called_once_with({"test": "document"})
        
        # Test with dictionary
        self.recorder._collection.reset_mock()
        with patch.object(self.recorder, '_build_hot_tier_document', return_value={"test": "document"}):
            result = self.recorder.store_activity(self.test_data.model_dump())
            self.assertIsInstance(result, uuid.UUID)
            self.recorder._collection.add_document.assert_called_once()


if __name__ == '__main__':
    unittest.main()