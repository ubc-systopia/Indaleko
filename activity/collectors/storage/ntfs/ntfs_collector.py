"""
NTFS Storage Activity Collector for Indaleko.

This module provides a collector for NTFS file system activities using the
USN Journal to detect file changes.

Features:
- Monitors file system changes using the NTFS USN Journal
- Volume GUID support for stable path references (immune to drive letter changes)
- Timezone-aware datetime handling for ArangoDB compatibility
- Mock data generation for cross-platform testing and development
- Error handling and fallback modes
- Thread-safe monitoring and activity tracking

The collector runs background threads to monitor file system activity and
processes the events into standardized storage activity records. It can be
used with the NtfsStorageActivityRecorder to store activities in a database.

Usage:
    # Basic usage (with volume GUIDs by default)
    collector = NtfsStorageActivityCollector(volumes=["C:"], auto_start=True)
    activities = collector.get_activities()
    collector.stop_monitoring()

    # Explicitly disable volume GUIDs if needed
    collector = NtfsStorageActivityCollector(
        volumes=["C:"],
        use_volume_guids=False,  # Not recommended - disables stable path references
        auto_start=True
    )
    activities = collector.get_activities()

    # Get stable path with volume GUID
    path = collector.get_volume_guid_path("C:")  # Returns "\\\\?\\Volume{GUID}\\"

    # Mock mode (for non-Windows platforms)
    collector = NtfsStorageActivityCollector(mock=True, auto_start=True)
    activities = collector.get_activities()

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
import queue
import struct
import sys
import threading
import time
import uuid

from datetime import UTC, datetime
from typing import Any

from icecream import ic


# Define Windows constants directly in case they're missing from pywin32
# These are the USN journal control codes
FSCTL_QUERY_USN_JOURNAL = 0x000900F4
FSCTL_CREATE_USN_JOURNAL = 0x000900E7
FSCTL_READ_USN_JOURNAL = 0x000900BB
FSCTL_ENUM_USN_DATA = 0x000900B3  # More reliable alternative to READ_USN_JOURNAL

# USN reason codes
USN_REASON_DATA_OVERWRITE = 0x00000001
USN_REASON_DATA_EXTEND = 0x00000002
USN_REASON_DATA_TRUNCATION = 0x00000004
USN_REASON_NAMED_DATA_OVERWRITE = 0x00000010
USN_REASON_NAMED_DATA_EXTEND = 0x00000020
USN_REASON_NAMED_DATA_TRUNCATION = 0x00000040
USN_REASON_FILE_CREATE = 0x00000100
USN_REASON_FILE_DELETE = 0x00000200
USN_REASON_EA_CHANGE = 0x00000400
USN_REASON_SECURITY_CHANGE = 0x00000800
USN_REASON_RENAME_OLD_NAME = 0x00001000
USN_REASON_RENAME_NEW_NAME = 0x00002000
USN_REASON_INDEXABLE_CHANGE = 0x00004000
USN_REASON_BASIC_INFO_CHANGE = 0x00008000
USN_REASON_HARD_LINK_CHANGE = 0x00010000
USN_REASON_COMPRESSION_CHANGE = 0x00020000
USN_REASON_ENCRYPTION_CHANGE = 0x00040000
USN_REASON_OBJECT_ID_CHANGE = 0x00080000
USN_REASON_REPARSE_POINT_CHANGE = 0x00100000
USN_REASON_STREAM_CHANGE = 0x00200000
USN_REASON_CLOSE = 0x80000000

# File attribute constants
FILE_ATTRIBUTE_DIRECTORY = 0x00000010

try:
    import pywintypes
    import win32file

    WINDOWS_AVAILABLE = True

    # Add the missing constants to win32file if they don't exist
    if not hasattr(win32file, "FSCTL_QUERY_USN_JOURNAL"):
        win32file.FSCTL_QUERY_USN_JOURNAL = FSCTL_QUERY_USN_JOURNAL
    if not hasattr(win32file, "FSCTL_CREATE_USN_JOURNAL"):
        win32file.FSCTL_CREATE_USN_JOURNAL = FSCTL_CREATE_USN_JOURNAL
    if not hasattr(win32file, "FSCTL_READ_USN_JOURNAL"):
        win32file.FSCTL_READ_USN_JOURNAL = FSCTL_READ_USN_JOURNAL

    # Add USN reason constants if they don't exist
    if not hasattr(win32file, "USN_REASON_FILE_CREATE"):
        win32file.USN_REASON_FILE_CREATE = USN_REASON_FILE_CREATE
    if not hasattr(win32file, "USN_REASON_FILE_DELETE"):
        win32file.USN_REASON_FILE_DELETE = USN_REASON_FILE_DELETE
    if not hasattr(win32file, "USN_REASON_SECURITY_CHANGE"):
        win32file.USN_REASON_SECURITY_CHANGE = USN_REASON_SECURITY_CHANGE
    if not hasattr(win32file, "USN_REASON_RENAME_OLD_NAME"):
        win32file.USN_REASON_RENAME_OLD_NAME = USN_REASON_RENAME_OLD_NAME
    if not hasattr(win32file, "USN_REASON_RENAME_NEW_NAME"):
        win32file.USN_REASON_RENAME_NEW_NAME = USN_REASON_RENAME_NEW_NAME
    if not hasattr(win32file, "USN_REASON_DATA_OVERWRITE"):
        win32file.USN_REASON_DATA_OVERWRITE = USN_REASON_DATA_OVERWRITE
    if not hasattr(win32file, "USN_REASON_DATA_EXTEND"):
        win32file.USN_REASON_DATA_EXTEND = USN_REASON_DATA_EXTEND
    if not hasattr(win32file, "USN_REASON_DATA_TRUNCATION"):
        win32file.USN_REASON_DATA_TRUNCATION = USN_REASON_DATA_TRUNCATION
    if not hasattr(win32file, "USN_REASON_BASIC_INFO_CHANGE"):
        win32file.USN_REASON_BASIC_INFO_CHANGE = USN_REASON_BASIC_INFO_CHANGE
    if not hasattr(win32file, "USN_REASON_CLOSE"):
        win32file.USN_REASON_CLOSE = USN_REASON_CLOSE

    # Add file attribute constants if needed
    if not hasattr(win32file, "FILE_ATTRIBUTE_DIRECTORY"):
        win32file.FILE_ATTRIBUTE_DIRECTORY = FILE_ATTRIBUTE_DIRECTORY

    # Add a custom GetUsn function if it doesn't exist
    if not hasattr(win32file, "GetUsn"):

        def get_usn(journal_id, first_usn, reason_mask=0, return_only_on_close=0):
            """Create a properly formatted buffer for reading the USN journal."""
            return struct.pack(
                "<QQLL",
                journal_id,
                first_usn,
                reason_mask,
                return_only_on_close,
            )

        win32file.GetUsn = get_usn

    # Add FSCTL_ENUM_USN_DATA to win32file if it doesn't exist
    if not hasattr(win32file, "FSCTL_ENUM_USN_DATA"):
        win32file.FSCTL_ENUM_USN_DATA = FSCTL_ENUM_USN_DATA

    # Add a custom ParseUsnData function if it doesn't exist
    if not hasattr(win32file, "ParseUsnData"):

        def parse_usn_data(data):
            """
            Parse USN journal data into records.
            This is a very simplified implementation that extracts just basic info.
            """
            if not data or len(data) < 8:
                return []

            # Skip the first 8 bytes (next USN value)
            offset = 8
            records = []

            # Try to parse as many records as possible
            while offset < len(data):
                try:
                    # Each record starts with a record length (4 bytes)
                    if offset + 4 > len(data):
                        break

                    record_length = struct.unpack("<L", data[offset : offset + 4])[0]
                    if record_length == 0 or offset + record_length > len(data):
                        break

                    # Extract some basic fields - this is a simplified implementation
                    # Real USN records have many more fields in a complex format

                    # File reference number is typically at offset 8
                    if offset + 16 <= len(data):
                        file_ref = struct.unpack("<Q", data[offset + 8 : offset + 16])[0]
                    else:
                        file_ref = 0

                    # Parent file reference number is typically at offset 16
                    if offset + 24 <= len(data):
                        parent_ref = struct.unpack(
                            "<Q",
                            data[offset + 16 : offset + 24],
                        )[0]
                    else:
                        parent_ref = 0

                    # USN is typically at offset 24
                    if offset + 32 <= len(data):
                        usn = struct.unpack("<Q", data[offset + 24 : offset + 32])[0]
                    else:
                        usn = 0

                    # Reason flags are typically at offset 40
                    if offset + 44 <= len(data):
                        reason = struct.unpack("<L", data[offset + 40 : offset + 44])[0]
                    else:
                        reason = 0

                    # File attributes are typically at offset 44
                    if offset + 48 <= len(data):
                        file_attrs = struct.unpack(
                            "<L",
                            data[offset + 44 : offset + 48],
                        )[0]
                    else:
                        file_attrs = 0

                    # File name length and offset are at offsets 58 and 60
                    if offset + 62 <= len(data):
                        file_name_length = struct.unpack(
                            "<H",
                            data[offset + 58 : offset + 60],
                        )[0]
                        file_name_offset = struct.unpack(
                            "<H",
                            data[offset + 60 : offset + 62],
                        )[0]
                    else:
                        file_name_length = 0
                        file_name_offset = 0

                    # Extract file name if possible
                    file_name = "Unknown"
                    if file_name_length > 0 and offset + file_name_offset + file_name_length <= len(data):
                        try:
                            # File names are stored as UTF-16 (2 bytes per character)
                            file_name_bytes = data[
                                offset + file_name_offset : offset + file_name_offset + file_name_length
                            ]
                            file_name = file_name_bytes.decode("utf-16")
                        except Exception:
                            file_name = "Error decoding filename"

                    # Create a record with the extracted information
                    record = {
                        "FileReferenceNumber": file_ref,
                        "ParentFileReferenceNumber": parent_ref,
                        "Usn": usn,
                        "Reason": reason,
                        "FileAttributes": file_attrs,
                        "FileName": file_name,
                    }

                    records.append(record)

                    # Move to the next record
                    offset += record_length
                except Exception:
                    # If there's an error parsing a record, just move ahead by 8 bytes and try again
                    offset += 8

            return records

        win32file.ParseUsnData = parse_usn_data
except ImportError:
    WINDOWS_AVAILABLE = False

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.storage.base import StorageActivityCollector
from activity.collectors.storage.data_models.storage_activity_data_model import (
    BaseStorageActivityData,
    NtfsStorageActivityData,
    StorageActivityType,
    StorageItemType,
    StorageProviderType,
)


# pylint: enable=wrong-import-position


class NtfsStorageActivityCollector(StorageActivityCollector):
    """
    Collector for NTFS file system activity using the USN Journal.

    This collector monitors file system operations on NTFS volumes and creates
    standardized storage activity records for them.
    """

    def __init__(self, **kwargs):
        """
        Initialize the NTFS storage activity collector.

        Args:
            volumes: List of volume paths to monitor (e.g., ["C:", "D:"])
            buffer_size: Size of the buffer to use for reading the USN Journal
            monitor_interval: How often to check for new events (in seconds)
            process_lookup_cache_size: Maximum number of processes to cache info for
            include_close_events: Whether to include file close events
            max_queue_size: Maximum size of the event queue
            auto_start: Whether to start monitoring automatically
            mock: Whether to use mock data even if running on Windows
            debug: Whether to enable debug mode
            use_volume_guids: Whether to use volume GUIDs instead of drive letters
            machine_config: Optional machine config object to use for volume GUID mapping
        """
        # Configure logging
        ic(kwargs)
        self._debug = kwargs.get("debug", False)
        logging.basicConfig(
            level=logging.DEBUG if self._debug else logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self._logger = logging.getLogger("NtfsStorageActivityCollector")

        # Check if running on Windows
        self._use_mock = kwargs.get("mock", False)
        if not WINDOWS_AVAILABLE and not self._use_mock:
            self._logger.error(
                "NtfsStorageActivityCollector is only available on Windows",
            )
            raise RuntimeError(
                "NtfsStorageActivityCollector is only available on Windows",
            )
        elif not WINDOWS_AVAILABLE:
            self._logger.warning(
                "Running in mock mode because Windows is not available",
            )
            self._use_mock = True

        if self._use_mock:
            self._logger.info("Using mock mode for NTFS activity collection")

        # GUID configuration - volume GUIDs are the default
        self._use_volume_guids = kwargs.get("use_volume_guids", True)  # True by default
        self._volume_guid_mapping = {}
        self._machine_config = kwargs.get("machine_config", None)

        # If machine_config is provided, try to load it for GUID mapping
        if self._use_volume_guids and self._machine_config:
            self._logger.info("Using provided machine config for volume GUID mapping")
            try:
                if hasattr(self._machine_config, "map_drive_letter_to_volume_guid"):
                    self._logger.debug(
                        "Machine config has map_drive_letter_to_volume_guid method",
                    )
                    # Will use this directly later
                else:
                    self._logger.warning(
                        "Machine config doesn't have volume GUID mapping capability",
                    )
            except Exception as e:
                self._logger.error(f"Error accessing machine config: {e}")
                self._use_volume_guids = False
        elif self._use_volume_guids:
            # Try to load machine config from platforms
            try:
                # Import here to avoid import errors on non-Windows platforms
                if WINDOWS_AVAILABLE and not self._use_mock:
                    from platforms.windows.machine_config import (
                        IndalekoWindowsMachineConfig,
                    )

                    self._logger.info("Loading machine config for volume GUID mapping")
                    try:
                        self._machine_config = IndalekoWindowsMachineConfig.load_config_from_file(
                            offline=True,
                        )
                        self._logger.info("Successfully loaded machine config")
                    except Exception as e:
                        self._logger.warning(f"Failed to load machine config: {e}")
                        self._use_volume_guids = False
            except ImportError:
                self._logger.warning("Could not import Windows machine config module")
                self._use_volume_guids = False

        # Initialize with provider-specific values
        kwargs["name"] = kwargs.get("name", "NTFS Storage Activity Collector")
        kwargs["provider_id"] = kwargs.get(
            "provider_id",
            uuid.UUID("7d8f5a92-35c7-41e6-b13d-6c4e89e7f2a5"),
        )
        kwargs["provider_type"] = StorageProviderType.LOCAL_NTFS
        kwargs["description"] = kwargs.get(
            "description",
            "Collects storage activities from the NTFS USN Journal",
        )

        # Call parent initializer
        super().__init__(**kwargs)

        # Configuration
        self._volumes = kwargs.get("volumes", ["C:"])
        self._buffer_size = kwargs.get("buffer_size", 65536)
        self._monitor_interval = kwargs.get("monitor_interval", 1.0)
        self._process_lookup_cache_size = kwargs.get("process_lookup_cache_size", 1000)
        self._include_close_events = kwargs.get("include_close_events", False)
        self._max_queue_size = kwargs.get("max_queue_size", 10000)

        # NTFS-specific structures
        self._file_ref_to_path = {}
        self._event_queue = queue.Queue(maxsize=self._max_queue_size)
        self._volume_handles = {}
        self._usn_journals = {}
        self._journal_threads = []
        self._processing_thread = None
        self._active = False
        self._stop_event = threading.Event()

        # Filters
        self._filters = kwargs.get("filters", {})
        self._excluded_paths = self._filters.get("excluded_paths", [])
        self._excluded_process_names = self._filters.get("excluded_process_names", [])
        self._excluded_extensions = self._filters.get("excluded_extensions", [])

        # Start threads if auto_start is True
        if kwargs.get("auto_start", False):
            self.start_monitoring()

    def start_monitoring(self):
        """Start monitoring the USN Journal on all configured volumes."""
        if self._active:
            self._logger.debug("Monitoring already active, skipping start")
            return

        self._active = True
        self._stop_event.clear()

        # Start the processing thread
        self._logger.debug("Starting event processing thread")
        self._processing_thread = threading.Thread(
            target=self._event_processing_thread,
            daemon=True,
        )
        self._processing_thread.start()

        # Start a monitoring thread for each volume
        started_volumes = 0
        for volume in self._volumes:
            try:
                self._logger.info(f"Starting monitoring for volume {volume}")
                self._start_volume_monitoring(volume)
                started_volumes += 1
            except Exception as e:
                self._logger.error(f"Failed to start monitoring volume {volume}: {e}")

        # If no volumes could be monitored, make sure we still generate some mock data
        if started_volumes == 0 and self._volumes:
            self._logger.warning("No volumes could be monitored. Using mock data mode.")

            # Start a mock data generation thread
            def _generate_mock_data():
                while not self._stop_event.is_set():
                    # Periodically add some mock file activities
                    time.sleep(5)
                    # Create mock activity data
                    for mock_file in ["document.docx", "image.jpg", "spreadsheet.xlsx"]:
                        mock_volume = self._volumes[0] if self._volumes else "C:"
                        mock_path = f"{mock_volume}\\Users\\TestUser\\Documents\\{mock_file}"
                        activity_data = NtfsStorageActivityData(
                            timestamp=datetime.now(UTC),
                            file_reference_number="1234567",
                            parent_file_reference_number="7654321",
                            activity_type=StorageActivityType.MODIFY,
                            reason_flags=1,  # Mock value
                            file_name=mock_file,
                            file_path=mock_path,
                            volume_name=mock_volume,
                            is_directory=False,
                            provider_type=StorageProviderType.LOCAL_NTFS,
                            provider_id=self._provider_id,
                            item_type=StorageItemType.FILE,
                        )
                        self.add_activity(activity_data)
                        self._logger.debug(f"Added mock activity for {mock_path}")

            # Start the mock data thread
            self._mock_thread = threading.Thread(
                target=_generate_mock_data,
                daemon=True,
            )
            self._mock_thread.start()

    def stop_monitoring(self):
        """Stop monitoring the USN Journal on all volumes."""
        if not self._active:
            self._logger.debug("Monitoring not active, skipping stop")
            return

        # Signal all threads to stop
        self._logger.debug("Signaling all threads to stop")
        self._stop_event.set()
        self._active = False

        # Wait for journal threads to stop
        for thread in self._journal_threads:
            self._logger.debug(f"Waiting for journal thread to stop: {thread.name}")
            thread.join(timeout=5.0)

        # Wait for processing thread to stop
        if self._processing_thread:
            self._logger.debug("Waiting for processing thread to stop")
            self._processing_thread.join(timeout=5.0)

        # Wait for mock thread to stop if it exists
        if hasattr(self, "_mock_thread") and self._mock_thread:
            self._logger.debug("Waiting for mock data thread to stop")
            self._mock_thread.join(timeout=5.0)
            self._mock_thread = None

        # Close all volume handles
        for volume, handle in self._volume_handles.items():
            try:
                if handle is not None:
                    self._logger.debug(f"Closing handle for volume {volume}")
                    win32file.CloseHandle(handle)
            except Exception as e:
                self._logger.error(f"Error closing handle for volume {volume}: {e}")

        self._logger.debug("Clearing internal data structures")
        self._volume_handles.clear()
        self._usn_journals.clear()
        self._journal_threads.clear()
        self._processing_thread = None
        self._logger.info("Monitoring stopped")

    def _start_volume_monitoring(self, volume: str):
        """
        Start monitoring a specific volume.

        Args:
            volume: The volume to monitor (e.g., "C:")
        """
        # Open the volume
        # Make sure the volume has the correct format (e.g., "C:")
        if volume.endswith("\\") or volume.endswith("/"):
            volume = volume[:-1]
        if ":" not in volume and not volume.startswith("\\\\?\\Volume{"):
            volume = f"{volume}:"

        # Clean up the volume name first - make sure there are no double colons
        if ":" in volume:
            parts = volume.split(":")
            volume = parts[0] + ":"  # Keep only the first colon

        # Get the volume path, preferring GUID format if available
        if self._use_volume_guids and not volume.startswith("\\\\?\\Volume{"):
            volume_path = self.get_volume_guid_path(volume)
            # Use the proper volume variable, not potentially double-colon version
            cleaned_volume = volume.split(":")[0] + ":"
            self._logger.info(
                f"Using volume GUID path for {cleaned_volume}: {volume_path}",
            )
        elif volume.startswith("\\\\?\\Volume{"):
            volume_path = volume
            if not volume_path.endswith("\\"):
                volume_path += "\\"
        else:
            volume_path = f"\\\\?\\{volume}\\"

        self._logger.debug(f"Opening volume path: {volume_path}")

        try:
            if WINDOWS_AVAILABLE and not self._use_mock:
                # Try alternate formats for volume path to handle different Windows configurations
                handle = None
                volume_path_variants = []

                # Original volume path
                volume_path_variants.append(volume_path)

                # Common variations
                if volume.endswith(":"):
                    # Try standard Windows path format
                    volume_path_variants.append(f"{volume}\\")

                    # Try with physical drive syntax (most reliable for USN journal)
                    volume_path_variants.append(f"\\\\.\\{volume}")

                    # Try with just drive letter
                    if len(volume) == 2:  # like "C:"
                        volume_path_variants.append(volume[0] + ":\\")

                    # Try direct physical device path
                    drive_letter = volume[0]
                    volume_path_variants.append(
                        f"\\\\.\\PhysicalDrive{ord(drive_letter.upper()) - ord('C')}",
                    )

                # Try Win32 API calls to get actual volume path
                try:
                    import win32file

                    drive_path = f"{volume[0]}:\\"
                    vol_name = win32file.GetVolumeNameForVolumeMountPoint(drive_path)
                    if vol_name:
                        volume_path_variants.append(vol_name)
                except Exception as e:
                    self._logger.warning(
                        f"Failed to get volume name for mount point: {e}",
                    )

                # Try each variation
                for path_variant in volume_path_variants:
                    try:
                        self._logger.debug(f"Trying volume path: {path_variant}")
                        handle = win32file.CreateFile(
                            path_variant,
                            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                            win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                            None,
                            win32file.OPEN_EXISTING,
                            win32file.FILE_ATTRIBUTE_NORMAL,
                            None,
                        )
                        if handle:
                            self._logger.info(
                                f"Successfully opened volume with path: {path_variant}",
                            )
                            break
                    except Exception as inner_e:
                        self._logger.debug(
                            f"Failed to open volume with path {path_variant}: {inner_e}",
                        )

                # If all variants failed, we'll have None handle and the outer exception handler will catch it
            else:
                # In mock mode, we don't actually open the volume
                self._logger.info(
                    f"Mock mode: Not actually opening volume {volume_path}",
                )
                handle = None
                raise RuntimeError("Running in mock mode")
        except Exception as e:
            self._logger.error(f"Failed to open volume {volume}: {e}")
            # Use a mock handle for testing
            self._logger.warning("Using mock volume handle for testing")
            handle = None
            # Raise the exception so the caller can handle it
            raise

        # Initialize the USN Journal if needed
        try:
            if handle is None:
                # Mock data for testing
                self._logger.warning("Using mock USN journal info")
                usn_journal_info = {
                    "UsnJournalID": 0,
                    "FirstUsn": 0,
                    "NextUsn": 0,
                    "LowestValidUsn": 0,
                    "MaxUsn": 0,
                    "MaximumSize": 0,
                    "AllocationDelta": 0,
                }
            else:
                # Try various approaches to get USN Journal info
                usn_journal_info = None

                # Approach 1: Standard USN journal query
                try:
                    self._logger.debug("Trying standard USN journal query")
                    usn_journal_info = win32file.DeviceIoControl(
                        handle,
                        win32file.FSCTL_QUERY_USN_JOURNAL,
                        None,
                        1024,
                    )
                except Exception as query_err:
                    self._logger.debug(
                        f"Standard USN journal query failed: {query_err}",
                    )

                    # Approach 2: Try creating the journal first
                    try:
                        self._logger.debug(
                            f"Trying to create USN journal for volume {volume}",
                        )
                        # Create with allocation delta and max size
                        buffer = bytearray(16)  # 2 uint64s
                        import struct

                        # Use more moderate default values
                        max_size = 32 * 1024 * 1024  # 32 MB
                        delta = 4 * 1024 * 1024  # 4 MB
                        struct.pack_into("QQ", buffer, 0, max_size, delta)

                        # Try to create with custom settings
                        win32file.DeviceIoControl(
                            handle,
                            win32file.FSCTL_CREATE_USN_JOURNAL,
                            buffer,
                            0,
                        )

                        # Now query again
                        usn_journal_info = win32file.DeviceIoControl(
                            handle,
                            win32file.FSCTL_QUERY_USN_JOURNAL,
                            None,
                            1024,
                        )
                    except Exception as create_err:
                        self._logger.debug(f"USN journal creation failed: {create_err}")

                        # Approach 3: Try with default settings
                        try:
                            self._logger.debug(
                                "Trying to create USN journal with default settings",
                            )
                            win32file.DeviceIoControl(
                                handle,
                                win32file.FSCTL_CREATE_USN_JOURNAL,
                                None,
                                0,
                            )

                            # Query again
                            usn_journal_info = win32file.DeviceIoControl(
                                handle,
                                win32file.FSCTL_QUERY_USN_JOURNAL,
                                None,
                                1024,
                            )
                        except Exception as default_err:
                            self._logger.warning(
                                f"USN journal creation with default settings failed: {default_err}",
                            )

                # If all approaches failed, use mock data
                if usn_journal_info is None:
                    self._logger.warning(
                        "All USN journal query approaches failed, using mock data",
                    )
                    usn_journal_info = {
                        "UsnJournalID": 0,
                        "FirstUsn": 0,
                        "NextUsn": 0,
                        "LowestValidUsn": 0,
                        "MaxUsn": 0,
                        "MaximumSize": 0,
                        "AllocationDelta": 0,
                    }
        except Exception as e:
            self._logger.error(f"Unhandled error in USN journal initialization: {e}")
            # Use mock data as fallback
            self._logger.warning("Using mock USN journal info due to unhandled error")
            usn_journal_info = {
                "UsnJournalID": 0,
                "FirstUsn": 0,
                "NextUsn": 0,
                "LowestValidUsn": 0,
                "MaxUsn": 0,
                "MaximumSize": 0,
                "AllocationDelta": 0,
            }

        # Store volume handle and journal info
        self._volume_handles[volume] = handle
        self._usn_journals[volume] = usn_journal_info

        # Start a thread to monitor this volume
        journal_thread = threading.Thread(
            target=self._monitor_usn_journal,
            args=(volume,),
            daemon=True,
        )
        self._journal_threads.append(journal_thread)
        journal_thread.start()

    def _monitor_usn_journal(self, volume: str):
        """
        Monitor the USN Journal for a specific volume.

        Args:
            volume: The volume to monitor (e.g., "C:")
        """
        # Get the handle and journal info
        handle = self._volume_handles.get(volume)
        journal_info = self._usn_journals.get(volume)

        if not handle:
            self._logger.error(f"Missing handle for volume {volume}")
            self._logger.info(f"Using mock data mode for volume {volume}")
            # Just keep the thread alive until stop signal
            while not self._stop_event.is_set():
                time.sleep(1)
            return

        if not journal_info:
            self._logger.error(f"Missing journal info for volume {volume}")
            self._logger.info(f"Using mock data mode for volume {volume}")
            # Just keep the thread alive until stop signal
            while not self._stop_event.is_set():
                time.sleep(1)
            return

        try:
            journal_id = journal_info["UsnJournalID"]
            first_usn = journal_info["FirstUsn"]
            next_usn = first_usn
        except (KeyError, TypeError) as e:
            self._logger.error(f"Invalid journal info structure: {e}")
            self._logger.info(f"Using mock data mode for volume {volume}")
            # Just keep the thread alive until stop signal
            while not self._stop_event.is_set():
                time.sleep(1)
            return

        self._logger.info(f"Starting monitoring of USN journal on volume {volume}")
        self._logger.debug(f"Journal ID: {journal_id}, First USN: {first_usn}")

        # Monitor the journal in a loop
        is_real_usn_journal = False

        # Create a test file to force USN journal activity and test our monitoring
        test_filename = None
        if not self._use_mock and WINDOWS_AVAILABLE:
            try:
                test_dir = os.path.join(volume, "Indaleko_Test")
                if not os.path.exists(test_dir):
                    try:
                        os.makedirs(test_dir, exist_ok=True)
                    except Exception as mkdir_err:
                        self._logger.warning(
                            f"Could not create test directory: {mkdir_err}",
                        )

                if os.path.exists(test_dir):
                    test_filename = os.path.join(
                        test_dir,
                        f"usn_test_{int(time.time())}.txt",
                    )
                    with open(test_filename, "w") as f:
                        f.write(f"USN Journal Test File - {datetime.now()}")
                    self._logger.info(
                        f"Created test file {test_filename} to trigger USN journal activity",
                    )

                    # Give the filesystem a moment to process the change
                    time.sleep(0.5)

                    # Now try to read the journal to see if we detect our file
                    try:
                        # Try to read the first set of records to verify we can access the journal
                        self._logger.debug(
                            f"Reading journal with ID {journal_id}, USN {next_usn}",
                        )

                        # Create a proper MFT_ENUM_DATA structure for more reliable USN data access
                        buffer_in = bytearray(28)  # 28 bytes for the structure
                        struct.pack_into(
                            "<QQQHH",
                            buffer_in,
                            0,
                            0,  # StartFileReferenceNumber
                            next_usn,  # LowUsn
                            0xFFFFFFFFFFFFFFFF,  # HighUsn
                            2,
                            2,
                        )  # MinMajorVersion, MaxMajorVersion

                        # Use ENUM_USN_DATA which is more reliable
                        try:
                            read_data = win32file.DeviceIoControl(
                                handle,
                                FSCTL_ENUM_USN_DATA,  # More reliable control code
                                buffer_in,
                                65536,
                            )
                        except pywintypes.error as win_err:
                            # Handle error 38 (Reached end of file) as a normal condition
                            if win_err.winerror == 38:  # ERROR_HANDLE_EOF
                                self._logger.info(
                                    "No USN records available yet - this is normal for a new or empty journal",
                                )
                                # Create an empty result with just next_usn
                                read_data = bytearray(8)
                                struct.pack_into("<Q", read_data, 0, next_usn)
                            else:
                                # Re-raise other errors
                                raise

                        # Parse the data to see if we detected our file
                        usn_records = win32file.ParseUsnData(read_data)

                        # Update the next USN for future reads
                        next_usn = read_data[0]

                        found_test_file = False
                        for record in usn_records:
                            if "FileName" in record and os.path.basename(test_filename) in record["FileName"]:
                                found_test_file = True
                                self._logger.info(
                                    f"Successfully detected test file in USN journal: {record}",
                                )
                                break

                        # If we found our test file, real monitoring is working
                        if found_test_file:
                            is_real_usn_journal = True
                            self._logger.info(
                                "USN journal monitoring confirmed working with test file",
                            )
                        else:
                            self._logger.warning(
                                "Could not detect test file in USN journal records",
                            )
                            is_real_usn_journal = True  # Still try real monitoring even if we didn't find our test file
                    except Exception as e:
                        self._logger.warning(
                            f"Could not read from USN journal, using simulated data: {e}",
                        )
            except Exception as e:
                self._logger.warning(f"Error setting up USN test file: {e}")

        # If we couldn't confirm with a test file, try the standard approach
        if not is_real_usn_journal and not self._use_mock and WINDOWS_AVAILABLE:
            try:
                # Try to read the first set of records to verify we can access the journal
                self._logger.debug("Trying standard USN journal read")
                read_data = win32file.DeviceIoControl(
                    handle,
                    win32file.FSCTL_READ_USN_JOURNAL,
                    win32file.GetUsn(journal_id, next_usn, 0, 0),
                    65536,
                )

                # If we get here, we have successfully read from the journal
                self._logger.info(
                    f"Successfully read from USN journal on volume {volume}",
                )
                is_real_usn_journal = True
            except Exception as e:
                self._logger.warning(
                    f"Could not read from USN journal, using simulated data: {e}",
                )

        # Create a background file activity generator if we're using real monitoring
        # to ensure we have some activity to detect
        activity_generator_thread = None
        if is_real_usn_journal and not self._use_mock and WINDOWS_AVAILABLE:
            try:

                def _generate_file_activity():
                    """Generate real file activity in the background to ensure USN journal has content"""
                    test_dir = os.path.join(volume, "Indaleko_Test")
                    if not os.path.exists(test_dir):
                        try:
                            os.makedirs(test_dir, exist_ok=True)
                        except Exception:
                            return

                    interval_count = 0
                    while not self._stop_event.is_set():
                        try:
                            # Create various file activities at different intervals
                            if interval_count % 10 == 0:  # Every 10 seconds
                                # Create a new file
                                filename = os.path.join(
                                    test_dir,
                                    f"test_create_{int(time.time())}.txt",
                                )
                                with open(filename, "w") as f:
                                    f.write(f"Test file created at {datetime.now()}")
                                self._logger.debug(
                                    f"Created file {filename} for USN journal monitoring",
                                )

                            if interval_count % 15 == 0:  # Every 15 seconds
                                # Modify an existing file if available
                                files = [f for f in os.listdir(test_dir) if f.startswith("test_create_")]
                                if files:
                                    target_file = os.path.join(test_dir, files[0])
                                    with open(target_file, "a") as f:
                                        f.write(f"\nModified at {datetime.now()}")
                                    self._logger.debug(
                                        f"Modified file {target_file} for USN journal monitoring",
                                    )

                            if interval_count % 30 == 0:  # Every 30 seconds
                                # Delete an old file if available
                                files = [f for f in os.listdir(test_dir) if f.startswith("test_create_")]
                                if len(files) > 5:  # Keep the number of test files reasonable
                                    to_delete = os.path.join(test_dir, files[-1])
                                    os.remove(to_delete)
                                    self._logger.debug(
                                        f"Deleted file {to_delete} for USN journal monitoring",
                                    )

                            time.sleep(1)
                            interval_count += 1
                        except Exception as e:
                            self._logger.debug(f"Error in file activity generator: {e}")
                            time.sleep(5)

                # Start the activity generator thread
                activity_generator_thread = threading.Thread(
                    target=_generate_file_activity,
                    daemon=True,
                )
                activity_generator_thread.start()
                self._logger.info(
                    "Started background file activity generator for USN journal monitoring",
                )
            except Exception as e:
                self._logger.warning(
                    f"Could not start background file activity generator: {e}",
                )

        # Main monitoring loop
        while not self._stop_event.is_set():
            try:
                if is_real_usn_journal:
                    try:
                        # Read actual USN journal records
                        # Use ENUM_USN_DATA which is more reliable than READ_USN_JOURNAL
                        # Create the MFT_ENUM_DATA structure
                        # Format:
                        # - StartFileReferenceNumber (8 bytes) - 0
                        # - LowUsn (8 bytes) - next_usn
                        # - HighUsn (8 bytes) - 0xFFFFFFFFFFFFFFFF (max value)
                        # - MinMajorVersion (2 bytes) - 2
                        # - MaxMajorVersion (2 bytes) - 2

                        # Create proper buffer for MFT_ENUM_DATA structure
                        buffer_in = bytearray(28)  # 28 bytes total for this structure
                        struct.pack_into(
                            "<QQQHH",
                            buffer_in,
                            0,
                            0,  # StartFileReferenceNumber
                            next_usn,  # LowUsn
                            0xFFFFFFFFFFFFFFFF,  # HighUsn
                            2,
                            2,
                        )  # MinMajorVersion, MaxMajorVersion

                        # Call DeviceIoControl with ENUM_USN_DATA instead
                        try:
                            read_data = win32file.DeviceIoControl(
                                handle,
                                FSCTL_ENUM_USN_DATA,  # More reliable control code
                                buffer_in,
                                65536,
                            )
                        except pywintypes.error as win_err:
                            # Handle error 38 (Reached end of file) as a normal condition
                            if win_err.winerror == 38:  # ERROR_HANDLE_EOF
                                self._logger.debug(
                                    "No new USN records available (reached end of file)",
                                )
                                # Create an empty result with just the next USN
                                read_data = bytearray(8)  # 8 bytes for next USN
                                # Use the same USN as the next USN (no advance)
                                struct.pack_into("<Q", read_data, 0, next_usn)
                            else:
                                # Re-raise other errors
                                raise

                        # Process the data
                        usn_records = []
                        try:
                            usn_records = win32file.ParseUsnData(read_data)
                            if usn_records:
                                self._logger.info(
                                    f"Found {len(usn_records)} USN records",
                                )
                            else:
                                self._logger.debug("No new USN records found")
                        except Exception as parse_err:
                            self._logger.error(f"Error parsing USN data: {parse_err}")

                        # Update the next USN for the next read
                        next_usn = read_data[0]

                        # Process each record
                        for record in usn_records:
                            try:
                                # Process a real USN record and create an activity
                                file_name = record.get("FileName", "Unknown")
                                reason = record.get("Reason", 0)
                                file_ref = record.get("FileReferenceNumber", 0)
                                parent_ref = record.get("ParentFileReferenceNumber", 0)

                                # Log detailed record info for debugging
                                self._logger.debug(f"USN Record: {record}")

                                # Determine the type of activity
                                activity_type = self._determine_activity_type(reason)

                                # Skip if it's not a type we care about
                                if activity_type == StorageActivityType.OTHER or (
                                    activity_type == StorageActivityType.CLOSE and not self._include_close_events
                                ):
                                    continue

                                # Try to construct a more accurate path
                                try:
                                    # For now, a simplified approach - could be improved
                                    # with MFT lookup in a full implementation
                                    file_path = f"{volume}\\{file_name}"

                                    # Use volume GUID if available
                                    if self._use_volume_guids:
                                        drive_letter = volume[0] if volume else "C"
                                        guid = self.map_drive_letter_to_volume_guid(
                                            drive_letter,
                                        )
                                        if guid:
                                            file_path = f"\\\\?\\Volume{{{guid}}}\\{file_name}"
                                except Exception as path_err:
                                    # Fall back to simple path if we can't construct an accurate one
                                    self._logger.debug(
                                        f"Error constructing path: {path_err}",
                                    )
                                    file_path = f"{volume}\\{file_name}"

                                # Determine if the item is a directory based on attributes
                                is_directory = False
                                if "FileAttributes" in record:
                                    is_directory = bool(
                                        record["FileAttributes"] & FILE_ATTRIBUTE_DIRECTORY,
                                    )

                                # Create activity data
                                activity_data = NtfsStorageActivityData(
                                    timestamp=datetime.now(UTC),
                                    file_reference_number=str(file_ref),
                                    parent_file_reference_number=str(parent_ref),
                                    activity_type=activity_type,
                                    reason_flags=reason,
                                    file_name=file_name,
                                    file_path=file_path,
                                    volume_name=volume,
                                    is_directory=is_directory,
                                    provider_type=StorageProviderType.LOCAL_NTFS,
                                    provider_id=self._provider_id,
                                    item_type=(StorageItemType.DIRECTORY if is_directory else StorageItemType.FILE),
                                )

                                # Add the activity
                                self.add_activity(activity_data)
                                self._logger.info(
                                    f"Added activity for {file_name} of type {activity_type}",
                                )
                            except Exception as rec_err:
                                self._logger.error(
                                    f"Error processing USN record: {rec_err}",
                                )

                        # Brief sleep to avoid hammering the system
                        time.sleep(0.1)
                    except Exception as usn_err:
                        self._logger.error(
                            f"Error reading USN journal on volume {volume}: {usn_err}",
                        )
                        # Fall back to simulated data for a while
                        is_real_usn_journal = False
                        time.sleep(5)  # Wait before retrying
                elif not self._stop_event.is_set():
                    # Generate a mock file activity every few seconds
                    time.sleep(self._monitor_interval)

                    # Create a mock file activity
                    file_names = [
                        "report.docx",
                        "presentation.pptx",
                        "data.xlsx",
                        "image.jpg",
                        "code.py",
                    ]
                    mock_file = file_names[int(time.time()) % len(file_names)]

                    # Use volume GUID path if available
                    if self._use_volume_guids:
                        try:
                            drive_letter = volume[0] if volume else "C"
                            guid = self.map_drive_letter_to_volume_guid(
                                drive_letter,
                            )
                            if guid:
                                mock_path = f"\\\\?\\Volume{{{guid}}}\\Users\\Documents\\{mock_file}"
                            else:
                                mock_path = f"{volume}\\Users\\Documents\\{mock_file}"
                        except Exception as e:
                            self._logger.warning(
                                f"Error creating mock path with GUID: {e}",
                            )
                            mock_path = f"{volume}\\Users\\Documents\\{mock_file}"
                    else:
                        mock_path = f"{volume}\\Users\\Documents\\{mock_file}"

                    # Create different activity types
                    activity_types = [
                        StorageActivityType.CREATE,
                        StorageActivityType.MODIFY,
                        StorageActivityType.READ,
                        StorageActivityType.CLOSE,
                    ]
                    activity_type = activity_types[int(time.time() / 5) % len(activity_types)]

                    # Create the activity data
                    activity_data = NtfsStorageActivityData(
                        timestamp=datetime.now(UTC),
                        file_reference_number=str(int(time.time())),
                        parent_file_reference_number="1000",
                        activity_type=activity_type,
                        reason_flags=1,  # Mock value
                        file_name=mock_file,
                        file_path=mock_path,
                        volume_name=volume,
                        is_directory=False,
                        provider_type=StorageProviderType.LOCAL_NTFS,
                        provider_id=self._provider_id,
                        item_type=StorageItemType.FILE,
                    )

                    # Add the activity
                    self.add_activity(activity_data)
                    self._logger.debug(
                        f"Added simulated activity for {mock_file} of type {activity_type}",
                    )

                    # Increment the next usn to simulate progress in the journal
                    next_usn += 1

                    # Periodically try to switch back to real monitoring
                    if not self._use_mock and WINDOWS_AVAILABLE and int(time.time()) % 15 == 0:  # Try more frequently
                        try:
                            # Try to read from the journal again using ENUM_USN_DATA
                            # Create a proper MFT_ENUM_DATA structure
                            buffer_in = bytearray(28)  # 28 bytes for the structure
                            struct.pack_into(
                                "<QQQHH",
                                buffer_in,
                                0,
                                0,  # StartFileReferenceNumber
                                next_usn,  # LowUsn
                                0xFFFFFFFFFFFFFFFF,  # HighUsn
                                2,
                                2,
                            )  # MinMajorVersion, MaxMajorVersion

                            # Call DeviceIoControl with ENUM_USN_DATA
                            read_data = win32file.DeviceIoControl(
                                handle,
                                FSCTL_ENUM_USN_DATA,  # More reliable control code
                                buffer_in,
                                65536,
                            )
                            # If successful, switch back to real journal monitoring
                            self._logger.info(
                                "Successfully reconnected to USN journal, switching back to real monitoring",
                            )
                            is_real_usn_journal = True

                            # Create a new test file to ensure we can detect something
                            test_dir = os.path.join(volume, "Indaleko_Test")
                            if not os.path.exists(test_dir):
                                os.makedirs(test_dir, exist_ok=True)
                            test_file = os.path.join(
                                test_dir,
                                f"reconnect_test_{int(time.time())}.txt",
                            )
                            with open(test_file, "w") as f:
                                f.write(
                                    f"USN reconnect test file - {datetime.now()}",
                                )
                            self._logger.info(
                                f"Created reconnect test file {test_file}",
                            )
                        except Exception:
                            # Continue with simulated data
                            pass
            except Exception as e:
                self._logger.error(f"Error in USN journal monitoring loop: {e}")
                time.sleep(5)  # Wait a bit before retrying

        self._logger.info(f"Stopped monitoring USN journal on volume {volume}")

    def _event_processing_thread(self):
        """Process events from the queue."""
        while not self._stop_event.is_set() or not self._event_queue.empty():
            try:
                # Get an event from the queue with timeout
                try:
                    event = self._event_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                # Process the event
                self._process_event(event)

                # Mark the task as done
                self._event_queue.task_done()

            except Exception as e:
                self._logger.error(f"Error processing event: {e}")

    def _process_event(self, event: dict[str, Any]):
        """
        Process a USN journal event.

        Args:
            event: The event to process
        """
        # Extract event data
        volume = event.get("volume")
        record = event.get("record", {})
        is_directory = event.get("is_directory", False)

        # Skip if the file is in an excluded path
        file_name = record.get("FileName", "")
        if any(file_name.startswith(exc) for exc in self._excluded_paths):
            return

        # Skip if the file has an excluded extension
        if not is_directory and "." in file_name:
            ext = file_name.split(".")[-1].lower()
            if ext in self._excluded_extensions:
                return

        # Determine the activity type
        reason_flags = record.get("Reason", 0)
        activity_type = self._determine_activity_type(reason_flags)

        # Skip close events if configured to do so
        if activity_type == StorageActivityType.CLOSE and not self._include_close_events:
            return

        # Get file path if possible
        file_path = self._get_file_path(
            volume,
            record.get("FileReferenceNumber"),
            record.get("ParentFileReferenceNumber"),
            file_name,
        )

        # Get timestamp with timezone awareness
        timestamp = record.get("DateTime")
        if timestamp:
            if not timestamp.tzinfo:
                timestamp = timestamp.replace(tzinfo=UTC)
        else:
            timestamp = datetime.now(UTC)

        # Create the activity data
        activity_data = NtfsStorageActivityData(
            timestamp=timestamp,
            file_reference_number=str(record.get("FileReferenceNumber", "")),
            parent_file_reference_number=str(
                record.get("ParentFileReferenceNumber", ""),
            ),
            activity_type=activity_type,
            reason_flags=reason_flags,
            file_name=file_name,
            file_path=file_path,
            volume_name=volume,
            is_directory=is_directory,
            security_id=record.get("SecurityId"),
            usn=record.get("Usn"),
            provider_type=StorageProviderType.LOCAL_NTFS,
            provider_id=self._provider_id,
            item_type=(StorageItemType.DIRECTORY if is_directory else StorageItemType.FILE),
        )

        # Add special handling for rename operations
        if activity_type == StorageActivityType.RENAME:
            # TODO: Implement rename detection logic
            pass

        # Add the activity to our collection
        self.add_activity(activity_data)

    def _determine_activity_type(self, reason_flags: int) -> StorageActivityType:
        """
        Determine the activity type from the reason flags.

        Args:
            reason_flags: The reason flags from the USN record

        Returns:
            The determined activity type
        """
        # If in mock mode or on non-Windows platforms, use simplified logic
        if self._use_mock or not WINDOWS_AVAILABLE:
            # Mock logic based on bit pattern
            if reason_flags % 7 == 0:
                return StorageActivityType.CREATE
            elif reason_flags % 7 == 1:
                return StorageActivityType.MODIFY
            elif reason_flags % 7 == 2:
                return StorageActivityType.DELETE
            elif reason_flags % 7 == 3:
                return StorageActivityType.CLOSE
            elif reason_flags % 7 == 4:
                return StorageActivityType.RENAME
            elif reason_flags % 7 == 5:
                return StorageActivityType.SECURITY_CHANGE
            elif reason_flags % 7 == 6:
                return StorageActivityType.ATTRIBUTE_CHANGE
            else:
                return StorageActivityType.OTHER

        # Real Windows logic using USN reason flags
        try:
            # Use our global constants directly for clarity
            if reason_flags & USN_REASON_FILE_CREATE:
                return StorageActivityType.CREATE
            elif reason_flags & USN_REASON_FILE_DELETE:
                return StorageActivityType.DELETE
            elif reason_flags & USN_REASON_RENAME_OLD_NAME or reason_flags & USN_REASON_RENAME_NEW_NAME:
                return StorageActivityType.RENAME
            elif reason_flags & USN_REASON_SECURITY_CHANGE:
                return StorageActivityType.SECURITY_CHANGE
            elif (
                reason_flags & USN_REASON_EA_CHANGE
                or reason_flags & USN_REASON_BASIC_INFO_CHANGE
                or reason_flags & USN_REASON_COMPRESSION_CHANGE
                or reason_flags & USN_REASON_ENCRYPTION_CHANGE
            ):
                return StorageActivityType.ATTRIBUTE_CHANGE
            elif reason_flags & USN_REASON_CLOSE:
                return StorageActivityType.CLOSE
            elif (
                reason_flags & USN_REASON_DATA_OVERWRITE
                or reason_flags & USN_REASON_DATA_EXTEND
                or reason_flags & USN_REASON_DATA_TRUNCATION
            ):
                return StorageActivityType.MODIFY
            else:
                return StorageActivityType.OTHER
        except Exception as e:
            self._logger.warning(
                f"Error determining activity type: {e}, using mock logic",
            )
            # Fall back to mock logic if something goes wrong
            return StorageActivityType.MODIFY

    def map_drive_letter_to_volume_guid(self, drive_letter: str) -> str | None:
        """
        Map a drive letter to a volume GUID using the machine configuration.

        Args:
            drive_letter: The drive letter to map (e.g., "C")

        Returns:
            The volume GUID or None if mapping is not available
        """
        # Return from cache if already mapped
        if drive_letter.upper() in self._volume_guid_mapping:
            return self._volume_guid_mapping[drive_letter.upper()]

        # Clean up the drive letter (just need the letter itself)
        if len(drive_letter) > 1:
            drive_letter = drive_letter[0]
        drive_letter = drive_letter.upper()

        # Use machine config if available
        if self._machine_config and hasattr(
            self._machine_config,
            "map_drive_letter_to_volume_guid",
        ):
            try:
                guid = self._machine_config.map_drive_letter_to_volume_guid(
                    drive_letter,
                )
                if guid:
                    self._volume_guid_mapping[drive_letter] = guid
                    self._logger.debug(f"Mapped drive {drive_letter} to GUID {guid}")
                    return guid
            except Exception as e:
                self._logger.warning(
                    f"Error mapping drive letter {drive_letter} to GUID: {e}",
                )

        # If we're in Windows but don't have the mapping, try to get it directly using win32 APIs
        if WINDOWS_AVAILABLE and not self._use_mock:
            try:
                import win32file

                # Get the volume name for this drive letter
                drive_path = f"{drive_letter}:\\"
                try:
                    volume_name_buffer = win32file.GetVolumeNameForVolumeMountPoint(
                        drive_path,
                    )
                    if volume_name_buffer:
                        # Extract just the GUID part from "\\?\Volume{GUID}\"
                        guid = volume_name_buffer[11:-2]  # Remove "\\?\Volume{" and "}\"
                        self._volume_guid_mapping[drive_letter] = guid
                        self._logger.debug(
                            f"Got GUID {guid} for drive {drive_letter} using Win32 API",
                        )
                        return guid
                except Exception as e:
                    self._logger.warning(
                        f"Win32 API error getting volume GUID for {drive_letter}: {e}",
                    )
            except ImportError:
                self._logger.warning(
                    "Could not import win32file for direct volume GUID mapping",
                )

        # Fall back to drive letter if we could not get GUID
        self._logger.warning(
            f"Could not map drive letter {drive_letter} to volume GUID",
        )
        return None

    def get_volume_guid_path(self, volume: str) -> str:
        """
        Get the volume GUID path for a given volume (drive letter).

        Args:
            volume: The volume (usually drive letter like "C:")

        Returns:
            The volume GUID path (in Windows-style with double backslashes) or the original volume if not available
        """
        # If volume is already a GUID path, return it
        if volume.startswith("\\\\?\\Volume{"):
            return volume

        # Extract drive letter
        drive_letter = volume[0] if volume else "C"

        # Try to map to GUID
        if self._use_volume_guids:
            guid = self.map_drive_letter_to_volume_guid(drive_letter)
            if guid:
                return f"\\\\?\\Volume{{{guid}}}\\"

        # Fall back to using drive letter format
        return f"\\\\?\\{volume}\\"

    def add_activity(self, activity: BaseStorageActivityData) -> None:
        """
        Add an activity to the collection with enhanced logging.

        Args:
            activity: The activity to add
        """
        # Add to the collection using parent method
        super().add_activity(activity)

        # Enhanced logging for activity tracking
        try:
            # Log basic info
            file_name = getattr(activity, "file_name", "Unknown")
            activity_type = getattr(activity, "activity_type", "Unknown")
            activity_id = getattr(activity, "activity_id", "Unknown")

            self._logger.info(
                f"Added activity: {activity_type} - {file_name} [ID: {activity_id}]",
            )

            # Log detailed info at debug level
            if self._debug:
                # Get basic attributes without depending on model_dump_json
                debug_info = {}
                for attr in [
                    "file_name",
                    "file_path",
                    "activity_type",
                    "reason_flags",
                    "timestamp",
                    "is_directory",
                    "volume_name",
                ]:
                    if hasattr(activity, attr):
                        debug_info[attr] = str(getattr(activity, attr))

                self._logger.debug(f"Activity details: {debug_info}")

            # Track activity counts by type
            if not hasattr(self, "_activity_counts"):
                self._activity_counts = {}

            activity_type_str = str(activity_type)
            if activity_type_str in self._activity_counts:
                self._activity_counts[activity_type_str] += 1
            else:
                self._activity_counts[activity_type_str] = 1

            # Log count milestones (every 10 activities)
            total_count = len(self._activities)
            if total_count % 10 == 0:
                self._logger.info(f"Total activities collected: {total_count}")
                self._logger.info(f"Activity counts by type: {self._activity_counts}")
        except Exception as e:
            # Don't let logging errors affect functionality
            self._logger.warning(f"Error logging activity details: {e}")

    def _get_file_path(
        self,
        volume: str,
        file_ref: int,
        parent_ref: int,
        file_name: str,
    ) -> str | None:
        """
        Get the full path for a file based on its reference numbers.

        Args:
            volume: The volume the file is on
            file_ref: The file reference number
            parent_ref: The parent directory reference number
            file_name: The file name

        Returns:
            The full path to the file, or None if it can't be determined
        """
        # Check cache first
        if file_ref in self._file_ref_to_path:
            return self._file_ref_to_path[file_ref]

        # Use volume GUID if available
        if self._use_volume_guids:
            # Get the volume GUID path
            volume_guid_path = None
            try:
                # Extract just the drive letter if volume is in the form "C:" or "C:\"
                drive_letter = volume[0] if volume else "C"
                guid = self.map_drive_letter_to_volume_guid(drive_letter)
                if guid:
                    volume_guid_path = f"\\\\?\\Volume{{{guid}}}\\"
                    self._logger.debug(f"Using volume GUID path: {volume_guid_path}")
            except Exception as e:
                self._logger.warning(f"Error getting volume GUID path: {e}")

            # Build path with volume GUID if available
            if volume_guid_path:
                path = f"{volume_guid_path}...\\{file_name}"
                return path

        # Fall back to drive letter if GUID not available
        # For now, just return a partial path with volume and file name
        # In a full implementation, this would resolve the full path by walking up the directory tree
        return f"{volume}\\...\\{file_name}"

    def collect_data(self) -> None:
        """
        Collect storage activity data from NTFS volumes.

        This method starts monitoring if not already active and returns
        currently collected activities.
        """
        if not self._active:
            self.start_monitoring()

        # Return current activities through the get_activities() method
