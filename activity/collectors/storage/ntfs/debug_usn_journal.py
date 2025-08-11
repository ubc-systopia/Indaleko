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
    sys.exit(1)

# Try to import pywin32 modules
try:
    import pywintypes
    import win32api
    import win32con
    import win32file
except ImportError:
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

        return filename
    except Exception:
        return None


def get_volume_handle(volume):
    """Get a handle to the volume."""
    # Clean up volume name
    if volume.endswith(("\\", "/")):
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
            return win32file.CreateFile(
                format,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                None,
                win32file.OPEN_EXISTING,
                win32file.FILE_ATTRIBUTE_NORMAL,
                None,
            )
        except Exception:
            pass

    return None


def get_usn_journal_info(handle):
    """Get information about the USN journal."""
    if handle is None:
        return None

    try:
        return win32file.DeviceIoControl(
            handle,
            win32file.FSCTL_QUERY_USN_JOURNAL,
            None,
            1024,
        )
    except Exception:

        try:
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

            # Query again
            return win32file.DeviceIoControl(
                handle,
                win32file.FSCTL_QUERY_USN_JOURNAL,
                None,
                1024,
            )
        except Exception:
            return None


def read_usn_records(handle, journal_id, usn):
    """Read USN journal records."""
    if handle is None:
        return None

    try:
        read_data = win32file.DeviceIoControl(
            handle,
            win32file.FSCTL_READ_USN_JOURNAL,
            win32file.GetUsn(journal_id, usn, 0, 0),
            65536,
        )


        # Parse USN data
        try:
            usn_records = win32file.ParseUsnData(read_data)
            return read_data[0], usn_records  # Return next_usn and records
        except Exception:
            return read_data[0], []
    except Exception:
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


def main() -> int | None:
    """Main function."""
    # Get volume from command line
    if len(sys.argv) < 2:
        return 1

    volume = sys.argv[1]

    # Open volume
    handle = get_volume_handle(volume)
    if handle is None:
        return 1

    try:
        # Get USN journal info
        journal_info = get_usn_journal_info(handle)
        if journal_info is None:
            return 1

        # Display journal info
        for key in journal_info:
            pass

        # Get starting USN
        journal_id = journal_info["UsnJournalID"]
        next_usn = journal_info["FirstUsn"]

        # Create a test file to generate activity
        create_test_file(volume)

        # Wait a moment for the journal to update
        time.sleep(1)

        # Read USN records
        next_usn, records = read_usn_records(handle, journal_id, next_usn)

        # Display records
        if records:
            for _i, record in enumerate(records):
                record.get("FileName", "Unknown")
                record.get("Reason", 0)
                record.get("FileReferenceNumber", 0)
                record.get("ParentFileReferenceNumber", 0)


                # Print other attributes
                for key in record:
                    if key not in [
                        "FileName",
                        "Reason",
                        "FileReferenceNumber",
                        "ParentFileReferenceNumber",
                    ]:
                        pass
        else:
            pass

        # Create another test file
        create_test_file(volume)

        # Wait a moment
        time.sleep(1)

        # Read more records
        next_usn, records = read_usn_records(handle, journal_id, next_usn)

        # Display records
        if records:
            for _i, record in enumerate(records):
                record.get("FileName", "Unknown")
                record.get("Reason", 0)

        else:
            pass

        return 0
    finally:
        # Close volume handle
        if handle:
            win32file.CloseHandle(handle)


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(1)
