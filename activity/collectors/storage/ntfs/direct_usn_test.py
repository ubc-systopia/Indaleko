#!/usr/bin/env python
"""
Direct USN Journal test script.

This script directly queries the USN Journal and dumps records to a file.
It's designed for diagnosing USN journal access issues.

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

import os
import sys
import struct
import json
import time
import argparse
import winioctlcon
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
from typing import Any, Optional, List, Dict, Tuple

from icecream import ic

# Make sure we're on Windows
if not sys.platform.startswith('win'):
    print("This script only works on Windows")
    sys.exit(1)

try:
    import win32file
    import pywintypes
except ImportError:
    print("This script requires pywin32. Please install it with 'pip install pywin32'")
    sys.exit(1)

# Import our usn_journal module
try:
    from activity.collectors.storage.ntfs.usn_journal import get_usn_journal_records
    MODULE_AVAILABLE = True
except ImportError:
    print("Warning: usn_journal module not found in path, using built-in implementation")
    MODULE_AVAILABLE = False

# Constants for USN journal operations (these might not be defined in pywin32)
FSCTL_QUERY_USN_JOURNAL = 0x000900f4
FSCTL_ENUM_USN_DATA = 0x000900b3
FSCTL_READ_USN_JOURNAL = 0x000900bb
FSCTL_CREATE_USN_JOURNAL = 0x000900e7

# USN reason flags
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
FILE_ATTRIBUTE_READONLY = 0x00000001
FILE_ATTRIBUTE_HIDDEN = 0x00000002
FILE_ATTRIBUTE_SYSTEM = 0x00000004
FILE_ATTRIBUTE_DIRECTORY = 0x00000010
FILE_ATTRIBUTE_ARCHIVE = 0x00000020
FILE_ATTRIBUTE_DEVICE = 0x00000040
FILE_ATTRIBUTE_NORMAL = 0x00000080
FILE_ATTRIBUTE_TEMPORARY = 0x00000100
FILE_ATTRIBUTE_SPARSE_FILE = 0x00000200
FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
FILE_ATTRIBUTE_COMPRESSED = 0x00000800
FILE_ATTRIBUTE_OFFLINE = 0x00001000
FILE_ATTRIBUTE_ENCRYPTED = 0x00004000

def get_reason_flags_text(reason_flags: int) -> str:
    """Convert reason flags to readable text."""
    reasons = []
    if reason_flags & USN_REASON_DATA_OVERWRITE:
        reasons.append("DATA_OVERWRITE")
    if reason_flags & USN_REASON_DATA_EXTEND:
        reasons.append("DATA_EXTEND")
    if reason_flags & USN_REASON_DATA_TRUNCATION:
        reasons.append("DATA_TRUNCATION")
    if reason_flags & USN_REASON_NAMED_DATA_OVERWRITE:
        reasons.append("NAMED_DATA_OVERWRITE")
    if reason_flags & USN_REASON_NAMED_DATA_EXTEND:
        reasons.append("NAMED_DATA_EXTEND")
    if reason_flags & USN_REASON_NAMED_DATA_TRUNCATION:
        reasons.append("NAMED_DATA_TRUNCATION")
    if reason_flags & USN_REASON_FILE_CREATE:
        reasons.append("FILE_CREATE")
    if reason_flags & USN_REASON_FILE_DELETE:
        reasons.append("FILE_DELETE")
    if reason_flags & USN_REASON_EA_CHANGE:
        reasons.append("EA_CHANGE")
    if reason_flags & USN_REASON_SECURITY_CHANGE:
        reasons.append("SECURITY_CHANGE")
    if reason_flags & USN_REASON_RENAME_OLD_NAME:
        reasons.append("RENAME_OLD_NAME")
    if reason_flags & USN_REASON_RENAME_NEW_NAME:
        reasons.append("RENAME_NEW_NAME")
    if reason_flags & USN_REASON_INDEXABLE_CHANGE:
        reasons.append("INDEXABLE_CHANGE")
    if reason_flags & USN_REASON_BASIC_INFO_CHANGE:
        reasons.append("BASIC_INFO_CHANGE")
    if reason_flags & USN_REASON_HARD_LINK_CHANGE:
        reasons.append("HARD_LINK_CHANGE")
    if reason_flags & USN_REASON_COMPRESSION_CHANGE:
        reasons.append("COMPRESSION_CHANGE")
    if reason_flags & USN_REASON_ENCRYPTION_CHANGE:
        reasons.append("ENCRYPTION_CHANGE")
    if reason_flags & USN_REASON_OBJECT_ID_CHANGE:
        reasons.append("OBJECT_ID_CHANGE")
    if reason_flags & USN_REASON_REPARSE_POINT_CHANGE:
        reasons.append("REPARSE_POINT_CHANGE")
    if reason_flags & USN_REASON_STREAM_CHANGE:
        reasons.append("STREAM_CHANGE")
    if reason_flags & USN_REASON_CLOSE:
        reasons.append("CLOSE")
    return " | ".join(reasons) if reasons else "NONE"

def get_file_attributes_text(file_attributes: int) -> str:
    """Convert file attributes to readable text."""
    attributes = []
    if file_attributes & FILE_ATTRIBUTE_READONLY:
        attributes.append("READONLY")
    if file_attributes & FILE_ATTRIBUTE_HIDDEN:
        attributes.append("HIDDEN")
    if file_attributes & FILE_ATTRIBUTE_SYSTEM:
        attributes.append("SYSTEM")
    if file_attributes & FILE_ATTRIBUTE_DIRECTORY:
        attributes.append("DIRECTORY")
    if file_attributes & FILE_ATTRIBUTE_ARCHIVE:
        attributes.append("ARCHIVE")
    if file_attributes & FILE_ATTRIBUTE_DEVICE:
        attributes.append("DEVICE")
    if file_attributes & FILE_ATTRIBUTE_NORMAL:
        attributes.append("NORMAL")
    if file_attributes & FILE_ATTRIBUTE_TEMPORARY:
        attributes.append("TEMPORARY")
    if file_attributes & FILE_ATTRIBUTE_SPARSE_FILE:
        attributes.append("SPARSE_FILE")
    if file_attributes & FILE_ATTRIBUTE_REPARSE_POINT:
        attributes.append("REPARSE_POINT")
    if file_attributes & FILE_ATTRIBUTE_COMPRESSED:
        attributes.append("COMPRESSED")
    if file_attributes & FILE_ATTRIBUTE_OFFLINE:
        attributes.append("OFFLINE")
    if file_attributes & FILE_ATTRIBUTE_ENCRYPTED:
        attributes.append("ENCRYPTED")
    return " | ".join(attributes) if attributes else "NONE"

def parse_usn_record_v2(data: bytes, offset: int) -> tuple[dict[str, Any], int]:
    """
    Parse a Version 2 USN record from binary data.

    Args:
        data: The binary data containing the record
        offset: Offset into the data where the record starts

    Returns:
        tuple of (record_dict, next_offset) or (None, next_offset) if invalid
    """
    # Make sure we have at least 4 bytes for record_length
    if offset + 4 > len(data):
        return None, len(data)

    # Record header (56 bytes)
    record_length = struct.unpack("<L", data[offset:offset+4])[0]
    if record_length == 0 or record_length < 60:  # Minimum valid size for a USN record
        return None, offset + 4

    # Make sure we have enough data
    if offset + record_length > len(data):
        return None, len(data)

    try:
        # Parse common fields (56 bytes total for V2 header)
        major_version = struct.unpack("<H", data[offset+4:offset+6])[0]
        minor_version = struct.unpack("<H", data[offset+6:offset+8])[0]
        file_ref_num = struct.unpack("<Q", data[offset+8:offset+16])[0]
        parent_ref_num = struct.unpack("<Q", data[offset+16:offset+24])[0]
        usn = struct.unpack("<Q", data[offset+24:offset+32])[0]
        timestamp = struct.unpack("<Q", data[offset+32:offset+40])[0]
        reason = struct.unpack("<L", data[offset+40:offset+44])[0]
        source_info = struct.unpack("<L", data[offset+44:offset+48])[0]
        security_id = struct.unpack("<L", data[offset+48:offset+52])[0]
        file_attributes = struct.unpack("<L", data[offset+52:offset+56])[0]

        # Extract filename (variable length, starts after the header)
        file_name_length = struct.unpack("<H", data[offset+56:offset+58])[0]
        file_name_offset = struct.unpack("<H", data[offset+58:offset+60])[0]

        # Calculate the offset where the filename starts
        filename_start = offset + file_name_offset

        # Extract the filename (as UTF-16)
        filename = ""
        if filename_start + file_name_length <= len(data):
            try:
                filename = data[filename_start:filename_start+file_name_length].decode('utf-16-le')
            except Exception as e:
                filename = f"<Decode Error: {data[filename_start:filename_start+file_name_length].hex()}>"

        # Convert Windows timestamp (100-nanosecond intervals since Jan 1, 1601)
        # to Unix timestamp (seconds since Jan 1, 1970)
        try:
            # Windows timestamp is in 100-nanosecond intervals since Jan 1, 1601
            # 116444736000000000 = number of 100-nanosecond intervals from Jan 1, 1601 to Jan 1, 1970
            unix_time = (timestamp - 116444736000000000) / 10000000
            timestamp_str = datetime.fromtimestamp(unix_time, timezone.utc).isoformat()
        except Exception as e:
            timestamp_str = f"<Invalid: {timestamp}>"

        # Create record dictionary
        record = {
            "record_length": record_length,
            "major_version": major_version,
            "minor_version": minor_version,
            "file_reference_number": f"{file_ref_num:016x}",  # Convert to hex string
            "parent_file_reference_number": f"{parent_ref_num:016x}",  # Convert to hex string
            "usn": usn,
            "timestamp": timestamp_str,
            "reason": reason,
            "reason_text": get_reason_flags_text(reason),
            "source_info": source_info,
            "security_id": security_id,
            "file_attributes": file_attributes,
            "file_attributes_text": get_file_attributes_text(file_attributes),
            "file_name": filename,
            "is_directory": bool(file_attributes & FILE_ATTRIBUTE_DIRECTORY)
        }

        # Return record and next offset
        return record, offset + record_length
    except Exception as e:
        # If parsing fails, try to skip this record
        print(f"Error parsing USN record at offset {offset}: {e}")
        # Try to move to the next record based on record_length
        if record_length > 0 and offset + record_length <= len(data):
            return None, offset + record_length
        else:
            # If we can't determine a proper next offset, skip 4 bytes
            return None, offset + 4

def parse_usn_data(data: bytes, verbose: bool = False) -> list[dict[str, Any]]:
    """
    Parse USN journal data into records.

    Args:
        data: The binary data from DeviceIoControl
        verbose: Whether to print verbose debugging information

    Returns:
        list of parsed USN records
    """
    if not data or len(data) < 8:
        return []

    # First 8 bytes is the next USN
    next_usn = struct.unpack("<Q", data[:8])[0]
    if verbose:
        print(f"Next USN from data: {next_usn}")

    records = []
    offset = 8  # Start after the next USN

    while offset < len(data):
        record, offset = parse_usn_record_v2(data, offset)
        if record:
            records.append(record)

    return records

def query_usn_journal(volume: str, start_usn: Optional[int] = None, verbose: bool = False) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Query the USN journal for a volume.

    Args:
        volume: Volume to query (e.g., "C:")
        start_usn: Starting USN to query from (if None, uses a recent USN)
        verbose: Whether to print verbose debugging information

    Returns:
        tuple of (journal_info, records)
    """
    # Standardize volume path
    if not volume.endswith(":"):
        volume = f"{volume}:"

    volume_path = f"\\\\.\\{volume}"
    if verbose:
        print(f"Opening volume {volume_path}")

    # Open volume
    try:
        handle = win32file.CreateFile(
            volume_path,
            win32file.GENERIC_READ,
            win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
            None,
            win32file.OPEN_EXISTING,
            win32file.FILE_ATTRIBUTE_NORMAL,
            None
        )
        if verbose:
            print("Successfully opened volume")
    except Exception as e:
        print(f"Error opening volume: {e}")
        return None, []

    # Query USN journal info
    try:
        journal_data = win32file.DeviceIoControl(
            handle,
            FSCTL_QUERY_USN_JOURNAL,
            None,
            1024
        )
        if verbose:
            print(f"Successfully queried USN journal, received {len(journal_data)} bytes")
            print(f"Raw journal data: {journal_data.hex()}")
    except Exception as e:
        print(f"Error querying USN journal: {e}")
        # Try to create the journal if it doesn't exist
        try:
            print(f"Trying to create USN journal on {volume}")
            # Create a 32MB journal with 4MB delta
            buffer = struct.pack("<QQ", 32*1024*1024, 4*1024*1024)
            win32file.DeviceIoControl(
                handle,
                FSCTL_CREATE_USN_JOURNAL,
                buffer,
                0
            )
            # Query again
            journal_data = win32file.DeviceIoControl(
                handle,
                FSCTL_QUERY_USN_JOURNAL,
                None,
                1024
            )
            print("Successfully created and queried USN journal")
        except Exception as create_err:
            print(f"Error creating USN journal: {create_err}")
            win32file.CloseHandle(handle)
            return None, []

    # Parse journal info
    try:
        journal_id = struct.unpack("<Q", journal_data[:8])[0]
        first_usn = struct.unpack("<Q", journal_data[8:16])[0]
        next_usn = struct.unpack("<Q", journal_data[16:24])[0]
        lowest_valid_usn = struct.unpack("<Q", journal_data[24:32])[0]

        # Use provided start_usn or default to something recent (next_usn - 1000)
        if start_usn is None:
            # Start from a reasonable point to avoid too much data
            start_usn = max(lowest_valid_usn, next_usn - 1000)

        journal_info = {
            "journal_id": journal_id,
            "first_usn": first_usn,
            "next_usn": next_usn,
            "lowest_valid_usn": lowest_valid_usn,
            "start_usn": start_usn
        }

        # Print numeric values in hex
        print(f"Journal ID (hex): {journal_id:#x}")
        print(f"First USN (hex): {first_usn:#x}")
        print(f"Next USN (hex): {next_usn:#x}")
        print(f"Lowest Valid USN (hex): {lowest_valid_usn:#x}")
        print(f"Start USN (hex): {start_usn:#x}")

        if verbose:
            print(f"Journal info: {json.dumps(journal_info, indent=2)}")
    except Exception as e:
        print(f"Error parsing journal info: {e}")
        win32file.CloseHandle(handle)
        return None, []

    # Try both methods to read the journal
    records = []

    # Method 1: FSCTL_ENUM_USN_DATA (recommended for newer Windows)
    try:
        if verbose:
            print(f"\nTrying FSCTL_ENUM_USN_DATA with start_usn={start_usn}")

        buffer_in = bytearray(28)  # 28 bytes for MFT_ENUM_DATA
        struct.pack_into("<QQQHH", buffer_in, 0,
                       0,               # StartFileReferenceNumber
                       start_usn,       # LowUsn
                       0xFFFFFFFFFFFFFFFF,  # HighUsn
                       2, 2)            # MinMajorVersion, MaxMajorVersion

        if verbose:
            print(f"Input buffer: {buffer_in.hex()}")

        # Read journal data
        read_data = win32file.DeviceIoControl(
            handle,
            FSCTL_ENUM_USN_DATA,
            buffer_in,
            65536
        )

        if verbose:
            print(f"Successfully read {len(read_data)} bytes using ENUM_USN_DATA")
            if len(read_data) > 0:
                print(f"First 32 bytes: {read_data[:32].hex()}")

        # Parse the records
        enum_records = parse_usn_data(read_data, verbose)
        if verbose:
            print(f"Found {len(enum_records)} records using ENUM_USN_DATA")
        records.extend(enum_records)
    except pywintypes.error as win_err:
        # Handle specific windows errors
        if win_err.winerror == 38:  # ERROR_HANDLE_EOF
            if verbose:
                print("No more USN records available (reached end of file)")
        else:
            print(f"Error reading USN journal with ENUM_USN_DATA: {win_err}")

    # Method 2: FSCTL_READ_USN_JOURNAL (if Method 1 failed)
    if len(records) == 0:
        if verbose:
            print(f"\nTrying FSCTL_READ_USN_JOURNAL with start_usn={start_usn}")

        # typedef struct {
        # USN       StartUsn;
        # DWORD     ReasonMask;
        # DWORD     ReturnOnlyOnClose;
        # DWORDLONG Timeout;
        # DWORDLONG BytesToWaitFor;
        # DWORDLONG UsnJournalID;
        # } READ_USN_JOURNAL_DATA_V0, *PREAD_USN_JOURNAL_DATA_V0, READ_USN_JOURNAL_DATA, *PREAD_USN_JOURNAL_DATA;

        # typedef struct {
        #
        #        USN StartUsn;
        #        ULONG ReasonMask;
        #        ULONG ReturnOnlyOnClose;
        #        ULONGLONG Timeout;
        #        ULONGLONG BytesToWaitFor;
        #        ULONGLONG UsnJournalID;
        #        USHORT MinMajorVersion;
        #        USHORT MaxMajorVersion;
        #
        #    } READ_USN_JOURNAL_DATA_V1, *PREAD_USN_JOURNAL_DATA_V1;


        # Create a 36-byte buffer based on the GitHub example approach
        buffer = bytearray(4096)

        ALL_INTERESTING_CHANGES = (
            winioctlcon.USN_REASON_BASIC_INFO_CHANGE |
            winioctlcon.USN_REASON_CLOSE |
            winioctlcon.USN_REASON_DATA_EXTEND |
            winioctlcon.USN_REASON_DATA_OVERWRITE |
            winioctlcon.USN_REASON_DATA_TRUNCATION |
            winioctlcon.USN_REASON_FILE_CREATE |
            winioctlcon.USN_REASON_FILE_DELETE |
            winioctlcon.USN_REASON_RENAME_NEW_NAME |
            winioctlcon.USN_REASON_RENAME_OLD_NAME
        )

        def ctl_code(device_type: int, function: int, method: int, access: int) -> int:
            """
            Generate a control code consistent with the CTL_CODE macro in C.

            Args:
                device_type (int): The device type (16-bit value).
                function (int): The function code (12-bit value).
                method (int): The method code (2-bit value).
                access (int): The access code (2-bit value).

            Returns:
                int: The generated control code.
            """
            return ((device_type << 16) | (access << 14) | (function << 2) | method)
        #define FSCTL_READ_USN_JOURNAL          CTL_CODE(FILE_DEVICE_FILE_SYSTEM, 46,  METHOD_NEITHER, FILE_ANY_ACCESS) // READ_USN_JOURNAL_DATA, USN

        ic(ctl_code(9, 46, 3, 0))

        ic('Packing buffer with USN journal data:',
            start_usn,
            ALL_INTERESTING_CHANGES,
            journal_id,
            winioctlcon.FSCTL_READ_USN_JOURNAL)

        # Pack only the first two fields (JournalID and StartUSN)
        # reason_mask = ALL_INTERESTING_CHANGES
        # inp = struct.pack('QLLQQQ', first_usn, reason_mask, 0, 0, 0, journal_id)
        struct.pack_into(
            "QLLQQQHH",  # format string
            buffer,      # where to put the data
            0,
            start_usn,   # StartUSN (8 bytes)
            ALL_INTERESTING_CHANGES,  # ReasonMask (4 bytes)
            0,           # ReturnOnlyOnClose (4 bytes)
            0,           # Timeout (8 bytes)
            0,           # BytesToWaitFor (8 bytes)
            journal_id,  # JournalID (8 bytes)
            2,
            2
        )

        # The rest of the buffer is left as zeros

        # Read journal data with the 36-byte buffer
        read_data = win32file.DeviceIoControl(
            handle,
            winioctlcon.FSCTL_READ_USN_JOURNAL,
            buffer,
            65536
        )

        if verbose:
            ic(f"Successfully read {len(read_data)} bytes using READ_USN_JOURNAL with 36-byte buffer")
            if len(read_data) > 0:
                print(f"First 32 bytes: {read_data[:32].hex()}")

        # Parse the records
        read_records = parse_usn_data(read_data, verbose)
        if verbose:
            print(f"Found {len(read_records)} records using READ_USN_JOURNAL")

        records.extend(read_records)


    # Close handle
    win32file.CloseHandle(handle)

    return journal_info, records

