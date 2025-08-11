#!/usr/bin/env python
r"""
NTFS Storage Activity Collector V2 for Indaleko.

This module provides a collector for NTFS file system activities using the
USN Journal to detect file changes. Based on the working implementation in foo.py.

Features:
- Monitors file system changes using the NTFS USN Journal
- Volume GUID support for stable path references (immune to drive letter changes)
- Timezone-aware datetime handling for ArangoDB compatibility
- Error handling for robust operation
- Thread-safe monitoring and activity tracking

The collector runs background threads to monitor file system activity and
processes the events into standardized storage activity records. It can be
used with the NtfsStorageActivityRecorder to store activities in a database.

Usage:
    # Basic usage (with volume GUIDs by default)
    collector = NtfsStorageActivityCollectorV2(volumes=["C:"], auto_start=True)
    activities = collector.get_activities()
    collector.stop_monitoring()

    # Explicitly disable volume GUIDs if needed
    collector = NtfsStorageActivityCollectorV2(
        volumes=["C:"],
        use_volume_guids=False,  # Not recommended - disables stable path references
        auto_start=True
    )
    activities = collector.get_activities()

    # Get stable path with volume GUID
    path = collector.get_volume_guid_path("C:")  # Returns "\\\\?\\Volume{GUID}\\"

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

import argparse
import ctypes
import json
import logging
import os
import queue
import struct
import sys
import threading
import time
import uuid

from ctypes import wintypes
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from icecream import ic


# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Check Windows availability and import Windows-specific modules if possible
WINDOWS_AVAILABLE = sys.platform.startswith("win")

# pylint: disable=wrong-import-position
# Import basic modules that are platform-agnostic
# Import storage activity models
import contextlib

from activity.collectors.storage.data_models.storage_activity_data_model import (  # noqa: E402
    NtfsStorageActivityData,
    StorageActivityType,
    StorageItemType,
    StorageProviderType,
)

# No longer needed: from data_models.source_identifier import IndalekoSourceIdentifierDataModel
# Import machine config for cli handling
from utils.cli.base import IndalekoBaseCLI  # noqa: E402
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel  # noqa: E402
from utils.cli.runner import IndalekoCLIRunner  # noqa: E402


if TYPE_CHECKING:
    from platforms.machine_config import IndalekoMachineConfig


# Only import Windows-specific base class if on Windows
if WINDOWS_AVAILABLE:
    from activity.collectors.storage.base import WindowsStorageActivityCollector

    # Performance mixin removed to avoid multiple inheritance issues
else:
    # Create mock classes for help/argument parsing on non-Windows platforms
    class WindowsStorageActivityCollector:
        """Placeholder base class for non-Windows platforms."""

        def __init__(self, **kwargs) -> None:
            # Store kwargs for potential use
            self._kwargs = kwargs

            # Initialize basic attributes
            self._activities = []
            self._logger = logging.getLogger("MockWindowsStorageActivityCollector")
            self._name = kwargs.get("name", "Mock Windows Storage Activity Collector")
            self._provider_id = kwargs.get("provider_id", uuid.uuid4())
            self._description = kwargs.get(
                "description",
                "Mock Windows Storage Activity Collector",
            )
            self._active = False
            self._volume_handles = {}
            self._stop_event = threading.Event()

        def start_monitoring(self) -> None:
            """Mock implementation."""
            self._active = True

        def stop_monitoring(self) -> None:
            """Mock implementation."""
            self._active = False

        def get_activities(self):
            """Return an empty list."""
            return self._activities

        def add_activity(self, activity) -> None:
            """Add an activity to the collection."""
            self._activities.append(activity)

        def perf_context(self, context_name):
            """Mock context manager."""

            class MockContext:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass

            return MockContext()


# pylint: enable=wrong-import-position

# Windows API constants
FSCTL_QUERY_USN_JOURNAL = 0x900F4
FSCTL_READ_USN_JOURNAL = 0x900BB
FSCTL_READ_UNPRIVILEGED_USN_JOURNAL = 0x900F8  # Unprivileged access
FILE_READ_DATA = 0x0001
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000

# Reason flags for USN records
REASON_FLAGS = {
    0x00000001: "DATA_OVERWRITE",
    0x00000002: "DATA_EXTEND",
    0x00000004: "DATA_TRUNCATION",
    0x00000010: "NAMED_DATA_OVERWRITE",
    0x00000020: "NAMED_DATA_EXTEND",
    0x00000040: "NAMED_DATA_TRUNCATION",
    0x00000100: "FILE_CREATE",
    0x00000200: "FILE_DELETE",
    0x00000400: "EA_CHANGE",
    0x00000800: "SECURITY_CHANGE",
    0x00001000: "RENAME_OLD_NAME",
    0x00002000: "RENAME_NEW_NAME",
    0x00004000: "INDEXABLE_CHANGE",
    0x00008000: "BASIC_INFO_CHANGE",
    0x00010000: "HARD_LINK_CHANGE",
    0x00020000: "COMPRESSION_CHANGE",
    0x00040000: "ENCRYPTION_CHANGE",
    0x00080000: "OBJECT_ID_CHANGE",
    0x00100000: "REPARSE_POINT_CHANGE",
    0x00200000: "STREAM_CHANGE",
    0x80000000: "CLOSE",
}

# Attribute flags
ATTRIBUTE_FLAGS = {
    0x00000020: "ARCHIVE",
    0x00000002: "HIDDEN",
    0x00000004: "SYSTEM",
    0x00000010: "DIRECTORY",
    0x00000080: "NORMAL",
    0x00000100: "TEMPORARY",
    0x00000200: "SPARSE_FILE",
    0x00000400: "REPARSE_POINT",
    0x00000800: "COMPRESSED",
    0x00001000: "OFFLINE",
    0x00002000: "NOT_CONTENT_INDEXED",
    0x00004000: "ENCRYPTED",
}


# Define USN_JOURNAL_DATA structure
class USN_JOURNAL_DATA(ctypes.Structure):
    _fields_ = [
        ("UsnJournalID", ctypes.c_ulonglong),  # 64-bit unsigned
        ("FirstUsn", ctypes.c_longlong),  # 64-bit signed
        ("NextUsn", ctypes.c_longlong),
        ("LowestValidUsn", ctypes.c_longlong),
        ("MaxUsn", ctypes.c_longlong),
        ("MaximumSize", ctypes.c_ulonglong),
        ("AllocationDelta", ctypes.c_ulonglong),
    ]


# Define READ_USN_JOURNAL_DATA structure (V0 for compatibility)
class READ_USN_JOURNAL_DATA(ctypes.Structure):
    _fields_ = [
        ("StartUsn", ctypes.c_longlong),
        ("ReasonMask", wintypes.DWORD),
        ("ReturnOnlyOnClose", wintypes.DWORD),
        ("Timeout", ctypes.c_ulonglong),
        ("BytesToWaitFor", ctypes.c_ulonglong),
        ("UsnJournalID", ctypes.c_ulonglong),
    ]


# Define USN_RECORD structure
class USN_RECORD(ctypes.Structure):
    _fields_ = [
        ("RecordLength", wintypes.DWORD),
        ("MajorVersion", wintypes.WORD),
        ("MinorVersion", wintypes.WORD),
        ("FileReferenceNumber", ctypes.c_ulonglong),
        ("ParentFileReferenceNumber", ctypes.c_ulonglong),
        ("Usn", ctypes.c_longlong),
        ("TimeStamp", wintypes.LARGE_INTEGER),
        ("Reason", wintypes.DWORD),
        ("SourceInfo", wintypes.DWORD),
        ("SecurityId", wintypes.DWORD),
        ("FileAttributes", wintypes.DWORD),
        ("FileNameLength", wintypes.WORD),
        ("FileNameOffset", wintypes.WORD),
        ("FileName", wintypes.WCHAR * 1),  # Variable length
    ]


def is_admin():
    """Check if the script is running with administrative privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def filetime_to_datetime(filetime):
    """Convert Windows FILETIME to Python datetime."""
    epoch_diff = 116444736000000000  # 100ns intervals from 1601 to 1970
    timestamp = (filetime - epoch_diff) / 10000000  # Convert to seconds
    if timestamp < 0:
        return datetime(1601, 1, 1, tzinfo=UTC)
    return datetime.fromtimestamp(timestamp, tz=UTC)


