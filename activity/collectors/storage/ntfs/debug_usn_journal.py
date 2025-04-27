#!/usr/bin/env python
"""
Debug tool for Windows USN Journal.

This is a minimal script to directly test USN journal functionality
without relying on any other code. Use this to diagnose USN journal issues.

Usage:
    python debug_usn_journal.py C:

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import os
import random
import sys
import time

from datetime import datetime


# Check if running on Windows
if not sys.platform.startswith("win"):
    print("ERROR: This script only works on Windows.")
    sys.exit(1)

# Try to import pywin32 modules
try:
    import pywintypes
    import win32api
    import win32con
    import win32file
except ImportError:
    print("ERROR: This script requires the pywin32 package.")
    print("Install it with: pip install pywin32")
    sys.exit(1)


def create_test_file(volume):
    """Create a test file to generate USN journal activity."""
    try:
        test_dir = os.path.join(volume, "Indaleko_Test")
        os.makedirs(test_dir, exist_ok=True)

        filename = os.path.join(test_dir, f"debug_test_{int(time.time())}.txt")
        with open(filename, "w") as f:
            f.write(f"Test file created at {datetime.now()}\n")
            f.write(f"Random data: {random.randint(1000, 9999)}\n")

        print(f"Created test file: {filename}")
        return filename
    except Exception as e:
        print(f"Error creating test file: {e}")
        return None


def get_volume_handle(volume):
    """Get a handle to the volume."""
    # Clean up volume name
    if volume.endswith("\\") or volume.endswith("/"):
        volume = volume[:-1]

    # Try different volume path formats
    formats = [
        f"{volume}\\",  # C:\
        f"\\\\?\\{volume}\\",  # \\?\C:\
        f"\\\\.\\{volume}",  # \\.\C:
        f"\\\\.\\{volume[0]}:",  # \\.\C:
    ]

    for format in formats:
        try:
            print(f"Trying to open volume with path: {format}")
            handle = win32file.CreateFile(
                format,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                None,
                win32file.OPEN_EXISTING,
                win32file.FILE_ATTRIBUTE_NORMAL,
                None,
            )
            print(f"SUCCESS: Opened volume with path: {format}")
            return handle
        except Exception as e:
            print(f"Failed to open volume with path {format}: {e}")

    return None


def get_usn_journal_info(handle):
    """Get information about the USN journal."""
    if handle is None:
        print("ERROR: Invalid volume handle.")
        return None

    try:
        print("Trying to query USN journal...")
        info = win32file.DeviceIoControl(
            handle,
            win32file.FSCTL_QUERY_USN_JOURNAL,
            None,
            1024,
        )
        print("SUCCESS: USN journal query successful.")
        return info
    except Exception as e:
        print(f"Failed to query USN journal: {e}")

        try:
            print("Trying to create USN journal...")
            buffer = bytearray(16)  # 2 uint64s
            import struct

            max_size = 32 * 1024 * 1024  # 32 MB
            delta = 4 * 1024 * 1024  # 4 MB
            struct.pack_into("QQ", buffer, 0, max_size, delta)

            win32file.DeviceIoControl(
                handle,
                win32file.FSCTL_CREATE_USN_JOURNAL,
                buffer,
                0,
            )
            print("SUCCESS: USN journal created.")

            # Query again
            info = win32file.DeviceIoControl(
                handle,
                win32file.FSCTL_QUERY_USN_JOURNAL,
                None,
                1024,
            )
            print("SUCCESS: USN journal query successful after creation.")
            return info
        except Exception as e2:
            print(f"Failed to create USN journal: {e2}")
            return None


def read_usn_records(handle, journal_id, usn):
    """Read USN journal records."""
    if handle is None:
        print("ERROR: Invalid volume handle.")
        return None

    try:
        print(f"Reading USN journal (ID: {journal_id}, USN: {usn})...")
        read_data = win32file.DeviceIoControl(
            handle,
            win32file.FSCTL_READ_USN_JOURNAL,
            win32file.GetUsn(journal_id, usn, 0, 0),
            65536,
        )

        print(
            f"SUCCESS: Read {len(read_data) if read_data else 0} bytes from USN journal.",
        )

        # Parse USN data
        try:
            usn_records = win32file.ParseUsnData(read_data)
            print(f"SUCCESS: Parsed {len(usn_records)} USN records.")
            return read_data[0], usn_records  # Return next_usn and records
        except Exception as e:
            print(f"Failed to parse USN data: {e}")
            return read_data[0], []
    except Exception as e:
        print(f"Failed to read USN journal: {e}")
        return usn, []


def format_usn_reason(reason):
    """Format USN reason flags into a readable string."""
    reasons = []

    if reason & win32file.USN_REASON_FILE_CREATE:
        reasons.append("FILE_CREATE")
    if reason & win32file.USN_REASON_FILE_DELETE:
        reasons.append("FILE_DELETE")
    if reason & win32file.USN_REASON_RENAME_OLD_NAME:
        reasons.append("RENAME_OLD_NAME")
    if reason & win32file.USN_REASON_RENAME_NEW_NAME:
        reasons.append("RENAME_NEW_NAME")
    if reason & win32file.USN_REASON_SECURITY_CHANGE:
        reasons.append("SECURITY_CHANGE")
    if reason & win32file.USN_REASON_DATA_OVERWRITE:
        reasons.append("DATA_OVERWRITE")
    if reason & win32file.USN_REASON_DATA_EXTEND:
        reasons.append("DATA_EXTEND")
    if reason & win32file.USN_REASON_DATA_TRUNCATION:
        reasons.append("DATA_TRUNCATION")
    if reason & win32file.USN_REASON_BASIC_INFO_CHANGE:
        reasons.append("BASIC_INFO_CHANGE")
    if reason & win32file.USN_REASON_CLOSE:
        reasons.append("CLOSE")

    return ", ".join(reasons) if reasons else f"UNKNOWN({reason})"


def main():
    """Main function."""
    # Get volume from command line
    if len(sys.argv) < 2:
        print("Usage: python debug_usn_journal.py <volume>")
        print("Example: python debug_usn_journal.py C:")
        return 1

    volume = sys.argv[1]
    print(f"Debugging USN journal for volume: {volume}")

    # Open volume
    handle = get_volume_handle(volume)
    if handle is None:
        print(
            "ERROR: Could not open volume. Try running with administrator privileges.",
        )
        return 1

    try:
        # Get USN journal info
        journal_info = get_usn_journal_info(handle)
        if journal_info is None:
            print("ERROR: Could not get USN journal information.")
            return 1

        # Display journal info
        print("\nUSN Journal Information:")
        for key, value in journal_info.items():
            print(f"  {key}: {value}")

        # Get starting USN
        journal_id = journal_info["UsnJournalID"]
        next_usn = journal_info["FirstUsn"]

        # Create a test file to generate activity
        print("\nCreating test file to generate USN journal activity...")
        create_test_file(volume)

        # Wait a moment for the journal to update
        print("Waiting for USN journal to update...")
        time.sleep(1)

        # Read USN records
        print("\nReading USN journal records...")
        next_usn, records = read_usn_records(handle, journal_id, next_usn)

        # Display records
        if records:
            print(f"\nFound {len(records)} USN records:")
            for i, record in enumerate(records):
                print(f"\nRecord {i+1}:")
                file_name = record.get("FileName", "Unknown")
                reason = record.get("Reason", 0)
                file_ref = record.get("FileReferenceNumber", 0)
                parent_ref = record.get("ParentFileReferenceNumber", 0)

                print(f"  File Name: {file_name}")
                print(f"  Reason: {format_usn_reason(reason)} ({reason})")
                print(f"  File Reference: {file_ref}")
                print(f"  Parent Reference: {parent_ref}")

                # Print other attributes
                for key, value in record.items():
                    if key not in [
                        "FileName",
                        "Reason",
                        "FileReferenceNumber",
                        "ParentFileReferenceNumber",
                    ]:
                        print(f"  {key}: {value}")
        else:
            print("\nNo USN records found. This may indicate one of several issues:")
            print("1. The USN journal is not enabled or working properly.")
            print("2. The volume doesn't support USN journals.")
            print(
                "3. There have been no file system changes since the journal started.",
            )
            print("4. You may need administrator privileges to access the USN journal.")

        # Create another test file
        print("\nCreating another test file...")
        create_test_file(volume)

        # Wait a moment
        time.sleep(1)

        # Read more records
        print("\nReading more USN journal records...")
        next_usn, records = read_usn_records(handle, journal_id, next_usn)

        # Display records
        if records:
            print(f"\nFound {len(records)} more USN records:")
            for i, record in enumerate(records):
                print(f"\nRecord {i+1}:")
                file_name = record.get("FileName", "Unknown")
                reason = record.get("Reason", 0)

                print(f"  File Name: {file_name}")
                print(f"  Reason: {format_usn_reason(reason)} ({reason})")
        else:
            print("\nNo new USN records found.")

        print("\nUSN journal debug complete.")
        return 0
    finally:
        # Close volume handle
        if handle:
            win32file.CloseHandle(handle)
            print("Closed volume handle.")


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"Unhandled error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