def create_test_files(volume: str, num_files: int = 3, verbose: bool = False) -> list[str]:
    """
    Create test files on the specified volume to generate USN journal activity.

    Args:
        volume: Volume to create files on (e.g., "C:")
        num_files: Number of files to create
        verbose: Whether to print verbose debugging information

    Returns:
        list of created file paths
    """
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
        with open(filepath, 'w') as f:
            f.write(f"Test file created at {datetime.now()}\n")
            f.write(f"This is test file {i+1} of {num_files}\n")
            f.flush()
            os.fsync(f.fileno())

        created_files.append(filepath)

        if verbose:
            print(f"Created test file: {filepath}")

        # Also read the file to generate read activity
        with open(filepath, 'r') as f:
            content = f.read()

        # And modify it to generate write activity
        with open(filepath, 'a') as f:
            f.write(f"Additional content added at {datetime.now()}\n")
            f.flush()
            os.fsync(f.fileno())

    # Create a file and rename it
    if num_files > 0:
        timestamp = int(datetime.now().timestamp())
        orig_name = os.path.join(test_dir, f"rename_test_{timestamp}.txt")
        new_name = os.path.join(test_dir, f"renamed_{timestamp}.txt")

        # Create file
        with open(orig_name, 'w') as f:
            f.write(f"Rename test file created at {datetime.now()}\n")

        # Rename it
        os.rename(orig_name, new_name)
        created_files.append(new_name)

        if verbose:
            print(f"Created and renamed file: {orig_name} -> {new_name}")

    return created_files