def get_volume_handle(volume_path):
    """
    Open a handle to the specified volume.

    This function exactly matches the implementation in foo.py.
    """
    # Check if we have admin rights
    is_admin_process = is_admin()
    ic(f"Running with administrator privileges: {is_admin_process}")

    # Use FILE_READ_DATA (0x0001) instead of GENERIC_READ (0x80000000)
    handle = ctypes.windll.kernel32.CreateFileW(
        volume_path,
        FILE_READ_DATA,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None,
        OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS,
        None,
    )

    if handle == -1:
        error = ctypes.get_last_error()
        if error == 5:  # ERROR_ACCESS_DENIED
            ic(f"Access denied when opening volume {volume_path}")
            ic("This usually means the process doesn't have administrator privileges.")
            ic(
                "Try running the script as administrator (right-click, Run as Administrator).",
            )
        raise ctypes.WinError()

    return handle


def query_usn_journal(handle):
    """Query the USN journal for metadata."""
    journal_data = USN_JOURNAL_DATA()
    bytes_returned = wintypes.DWORD()

    success = ctypes.windll.kernel32.DeviceIoControl(
        handle,
        FSCTL_QUERY_USN_JOURNAL,
        None,
        0,
        ctypes.byref(journal_data),
        ctypes.sizeof(journal_data),
        ctypes.byref(bytes_returned),
        None,
    )
    if not success:
        raise ctypes.WinError()

    return journal_data


def read_usn_journal(handle, journal_id, start_usn):
    """
    Read USN journal entries.

    Based on the foo.py implementation with minimal error handling.
    """
    # Create the READ_USN_JOURNAL_DATA structure
    read_data = READ_USN_JOURNAL_DATA(
        StartUsn=start_usn,
        ReasonMask=0xFFFFFFFF,  # All reasons
        ReturnOnlyOnClose=0,
        Timeout=0,
        BytesToWaitFor=0,
        UsnJournalID=journal_id,
    )

    # Create the buffer
    buffer_size = 4096
    buffer = ctypes.create_string_buffer(buffer_size)
    bytes_returned = wintypes.DWORD()

    # Call DeviceIoControl
    success = ctypes.windll.kernel32.DeviceIoControl(
        handle,
        FSCTL_READ_USN_JOURNAL,
        ctypes.byref(read_data),
        ctypes.sizeof(read_data),
        buffer,
        buffer_size,
        ctypes.byref(bytes_returned),
        None,
    )

    if not success:
        error = ctypes.get_last_error()
        ic(f"DeviceIoControl failed with Win32 error code: {error}")
        raise ctypes.WinError(error)

    return buffer, bytes_returned.value


def parse_usn_record(buffer, offset, bytes_returned):
    """Parse a USN record from the buffer."""
    if offset + 4 > bytes_returned:
        return None

    record_length = struct.unpack_from("<I", buffer, offset)[0]
    if record_length == 0 or offset + record_length > bytes_returned:
        return None

    record = USN_RECORD.from_buffer_copy(buffer[offset : offset + record_length])

    filename_offset = record.FileNameOffset
    filename_length = record.FileNameLength
    filename_end = filename_offset + filename_length
    if filename_end > record_length:
        return None

    try:
        filename = buffer[offset + filename_offset : offset + filename_end].decode(
            "utf-16-le",
            errors="replace",
        )
    except UnicodeDecodeError:
        filename = "<invalid filename>"

    reasons = [name for flag, name in REASON_FLAGS.items() if record.Reason & flag]
    attributes = [name for flag, name in ATTRIBUTE_FLAGS.items() if record.FileAttributes & flag]
    timestamp = filetime_to_datetime(record.TimeStamp)

    return {
        "USN": record.Usn,
        "FileName": filename,
        "Timestamp": timestamp,
        "Reasons": reasons,
        "Attributes": attributes,
        "FileReferenceNumber": record.FileReferenceNumber,
        "ParentFileReferenceNumber": record.ParentFileReferenceNumber,
        "FileAttributes": record.FileAttributes,
    }


