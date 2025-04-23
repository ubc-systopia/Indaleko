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

import argparse
import ctypes
import json
import os
import struct
import subprocess
import sys
import tempfile
import time
import uuid
from ctypes import wintypes
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import winioctlcon
from icecream import ic

# Make sure we're on Windows
if not sys.platform.startswith('win'):
    print("This script only works on Windows")
    sys.exit(1)

try:
    import pywintypes
    import win32file
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

# Add new FSCTL constant
FSCTL_READ_UNPRIVILEGED_USN_JOURNAL = 0x900f8

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
            "is_directory": bool(file_attributes & FILE_ATTRIBUTE_DIRECTORY),
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

def is_admin() -> bool:
    """Check if the script is running with administrative privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

def read_usn_journal(handle: int, journal_id: int, start_usn: int, verbose: bool = False) -> tuple[bytes, int]:
    """
    Read USN journal entries.

    This implementation matches the working implementation in ntfs_collector_v2.py,
    which was adapted from the successful approach in foo.py.

    Args:
        handle: Volume handle
        journal_id: USN journal ID
        start_usn: Starting USN for reading journal entries
        verbose: Whether to print verbose debugging information

    Returns:
        Tuple of (buffer, bytes_returned)
    """
    if verbose:
        print(f"Reading USN journal: handle={handle}, journal_id={journal_id}, start_usn={start_usn}")

    # Prepare the data structure - exactly as in the working implementation
    read_data = READ_USN_JOURNAL_DATA(
        StartUsn=start_usn,
        ReasonMask=0xFFFFFFFF,  # All reasons
        ReturnOnlyOnClose=0,
        Timeout=0,
        BytesToWaitFor=0,
        UsnJournalID=journal_id,
    )

    # Create the buffer
    buffer_size = 8192  # Increased from 4096 for more data
    buffer = ctypes.create_string_buffer(buffer_size)
    bytes_returned = wintypes.DWORD()

        if verbose:
        print(f"Using FILE_READ_DATA access flag")
        print(f"ReadData structure: StartUsn={read_data.StartUsn}, JournalID={read_data.UsnJournalID}")
        print(f"Buffer size: {buffer_size} bytes")

    try:
        # Call DeviceIoControl - matching the working implementation
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

        if success:
        if verbose:
                print(f"Successfully read {bytes_returned.value} bytes from USN journal")
                if bytes_returned.value > 0:
                    print(f"First 32 bytes: {buffer.raw[:32].hex()}")
            return buffer.raw, bytes_returned.value
        else:
            error = ctypes.get_last_error()
            if verbose:
                print(f"DeviceIoControl failed with Win32 error code: {error}")

            # Try unprivileged access as fallback
            if error == 5:  # 5 = ERROR_ACCESS_DENIED
                if verbose:
                    print("Access denied, trying unprivileged USN journal access...")

                # Reset buffer for clean attempt
                buffer = ctypes.create_string_buffer(buffer_size)
                bytes_returned = wintypes.DWORD()

                try:
                    success = ctypes.windll.kernel32.DeviceIoControl(
                handle,
                        FSCTL_READ_UNPRIVILEGED_USN_JOURNAL,
                        ctypes.byref(read_data),
                        ctypes.sizeof(read_data),
                buffer,
                        buffer_size,
                        ctypes.byref(bytes_returned),
                        None
                    )

                    if success:
                        if verbose:
                            print(f"Unprivileged USN journal access succeeded, got {bytes_returned.value} bytes")
                        return buffer.raw, bytes_returned.value
                    else:
                        error = ctypes.get_last_error()
                        if verbose:
                            print(f"Unprivileged access also failed with error code: {error}")
                except Exception as e:
                    if verbose:
                        print(f"Error during unprivileged access attempt: {e}")

            # If we get here, all attempts failed
            raise ctypes.WinError(error)

    except Exception as e:
        if verbose:
            print(f"Error reading USN journal: {e}")

        # Check if it's an access denied error
        is_access_denied = False
        if hasattr(e, 'winerror') and e.winerror == 5:
            is_access_denied = True
        elif hasattr(e, 'args') and len(e.args) > 0 and e.args[0] == 5:
            is_access_denied = True

        if is_access_denied:
            print("\nAccess denied. Some USN journal operations require administrative privileges.")
            print("Please run this script with elevated privileges (Run as Administrator).")

        raise e

def get_volume_handle(volume_path: str) -> int:
    """
    Get a volume handle using ctypes with FILE_READ_DATA access.

    This is critical - using FILE_READ_DATA (0x0001) instead of GENERIC_READ (0x80000000)
    allows proper access to the USN journal even without admin privileges in some cases.
    """
    # FILE_READ_DATA = 0x0001 (Critical for USN journal access)
    FILE_READ_DATA = 0x0001
    FILE_SHARE_READ = 0x00000001
    FILE_SHARE_WRITE = 0x00000002
    OPEN_EXISTING = 3
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000

    # Check if we're running with admin rights
    admin_status = is_admin()
    print(f"Running with administrator privileges: {admin_status}")

    handle = ctypes.windll.kernel32.CreateFileW(
        volume_path,
        FILE_READ_DATA,  # Use FILE_READ_DATA instead of GENERIC_READ
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None,
        OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS,
        None
    )

    if handle == -1:  # INVALID_HANDLE_VALUE
        error = ctypes.get_last_error()
        if error == 5:  # ERROR_ACCESS_DENIED
            print(f"Access denied when opening volume {volume_path}")
            print("This usually means the process doesn't have administrator privileges.")
            print("Try running the script as administrator (right-click, Run as Administrator).")
        raise ctypes.WinError(error)

    return handle

def read_usn_journal_from_foo(handle: int, journal_id: int, start_usn: int, verbose: bool = False) -> tuple[bytes, int]:
    """Read USN journal entries by importing and using the working implementation from foo.py."""
        if verbose:
        print(f"Reading USN journal by importing foo.py implementation")
        print(f"Parameters: journal_id={journal_id}, start_usn={start_usn}")

    try:
        # Import foo.py from the same directory
        import importlib.util
        import os
        import sys

        # Get the current directory where our script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Path to foo.py in the same directory
        foo_path = os.path.join(script_dir, "foo.py")

        if verbose:
            print(f"Looking for foo.py at: {foo_path}")

        if os.path.exists(foo_path):
        if verbose:
                print("foo.py found, importing...")

            # Import foo.py as a module
            spec = importlib.util.spec_from_file_location("foo", foo_path)
            foo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(foo)

            if verbose:
                print("Successfully imported foo.py")
                print("Calling foo.read_usn_journal...")

            # Call the read_usn_journal function from foo.py
            buffer, bytes_returned = foo.read_usn_journal(handle, journal_id, start_usn)

            if verbose:
                print(f"Successfully read {bytes_returned} bytes using foo.py")
                if bytes_returned > 0:
                    print(f"First 32 bytes: {buffer.raw[:32].hex()}")

            return buffer.raw, bytes_returned
        else:
            if verbose:
                print(f"foo.py not found at {foo_path}")
            raise FileNotFoundError(f"foo.py not found at {foo_path}")

    except Exception as e:
        if verbose:
            print(f"Error using foo.py implementation: {e}")
        raise e

def query_usn_journal(volume, start_usn=None, verbose=False):
    """
    Query the USN journal for a specified volume using usn_bridge.py

            Args:
        volume (str): Volume name (e.g. "C:")
        start_usn (int, optional): Starting USN for the query
        verbose (bool, optional): Enable verbose output

            Returns:
        list: List of USN journal records
    """
    if verbose:
        print(f"Querying USN journal on volume {volume}")

    # Standardize volume name
    if not volume.endswith(':'):
        volume = f"{volume}:"

    # Get the script directory to find usn_bridge.py
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bridge_script = os.path.join(script_dir, "usn_bridge.py")

    if not os.path.exists(bridge_script):
        if verbose:
            print(f"Error: usn_bridge.py not found at {bridge_script}")
        return []

    # Create a temporary file to store the bridge output
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as temp_file:
        output_file = temp_file.name

    try:
        # Build the command to run the bridge script
        cmd = [sys.executable, bridge_script, "--volume", volume, "--output", output_file]

        if start_usn is not None:
            cmd.extend(["--start-usn", str(start_usn)])

        if verbose:
            cmd.append("--verbose")
            print(f"Running: {' '.join(cmd)}")

        # Run the bridge script
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
        if verbose:
                print(f"Error running usn_bridge.py: {result.stderr}")
            return []

        # Parse the output file
        records = []
        current_record = {}

        with open(output_file, 'r') as f:
            lines = f.readlines()

            for line in lines:
                line = line.strip()
                if not line:
                    if current_record:
                        records.append(current_record)
                        current_record = {}
                    continue

                if line.startswith("USN:"):
                    if current_record:
                        records.append(current_record)
                        current_record = {}

                    # Start a new record
                    current_record = {"USN": line.split("USN:")[1].strip()}
                    continue

                # Parse other lines in the record
                if ":" in line:
                    parts = line.split(":", 1)
                    key = parts[0].strip()
                    value = parts[1].strip()
                    current_record[key] = value

            # Add the last record if there is one
            if current_record:
                records.append(current_record)

        if verbose:
            print(f"Found {len(records)} USN journal records")

        return records

    except Exception as e:
        if verbose:
            print(f"Error querying USN journal: {e}")
        return []

    finally:
        # Clean up the temporary file
        try:
            if os.path.exists(output_file):
                os.unlink(output_file)
        except:
            pass

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
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="USN Journal Direct Test Tool")
    parser.add_argument("--volume", type=str, default="C:",
                      help="Volume to query (default: C:)")
    parser.add_argument("--start-usn", type=int,
                      help="Starting USN for the query (defaults to most recent entries)")
    parser.add_argument("--output", type=str, default="usn_records.jsonl",
                      help="Output file (default: usn_records.jsonl)")
    parser.add_argument("--verbose", action="store_true",
                      help="Enable verbose output")
    parser.add_argument("--fsutil", action="store_true",
                      help="Use fsutil to get USN journal info")
    parser.add_argument("--create-test-files", action="store_true",
                      help="Create test files to generate USN activity")
    parser.add_argument("--direct-access", action="store_true",
                      help="Use direct access mode instead of bridge (recommended)")
    parser.add_argument("--use-module", action="store_true",
                      help="Use the usn_journal module if available")
    parser.add_argument("--use-foo", action="store_true",
                      help="Import and use foo.py directly")

    args = parser.parse_args()

    # Standardize volume name
    volume = args.volume
    if not volume.endswith(':'):
        volume = f"{volume}:"

    # Format volume path for Windows API
    volume_path = fr"\\.\{volume}"

    # Print test mode information
    print(f"USN Journal Test Tool running in {'verbose' if args.verbose else 'normal'} mode")
    print(f"Target volume: {volume} (path: {volume_path})")
    print(f"Running with admin privileges: {is_admin()}")

    # Show USN journal information if requested
    if args.fsutil:
        print(f"\nUSN Journal info for {volume} (via fsutil):")
        journal_info = check_usn_journal_status(volume, args.verbose)

        if journal_info and "usn_journal" in journal_info:
            print("\nUSN Journal Status:")
            for key, value in journal_info["usn_journal"].items():
                        print(f"  {key}: {value}")

            # Extract USN journal ID if present
            journal_id = None
            if "USN Journal ID" in journal_info["usn_journal"]:
                try:
                    journal_id = int(journal_info["usn_journal"]["USN Journal ID"], 16)
                    print(f"\nDetected USN Journal ID: {journal_id} (0x{journal_id:x})")
                except:
                    pass
        else:
            subprocess.run(["fsutil", "usn", "queryjournal", volume], capture_output=args.verbose)
        print()

    # Create test files if requested
    if args.create_test_files:
        print(f"\nCreating test files on {volume}")
        created_files = create_test_files(volume, num_files=3, verbose=args.verbose)

        if created_files:
            print(f"Created {len(created_files)} test files for USN activity")
            for i, file in enumerate(created_files[:5], 1):  # Show at most 5 files
                print(f"  {i}. {file}")

            if len(created_files) > 5:
                print(f"  ... and {len(created_files) - 5} more files")

        print()

    # Try direct access if requested
    records = []
    if args.direct_access:
        print(f"\nAttempting direct access to USN journal on {volume}...")
        try:
            # Get a handle to the volume
            handle = get_volume_handle(volume_path)
            print(f"Successfully opened volume handle: {handle}")

            # Query USN journal information
            journal_info = check_usn_journal_status(volume, args.verbose)
            journal_id = None

            if journal_info and "usn_journal" in journal_info and "USN Journal ID" in journal_info["usn_journal"]:
                try:
                    journal_id = int(journal_info["usn_journal"]["USN Journal ID"], 16)
                except:
                    pass

            if journal_id is None:
                # Use a fallback mechanism to get journal ID
                # For test purposes, use a hardcoded ID (should be replaced with proper detection)
                journal_id = 0x2000000000005
                print(f"Using fallback USN Journal ID: {journal_id} (0x{journal_id:x})")

            # Read USN journal entries
            start_usn = args.start_usn or 0
            print(f"Reading USN journal entries starting from USN {start_usn}...")

            buffer, bytes_returned = read_usn_journal(handle, journal_id, start_usn, args.verbose)

            if bytes_returned > 0:
                print(f"Successfully read {bytes_returned} bytes from USN journal")
                # Parse USN records
                usn_records = parse_usn_data(buffer[:bytes_returned], args.verbose)
                print(f"Found {len(usn_records)} USN records")

                # Save records to the output file
                with open(args.output, 'w') as f:
                    for record in usn_records:
                        f.write(json.dumps(record) + '\n')

                print(f"Wrote {len(usn_records)} USN records to {args.output}")
                records = usn_records
                    else:
                print("No USN data returned (0 bytes)")

            # Close the handle
            ctypes.windll.kernel32.CloseHandle(handle)

        except Exception as e:
            print(f"Error during direct USN journal access: {e}")
            import traceback
            traceback.print_exc()

    # Import and use foo.py directly if requested
    elif args.use_foo:
        print(f"\nImporting and using foo.py implementation...")
        try:
            handle = get_volume_handle(volume_path)
            journal_info = check_usn_journal_status(volume, args.verbose)
            journal_id = None

            if journal_info and "usn_journal" in journal_info and "USN Journal ID" in journal_info["usn_journal"]:
                try:
                    journal_id = int(journal_info["usn_journal"]["USN Journal ID"], 16)
                except:
                    pass

            if journal_id is None:
                journal_id = 0x2000000000005
                print(f"Using fallback USN Journal ID: {journal_id} (0x{journal_id:x})")

            start_usn = args.start_usn or 0
            buffer, bytes_returned = read_usn_journal_from_foo(handle, journal_id, start_usn, args.verbose)

            if bytes_returned > 0:
                usn_records = parse_usn_data(buffer[:bytes_returned], args.verbose)
                print(f"Found {len(usn_records)} USN records")

                with open(args.output, 'w') as f:
                    for record in usn_records:
            f.write(json.dumps(record) + '\n')

                print(f"Wrote {len(usn_records)} USN records to {args.output}")
                records = usn_records
            else:
                print("No USN data returned (0 bytes)")

            # Close the handle
            ctypes.windll.kernel32.CloseHandle(handle)

        except Exception as e:
            print(f"Error using foo.py implementation: {e}")
            import traceback
            traceback.print_exc()

    # Use the module if available and requested
    elif args.use_module and MODULE_AVAILABLE:
        print(f"\nUsing usn_journal module...")
        try:
            start_usn = args.start_usn or 0
            volume_letter = volume[0]

            from activity.collectors.storage.ntfs.usn_journal import (
                get_usn_journal_records,
            )
            usn_records = get_usn_journal_records(volume_letter, start_usn, args.verbose)

            if usn_records:
                print(f"Found {len(usn_records)} USN records")

                with open(args.output, 'w') as f:
                    for record in usn_records:
                        f.write(json.dumps(record) + '\n')

                print(f"Wrote {len(usn_records)} USN records to {args.output}")
                records = usn_records
            else:
                print("No USN records found")

        except Exception as e:
            print(f"Error using usn_journal module: {e}")
            import traceback
            traceback.print_exc()

    # Fall back to the bridge method
    else:
        print(f"\nUsing bridge method to query USN journal...")
        records = query_usn_journal(volume, args.start_usn, args.verbose)

        if records:
            # Write records to the output file
            with open(args.output, 'w') as f:
                for record in records:
                    f.write(json.dumps(record) + '\n')

            print(f"Wrote {len(records)} USN records to {args.output}")
        else:
            print("No USN records found or an error occurred using bridge method.")

    # Print a summary
    print("\nSummary:")
    print(f"  Test volume: {volume}")
    print(f"  Admin privileges: {is_admin()}")
    print(f"  Records found: {len(records)}")
    print(f"  Output file: {args.output}")

    if records:
        print("\nSample records (up to 5):")
        for i, record in enumerate(records[:5], 1):
            filename = record.get("file_name", "unknown")
            reason = record.get("reason_text", "unknown")
            print(f"  {i}. {filename} - {reason}")

    print("\nTest completed.")

if __name__ == "__main__":
    main()
