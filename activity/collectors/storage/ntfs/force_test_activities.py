#!/usr/bin/env python
"""
Force test activities for NTFS Activity Collector.

This script generates test files and monitors USN journal activity.
It's useful for testing and debugging the NTFS activity collector.

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
import time
from datetime import UTC, datetime
from typing import Any

# Check if we're on Windows
IS_WINDOWS = sys.platform.startswith("win")

# Add parent directories to sys.path
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from activity.collectors.storage.data_models.storage_activity_data_model import (
    NtfsStorageActivityData,
    StorageActivityType,
    StorageItemType,
    StorageProviderType,
)
from activity.collectors.storage.ntfs.usn_journal import (
    create_test_files,
    get_usn_journal_records,
)


def generate_test_files(
    volume: str, num_files: int = 3, verbose: bool = False,
) -> list[str]:
    """Generate test files on the volume."""
    if verbose:
        print(f"Creating {num_files} test files on volume {volume}...")

    # Create test files using our utility function
    created_files = create_test_files(volume, num_files, verbose)

    if verbose:
        print(f"Created {len(created_files)} test files:")
        for filepath in created_files:
            print(f"  - {filepath}")

    return created_files


def map_usn_record_to_activity(usn_record: dict[str, Any]) -> NtfsStorageActivityData:
    """Map a USN journal record to an activity data model."""
    # Extract the reason flags
    reason = usn_record.get("reason", 0)

    # Determine activity type
    activity_type = determine_activity_type(reason)

    # Get timestamp
    timestamp = usn_record.get("timestamp_dt", datetime.now(UTC))

    # Get file attributes
    is_directory = usn_record.get("is_directory", False)
    file_name = usn_record.get("file_name", "Unknown")

    # Create activity data
    return NtfsStorageActivityData(
        timestamp=timestamp,
        file_reference_number=usn_record.get("file_reference_number", "0"),
        parent_file_reference_number=usn_record.get(
            "parent_file_reference_number", "0",
        ),
        activity_type=activity_type,
        reason_flags=reason,
        file_name=file_name,
        file_path=file_name,  # USN records don't include full path
        volume_name="C:",  # Default, will be overridden in real collector
        is_directory=is_directory,
        provider_type=StorageProviderType.LOCAL_NTFS,
        provider_id="00000000-0000-0000-0000-000000000000",  # Placeholder
        item_type=StorageItemType.DIRECTORY if is_directory else StorageItemType.FILE,
        usn=usn_record.get("usn", 0),
    )


def determine_activity_type(reason_flags: int) -> StorageActivityType:
    """Determine activity type from USN reason flags."""
    from activity.collectors.storage.ntfs.usn_journal import (
        USN_REASON_BASIC_INFO_CHANGE,
        USN_REASON_CLOSE,
        USN_REASON_COMPRESSION_CHANGE,
        USN_REASON_DATA_EXTEND,
        USN_REASON_DATA_OVERWRITE,
        USN_REASON_DATA_TRUNCATION,
        USN_REASON_EA_CHANGE,
        USN_REASON_ENCRYPTION_CHANGE,
        USN_REASON_FILE_CREATE,
        USN_REASON_FILE_DELETE,
        USN_REASON_HARD_LINK_CHANGE,
        USN_REASON_INDEXABLE_CHANGE,
        USN_REASON_NAMED_DATA_EXTEND,
        USN_REASON_NAMED_DATA_OVERWRITE,
        USN_REASON_NAMED_DATA_TRUNCATION,
        USN_REASON_OBJECT_ID_CHANGE,
        USN_REASON_RENAME_NEW_NAME,
        USN_REASON_RENAME_OLD_NAME,
        USN_REASON_REPARSE_POINT_CHANGE,
        USN_REASON_SECURITY_CHANGE,
        USN_REASON_STREAM_CHANGE,
    )

    # First priority: file lifecycle events
    if reason_flags & USN_REASON_FILE_CREATE:
        return StorageActivityType.CREATE

    if reason_flags & USN_REASON_FILE_DELETE:
        return StorageActivityType.DELETE

    if (
        reason_flags & USN_REASON_RENAME_OLD_NAME
        or reason_flags & USN_REASON_RENAME_NEW_NAME
    ):
        return StorageActivityType.RENAME

    # Second priority: content changes
    if (
        reason_flags & USN_REASON_DATA_OVERWRITE
        or reason_flags & USN_REASON_DATA_EXTEND
        or reason_flags & USN_REASON_DATA_TRUNCATION
        or reason_flags & USN_REASON_NAMED_DATA_OVERWRITE
        or reason_flags & USN_REASON_NAMED_DATA_EXTEND
        or reason_flags & USN_REASON_NAMED_DATA_TRUNCATION
    ):
        return StorageActivityType.MODIFY

    # Third priority: attribute changes
    if (
        reason_flags & USN_REASON_EA_CHANGE
        or reason_flags & USN_REASON_SECURITY_CHANGE
        or reason_flags & USN_REASON_BASIC_INFO_CHANGE
        or reason_flags & USN_REASON_COMPRESSION_CHANGE
        or reason_flags & USN_REASON_ENCRYPTION_CHANGE
        or reason_flags & USN_REASON_OBJECT_ID_CHANGE
        or reason_flags & USN_REASON_REPARSE_POINT_CHANGE
        or reason_flags & USN_REASON_INDEXABLE_CHANGE
        or reason_flags & USN_REASON_HARD_LINK_CHANGE
        or reason_flags & USN_REASON_STREAM_CHANGE
    ):
        return StorageActivityType.ATTRIBUTE_CHANGE

    # Last priority: close events
    if reason_flags & USN_REASON_CLOSE:
        return StorageActivityType.CLOSE

    # If none of the above, treat as READ or OTHER
    if reason_flags != 0:
        return StorageActivityType.READ

    return StorageActivityType.OTHER


def generate_mock_activities(
    num_activities: int = 5, verbose: bool = False,
) -> list[NtfsStorageActivityData]:
    """Generate mock activities without using the USN journal."""
    if verbose:
        print(f"Generating {num_activities} mock activities...")

    activities = []

    # File types for mock data
    file_types = [
        "document.docx",
        "spreadsheet.xlsx",
        "image.jpg",
        "presentation.pptx",
        "text.txt",
        "archive.zip",
    ]

    # Activity types
    activity_types = [
        StorageActivityType.CREATE,
        StorageActivityType.MODIFY,
        StorageActivityType.READ,
        StorageActivityType.DELETE,
        StorageActivityType.RENAME,
    ]

    # Generate mock activities
    for i in range(num_activities):
        # Select file type and activity type
        file_type_idx = i % len(file_types)
        activity_type_idx = i % len(activity_types)

        file_name = file_types[file_type_idx]
        activity_type = activity_types[activity_type_idx]

        # Create mock path
        file_path = f"C:\\Users\\Documents\\{file_name}"

        # Generate mock file reference numbers
        file_ref = str(int(time.time() * 1000) + i)
        parent_ref = str(int(time.time() * 500) + i)

        # Create activity
        activity = NtfsStorageActivityData(
            timestamp=datetime.now(UTC),
            file_reference_number=file_ref,
            parent_file_reference_number=parent_ref,
            activity_type=activity_type,
            reason_flags=1 << (i % 16),  # Mock reason flags
            file_name=file_name,
            file_path=file_path,
            volume_name="C:",
            is_directory=False,
            provider_type=StorageProviderType.LOCAL_NTFS,
            provider_id="00000000-0000-0000-0000-000000000000",  # Placeholder
            item_type=StorageItemType.FILE,
        )

        activities.append(activity)

        if verbose:
            print(f"  Generated mock activity: {activity_type} - {file_name}")

    return activities


def save_activities_to_file(
    activities: list[NtfsStorageActivityData], output_path: str,
) -> None:
    """Save activities to a JSONL file."""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        # First write the metadata as a single line
        metadata = {
            "record_type": "metadata",
            "timestamp": datetime.now(UTC).isoformat(),
            "total_activities": len(activities),
        }
        f.write(json.dumps(metadata, default=str) + "\n")

        # Then write each activity as a separate line
        for activity in activities:
            activity_data = activity.model_dump()
            activity_data["record_type"] = "activity"
            f.write(json.dumps(activity_data, default=str) + "\n")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Force test activities for NTFS Activity Collector",
    )
    parser.add_argument(
        "--volume", type=str, default="C:", help="Volume to monitor (default: C:)",
    )
    parser.add_argument(
        "--num-files",
        type=int,
        default=3,
        help="Number of test files to create (default: 3)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="ntfs_activities.jsonl",
        help="Output file (default: ntfs_activities.jsonl)",
    )
    parser.add_argument(
        "--mock", action="store_true", help="Use mock activities instead of USN journal",
    )
    parser.add_argument(
        "--num-activities",
        type=int,
        default=5,
        help="Number of mock activities (default: 5)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    # Check if we're on Windows
    if not IS_WINDOWS and not args.mock:
        print("Not running on Windows. Switching to mock mode.")
        args.mock = True

    activities = []

    try:
        # If in mock mode, just generate mock activities
        if args.mock:
            activities = generate_mock_activities(args.num_activities, args.verbose)
        else:
            # Create test files
            generated_files = generate_test_files(
                args.volume, args.num_files, args.verbose,
            )

            # Give the filesystem a moment to process the changes
            if args.verbose:
                print("Waiting for filesystem to process changes...")
            time.sleep(1)

            # Query USN journal
            if args.verbose:
                print(f"Querying USN journal on volume {args.volume}...")

            journal_info, records = get_usn_journal_records(
                args.volume, None, args.verbose,
            )

            if not journal_info or not records:
                print("Failed to get USN journal records. Falling back to mock mode.")
                activities = generate_mock_activities(args.num_activities, args.verbose)
            else:
                if args.verbose:
                    print(f"Got {len(records)} USN journal records.")

                # Convert USN journal records to activities
                activities = [map_usn_record_to_activity(record) for record in records]

                # Limit the number of activities if needed
                if len(activities) > 100:
                    if args.verbose:
                        print(f"Limiting to 100 activities (out of {len(activities)})")
                    activities = activities[:100]

                if args.verbose:
                    print(f"Generated {len(activities)} activities from USN journal.")

        # Save activities to file
        if args.verbose:
            print(f"Saving {len(activities)} activities to {args.output}...")

        save_activities_to_file(activities, args.output)
        print(f"Saved {len(activities)} activities to {args.output}")

    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()

    # Display summary
    print("\nActivity Summary:")
    if activities:
        # Count by type
        activity_counts = {}
        for activity in activities:
            activity_type = str(activity.activity_type)
            if activity_type in activity_counts:
                activity_counts[activity_type] += 1
            else:
                activity_counts[activity_type] = 1

        # Print counts
        for activity_type, count in activity_counts.items():
            print(f"  {activity_type}: {count}")

        # Print a few sample activities
        print("\nSample Activities:")
        for i, activity in enumerate(activities[:5]):
            print(f"  {i+1}. {activity.activity_type} - {activity.file_name}")
    else:
        print("  No activities generated.")


if __name__ == "__main__":
    main()