class NtfsStorageActivityCollectorV2(WindowsStorageActivityCollector):
    """
    Collector for NTFS file system activity using the USN Journal. Version 2 implementation
    based on the working code from foo.py.

    This collector monitors file system operations on NTFS volumes and creates
    standardized storage activity records for them.
    """

    # Helper method to extract performance counters
    def extract_counters(self) -> dict[str, int]:
        """Extract performance counters."""
        return {
            "activities_collected": (len(self._activities) if hasattr(self, "_activities") else 0),
            "active": 1 if self._active else 0,
        }

    # Service registration information
    indaleko_ntfs_collector_uuid = "7d8f5a92-35c7-41e6-b13d-6c4e89e7f2a5"
    indaleko_ntfs_collector_service_name = "NTFS Storage Activity Collector V2"
    indaleko_ntfs_collector_service_description = "Collects storage activities from the NTFS USN Journal"
    indaleko_ntfs_collector_service_version = "2.0"
    indaleko_ntfs_collector_service_file_name = "ntfs_collector_v2"

    @classmethod
    def get_collector_service_file_name(cls) -> str:
        """Get the service file name for this collector."""
        return cls.indaleko_ntfs_collector_service_file_name

    @classmethod
    def get_collector_service_registration_name(cls) -> str:
        """Get the service registration name for this collector."""
        return cls.indaleko_ntfs_collector_service_name

    @classmethod
    def get_collector_service_identifier(cls) -> uuid.UUID:
        """Get the service identifier for this collector."""
        return uuid.UUID(cls.indaleko_ntfs_collector_uuid)

    @classmethod
    def get_collector_service_description(cls) -> str:
        """Get the service description for this collector."""
        return cls.indaleko_ntfs_collector_service_description

    @classmethod
    def get_collector_service_version(cls) -> str:
        """Get the service version for this collector."""
        return cls.indaleko_ntfs_collector_service_version

    def __init__(self, **kwargs) -> None:
        """
        Initialize the NTFS storage activity collector.

        Args:
            volumes: List of volume paths to monitor (e.g., ["C:", "D:"])
            buffer_size: Size of the buffer to use for reading the USN Journal
            monitor_interval: How often to check for new events (in seconds)
            include_close_events: Whether to include file close events
            max_queue_size: Maximum size of the event queue
            auto_start: Whether to start monitoring automatically
            debug: Whether to enable debug mode
            use_volume_guids: Whether to use volume GUIDs instead of drive letters
            machine_config: Optional machine config object to use for volume GUID mapping
        """
        # Check if we're just being initialized for command-line help
        help_mode = "--help" in sys.argv or "-h" in sys.argv

        # Full initialization only when we're on Windows and not just showing help
        if not help_mode:
            # Check Windows availability first - this init method should only run on Windows
            if not WINDOWS_AVAILABLE:
                raise RuntimeError(
                    "NtfsStorageActivityCollectorV2 initialization requires Windows",
                )

        # Configure logging
        self._debug = kwargs.get("debug", False)
        logging.basicConfig(
            level=logging.DEBUG if self._debug else logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self._logger = logging.getLogger("NtfsStorageActivityCollectorV2")

        # If we're just in help mode, skip the full initialization
        if help_mode:
            # Set minimal attributes needed for CLI help
            self._volumes = []
            self._active = False
            self._stop_event = None
            return

        # Initialize with provider-specific values
        kwargs["name"] = kwargs.get("name", self.indaleko_ntfs_collector_service_name)
        kwargs["provider_id"] = kwargs.get(
            "provider_id",
            uuid.UUID(self.indaleko_ntfs_collector_uuid),
        )
        kwargs["provider_type"] = StorageProviderType.LOCAL_NTFS
        kwargs["description"] = kwargs.get(
            "description",
            self.indaleko_ntfs_collector_service_description,
        )
        kwargs["version"] = kwargs.get(
            "version",
            self.indaleko_ntfs_collector_service_version,
        )

        # Call parent initializer
        WindowsStorageActivityCollector.__init__(self, **kwargs)

        # Configuration
        self._volumes = kwargs.get("volumes", ["C:"])
        self._buffer_size = kwargs.get("buffer_size", 65536)
        self._monitor_interval = kwargs.get("monitor_interval", 1.0)
        self._include_close_events = kwargs.get("include_close_events", False)
        self._max_queue_size = kwargs.get("max_queue_size", 10000)
        self._use_volume_guids = kwargs.get("use_volume_guids", True)

        # NTFS-specific structures
        self._file_ref_to_path = {}
        self._event_queue = queue.Queue(maxsize=self._max_queue_size)
        self._volume_handles = {}
        self._usn_journals = {}
        self._journal_threads = []
        self._processing_thread = None
        self._active = False
        self._stop_event = threading.Event()

        # Last processed USN for each volume
        self._last_processed_usn = {}

        # State persistence - prioritize explicit state_file parameter
        self._state_file = kwargs.get("state_file")

        if self._state_file is None:
            # Config directory is preferred for state file
            config_dir = kwargs.get("config_dir")

            # Try to find Indaleko config directory if not specified
            if config_dir is None and os.environ.get("INDALEKO_ROOT"):
                potential_config_dir = os.path.join(
                    os.environ.get("INDALEKO_ROOT"),
                    "config",
                )
                if os.path.isdir(potential_config_dir):
                    config_dir = potential_config_dir

            # Fallback to data directory if necessary
            if config_dir is None and self._output_path:
                config_dir = os.path.dirname(self._output_path)

            # Generate state filename with provider ID for uniqueness
            if config_dir:
                # Create a subdirectory for collector states
                collector_state_dir = os.path.join(config_dir, "collector_states")
                state_filename = f"ntfs_collector_state_{self._provider_id}.json"
                self._state_file = os.path.join(collector_state_dir, state_filename)

                # Ensure the directory exists
                os.makedirs(collector_state_dir, exist_ok=True)

        # Log state file location if set
        if self._state_file:
            self._logger.info(f"Using state file: {self._state_file}")
            ic(f"Using state file: {self._state_file}")
        else:
            self._logger.info("No state file configured - state will not be persisted")
            ic("No state file configured - state will not be persisted")

        # Load saved state if available
        self._load_state()

        # Filters
        self._filters = kwargs.get("filters", {})
        self._excluded_paths = self._filters.get("excluded_paths", [])
        self._excluded_process_names = self._filters.get("excluded_process_names", [])
        self._excluded_extensions = self._filters.get("excluded_extensions", [])

        # Strategy flags
        self._try_unprivileged = kwargs.get("try_unprivileged", True)

        # Output path for saving activities
        self._output_path = kwargs.get("output_path")

        # Print debug information
        if self._debug:
            ic("\n==== NTFS Collector Debug Information ====")
            ic(f"Platform: {sys.platform}")
            ic(f"Windows Available: {WINDOWS_AVAILABLE}")
            ic(f"PyWin32 Available: {PYWIN32_AVAILABLE}")
            ic(f"Is Admin: {is_admin()}")
            ic(f"Using Volume GUIDs: {self._use_volume_guids}")
            ic(f"Volumes to Monitor: {self._volumes}")
            ic(f"State File: {self._state_file}")
            ic("Strategy Options:")
            ic(f"  - Try Unprivileged Access: {self._try_unprivileged}")

            # Check Windows version if available
            if WINDOWS_AVAILABLE:
                try:
                    import platform

                    win_version = platform.win32_ver()[0]
                    ic(f"Windows Version: {win_version}")
                except Exception as e:
                    ic(f"Error getting Windows version: {e}")

            ic("=========================================\n")

        # Start threads if auto_start is True
        if kwargs.get("auto_start", False):
            self.start_monitoring()

    def perf_context(self, context_name):
        """Simple implementation of perf_context that acts as a no-op context manager."""

        class NoOpContext:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

        return NoOpContext()

    def _save_state(self) -> None:
        """Save the collector state to a file for resuming later."""
        if not self._state_file:
            self._logger.debug("No state file specified, skipping state save")
            return

        try:
            # Create state dictionary
            state = {
                "last_processed_usn": self._last_processed_usn,
                "timestamp": datetime.now(UTC).isoformat(),
                "collector_version": self.get_collector_service_version(),
                "collector_id": str(self._provider_id),
            }

            # Ensure directory exists
            os.makedirs(os.path.dirname(self._state_file), exist_ok=True)

            # Save to file
            with open(self._state_file, "w") as f:
                json.dump(state, f, indent=2)

            self._logger.info(f"Saved collector state to {self._state_file}")
            ic(f"Saved collector state to {self._state_file}")
        except Exception as e:
            self._logger.exception(f"Error saving state to {self._state_file}: {e}")
            ic(f"Error saving state to {self._state_file}: {e}")

    def _load_state(self) -> None:
        """Load the collector state from a file."""
        if not self._state_file or not os.path.exists(self._state_file):
            self._logger.debug("No state file found, starting with empty state")
            return

        try:
            with open(self._state_file) as f:
                state = json.load(f)

            # Load last processed USN values
            if "last_processed_usn" in state:
                self._last_processed_usn = state["last_processed_usn"]
                self._logger.info(
                    f"Loaded last processed USN values: {self._last_processed_usn}",
                )
                ic(f"Loaded last processed USN values: {self._last_processed_usn}")

                # Check if the state file looks very old - if so, clear it
                timestamp = state.get("timestamp", None)
                if timestamp:
                    try:
                        state_time = datetime.fromisoformat(timestamp)
                        current_time = datetime.now(UTC)
                        # If state is more than 7 days old, it might be too old for the journal
                        if (current_time - state_time).days > 7:
                            ic(
                                f"WARNING: State file is more than 7 days old ({state_time.isoformat()})",
                            )
                            ic(
                                "USN Journal entries might have been overwritten. Will validate USN when connecting.",
                            )
                    except Exception as date_error:
                        self._logger.warning(
                            f"Could not parse state timestamp: {date_error}",
                        )

            self._logger.info(f"Loaded collector state from {self._state_file}")
        except Exception as e:
            self._logger.exception(f"Error loading state from {self._state_file}: {e}")
            ic(f"Error loading state from {self._state_file}: {e}")
            # Continue with empty state

    def retrieve_activities(self, last_processed_usn: int) -> list[Any]:
        """Retrieve the activities from the USN journal, starting from the last processed USN."""
        ic(dir(self))

    def start_monitoring(self) -> None:
        """Start monitoring the USN Journal on all configured volumes."""
        with self.perf_context("start_monitoring"):
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
            for volume in self._volumes:
                try:
                    self._logger.info(f"Starting monitoring for volume {volume}")
                    self._start_volume_monitoring(volume)
                except Exception as e:
                    self._logger.exception(
                        f"Failed to start monitoring volume {volume}: {e}",
                    )

    def stop_monitoring(self) -> None:
        """Stop monitoring the USN Journal on all volumes."""
        with self.perf_context("stop_monitoring"):
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

            # Close all volume handles
            for volume, handle in self._volume_handles.items():
                try:
                    if handle is not None:
                        self._logger.debug(f"Closing handle for volume {volume}")
                        ctypes.windll.kernel32.CloseHandle(handle)
                except Exception as e:
                    self._logger.exception(f"Error closing handle for volume {volume}: {e}")

            # Save state before clearing
            self._save_state()

            self._logger.debug("Clearing internal data structures")
            self._volume_handles.clear()
            self._usn_journals.clear()
            self._journal_threads.clear()
            self._processing_thread = None
            self._logger.info("Monitoring stopped")
            ic("Monitoring stopped. State saved for future runs.")

    def get_volume_guid_path(self, drive_letter):
        """
        Get the Volume GUID path for a drive letter.

        Args:
            drive_letter: The drive letter (e.g., "C:" or "C")

        Returns:
            Volume GUID path or None if not available
        """
        # Clean up the drive letter format
        if len(drive_letter) > 1:
            drive_letter = drive_letter[0]

        try:
            # Use the volume GUID from the machine config if available
            guid = self.map_drive_letter_to_volume_guid(drive_letter)
            if guid:
                return f"\\\\?\\Volume{{{guid}}}\\"

            # Fallback: try to use Win32 API to get volume info
            if WINDOWS_AVAILABLE and PYWIN32_AVAILABLE:
                import win32file

                # Make sure the drive letter has a colon
                if not drive_letter.endswith(":"):
                    drive_letter = f"{drive_letter}:"

                # Try to get the volume name using Win32
                try:
                    return win32file.GetVolumeNameForVolumeMountPoint(
                        f"{drive_letter}\\",
                    )
                except Exception as e:
                    self._logger.debug(f"Error getting volume GUID with Win32API: {e}")

            return None
        except Exception as e:
            self._logger.exception(f"Error getting volume GUID path: {e}")
            return None

    def map_drive_letter_to_volume_guid(self, drive_letter):
        """
        Map a drive letter to its volume GUID.

        Args:
            drive_letter: The drive letter (e.g., "C")

        Returns:
            Volume GUID string or None if not available
        """
        try:
            # Simple implementation - can be enhanced with machine config integration
            # For now, just try to get it from Windows
            if WINDOWS_AVAILABLE and PYWIN32_AVAILABLE:
                import win32file

                # Make sure the drive letter has a colon
                if not drive_letter.endswith(":"):
                    drive_letter = f"{drive_letter}:"

                try:
                    volume_name = win32file.GetVolumeNameForVolumeMountPoint(
                        f"{drive_letter}\\",
                    )
                    # Extract GUID part from volume name
                    # Format is typically \\?\Volume{GUID}\
                    if volume_name and "{" in volume_name and "}" in volume_name:
                        start = volume_name.find("{") + 1
                        end = volume_name.find("}")
                        if start > 0 and end > start:
                            return volume_name[start:end]
                except Exception as e:
                    self._logger.debug(f"Error getting volume GUID with Win32API: {e}")

            return None
        except Exception as e:
            self._logger.exception(f"Error mapping drive letter to GUID: {e}")
            return None

    def _start_volume_monitoring(self, volume: str) -> None:
        """
        Start monitoring a specific volume.

        Args:
            volume: The volume to monitor (e.g., "C:")
        """
        # Standardize the volume format - match exactly what foo.py does
        if not volume.endswith(":"):
            volume = f"{volume}:"

        # Format volume path exactly like foo.py
        volume_path = f"\\\\.\\{volume}"

        ic(f"Using volume path: {volume_path}")

        self._logger.debug(f"Opening volume path: {volume_path}")

        # Open the volume handle
        try:
            handle = get_volume_handle(volume_path)
        except Exception as e:
            self._logger.exception(f"Failed to open volume {volume}: {e}")
            raise

        # Initialize the USN Journal
        try:
            # Get actual USN journal info
            journal_data = query_usn_journal(handle)

            # Print the journal info
            ic(f"Journal ID: {journal_data.UsnJournalID}")
            ic(f"First USN: {journal_data.FirstUsn}")
            ic(f"Next USN: {journal_data.NextUsn}")

            # Convert to dictionary for consistency
            usn_journal_info = {
                "UsnJournalID": journal_data.UsnJournalID,
                "FirstUsn": journal_data.FirstUsn,
                "NextUsn": journal_data.NextUsn,
                "LowestValidUsn": journal_data.LowestValidUsn,
                "MaxUsn": journal_data.MaxUsn,
                "MaximumSize": journal_data.MaximumSize,
                "AllocationDelta": journal_data.AllocationDelta,
            }
            ic(usn_journal_info)
        except Exception as e:
            self._logger.exception(f"Error initializing USN journal: {e}")
            # Close handle and re-raise
            with contextlib.suppress(Exception):
                ctypes.windll.kernel32.CloseHandle(handle)
            raise

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

    def _monitor_usn_journal(self, volume: str) -> None:
        """
        Monitor the USN Journal for a specific volume.

        Args:
            volume: The volume to monitor (e.g., "C:")
        """
        # Get the handle and journal info
        handle = self._volume_handles.get(volume)
        journal_info = self._usn_journals.get(volume)

        if not handle:
            self._logger.error("Missing handle for volume %s", volume)
            ic(f"ERROR: Missing handle for volume {volume}")
            return

        try:
            journal_id = journal_info["UsnJournalID"]
            first_usn = journal_info["FirstUsn"]

            # Use saved state if available
            if volume in self._last_processed_usn:
                saved_usn = self._last_processed_usn[volume]

                # Simply use the max of last processed USN and lowest valid USN
                next_usn = max(saved_usn, journal_info["LowestValidUsn"])

                if next_usn > saved_usn:
                    ic(
                        f"Saved USN position {saved_usn} is older than oldest available ({journal_info['LowestValidUsn']})",
                    )
                    ic(f"Starting from USN {next_usn}")
                else:
                    ic(f"Resuming from saved USN position: {next_usn}")
            else:
                next_usn = first_usn
                ic(
                    f"No saved state for volume {volume}, starting from first USN: {first_usn}",
                )
        except (KeyError, TypeError) as e:
            self._logger.exception("Invalid journal info structure: %s", e)
            ic(f"ERROR: Invalid journal info structure: {e}")
            return

        self._logger.info("Starting monitoring of USN journal on volume %s", volume)
        ic(f"Starting monitoring of USN journal on volume {volume}")
        ic(f"Journal ID: {journal_id}, First USN: {first_usn}")

        # Create a test file to trigger USN journal activity
        test_dir = os.path.join(volume, "Indaleko_Test")
        try:
            if not os.path.exists(test_dir):
                os.makedirs(test_dir, exist_ok=True)

            test_filename = os.path.join(test_dir, f"usn_test_{int(time.time())}.txt")
            with open(test_filename, "w", encoding="utf-8") as f:
                f.write(f"USN Journal Test File - {datetime.now()}")
            ic(f"Created test file {test_filename} to trigger USN journal activity")
        except Exception as e:
            ic(f"Error creating test file: {e}")

        # Record counter for debug output
        record_count = 0

        # Main monitoring loop
        while not self._stop_event.is_set():
            try:
                try:
                    # Read the journal using our implementation
                    buffer, bytes_returned = read_usn_journal(
                        handle,
                        journal_id,
                        next_usn,
                    )
                except Exception as e:
                    ic(f"Error reading USN journal: {e} for usn {next_usn}")

                    # Get current journal info
                    try:
                        journal_data = query_usn_journal(handle)
                        ic(
                            f"Current journal state - First USN: {journal_data.FirstUsn}, Next USN: {journal_data.NextUsn}",
                        )

                        # If our next_usn is outside the valid range, adjust it
                        if next_usn < journal_data.LowestValidUsn:
                            next_usn = journal_data.FirstUsn
                            ic(f"Adjusting next_usn to journal's first USN: {next_usn}")
                    except Exception as journal_error:
                        ic(f"Could not query journal: {journal_error}")

                    # Create minimal valid result with just an incremented USN
                    buffer = ctypes.create_string_buffer(8)
                    next_usn += 1  # Increment by 1 to make progress
                    struct.pack_into("<Q", buffer, 0, next_usn)
                    bytes_returned = 8

                if bytes_returned > 8:  # Make sure we got more than just the next USN
                    ic(f"Read {bytes_returned} bytes from USN journal")

                # Parse the data
                offset = 8  # Skip first 8 bytes (NextUsn)
                records_in_batch = 0

                while offset < bytes_returned:
                    record = parse_usn_record(buffer, offset, bytes_returned)
                    if record is None:
                        ic(f"Failed to parse record at offset {offset}")
                        break

                    # Process the record
                    self._process_usn_record(volume, record)
                    records_in_batch += 1
                    record_count += 1

                    # Move to the next record
                    record_length = struct.unpack_from("<I", buffer, offset)[0]
                    offset += record_length

                if records_in_batch > 0:
                    ic(
                        f"Processed {records_in_batch} records in this batch. Total: {record_count}",
                    )

                # Update the next USN for the next read
                next_usn = struct.unpack_from("<Q", buffer, 0)[0]  # Extract NextUsn from buffer

                # Save the USN position for this volume
                self._last_processed_usn[volume] = next_usn

                # Periodically save state (every 100 records)
                if record_count % 100 == 0 and record_count > 0:
                    self._save_state()

                # Brief pause to avoid hammering the system
                time.sleep(0.1)

            except Exception as e:
                ic(f"Error reading USN journal on volume {volume}: {e}")

                # Enhanced error diagnostics
                import traceback

                traceback.print_exc()

                # Show OS error if available
                if hasattr(e, "winerror"):
                    ic(f"Windows error code: {e.winerror}")
                    if e.winerror == 5:  # ERROR_ACCESS_DENIED
                        ic("\nAccess denied error detected.")
                        ic(
                            "This error typically occurs when the process doesn't have sufficient privileges.",
                        )
                        ic("Possible solutions:")
                        ic(
                            "1. Run the process as administrator (right-click, 'Run as Administrator')",
                        )
                        ic(
                            "2. Ensure your user account has the 'Manage auditing and security log' privilege",
                        )
                        ic("3. Try enabling/using the unprivileged USN journal access")

                # Check if it looks like a journal problem
                if "invalid parameter" in str(e).lower():
                    ic("\nInvalid parameter error detected.")
                    ic(
                        "This could indicate that the USN journal data structure is incorrect.",
                    )
                    ic("Possible solutions:")
                    ic("1. Double-check the journal_id and start_usn values")
                    ic(
                        "2. Ensure READ_USN_JOURNAL_DATA structure matches exactly what Windows expects",
                    )

                # Check for buffer-related problems
                if "buffer" in str(e).lower():
                    ic("\nBuffer-related error detected.")
                    ic("This could be related to memory allocation or buffer sizing.")
                    ic("Possible solutions:")
                    ic("1. Try with a smaller buffer size")
                    ic("2. Check memory allocation in read_usn_journal")

                # Wait before retrying
                ic("\nWaiting before retry...")
                time.sleep(1)

        ic(
            f"Stopped monitoring USN journal on volume {volume}. Processed {record_count} total records.",
        )

    def _process_usn_record(self, volume: str, record: dict[str, Any]) -> None:
        """
        Process a USN record and create an activity from it.

        Args:
            volume: The volume the record is from
            record: The parsed USN record
        """
        # Add debug print to see what records we're getting
        ic(f"Processing USN record: {record}")

        try:
            # Skip excluded files
            file_name = record.get("FileName", "")
            if any(file_name.startswith(exc) for exc in self._excluded_paths):
                ic(f"Skipping excluded file: {file_name}")
                return

            # Skip excluded extensions
            if "." in file_name:
                ext = file_name.split(".")[-1].lower()
                if ext in self._excluded_extensions:
                    ic(f"Skipping excluded extension: {ext} for file {file_name}")
                    return

            # Determine the activity type based on reason flags
            reason_flags_list = record.get("Reasons", [])
            reason_flags = 0  # Default value

            # Convert the reason flags from list of strings to a numeric value
            for reason in reason_flags_list:
                for flag, name in REASON_FLAGS.items():
                    if name == reason:
                        reason_flags |= flag

            activity_type = self._determine_activity_type(reason_flags)
            ic(
                f"Determined activity type: {activity_type} for {file_name} (reasons: {reason_flags_list})",
            )

            # Skip close events if configured to do so
            if activity_type == StorageActivityType.CLOSE and not self._include_close_events:
                ic(
                    f"Skipping CLOSE event for {file_name} (include_close_events is False)",
                )
                return

            # Check if it's a directory
            is_directory = "DIRECTORY" in record.get("Attributes", [])

            # Create the path - in a full implementation, this would be more sophisticated
            file_path = f"{volume}\\{file_name}"

            # Use volume GUID if available
            if self._use_volume_guids:
                try:
                    drive_letter = volume[0] if volume else "C"
                    guid = self.map_drive_letter_to_volume_guid(drive_letter)
                    if guid:
                        file_path = f"\\\\?\\Volume{{{guid}}}\\{file_name}"
                except Exception as e:
                    self._logger.debug(f"Error creating path with GUID: {e}")

            # Create activity data
            activity_data = NtfsStorageActivityData(
                timestamp=record.get("Timestamp", datetime.now(UTC)),
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
                provider_type=StorageProviderType.LOCAL_NTFS,
                provider_id=self._provider_id,
                item_type=(StorageItemType.DIRECTORY if is_directory else StorageItemType.FILE),
            )

            # Add the activity
            self.add_activity(activity_data)
            ic(f"Added activity for {file_name} of type {activity_type}")
            ic(f"Current activities count: {len(self._activities)}")
        except Exception as e:
            ic(f"Error processing USN record: {e}")
            import traceback

            traceback.print_exc()

    def _event_processing_thread(self) -> None:
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
                self._logger.exception(f"Error processing event: {e}")

    def _process_event(self, event: dict[str, Any]) -> None:
        """
        Process a USN journal event.

        Args:
            event: The event to process
        """
        # Extract event data
        volume = event.get("volume")
        record = event.get("record", {})

        # Process the event and create an activity
        self._process_usn_record(volume, record)

    def _determine_activity_type(self, reason_flags: int) -> StorageActivityType:
        """
        Determine the activity type from the reason flags.

        Args:
            reason_flags: The reason flags from the USN record

        Returns:
            The determined activity type
        """
        # Handle real Windows USN reason flags
        try:
            # Use our defined constants directly
            if reason_flags & 0x00000100:  # FILE_CREATE
                return StorageActivityType.CREATE
            if reason_flags & 0x00000200:  # FILE_DELETE
                return StorageActivityType.DELETE
            if reason_flags & 0x00001000 or reason_flags & 0x00002000:  # RENAME_OLD_NAME or RENAME_NEW_NAME
                return StorageActivityType.RENAME
            if reason_flags & 0x00000800:  # SECURITY_CHANGE
                return StorageActivityType.SECURITY_CHANGE
            if (
                reason_flags & 0x00000400
                or reason_flags & 0x00008000
                or reason_flags & 0x00020000
                or reason_flags & 0x00040000
            ):  # Various attribute changes
                return StorageActivityType.ATTRIBUTE_CHANGE
            if reason_flags & 0x80000000:  # CLOSE
                return StorageActivityType.CLOSE
            if (
                reason_flags & 0x00000001 or reason_flags & 0x00000002 or reason_flags & 0x00000004
            ):  # DATA_OVERWRITE, DATA_EXTEND, DATA_TRUNCATION
                return StorageActivityType.MODIFY
            return StorageActivityType.OTHER
        except Exception as e:
            self._logger.warning(
                f"Error determining activity type: {e}, using default MODIFY",
            )
            # Fall back to a common activity type if something goes wrong
            return StorageActivityType.MODIFY

    def collect_data(self) -> None:
        """
        Collect storage activity data from NTFS volumes.

        This method starts monitoring if not already active and returns
        currently collected activities.
        """
        with self.perf_context("collect_data"):
            if not self._active:
                self.start_monitoring()

            # Let it run for a bit to collect some data
            if not self._activities:
                time.sleep(2)

            return

    def save_activities_to_file(self, output_file=None):
        """
        Save collected activities to a file.

        Args:
            output_file: Optional file path. If not provided, uses the one from initialization
        """
        file_path = output_file
        if not file_path and hasattr(self, "_output_path"):
            file_path = self._output_path

        if not file_path:
            # Default to a timestamped file in the current directory
            file_path = f"ntfs_activities_{int(time.time())}.json"

        self._logger.info(f"Saving activities to {file_path}")

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                # Convert activities to JSON-serializable format
                activities_json = []
                for activity in self._activities:
                    # Convert timezone-aware datetime to ISO format string
                    activity_dict = activity.model_dump()
                    if activity_dict.get("timestamp"):
                        activity_dict["timestamp"] = activity_dict["timestamp"].isoformat()
                    activities_json.append(activity_dict)

                json.dump(activities_json, f, indent=2)

            self._logger.info(
                "Saved %d activities to %s",
                len(self._activities),
                file_path,
            )
            return file_path
        except Exception as e:
            self._logger.exception(f"Error saving activities to file: {e}")
            return None

    @classmethod
    def get_collector_cli_handler_mixin(cls):
        """Get the CLI handler mixin for this collector."""
        return cls.cli_handler_mixin

    class cli_handler_mixin(IndalekoBaseCLI.default_handler_mixin):
        """CLI handler mixin for the NTFS collector."""

        @staticmethod
        def get_pre_parser() -> argparse.ArgumentParser | None:
            """Get the pre-parser for command line arguments."""
            parser = argparse.ArgumentParser(add_help=False)

            # Add NTFS collector specific arguments
            parser.add_argument(
                "--volumes",
                help="Comma-separated list of volumes to monitor (default=C:)",
                type=str,
                default="C:",
            )
            parser.add_argument(
                "--no-volume-guids",
                help="Disable use of volume GUIDs for stable paths",
                action="store_true",
            )
            parser.add_argument(
                "--include-close-events",
                help="Include file close events in activity collection",
                action="store_true",
            )
            parser.add_argument(
                "--monitor-interval",
                help="Interval in seconds between monitoring checks (default=1.0)",
                type=float,
                default=1.0,
            )
            parser.add_argument(
                "--try-unprivileged",
                help="Try unprivileged USN journal access if regular access fails",
                action="store_true",
                default=True,
            )
            return parser

        @staticmethod
        def load_machine_config(keys: dict[str, str]) -> "IndalekoMachineConfig":
            """Load the machine configuration."""
            if "machine_config_file" not in keys:
                raise ValueError(
                    "load_machine_config: machine_config_file must be specified",
                )
            offline = keys.get("offline", False)
            platform_class = keys["class"]  # must exist
            return platform_class.load_config_from_file(
                config_file=str(keys["machine_config_file"]),
                offline=offline,
            )

    @staticmethod
    def ntfs_run(keys: dict[str, str]) -> dict | None:
        """Run the NTFS collector."""
        # Check if we're just asking for help
        args = keys["args"]
        if hasattr(args, "help") and args.help:
            return None

        # Verify we're on Windows with pywin32 available before proceeding
        if not WINDOWS_AVAILABLE:
            ic("USN Journal data collection only works on Windows platforms.")
            ic(
                "This script can show help on any platform, but requires Windows to actually run.",
            )
            sys.exit(1)

        if not PYWIN32_AVAILABLE:
            ic(
                "This script requires pywin32. Please install it with 'pip install pywin32'",
            )
            sys.exit(1)

        args = keys["args"]  # must be there.
        cli = keys["cli"]  # must be there.
        config_data = cli.get_config_data()
        debug = hasattr(args, "debug") and args.debug

        # Get the machine config class and collector class
        machine_config_class = keys["parameters"]["MachineConfigClass"]
        collector_class = keys["parameters"]["CollectorClass"]

        # Create output filenames
        output_file = os.path.join(args.datadir, config_data["OutputFile"])

        # Load machine config
        machine_config = cli.handler_mixin.load_machine_config(
            {
                "machine_config_file": os.path.join(
                    args.configdir,
                    args.machine_config,
                ),
                "offline": args.offline,
                "class": machine_config_class,
            },
        )

        # Parse the volumes
        volumes = args.volumes.split(",") if hasattr(args, "volumes") else ["C:"]

        # Create the collector
        collector = collector_class(
            machine_config=machine_config,
            volumes=volumes,
            use_volume_guids=(not args.no_volume_guids if hasattr(args, "no_volume_guids") else True),
            include_close_events=(args.include_close_events if hasattr(args, "include_close_events") else False),
            monitor_interval=(args.monitor_interval if hasattr(args, "monitor_interval") else 1.0),
            try_unprivileged=(args.try_unprivileged if hasattr(args, "try_unprivileged") else True),
            debug=debug,
            timestamp=config_data["Timestamp"],
            output_path=output_file,
        )

        # Performance measurement wrapper
        def collect_data(collector, **kwargs) -> None:
            collector.collect_data()

        def extract_counters(**kwargs):
            collector = kwargs.get("collector")
            if collector:
                return {"activities": len(collector.get_activities())}
            return {}

        # Measure performance and collect data
        with collector.perf_context("total_collection_time"):
            # Collect the data
            collector.collect_data()

            # Let it run for a bit to collect activities
            time.sleep(5)

            # Save activities to file
            collector.save_activities_to_file()

            # Stop monitoring
            collector.stop_monitoring()

        # Log some stats
        if debug:
            activity_count = len(collector.get_activities())
            ic(f"Collected {activity_count} activities")

        return None


def main() -> None:
    """The CLI handler for the NTFS storage activity collector."""
    try:
        # Don't attempt to import Windows-specific modules if we're just showing help
        if "--help" in sys.argv or "-h" in sys.argv:
            # For help command, use a generic machine config
            from platforms.machine_config import IndalekoMachineConfig

            MachineConfigClass = IndalekoMachineConfig
        else:
            # For actual operation, check platform
            if not WINDOWS_AVAILABLE:
                ic("USN Journal data collection only works on Windows platforms.")
                ic(
                    "This script can show help on any platform, but requires Windows to actually run.",
                )
                sys.exit(1)

            # Make sure pywin32 is available
            if not PYWIN32_AVAILABLE:
                ic(
                    "This script requires pywin32. Please install it with 'pip install pywin32'",
                )
                sys.exit(1)

            # Now it's safe to import Windows-specific modules
            from platforms.windows.machine_config import IndalekoWindowsMachineConfig

            MachineConfigClass = IndalekoWindowsMachineConfig

        # Create the CLI runner
        cli_runner = IndalekoCLIRunner(
            cli_data=IndalekoBaseCliDataModel(
                RegistrationServiceName=NtfsStorageActivityCollectorV2.get_collector_service_registration_name(),
                FileServiceName=NtfsStorageActivityCollectorV2.get_collector_service_file_name(),
            ),
            handler_mixin=NtfsStorageActivityCollectorV2.get_collector_cli_handler_mixin(),
            features=IndalekoBaseCLI.cli_features(input=False),
            Run=NtfsStorageActivityCollectorV2.ntfs_run,
            RunParameters={
                "CollectorClass": NtfsStorageActivityCollectorV2,
                "MachineConfigClass": MachineConfigClass,
            },
        )

        # Run the CLI runner
        cli_runner.run()
    except Exception as e:
        ic(f"Error running NTFS collector: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