def check_usn_journal_status(volume, verbose=False):
    """
    Use fsutil to check USN journal status and other NTFS diagnostics.

    Args:
        volume: The volume to check (e.g., "C:")
        verbose: Whether to print verbose debugging information

    Returns:
        dictionary with fsutil output or None if failed
    """
    # Only works on Windows
    if not sys.platform.startswith('win'):
        print("fsutil only works on Windows")
        return None

    try:
        # Standardize volume path
        if not volume.endswith(":"):
            volume = f"{volume}:"

        if verbose:
            print(f"Checking USN journal status with fsutil for volume {volume}")

        import subprocess

        # dictionary to store all diagnostic info
        all_info = {}

        # Check USN journal status
        result = subprocess.run(
            f"fsutil usn queryjournal {volume}",
            shell=True,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            # Parse output into a dictionary
            output = result.stdout.strip()
            if verbose:
                print("Raw fsutil USN journal output:")
                print(output)

            journal_info = {}
            for line in output.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    journal_info[key.strip()] = value.strip()

            all_info["usn_journal"] = journal_info
        else:
            if verbose:
                print(f"fsutil usn queryjournal error: {result.stderr}")
            all_info["usn_journal"] = {"error": result.stderr.strip() if result.stderr else "Unknown error"}

        # If verbose, collect additional diagnostic information
        if verbose:
            # Check filesystem info
            try:
                result = subprocess.run(
                    f"fsutil fsinfo ntfsinfo {volume}",
                    shell=True,
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0:
                    print("\nNTFS volume information:")
                    print(result.stdout)

                    # Add summary to all_info
                    ntfs_info = {}
                    for line in result.stdout.splitlines():
                        if ":" in line:
                            key, value = line.split(":", 1)
                            ntfs_info[key.strip()] = value.strip()

                    all_info["ntfs_info"] = ntfs_info
            except Exception as e:
                print(f"Error checking NTFS info: {e}")

            # Check volume info
            try:
                result = subprocess.run(
                    f"fsutil volume diskfree {volume}",
                    shell=True,
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0:
                    print("\nVolume space information:")
                    print(result.stdout)

                    # Add summary to all_info
                    disk_info = {}
                    for line in result.stdout.splitlines():
                        if ":" in line:
                            key, value = line.split(":", 1)
                            disk_info[key.strip()] = value.strip()

                    all_info["disk_info"] = disk_info
            except Exception as e:
                print(f"Error checking volume info: {e}")

        return all_info
    except Exception as e:
        print(f"Error running fsutil diagnostics: {e}")
        return None


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="USN Journal Test Tool")
    parser.add_argument("--volume", type=str, default="C:", help="Volume to query (default: C:)")
    parser.add_argument("--start-usn", type=int, help="Starting USN (defaults to recent entries)")
    parser.add_argument("--output", type=str, default="usn_records.jsonl", help="Output file (default: usn_records.jsonl)")
    parser.add_argument("--limit", type=int, default=100, help="Maximum records to output (default: 100)")
    parser.add_argument("--create-test-files", action="store_true", help="Create test files to generate USN activity")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose debugging output")
    parser.add_argument("--fsutil", action="store_true", help="Check USN journal status with fsutil")
    args = parser.parse_args()

    # Check USN journal status with fsutil if requested
    if args.fsutil and sys.platform.startswith('win'):
        print("\n=== USN Journal Status via fsutil ===")
        fsutil_info = check_usn_journal_status(args.volume, args.verbose)
        if fsutil_info:
            if "usn_journal" in fsutil_info:
                print("\nUSN Journal Information:")
                for key, value in fsutil_info["usn_journal"].items():
                    print(f"  {key}: {value}")

            # In non-verbose mode, only show USN info (verbose mode already shows the full output)
            if not args.verbose:
                if "ntfs_info" in fsutil_info:
                    print("\nNTFS Volume Information (Selected):")
                    for key in ["Bytes Per Sector", "Bytes Per Cluster", "Bytes Per FileRecord Segment", "Clusters Per FileRecord Segment", "Volume Size"]:
                        if key in fsutil_info["ntfs_info"]:
                            print(f"  {key}: {fsutil_info['ntfs_info'][key]}")

                if "disk_info" in fsutil_info:
                    print("\nVolume Space Information:")
                    for key, value in fsutil_info["disk_info"].items():
                        print(f"  {key}: {value}")
        print()

    # Create test files if requested or in verbose mode
    if args.create_test_files or args.verbose:
        print(f"Creating test files on volume {args.volume} to generate USN activity...")
        created_files = create_test_files(args.volume, 3, args.verbose)
        print(f"Created {len(created_files)} test files")

        # Sleep briefly to allow USN journal to update
        time.sleep(1)

    print(f"Querying USN journal for volume {args.volume}")
    journal_info, records = query_usn_journal(args.volume, args.start_usn, args.verbose)

    if not journal_info:
        print("Failed to query USN journal")
        # If fsutil wasn't already checked, try it now as a fallback diagnostic
        if not args.fsutil and sys.platform.startswith('win'):
            print("\n=== Checking USN Journal Status with fsutil (fallback) ===")
            fsutil_info = check_usn_journal_status(args.volume, True)  # Force verbose
            if fsutil_info:
                print("\nFallback USN Journal Diagnostics:")
                if "usn_journal" in fsutil_info:
                    if "error" in fsutil_info["usn_journal"]:
                        print(f"  USN Journal Error: {fsutil_info['usn_journal']['error']}")
                    else:
                        print("  USN Journal Information:")
                        for key, value in fsutil_info["usn_journal"].items():
                            print(f"    {key}: {value}")

                # Also print some basic troubleshooting advice
                print("\nPossible solutions to try:")
                print("  1. Check if you have administrative privileges")
                print("  2. Try creating a new USN journal with: fsutil usn createjournal m=32768 a=4096 <volume>")
                print("  3. Check for NTFS file system corruption with: chkdsk <volume>")
                print("  4. Try restarting the computer if journal creation fails")
            print()
        return

    # Limit records if needed
    if len(records) > args.limit:
        print(f"Limiting output to {args.limit} records (out of {len(records)})")
        records = records[:args.limit]

    # Save records to file
    with open(args.output, 'w', encoding='utf-8') as f:
        # Write journal info
        journal_info_record = {"record_type": "journal_info", **journal_info}
        f.write(json.dumps(journal_info_record) + '\n')

        # Write records
        for record in records:
            record["record_type"] = "usn_record"
            f.write(json.dumps(record) + '\n')

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

    # If verbose and we didn't check with fsutil before, do it now for comparison
    if args.verbose and not args.fsutil and sys.platform.startswith('win'):
        print("\n=== USN Journal Status via fsutil (final check) ===")
        fsutil_info = check_usn_journal_status(args.volume, False)
        if fsutil_info and "usn_journal" in fsutil_info:
            # Just check if values have changed compared to the USN info we retrieved
            if journal_info:
                print("\nComparison of USN values:")
                usn_info = fsutil_info["usn_journal"]
                for key, value in usn_info.items():
                    # Try to find equivalent keys in our journal_info
                    equivalent_key = None
                    if key.lower() == "usn journal id":
                        equivalent_key = "journal_id"
                    elif key.lower() == "first usn":
                        equivalent_key = "first_usn"
                    elif key.lower() == "next usn":
                        equivalent_key = "next_usn"
                    elif key.lower() == "lowest valid usn" or key.lower() == "lowest usn":
                        equivalent_key = "lowest_valid_usn"

                    if equivalent_key and equivalent_key in journal_info:
                        api_value = journal_info[equivalent_key]
                        print(f"  {key}:")
                        print(f"    - fsutil value: {value}")
                        print(f"    - API value:    {api_value}")

                        # If values don't match, highlight it
                        if str(api_value) not in str(value):
                            print(f"    - NOTE: Values don't appear to match!")
            else:
                # Just show the fsutil values
                print("\nUSN Journal Information from fsutil:")
                for key, value in fsutil_info["usn_journal"].items():
                    print(f"  {key}: {value}")
        print()

if __name__ == "__main__":
    main()
