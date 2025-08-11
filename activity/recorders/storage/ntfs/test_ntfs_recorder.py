"""
Test script for the NTFS Storage Activity Recorder.

This module tests the NTFS Storage Activity Recorder's functionality,
focusing on proper collection registration, database interaction, and
timezone-aware datetime handling.

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
import sys
import unittest
import uuid

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch


# Set logging level
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up Indaleko root
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

try:
    # pylint: disable=wrong-import-position
    from activity.collectors.storage.data_models.storage_activity_data_model import (
        NtfsStorageActivityData,
        StorageActivityType,
        StorageItemType,
        StorageProviderType,
    )
    from activity.collectors.storage.ntfs.ntfs_collector import (
        NtfsStorageActivityCollector,
    )
    from activity.recorders.storage.ntfs.ntfs_recorder import (
        NtfsStorageActivityRecorder,
    )

    # pylint: enable=wrong-import-position
except ImportError as e:
    logger.exception(f"Import error: {e}")
    logger.exception("This test module requires specific Python packages.")
    sys.exit(1)


class TestNtfsStorageActivityRecorder(unittest.TestCase):
    """Tests for the NTFS Storage Activity Recorder."""

    def setUp(self):
        """Set up test environment."""
        # Create a mock collector
        self.mock_collector = MagicMock(spec=NtfsStorageActivityCollector)
        self.mock_collector._active = False
        self.mock_collector._volumes = ["C:"]
        self.mock_collector._provider_id = uuid.UUID(
            "7d8f5a92-35c7-41e6-b13d-6c4e89e7f2a5",
        )

        # Mock activity data
        self.mock_activities = []
        for i in range(5):
            activity = NtfsStorageActivityData(
                timestamp=datetime.now(UTC),
                file_reference_number=f"{1000 + i}",
                parent_file_reference_number="1000",
                activity_type=StorageActivityType.CREATE,
                reason_flags=1,
                file_name=f"test_{i}.txt",
                file_path=f"C:\\test\\test_{i}.txt",
                volume_name="C:",
                is_directory=False,
                provider_type=StorageProviderType.LOCAL_NTFS,
                provider_id=self.mock_collector._provider_id,
                item_type=StorageItemType.FILE,
            )
            self.mock_activities.append(activity)

        # Set up the collector to return mock activities
        self.mock_collector.get_activities.return_value = self.mock_activities

        # Mock database connection
        self.mock_db = MagicMock()
        self.mock_db.db = MagicMock()
        self.mock_db.db.aql = MagicMock()

        # Mock collection
        self.mock_collection = MagicMock()
        self.mock_collection.name = "NtfsStorageActivity_mock"
        self.mock_collection.add_document.return_value = {
            "_id": "mock_id",
            "_key": "mock_key",
        }

        # Mock environment for patches
        self.patches = []

    def tearDown(self):
        """Clean up patches."""
        for p in self.patches:
            p.stop()

    @patch("activity.recorders.storage.base.StorageActivityRecorder._connect_to_db")
    @patch(
        "activity.recorders.storage.base.StorageActivityRecorder._register_with_activity_service",
    )
    @patch("hashlib.md5")
    def test_recorder_initialization(self, mock_md5, mock_register, mock_connect):
        """Test proper initialization of the recorder."""
        # Set up mock for the MD5 hash used in collection name
        mock_md5_instance = MagicMock()
        mock_md5_instance.hexdigest.return_value = "abcdef1234567890"
        mock_md5.return_value = mock_md5_instance

        # Create recorder with mock collector
        recorder = NtfsStorageActivityRecorder(
            collector=self.mock_collector,
            no_db=True,  # Don't try to connect to a real DB
        )

        # Verify UUID-based collection name is used
        recorder_id = uuid.UUID("9b3a7e8c-6d2f-4e91-8b5a-f3c7d2e1a0b9")
        expected_hash = mock_md5_instance.hexdigest.return_value[:8]
        expected_collection_name = f"NtfsStorageActivity_{expected_hash}"

        assert recorder._collection_name == expected_collection_name
        assert recorder._recorder_id == recorder_id

        # Verify service registration was attempted
        mock_register.assert_called_once()

    @patch("activity.recorders.storage.base.StorageActivityRecorder._connect_to_db")
    @patch(
        "activity.recorders.storage.base.StorageActivityRecorder._register_with_activity_service",
    )
    def test_collect_and_store_activities(self, mock_register, mock_connect):
        """Test collecting and storing activities."""
        # Create recorder with mock collector
        recorder = NtfsStorageActivityRecorder(
            collector=self.mock_collector,
            no_db=True,  # Don't try to connect to a real DB
        )

        # Mock the store_activities method
        recorder.store_activities = MagicMock()
        recorder.store_activities.return_value = [uuid.uuid4() for _ in range(5)]

        # Call collect_and_store_activities
        activity_ids = recorder.collect_and_store_activities(start_monitoring=True)

        # Verify collector was started
        self.mock_collector.start_monitoring.assert_called_once()

        # Verify activities were fetched
        self.mock_collector.get_activities.assert_called_once()

        # Verify activities were stored
        recorder.store_activities.assert_called_once_with(self.mock_activities)

        # Verify correct number of activity IDs returned
        assert len(activity_ids) == 5

    @patch("activity.recorders.storage.base.StorageActivityRecorder._connect_to_db")
    @patch(
        "activity.recorders.storage.base.StorageActivityRecorder._register_with_activity_service",
    )
    def test_build_ntfs_activity_document(self, mock_register, mock_connect):
        """Test building an NTFS activity document with semantic attributes."""
        # Create recorder with mock collector
        recorder = NtfsStorageActivityRecorder(
            collector=self.mock_collector,
            no_db=True,  # Don't try to connect to a real DB
        )

        # Create a test activity
        test_activity = NtfsStorageActivityData(
            timestamp=datetime.now(UTC),
            file_reference_number="12345",
            parent_file_reference_number="6789",
            activity_type=StorageActivityType.MODIFY,
            reason_flags=1,
            file_name="test_doc.docx",
            file_path="C:\\Users\\Test\\Documents\\test_doc.docx",
            volume_name="C:",
            is_directory=False,
            provider_type=StorageProviderType.LOCAL_NTFS,
            provider_id=self.mock_collector._provider_id,
            item_type=StorageItemType.FILE,
        )

        # Build document
        with patch(
            "activity.recorders.storage.ntfs.ntfs_recorder.get_semantic_attributes_for_activity",
        ) as mock_get_attr:
            # Mock semantic attributes
            mock_get_attr.return_value = []

            # Build document
            document = recorder._build_ntfs_activity_document(test_activity)

            # Verify document structure
            assert "Record" in document
            assert "Data" in document["Record"]
            assert "timestamp" in document["Record"]["Data"]
            assert "file_name" in document["Record"]["Data"]
            assert "file_path" in document["Record"]["Data"]

            # Verify semantic attributes were added
            assert "SemanticAttributes" in document

            # Verify NTFS-specific attribute was added
            ntfs_attr_found = False
            for attr in document["SemanticAttributes"]:
                if "STORAGE_NTFS" in attr.get("Label", ""):
                    ntfs_attr_found = True
                    break

            assert ntfs_attr_found

    @patch("activity.recorders.storage.base.StorageActivityRecorder._connect_to_db")
    @patch(
        "activity.recorders.storage.base.StorageActivityRecorder._register_with_activity_service",
    )
    def test_timezone_aware_datetime_handling(self, mock_register, mock_connect):
        """Test proper handling of timezone-aware datetimes."""
        # Create recorder with mock collector
        recorder = NtfsStorageActivityRecorder(
            collector=self.mock_collector,
            no_db=True,  # Don't try to connect to a real DB
        )

        # Create a test activity with naive datetime
        naive_datetime = datetime.now()
        test_activity = NtfsStorageActivityData(
            timestamp=naive_datetime,  # Naive datetime without timezone
            file_reference_number="12345",
            parent_file_reference_number="6789",
            activity_type=StorageActivityType.MODIFY,
            reason_flags=1,
            file_name="test_doc.docx",
            file_path="C:\\Users\\Test\\Documents\\test_doc.docx",
            volume_name="C:",
            is_directory=False,
            provider_type=StorageProviderType.LOCAL_NTFS,
            provider_id=self.mock_collector._provider_id,
            item_type=StorageItemType.FILE,
        )

        # Verify timezone is added during validation
        assert test_activity.timestamp.tzinfo is not None

        # Build document
        with patch(
            "activity.recorders.storage.ntfs.ntfs_recorder.get_semantic_attributes_for_activity",
        ):
            document = recorder._build_ntfs_activity_document(test_activity)

            # Verify timestamp in document has timezone info
            doc_timestamp = document["Record"]["Data"]["timestamp"]
            assert isinstance(doc_timestamp, datetime)
            assert doc_timestamp.tzinfo is not None

    @patch("activity.recorders.storage.base.StorageActivityRecorder._connect_to_db")
    @patch(
        "activity.recorders.storage.base.StorageActivityRecorder._register_with_activity_service",
    )
    def test_no_db_mode(self, mock_register, mock_connect):
        """Test recorder operation in no_db mode."""
        # Create recorder with no_db=True
        NtfsStorageActivityRecorder(
            collector=self.mock_collector,
            no_db=True,
        )

        # Verify database connection was not attempted
        mock_connect.assert_not_called()

        # Verify activity service registration was still attempted
        mock_register.assert_called_once()

    @patch("activity.recorders.storage.base.StorageActivityRecorder._connect_to_db")
    @patch(
        "activity.recorders.storage.base.StorageActivityRecorder._register_with_activity_service",
    )
    def test_get_recorder_characteristics(self, mock_register, mock_connect):
        """Test getting recorder characteristics."""
        # Create recorder with mock collector
        recorder = NtfsStorageActivityRecorder(
            collector=self.mock_collector,
            no_db=True,
        )

        # Get characteristics
        characteristics = recorder.get_recorder_characteristics()

        # Verify characteristics
        assert any("ACTIVITY_DATA_SYSTEM_ACTIVITY" in str(char) for char in characteristics)
        assert any("ACTIVITY_DATA_FILE_ACTIVITY" in str(char) for char in characteristics)
        assert any("ACTIVITY_DATA_WINDOWS_SPECIFIC" in str(char) for char in characteristics)

    @patch("activity.recorders.storage.base.StorageActivityRecorder._connect_to_db")
    @patch(
        "activity.recorders.storage.base.StorageActivityRecorder._register_with_activity_service",
    )
    @patch("activity.recorders.storage.ntfs.ntfs_recorder.NtfsStorageActivityCollector")
    def test_fallback_collector_creation(
        self,
        mock_collector_class,
        mock_register,
        mock_connect,
    ):
        """Test fallback collector creation when primary creation fails."""
        # Make the primary collector creation fail
        mock_collector_class.side_effect = [RuntimeError("Test error"), MagicMock()]

        # Create recorder without passing a collector
        recorder = NtfsStorageActivityRecorder(no_db=True)

        # Verify collector class was called twice (first fails, second succeeds)
        assert mock_collector_class.call_count == 2

        # Verify we have a collector
        assert recorder._ntfs_collector is not None


def main():
    """Run the test suite."""
    unittest.main()


if __name__ == "__main__":
    main()
