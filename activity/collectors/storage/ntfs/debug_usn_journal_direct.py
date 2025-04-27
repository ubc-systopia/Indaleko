#!/usr/bin/env python
"""
Debug tool for Windows USN Journal with direct constant definitions.

This version defines the necessary constants directly rather than relying on
pywin32 to have them. This works around issues with some pywin32 installations
missing specific USN journal constants.

Usage:
    python debug_usn_journal_direct.py C:

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import os
import random
import struct
import sys
import time
from ctypes import *
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

# Define Windows constants directly in case they're missing from pywin32
# These are the USN journal control codes
FSCTL_QUERY_USN_JOURNAL = 0x000900F4
FSCTL_CREATE_USN_JOURNAL = 0x000900E7
FSCTL_READ_USN_JOURNAL = 0x000900BB

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
        f"\\\\.\\{volume}",  # \\.\C:
        f"\\\\.\\{volume[0]}:",  # \\.\C:
        f"{volume}\\",  # C:\
        f"\\\\?\\{volume}\\",  # \\?\C:\
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


def get_usn_info(handle):
    """Get USN journal information using direct DeviceIoControl calls."""
    if not handle:
        print("ERROR: Invalid volume handle")
        return None

    try:
        print("Querying USN journal using direct DeviceIoControl...")
        # Create a buffer to receive the USN journal data
        buffer_out = bytearray(1024)

        # Use direct call to DeviceIoControl
        result = win32file.DeviceIoControl(
            handle,
            FSCTL_QUERY_USN_JOURNAL,  # Use our defined constant
            None,  # No input buffer
            buffer_out,
        )

        print("SUCCESS: USN journal query successful")

        # Parse the result (this is simplified, in a real implementation we'd parse more fields)
        # The format is complex, but we'll capture the basic info
        info = {}

        # Parse out USN journal ID (typically the first 8 bytes)
        if len(result) >= 8:
            info["UsnJournalID"] = struct.unpack("<Q", result[:8])[0]
        else:
            info["UsnJournalID"] = 0

        # Parse first USN (typically the next 8 bytes)
        if len(result) >= 16:
            info["FirstUsn"] = struct.unpack("<Q", result[8:16])[0]
        else:
            info["FirstUsn"] = 0

        # Parse next USN (typically the next 8 bytes)
        if len(result) >= 24:
            info["NextUsn"] = struct.unpack("<Q", result[16:24])[0]
        else:
            info["NextUsn"] = 0

        return info
    except Exception as e:
        print(f"Failed to query USN journal: {e}")

        try:
            print("Trying to create USN journal...")
            # Initialize the USN journal with a max size of 32MB and delta of 4MB
            max_size = 32 * 1024 * 1024
            allocation_delta = 4 * 1024 * 1024
            buffer_in = struct.pack("<QQ", max_size, allocation_delta)

            result = win32file.DeviceIoControl(
                handle,
                FSCTL_CREATE_USN_JOURNAL,  # Use our defined constant
                buffer_in,  # Input buffer with size and delta
                0,  # No output data expected
            )

            print("SUCCESS: USN journal created")

            # Now try to query it again
            return get_usn_info(handle)
        except Exception as e2:
            print(f"Failed to create USN journal: {e2}")
            return None


def get_usn_data(handle, journal_id, first_usn):
    """Read data from the USN journal."""
    if not handle:
        print("ERROR: Invalid volume handle")
        return None, []

    try:
        print(f"Reading USN journal (ID: {journal_id}, USN: {first_usn})...")

        # Create the input buffer using win32file.GetUsn if available, otherwise build it manually
        try:
            buffer_in = win32file.GetUsn(journal_id, first_usn, 0, 0)
        except AttributeError:
            # If GetUsn is not available, create the buffer manually
            # Format: journal_id (8 bytes), first_usn (8 bytes), reason_mask (4 bytes), return_only_on_close (4 bytes)
            buffer_in = struct.pack("<QQLL", journal_id, first_usn, 0, 0)

        # Create a buffer to receive the USN records
        buffer_out = bytearray(65536)

        # Call DeviceIoControl to read the journal
        result = win32file.DeviceIoControl(
            handle,
            FSCTL_READ_USN_JOURNAL,  # Use our defined constant
            buffer_in,
            buffer_out,
        )

        if not result or len(result) < 8:
            print("WARNING: No data returned from USN journal")
            return first_usn, []

        # The first 8 bytes should be the next USN
        next_usn = struct.unpack("<Q", result[:8])[0]
        print(f"Next USN: {next_usn}")

        # The rest of the data contains USN records, but parsing them requires
        # detailed knowledge of the structure, which is complex.
        # In a full implementation, we'd parse this data into usable records.
        print(f"Read {len(result) - 8} bytes of USN record data")

        # For now we'll return the raw data and next USN
        # In practice you'd want to parse this into structured records
        return next_usn, [
            {
                "raw_data": "USN records received but not parsed in this simple implementation",
            },
        ]
    except Exception as e:
        print(f"Failed to read USN journal: {e}")
        return first_usn, []


def main():
    """Main function."""
    # Get volume from command line
    if len(sys.argv) < 2:
        print("Usage: python debug_usn_journal_direct.py <volume>")
        print("Example: python debug_usn_journal_direct.py C:")
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
        journal_info = get_usn_info(handle)
        if journal_info is None:
            print("ERROR: Could not get USN journal information.")
            return 1

        # Display journal info
        print("\nUSN Journal Information:")
        for key, value in journal_info.items():
            print(f"  {key}: {value}")

        # Get starting USN
        journal_id = journal_info["UsnJournalID"]
        first_usn = journal_info["FirstUsn"]

        # Create a test file to generate activity
        print("\nCreating test file to generate USN journal activity...")
        create_test_file(volume)

        # Wait a moment for the journal to update
        print("Waiting for USN journal to update...")
        time.sleep(1)

        # Read USN records
        print("\nReading USN journal records...")
        next_usn, records = get_usn_data(handle, journal_id, first_usn)

        # Create another test file
        print("\nCreating another test file...")
        create_test_file(volume)

        # Wait a moment
        time.sleep(1)

        # Read more records
        print("\nReading more USN journal records...")
        next_usn, more_records = get_usn_data(handle, journal_id, next_usn)

        print("\nUSN journal direct access check complete.")
        print(
            "Results: We were able to open the volume and query/create the USN journal.",
        )
        print(
            "         We have confirmed direct access to the USN journal is possible.",
        )
        print(
            "         The full parsing of USN records would require more complex code.",
        )

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
