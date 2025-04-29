#!/usr/bin/env python
"""
USN Journal test using direct ctypes implementation.

This script directly queries the USN Journal using ctypes and dumps records to a file.
This avoids the buffer format issues with PyWin32.

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
import os
import struct
import sys
import time
from ctypes import wintypes
from datetime import UTC, datetime

# Make sure we're on Windows
if not sys.platform.startswith("win"):
    print("This script only works on Windows")
    sys.exit(1)

# Windows API constants
FSCTL_QUERY_USN_JOURNAL = 0x900F4
FSCTL_READ_USN_JOURNAL = 0x900BB
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
    except:
        return False


def filetime_to_datetime(filetime):
    """Convert Windows FILETIME to Python datetime."""
    epoch_diff = 116444736000000000  # 100ns intervals from 1601 to 1970
    timestamp = (filetime - epoch_diff) / 10000000  # Convert to seconds
    if timestamp < 0:
        return datetime(1601, 1, 1)
    return datetime.fromtimestamp(timestamp)


def get_volume_handle(volume_path):
    """Open a handle to the specified volume."""
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
        raise ctypes.WinError()
    return handle


def query_usn_journal(handle, verbose=False):
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


def read_usn_journal(handle, journal_id, start_usn, verbose=False):
    """Read USN journal entries."""
    read_data = READ_USN_JOURNAL_DATA(
        StartUsn=start_usn,
        ReasonMask=0xFFFFFFFF,  # All reasons
        ReturnOnlyOnClose=0,
        Timeout=0,
        BytesToWaitFor=0,
        UsnJournalID=journal_id,
    )
    buffer_size = 65536
    buffer = ctypes.create_string_buffer(buffer_size)
    bytes_returned = wintypes.DWORD()

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
        print(f"DeviceIoControl failed with Win32 error code: {error}")
        raise ctypes.WinError(error)

    return buffer, bytes_returned.value


def parse_usn_record(buffer, offset, bytes_returned, verbose=False):
    """Parse a USN record from the buffer."""
    if offset + 4 > bytes_returned:
        return None, bytes_returned

    record_length = struct.unpack_from("<I", buffer, offset)[0]
    if record_length == 0 or offset + record_length > bytes_returned:
        return None, offset + 4

    # Read fields manually to avoid alignment issues
    try:
        major_version = struct.unpack_from("<H", buffer, offset + 4)[0]
        minor_version = struct.unpack_from("<H", buffer, offset + 6)[0]
        file_ref_num = struct.unpack_from("<Q", buffer, offset + 8)[0]
        parent_ref_num = struct.unpack_from("<Q", buffer, offset + 16)[0]
        usn = struct.unpack_from("<Q", buffer, offset + 24)[0]
        timestamp = struct.unpack_from("<Q", buffer, offset + 32)[0]
        reason = struct.unpack_from("<I", buffer, offset + 40)[0]
        source_info = struct.unpack_from("<I", buffer, offset + 44)[0]
        security_id = struct.unpack_from("<I", buffer, offset + 48)[0]
        file_attributes = struct.unpack_from("<I", buffer, offset + 52)[0]
        file_name_length = struct.unpack_from("<H", buffer, offset + 56)[0]
        file_name_offset = struct.unpack_from("<H", buffer, offset + 58)[0]

        # Extract filename
        filename_start = offset + file_name_offset
        filename_end = filename_start + file_name_length

        if filename_end <= offset + record_length and filename_end <= bytes_returned:
            try:
                filename = buffer[filename_start:filename_end].decode("utf-16-le")
            except UnicodeDecodeError:
                filename = "<invalid filename>"
        else:
            filename = "<filename out of bounds>"

        # Convert timestamp
        try:
            # Windows timestamp is in 100-nanosecond intervals since Jan 1, 1601
            # 116444736000000000 = intervals from Jan 1, 1601 to Jan 1, 1970
            unix_time = (timestamp - 116444736000000000) / 10000000
            timestamp_dt = datetime.fromtimestamp(unix_time, UTC)
            timestamp_str = timestamp_dt.isoformat()
        except Exception:
            timestamp_str = f"<Invalid: {timestamp}>"
            timestamp_dt = datetime.now(UTC)

        # Get reason text
        reason_text = []
        for flag, name in REASON_FLAGS.items():
            if reason & flag:
                reason_text.append(name)
        reason_str = " | ".join(reason_text) if reason_text else "NONE"

        # Get attributes text
        attr_text = []
        for flag, name in ATTRIBUTE_FLAGS.items():
            if file_attributes & flag:
                attr_text.append(name)
        attr_str = " | ".join(attr_text) if attr_text else "NONE"

        record = {
            "usn": usn,
            "file_name": filename,
            "timestamp": timestamp_str,
            "reason": reason,
            "reason_text": reason_str,
            "file_reference_number": f"{file_ref_num:016x}",
            "parent_file_reference_number": f"{parent_ref_num:016x}",
            "file_attributes": file_attributes,
            "file_attributes_text": attr_str,
            "is_directory": bool(
                file_attributes & 0x00000010,
            ),  # FILE_ATTRIBUTE_DIRECTORY
        }

        return record, offset + record_length
    except Exception as e:
        print(f"Error parsing record at offset {offset}: {e}")
        return None, offset + (record_length if record_length > 0 else 4)


def create_test_files(volume, num_files=3, verbose=False):
    """Create test files to generate USN journal activity."""
    # Standardize volume path
    if not volume.endswith(":"):
        volume = f"{volume}:"

    # Create test directory
    test_dir = os.path.join(volume, "Indaleko_Test")
    os.makedirs(test_dir, exist_ok=True)

    created_files = []

    # Create test files
    for i in range(num_files):
        timestamp = int(datetime.now().timestamp())
        filename = f"test_file_{timestamp}_{i}.txt"
        filepath = os.path.join(test_dir, filename)

        # Create the file
        with open(filepath, "w") as f:
            f.write(f"Test file created at {datetime.now()}\n")
            f.write(f"This is test file {i+1} of {num_files}\n")
            f.flush()
            os.fsync(f.fileno())

        created_files.append(filepath)

        if verbose:
            print(f"Created test file: {filepath}")

        # Also read the file to generate read activity
        with open(filepath) as f:
            content = f.read()

        # And modify it to generate write activity
        with open(filepath, "a") as f:
            f.write(f"Additional content added at {datetime.now()}\n")
            f.flush()
            os.fsync(f.fileno())

    # Create a file and rename it
    if num_files > 0:
        timestamp = int(datetime.now().timestamp())
        orig_name = os.path.join(test_dir, f"rename_test_{timestamp}.txt")
        new_name = os.path.join(test_dir, f"renamed_{timestamp}.txt")

        # Create file
        with open(orig_name, "w") as f:
            f.write(f"Rename test file created at {datetime.now()}\n")

        # Rename it
        os.rename(orig_name, new_name)
        created_files.append(new_name)

        if verbose:
            print(f"Created and renamed file: {orig_name} -> {new_name}")

    return created_files


def check_usn_journal_status(volume, verbose=False):
    """Use fsutil to check USN journal status."""
    import subprocess

    # Standardize volume path
    if not volume.endswith(":"):
        volume = f"{volume}:"

    result = subprocess.run(
        f"fsutil usn queryjournal {volume}",
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode == 0:
        output = result.stdout.strip()
        if verbose:
            print(result.stdout)

        # Parse output into a dictionary
        info = {}
        for line in output.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                info[key.strip()] = value.strip()

        return info
    else:
        print(f"fsutil error: {result.stderr}")
        return None


def main():
    parser = argparse.ArgumentParser(description="USN Journal Reader using ctypes")
    parser.add_argument(
        "--volume",
        type=str,
        default="C:",
        help="Volume to query (default: C:)",
    )
    parser.add_argument(
        "--start-usn",
        type=int,
        help="Starting USN (defaults to recent entries)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="usn_records.jsonl",
        help="Output file (default: usn_records.jsonl)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum records to output (default: 100)",
    )
    parser.add_argument(
        "--create-test-files",
        action="store_true",
        help="Create test files to generate USN activity",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose debugging output",
    )
    parser.add_argument(
        "--fsutil",
        action="store_true",
        help="Check USN journal status with fsutil",
    )
    args = parser.parse_args()

    # Check administrator privileges
    if not is_admin():
        print("This script requires administrator privileges.")
        print("Please run as administrator and try again.")
        return

    # Check USN journal status with fsutil if requested
    if args.fsutil:
        print("\n=== USN Journal Status via fsutil ===")
        fsutil_info = check_usn_journal_status(args.volume, args.verbose)
        if fsutil_info:
            print("\nUSN Journal Information from fsutil:")
            for key, value in fsutil_info.items():
                print(f"  {key}: {value}")
        print()

    # Create test files if requested
    if args.create_test_files:
        print(
            f"Creating test files on volume {args.volume} to generate USN activity...",
        )
        created_files = create_test_files(args.volume, 3, args.verbose)
        print(f"Created {len(created_files)} test files")

        # Sleep briefly to allow USN journal to update
        time.sleep(1)

    # Standardize volume path
    if not args.volume.endswith(":"):
        args.volume = f"{args.volume}:"

    volume_path = f"\\\\.\\{args.volume}"
    print(f"Opening volume {volume_path}")

    try:
        # Open volume handle
        handle = get_volume_handle(volume_path)
        print("Successfully opened volume")

        try:
            # Query USN journal
            journal_data = query_usn_journal(handle, args.verbose)
            print(f"Journal ID: {journal_data.UsnJournalID}")
            print(f"First USN: {journal_data.FirstUsn}")
            print(f"Next USN: {journal_data.NextUsn}")
            print(f"Lowest Valid USN: {journal_data.LowestValidUsn}")

            # Determine start USN
            start_usn = args.start_usn
            if start_usn is None:
                # Start from records further back to make sure we get some data
                start_usn = max(
                    journal_data.LowestValidUsn,
                    journal_data.NextUsn - 100000,
                )
                print(f"Using calculated start USN: {start_usn}")

            # Read journal records
            print(f"Reading USN journal records from USN {start_usn}")
            buffer, bytes_returned = read_usn_journal(
                handle,
                journal_data.UsnJournalID,
                start_usn,
                args.verbose,
            )
            print(f"Read {bytes_returned} bytes from USN journal")

            # First 8 bytes is NextUSN
            next_usn = struct.unpack_from("<Q", buffer, 0)[0]
            print(f"Next USN from data: {next_usn}")

            # Parse records
            records = []
            offset = 8  # Start after NextUSN
            while offset < bytes_returned:
                record, offset = parse_usn_record(
                    buffer,
                    offset,
                    bytes_returned,
                    args.verbose,
                )
                if record:
                    records.append(record)

            print(f"Found {len(records)} records")

            # Limit records if needed
            if len(records) > args.limit:
                print(
                    f"Limiting output to {args.limit} records (out of {len(records)})",
                )
                records = records[: args.limit]

            # Build journal info dictionary for output
            journal_info = {
                "journal_id": journal_data.UsnJournalID,
                "first_usn": journal_data.FirstUsn,
                "next_usn": journal_data.NextUsn,
                "lowest_valid_usn": journal_data.LowestValidUsn,
                "start_usn": start_usn,
            }

            # Save records to file
            with open(args.output, "w", encoding="utf-8") as f:
                # Write journal info
                journal_info_record = {"record_type": "journal_info", **journal_info}
                f.write(json.dumps(journal_info_record) + "\n")

                # Write records
                for record in records:
                    record["record_type"] = "usn_record"
                    f.write(json.dumps(record) + "\n")

            print(f"Saved {len(records)} records to {args.output}")

            # Print a few sample records
            if records:
                print("\nSample Records:")
                for i, record in enumerate(records[:5]):
                    print(f"\nRecord {i+1}:")
                    print(f"  USN: {record['usn']}")
                    print(f"  File: {record['file_name']}")
                    print(f"  Reason: {record['reason_text']}")
                    print(f"  Timestamp: {record['timestamp']}")
                    print(f"  Attributes: {record['file_attributes_text']}")

        finally:
            # Close volume handle
            ctypes.windll.kernel32.CloseHandle(handle)

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
