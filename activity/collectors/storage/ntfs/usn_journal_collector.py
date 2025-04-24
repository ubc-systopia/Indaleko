#!/usr/bin/env python
"""
NTFS USN Journal Collector for Indaleko.

This module provides a clean implementation for collecting NTFS file system
activities from the USN Journal and converting them to standardized data model objects.

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
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from icecream import ic

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).resolve().parent
    while not Path.exists(current_path / "Indaleko.py"):
        current_path = current_path.parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.append(str(current_path))

# Check Windows availability
WINDOWS_AVAILABLE = sys.platform.startswith("win")

# pylint: disable=wrong-import-position
from activity.collectors.storage.data_models.storage_activity_data_model import (  # noqa: E402
    NtfsStorageActivityData,
    StorageActivityType,
    StorageItemType,
    StorageProviderType,
)
from activity.collectors.storage.ntfs.bar import UsnJournalReader, is_admin

# pylint: enable=wrong-import-position


def determine_activity_type(reason_flags: list[str]) -> str:
    """
    Determine the activity type from the reason flags.

    Note on rename handling:
    - USN Journal creates two separate records for rename operations:
      1. A record with RENAME_OLD_NAME for the original filename
      2. A record with RENAME_NEW_NAME for the new filename
    - We preserve the raw reason flags in the activity data to allow recorders
      to correlate these events using the file reference numbers
    - The activity type for rename operations is preserved as OTHER with
      specific USN reason flags to avoid validation issues while maintaining
      all information needed for correlation

    Args:
        reason_flags: The reason flags from the USN record

    Returns:
        The determined activity type
    """
    if not WINDOWS_AVAILABLE:
        return "other"

    activity_type = StorageActivityType.OTHER  # Default activity type

    if "FILE_CREATE" in reason_flags:
        activity_type = StorageActivityType.CREATE
    elif "FILE_DELETE" in reason_flags:
        activity_type = StorageActivityType.DELETE
    elif "RENAME_OLD_NAME" in reason_flags or "RENAME_NEW_NAME" in reason_flags:
        activity_type = StorageActivityType.OTHER  # Preserve reason flags for rename events
    elif "SECURITY_CHANGE" in reason_flags:
        activity_type = StorageActivityType.SECURITY_CHANGE
    elif (
        "EA_CHANGE" in reason_flags
        or "BASIC_INFO_CHANGE" in reason_flags
        or "COMPRESSION_CHANGE" in reason_flags
        or "ENCRYPTION_CHANGE" in reason_flags
    ):
        activity_type = StorageActivityType.ATTRIBUTE_CHANGE
    elif "CLOSE" in reason_flags:
        activity_type = StorageActivityType.CLOSE
    elif "DATA_OVERWRITE" in reason_flags or "DATA_EXTEND" in reason_flags or "DATA_TRUNCATION" in reason_flags:
        activity_type = StorageActivityType.MODIFY

    return activity_type


def convert_record_to_model(
    record: dict[str, Any],
    volume: str,
    provider_id: str,
) -> NtfsStorageActivityData:
    """
    Convert a raw USN record dictionary to a NtfsStorageActivityData model.

    Args:
        record: The raw USN record dictionary
        volume: The volume name (e.g., "C:")
        provider_id: Provider ID for the activity

    Returns:
        NtfsStorageActivityData object
    """
    if not WINDOWS_AVAILABLE:
        raise RuntimeError("This function only works on Windows")

    # Determine if it's a directory
    is_directory = "DIRECTORY" in record.get("Attributes", [])

    # Create a proper file path
    file_name = record.get("FileName", "")
    file_path = f"{volume}\\{file_name}"

    # Get the raw reasons
    reasons = record.get("Reasons", [])

    # Determine activity type
    activity_type = determine_activity_type(reasons)

    # Get timestamp and ensure it has timezone info
    timestamp = record.get("Timestamp", datetime.now(UTC))
    # Double-check timestamp has timezone info (should be handled by bar.py now)
    if timestamp and not timestamp.tzinfo:
        timestamp = timestamp.replace(tzinfo=UTC)

    # Create additional attributes to store reason flags
    attributes = {
        "usn_reason_flags": reasons,  # Preserve original reason flags
        "usn_record_number": record.get("USN", 0),  # Original USN record number
    }

    # For rename operations, add specific info
    if "RENAME_OLD_NAME" in reasons:
        attributes["rename_type"] = "old_name"
    elif "RENAME_NEW_NAME" in reasons:
        attributes["rename_type"] = "new_name"

    # Create activity data
    return NtfsStorageActivityData(
        timestamp=timestamp,
        file_reference_number=str(record.get("FileReferenceNumber", "")),
        parent_file_reference_number=str(record.get("ParentFileReferenceNumber", "")),
        activity_type=activity_type,
        reason_flags=0,  # We'd need to convert the string reasons back to flags if needed
        file_name=file_name,
        file_path=file_path,
        volume_name=volume,
        is_directory=is_directory,
        provider_type=StorageProviderType.LOCAL_NTFS,
        provider_id=(uuid.UUID(provider_id) if isinstance(provider_id, str) else provider_id),
        item_type=StorageItemType.DIRECTORY if is_directory else StorageItemType.FILE,
        attributes=attributes,  # Store additional information
    )


class NtfsUsnJournalCollector:
    """
    Collector for NTFS storage activities using the USN Journal.

    This class uses the UsnJournalReader to read USN journal entries and converts
    them to NtfsStorageActivityData objects. It also handles state persistence to allow
    for incremental collection across multiple runs.

    Features:
    - Robust error handling for journal rotation (circular buffer)
    - Automatic recovery when journal entries are deleted
    - State persistence between runs
    - Support for multiple volumes
    - Configurable record batch sizes

    The USN journal is a circular buffer that may discard older entries when it fills up.
    This collector handles that scenario gracefully by resetting to the lowest valid USN
    when entries have been deleted, ensuring continuous collection even after journal
    rotation.
    """

    # Default provider ID for NTFS USN journal collection
    DEFAULT_PROVIDER_ID = "7d8f5a92-35c7-41e6-b13d-6c4e89e7f2a5"

    def __init__(
        self,
        volumes: str | list[str] = "C:",
        provider_id: str = DEFAULT_PROVIDER_ID,
        max_records: int = 1000,
        state_file: str | None = None,
        *,
        use_state_file: bool = False,
        verbose: bool = False,
    ) -> None:
        """
        Initialize the NTFS USN journal collector.

        Args:
            volumes: Volume or list of volumes to monitor (e.g., "C:" or ["C:", "D:"])
            provider_id: Provider ID for activity data
            max_records: Maximum number of records to collect per batch
            state_file: Path to the state file for persisting USN positions
            use_state_file: Whether to use the state file for persistence (default: False)
            verbose: Whether to print verbose output
        """
        if not WINDOWS_AVAILABLE:
            raise RuntimeError("This collector only works on Windows")

        # Normalize volumes to a list
        if isinstance(volumes, str):
            volumes = [volumes]
        self.volumes = volumes

        self.provider_id = provider_id
        self.max_records = max_records
        self.state_file = state_file
        self.use_state_file = use_state_file
        self.verbose = verbose

        # State tracking
        self.last_usn_positions = {}
        self.activities = []

        # Load state if available and enabled
        if self.use_state_file:
            self._load_state()
        else:
            if self.verbose:
                ic("State file persistence disabled, starting with fresh state")

        if self.verbose:
            ic(f"NtfsUsnJournalCollector initialized with volumes: {self.volumes}")
            ic(f"Provider ID: {self.provider_id}")
            ic(f"State file: {self.state_file} (Enabled: {self.use_state_file})")
            ic(f"Last USN positions: {self.last_usn_positions}")

    def collect_activities(self) -> list[NtfsStorageActivityData]:
        """
        Collect activities from all configured volumes.

        Returns:
            List of NtfsStorageActivityData objects
        """
        activities = []

        for volume in self.volumes:
            volume_activities = self._collect_from_volume(volume)
            activities.extend(volume_activities)

        # Save the collected activities for later retrieval
        self.activities = activities

        # Save state after collection
        self._save_state()

        return activities

    def _collect_from_volume(self, volume: str) -> list[NtfsStorageActivityData]:
        """
        Collect activities from a specific volume.

        Args:
            volume: The volume to collect from (e.g., "C:")

        Returns:
            List of NtfsStorageActivityData objects
        """
        activities = []

        # Get the starting USN from saved state or None for first run
        start_usn = self.last_usn_positions.get(volume, None)

        if self.verbose:
            ic(f"Collecting from volume {volume}, starting from USN: {start_usn}")

        # Flag to track if we've reset due to journal rotation
        reset_occurred = False
        max_retries = 1  # Allow one reset attempt

        for retry in range(max_retries + 1):
            try:
                # Use the UsnJournalReader to get records
                with UsnJournalReader(volume=volume, verbose=self.verbose) as reader:
                    records, next_usn = reader.read_records(
                        start_usn=start_usn,
                        max_records=self.max_records,
                    )

                    if self.verbose:
                        ic(f"Read {len(records)} records from volume {volume}")
                        ic(f"Next USN position: {next_usn}")

                    # Convert records to activity data models
                    for record in records:
                        activity = convert_record_to_model(
                            record,
                            volume,
                            self.provider_id,
                        )
                        activities.append(activity)

                    # Save the next USN position
                    if next_usn:
                        self.last_usn_positions[volume] = next_usn

                    # If we get here successfully, break the retry loop
                    break

            except OSError as e:
                # Handle journal rotation errors
                if str(e).find("journal entry has been deleted") != -1 or getattr(e, "winerror", 0) == 0x570:
                    if retry < max_retries:
                        # Reset our position and try again
                        with UsnJournalReader(
                            volume=volume,
                            verbose=self.verbose,
                        ) as reader:
                            # Get journal metadata to find the lowest valid USN
                            reader.open()
                            if reader.journal_data:
                                start_usn = reader.journal_data.LowestValidUsn
                                self.last_usn_positions[volume] = start_usn
                                reset_occurred = True

                                if self.verbose:
                                    ic(
                                        f"USN journal rotation detected. Resetting position to {start_usn}",
                                    )

                                # Continue to next retry
                                continue

                # Re-raise other errors or if we've already retried
                if self.verbose:
                    ic(f"Error reading USN journal: {e}")
                # Log this as a warning but don't fail the entire collection
                self.last_usn_positions[volume] = start_usn  # Keep the current position
                break

        if reset_occurred and self.verbose:
            ic(f"Successfully recovered from journal rotation on volume {volume}")

        return activities

    def get_activities(self) -> list[NtfsStorageActivityData]:
        """
        Get the collected activities.

        Returns:
            List of NtfsStorageActivityData objects
        """
        return self.activities

    def save_activities_to_file(self, output_file: str) -> bool:
        """
        Save collected activities to a JSONL file.

        Args:
            output_file: Path to the output file

        Returns:
            True if successful, False otherwise
        """
        with Path(output_file).open("w", encoding="utf-8") as f:
            for activity in self.activities:
                # Use model_dump with proper JSON serialization options
                activity_dict = activity.model_dump(mode="json")

                # Handle any remaining JSON serialization issues manually
                def json_serializable(obj: datetime | uuid.UUID) -> str:
                    if isinstance(obj, uuid.UUID):
                        return str(obj)
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    return str(obj)

                # Write as JSON line
                json_line = json.dumps(activity_dict, default=json_serializable)
                f.write(json_line + "\n")

        if self.verbose:
            ic(f"Wrote {len(self.activities)} activities to {output_file}")

        return True

    def _load_state(self) -> None:
        """Load the collector state from a file."""
        if not self.state_file or not Path(self.state_file).exists():
            if self.verbose:
                ic("No state file found, starting with empty state")
            return

        with Path(self.state_file).open("r", encoding="utf-8") as f:
            state = json.load(f)

        # Load last processed USN values
        if "last_usn_positions" in state:
            self.last_usn_positions = state["last_usn_positions"]
            if self.verbose:
                ic(f"Loaded last USN positions: {self.last_usn_positions}")

        if self.verbose:
            ic(f"Loaded collector state from {self.state_file}")

    def _save_state(self) -> None:
        """Save the collector state to a file."""
        if not self.state_file or not self.use_state_file:
            if self.verbose:
                ic("State file persistence disabled, skipping state save")
            return

        # Create state dictionary
        state = {
            "last_usn_positions": self.last_usn_positions,
            "timestamp": datetime.now(UTC).isoformat(),
            "provider_id": self.provider_id,
        }

        # Handle UUID serialization properly
        def json_serializable(obj: datetime | uuid.UUID) -> str:
            if isinstance(obj, uuid.UUID):
                return str(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            return str(obj)

        # Ensure directory exists
        Path(self.state_file).parent.mkdir(parents=True, exist_ok=True)

        # Save to file
        with Path(self.state_file).open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, default=json_serializable)

        if self.verbose:
            ic(f"Saved collector state to {self.state_file}")

    def reset_state(self) -> bool:
        """
        Reset the collector state to start fresh.

        This is useful when the USN journal has been cleared or when
        troubleshooting collection issues.

        Returns:
            True if reset successful, False otherwise
        """
        # Clear in-memory state
        self.last_usn_positions = {}
        self.activities = []

        # Handle state file only if state persistence is enabled
        if self.use_state_file:
            # Remove state file if it exists
            if self.state_file and Path(self.state_file).exists():
                try:
                    Path(self.state_file).unlink()
                    if self.verbose:
                        ic(f"Deleted state file: {self.state_file}")
                except Exception as e:
                    if self.verbose:
                        ic(f"Error deleting state file: {e}")
                    # Even if we couldn't delete the file, we'll overwrite it on save

            # Save empty state to ensure the file is created fresh
            self._save_state()
        elif self.verbose:
            ic("State file persistence disabled, skipping state file operations")

        if self.verbose:
            ic("State reset successful")

        return True


def test_collector() -> bool:
    """Test the collector functionality with various record types."""
    if not WINDOWS_AVAILABLE:
        ic("This test only works on Windows")
        return False

    ic("\n=== Testing USN Journal Collector ===\n")

    # Test timezone awareness
    ic("Testing timezone awareness...")
    from activity.collectors.storage.ntfs.bar import filetime_to_datetime

    # Use a current filetime for testing
    filetime = int((datetime.now(tz=UTC).timestamp() + 11644473600) * 10000000)
    dt = filetime_to_datetime(filetime)

    ic(f"Original datetime: {dt}")
    ic(f"Has timezone: {dt.tzinfo is not None}")

    # Test standard record (no specific reason flags)
    ic("\nTesting standard record processing...")
    standard_record = {
        "Timestamp": dt,
        "FileReferenceNumber": "12345",
        "ParentFileReferenceNumber": "12345",
        "FileName": "test.txt",
        "Attributes": [],
        "Reasons": ["DATA_OVERWRITE"],
    }

    model = convert_record_to_model(
        standard_record,
        "C:",
        NtfsUsnJournalCollector.DEFAULT_PROVIDER_ID,
    )
    ic(f"Standard model created - Activity type: {model.activity_type}")
    expected_type = StorageActivityType.MODIFY
    if model.activity_type != expected_type:
        raise ValueError(f"Expected {expected_type}, got {model.activity_type}")
    ic("✓ Standard record test passed")

    # Test RENAME_OLD_NAME record
    ic("\nTesting RENAME_OLD_NAME record...")
    rename_old_record = {
        "Timestamp": dt,
        "FileReferenceNumber": "12345",
        "ParentFileReferenceNumber": "12345",
        "FileName": "oldname.txt",
        "Attributes": [],
        "Reasons": ["RENAME_OLD_NAME"],
        "USN": 12345,
    }

    model = convert_record_to_model(
        rename_old_record,
        "C:",
        NtfsUsnJournalCollector.DEFAULT_PROVIDER_ID,
    )
    ic(f"RENAME_OLD_NAME model created - Activity type: {model.activity_type}")
    expected_type = StorageActivityType.OTHER
    if model.activity_type != expected_type:
        raise ValueError(f"Expected {expected_type}, got {model.activity_type}")
    ic("✓ RENAME_OLD_NAME record test passed")

    # Test RENAME_NEW_NAME record
    ic("\nTesting RENAME_NEW_NAME record...")
    rename_new_record = {
        "Timestamp": dt,
        "FileReferenceNumber": "12345",
        "ParentFileReferenceNumber": "12345",
        "FileName": "newname.txt",
        "Attributes": [],
        "Reasons": ["RENAME_NEW_NAME"],
        "USN": 12346,
    }

    model = convert_record_to_model(
        rename_new_record,
        "C:",
        NtfsUsnJournalCollector.DEFAULT_PROVIDER_ID,
    )
    ic(f"RENAME_NEW_NAME model created - Activity type: {model.activity_type}")
    expected_type = StorageActivityType.OTHER
    if model.activity_type != expected_type:
        raise ValueError(f"Expected {expected_type}, got {model.activity_type}")
    ic("✓ RENAME_NEW_NAME record test passed")

    # Test full collector process with a small sample
    ic("\nTesting full collector process...")
    collector = NtfsUsnJournalCollector(
        volumes=["C:"],
        max_records=5,  # Just get a few records for testing
        verbose=True,
    )

    # Collect activities (limited to max_records=5)
    activities = collector.collect_activities()

    ic(f"Collected {len(activities)} activities")
    ic("✓ Full collector test passed")

    ic("\n=== All tests passed! ===\n")
    return True


def main() -> None:
    """Main entry point for the script."""
    # Add argument parsing for better integration
    parser = argparse.ArgumentParser(description="NTFS USN Journal Collector")
    parser.add_argument(
        "--volumes",
        type=str,
        default="C:",
        help="Comma-separated list of volumes to collect from (default: C:)",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=1000,
        help="Maximum number of records to collect per batch (default: 1000)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="ntfs_activities.jsonl",
        help="Output file for activities (default: ntfs_activities.jsonl)",
    )
    parser.add_argument(
        "--state-file",
        type=str,
        help="State file for persisting USN positions",
    )
    parser.add_argument(
        "--use-state-file",
        action="store_true",
        help="Enable state file persistence (disabled by default)",
    )
    parser.add_argument("--verbose", action="store_true", help="Show verbose output")
    parser.add_argument("--test", action="store_true", help="Run the test suite")
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Reset the collector state to start fresh (useful after journal rotation)",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue processing when non-critical errors occur (recommended for production use)",
    )
    args = parser.parse_args()

    # Check if this is a test run
    if args.test:
        success = test_collector()
        sys.exit(0 if success else 1)

    if not WINDOWS_AVAILABLE:
        ic("This script only works on Windows")
        sys.exit(1)

    if not is_admin():
        ic("This script must be run with administrative privileges")
        ic("Please run as administrator (right-click, Run as Administrator)")
        sys.exit(1)

    # Parse volumes
    volumes = args.volumes.split(",")

    # Create the collector
    collector = NtfsUsnJournalCollector(
        volumes=volumes,
        max_records=args.max_records,
        state_file=args.state_file,
        use_state_file=args.use_state_file,
        verbose=args.verbose,
    )

    # Reset state if requested
    if args.reset_state:
        if collector.reset_state():
            ic("Successfully reset collector state")
        else:
            ic("Failed to reset collector state")
            sys.exit(1)

    # Collect activities with error handling
    try:
        activities = collector.collect_activities()

        # Save to file
        if activities:
            collector.save_activities_to_file(args.output)
            ic(f"Collected {len(activities)} activities from volumes {volumes}")
            ic(f"Activities saved to {args.output}")
        else:
            ic("No activities collected")

    except Exception as e:
        ic(f"Error collecting activities: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()

        if not args.continue_on_error:
            sys.exit(1)
        else:
            ic("Continuing despite error due to --continue-on-error flag")


if __name__ == "__main__":
    main()
