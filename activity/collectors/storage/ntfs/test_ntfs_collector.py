"""
Test script for the NTFS Storage Activity Collector.

This module tests the NTFS Storage Activity Collector's functionality,
focusing on volume GUID mapping, error handling, and mock data generation.

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
import time
import unittest
from datetime import datetime
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

    # pylint: enable=wrong-import-position
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error("This test module requires specific Python packages.")
    sys.exit(1)


class TestNtfsStorageActivityCollector(unittest.TestCase):
    """Tests for the NTFS Storage Activity Collector."""

    def setUp(self):
        """Set up test environment."""
        # Create a mock machine config for testing volume GUID mapping
        self.mock_machine_config = MagicMock()
        self.mock_machine_config.map_drive_letter_to_volume_guid = MagicMock(
            return_value="12345678-1234-1234-1234-123456789abc",
        )

    def test_init_with_mock_mode(self):
        """Test initialization with mock mode."""
        # Force mock mode and Windows availability to True for test
        with patch(
            "activity.collectors.storage.ntfs.ntfs_collector.WINDOWS_AVAILABLE",
            True,
        ):
            collector = NtfsStorageActivityCollector(
                mock=True,
                volumes=["C:"],
                debug=True,
            )

        self.assertTrue(collector._use_mock)
        self.assertEqual(collector._volumes, ["C:"])
        self.assertTrue(
            collector._use_volume_guids,
        )  # Volume GUIDs should be the default

    def test_init_with_disabled_volume_guids(self):
        """Test initialization with volume GUIDs explicitly disabled."""
        # Force Windows availability to True for test
        with patch(
            "activity.collectors.storage.ntfs.ntfs_collector.WINDOWS_AVAILABLE",
            True,
        ):
            collector = NtfsStorageActivityCollector(
                mock=True,
                volumes=["C:"],
                use_volume_guids=False,
            )

            self.assertFalse(collector._use_volume_guids)

    def test_volume_guid_mapping(self):
        """Test mapping drive letters to volume GUIDs."""
        # Force Windows availability to True for test
        with patch(
            "activity.collectors.storage.ntfs.ntfs_collector.WINDOWS_AVAILABLE",
            True,
        ):
            collector = NtfsStorageActivityCollector(
                mock=True,
                volumes=["C:"],
                machine_config=self.mock_machine_config,
            )

        # Test mapping with the mock machine config
        guid = collector.map_drive_letter_to_volume_guid("C")
        self.assertEqual(guid, "12345678-1234-1234-1234-123456789abc")

        # Test that results are cached
        self.mock_machine_config.map_drive_letter_to_volume_guid.assert_called_once_with(
            "C",
        )

        # Call again to verify cache is used
        guid = collector.map_drive_letter_to_volume_guid("C")
        self.assertEqual(guid, "12345678-1234-1234-1234-123456789abc")

        # Should still be called only once because we're using the cache
        self.mock_machine_config.map_drive_letter_to_volume_guid.assert_called_once()

    def test_get_volume_guid_path(self):
        """Test getting a volume GUID path from a drive letter."""
        # Force Windows availability to True for test
        with patch(
            "activity.collectors.storage.ntfs.ntfs_collector.WINDOWS_AVAILABLE",
            True,
        ):
            collector = NtfsStorageActivityCollector(
                mock=True,
                volumes=["C:"],
                machine_config=self.mock_machine_config,
            )

        # Test with a drive letter
        path = collector.get_volume_guid_path("C:")
        self.assertEqual(path, "\\\\?\\Volume{12345678-1234-1234-1234-123456789abc}\\")

        # Test with a volume GUID path already
        existing_guid_path = "\\\\?\\Volume{ABCDEF12-1234-5678-9ABC-DEF123456789}\\"
        path = collector.get_volume_guid_path(existing_guid_path)
        self.assertEqual(path, existing_guid_path)

        # Test with volume GUIDs disabled
        collector._use_volume_guids = False
        path = collector.get_volume_guid_path("D:")
        self.assertEqual(path, "\\\\?\\D:\\")

    def test_fallback_to_drive_letter(self):
        """Test fallback to drive letter when volume GUID mapping fails."""
        # Create a collector with a machine config that raises an exception
        self.mock_machine_config.map_drive_letter_to_volume_guid.side_effect = Exception("Mapping failed")

        # Force Windows availability to True for test
        with patch(
            "activity.collectors.storage.ntfs.ntfs_collector.WINDOWS_AVAILABLE",
            True,
        ):
            collector = NtfsStorageActivityCollector(
                mock=True,
                volumes=["C:"],
                machine_config=self.mock_machine_config,
            )

        # Get volume GUID path should fall back to drive letter format
        path = collector.get_volume_guid_path("C:")
        self.assertEqual(path, "\\\\?\\C:\\")

    def test_mock_data_generation(self):
        """Test mock data generation when on non-Windows platforms."""
        with patch(
            "activity.collectors.storage.ntfs.ntfs_collector.WINDOWS_AVAILABLE",
            False,
        ):
            collector = NtfsStorageActivityCollector(volumes=["C:"], auto_start=True)

            # Let it generate some activities
            time.sleep(6)

            # Get the activities
            activities = collector.get_activities()

            # Should have generated some activities
            self.assertGreater(len(activities), 0)

            # Check activity properties
            for activity in activities:
                self.assertIsInstance(activity, NtfsStorageActivityData)
                self.assertIsNotNone(activity.timestamp)
                self.assertIsNotNone(activity.file_path)
                self.assertIsNotNone(activity.activity_type)

                # Verify timezone awareness
                self.assertIsNotNone(activity.timestamp.tzinfo)

            # Stop monitoring
            collector.stop_monitoring()

    def test_usn_journal_monitoring_mock(self):
        """Test USN journal monitoring in mock mode."""
        collector = NtfsStorageActivityCollector(
            mock=True,
            volumes=["C:"],
            auto_start=False,
        )

        # Start monitoring
        collector.start_monitoring()

        # Let it generate some activities
        time.sleep(3)

        # Get the activities
        activities = collector.get_activities()

        # Should have generated some activities
        self.assertGreater(len(activities), 0)

        # Verify activity properties
        for activity in activities:
            # Verify proper provider ID
            self.assertEqual(activity.provider_id, collector._provider_id)

            # Verify proper provider type
            self.assertEqual(activity.provider_type, StorageProviderType.LOCAL_NTFS)

            # Verify timestamp has timezone
            self.assertIsNotNone(activity.timestamp.tzinfo)

        # Stop monitoring
        collector.stop_monitoring()

    def test_error_handling_volume_opening(self):
        """Test error handling when opening volumes."""
        with patch(
            "activity.collectors.storage.ntfs.ntfs_collector.win32file.CreateFile",
            side_effect=Exception("Failed to open volume"),
        ):

            collector = NtfsStorageActivityCollector(
                mock=False,
                volumes=["C:"],
                auto_start=True,  # Not in mock mode
            )

            # Should have fallen back to mock data generation
            self.assertIsNone(collector._volume_handles.get("C:"))

            # Let it generate some activities
            time.sleep(3)

            # Get the activities (should have some mock data)
            activities = collector.get_activities()

            # Should have generated some activities despite the error
            self.assertGreater(len(activities), 0)

            # Stop monitoring
            collector.stop_monitoring()

    def test_stopping_monitoring(self):
        """Test that monitoring can be stopped correctly."""
        # Force Windows availability to True for test
        with patch(
            "activity.collectors.storage.ntfs.ntfs_collector.WINDOWS_AVAILABLE",
            True,
        ):
            collector = NtfsStorageActivityCollector(
                mock=True,
                volumes=["C:"],
                auto_start=True,
            )

        # Let it generate some activities
        time.sleep(2)

        # Verify monitoring is active
        self.assertTrue(collector._active)

        # Stop monitoring
        collector.stop_monitoring()

        # Verify monitoring is inactive
        self.assertFalse(collector._active)

        # Get activities collected before stopping
        activities_before = len(collector.get_activities())

        # Wait a bit
        time.sleep(2)

        # Get activities after waiting
        activities_after = len(collector.get_activities())

        # Should be the same count (no new activities after stopping)
        self.assertEqual(activities_before, activities_after)

    def test_timezone_aware_timestamps(self):
        """Test that all timestamps have timezone information."""
        # Force Windows availability to True for test
        with patch(
            "activity.collectors.storage.ntfs.ntfs_collector.WINDOWS_AVAILABLE",
            True,
        ):
            collector = NtfsStorageActivityCollector(
                mock=True,
                volumes=["C:"],
                auto_start=True,
            )

        # Let it generate some activities
        time.sleep(2)

        # Get the activities
        activities = collector.get_activities()

        # Verify all timestamps have timezone info
        for activity in activities:
            self.assertIsNotNone(activity.timestamp.tzinfo)

        # Create an activity with naive datetime
        naive_timestamp = datetime.now()  # No timezone

        # Add it to the collector
        activity_data = NtfsStorageActivityData(
            timestamp=naive_timestamp,
            file_reference_number="1234",
            parent_file_reference_number="5678",
            activity_type=StorageActivityType.CREATE,
            reason_flags=1,
            file_name="test.txt",
            file_path="C:\\test.txt",
            volume_name="C:",
            is_directory=False,
            provider_type=StorageProviderType.LOCAL_NTFS,
            provider_id=collector._provider_id,
            item_type=StorageItemType.FILE,
        )

        # Add the activity
        collector.add_activity(activity_data)

        # Get the activities again
        activities = collector.get_activities()

        # Find our test activity
        test_activity = None
        for activity in activities:
            if activity.file_name == "test.txt":
                test_activity = activity
                break

        # Verify the naive timestamp was converted to have timezone info
        self.assertIsNotNone(test_activity)
        self.assertIsNotNone(test_activity.timestamp.tzinfo)

        # Stop monitoring
        collector.stop_monitoring()


def main():
    """Run the test suite."""
    unittest.main()


if __name__ == "__main__":
    main()
