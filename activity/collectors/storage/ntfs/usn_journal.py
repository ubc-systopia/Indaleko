#!/usr/bin/env python
"""
USN Journal interaction module for Indaleko.

This module provides functions for interacting with the NTFS USN Journal on Windows.
It's designed to be imported and used by the NTFS activity collector.

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

import ctypes
import logging
import os
import struct
import sys
from ctypes import wintypes
from datetime import UTC, datetime
from typing import Any

# Constants for USN journal operations (these might not be defined in pywin32)
FSCTL_QUERY_USN_JOURNAL = 0x000900F4
FSCTL_ENUM_USN_DATA = 0x000900B3
FSCTL_READ_USN_JOURNAL = 0x000900BB
FSCTL_CREATE_USN_JOURNAL = 0x000900E7

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

# Setup module logger
logger = logging.getLogger(__name__)

# Check if we're on Windows
IS_WINDOWS = sys.platform.startswith("win")

# Windows API constants for ctypes approach
FILE_READ_DATA = 0x0001
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000


# Define USN_JOURNAL_DATA structure for ctypes
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


# Define READ_USN_JOURNAL_DATA structure for ctypes
class READ_USN_JOURNAL_DATA(ctypes.Structure):
    _fields_ = [
        ("StartUsn", ctypes.c_longlong),
        ("ReasonMask", wintypes.DWORD),
        ("ReturnOnlyOnClose", wintypes.DWORD),
        ("Timeout", ctypes.c_ulonglong),
        ("BytesToWaitFor", ctypes.c_ulonglong),
        ("UsnJournalID", ctypes.c_ulonglong),
    ]


# Define USN_RECORD structure for ctypes
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


# Check if PyWin32 is available for compatibility with existing code
if IS_WINDOWS:
    try:
        import pywintypes
        import win32file

        WIN32_AVAILABLE = True
    except ImportError:
        logger.warning(
            "PyWin32 is not installed. Using ctypes for all USN Journal functions.",
        )
        WIN32_AVAILABLE = False
else:
    logger.warning("Not running on Windows. USN Journal functions will not work.")
    WIN32_AVAILABLE = False


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


def parse_usn_record_v2(
    data: bytes,
    offset: int,
    debug: bool = False,
) -> tuple[dict[str, Any], int]:
    """
    Parse a Version 2 USN record from binary data.

    Args:
        data: The binary data containing the record
        offset: Offset into the data where the record starts
        debug: Whether to print debug information

    Returns:
        Tuple of (record_dict, next_offset) or (None, next_offset) if invalid
    """
    # Make sure we have at least 4 bytes for record_length
    if offset + 4 > len(data):
        return None, len(data)

    # Record header (56 bytes)
    record_length = struct.unpack("<L", data[offset : offset + 4])[0]
    if record_length == 0 or record_length < 60:  # Minimum valid size for a USN record
        return None, offset + 4

    # Make sure we have enough data
    if offset + record_length > len(data):
        return None, len(data)

    try:
        # Parse common fields (56 bytes total for V2 header)
        major_version = struct.unpack("<H", data[offset + 4 : offset + 6])[0]
        minor_version = struct.unpack("<H", data[offset + 6 : offset + 8])[0]
        file_ref_num = struct.unpack("<Q", data[offset + 8 : offset + 16])[0]
        parent_ref_num = struct.unpack("<Q", data[offset + 16 : offset + 24])[0]
        usn = struct.unpack("<Q", data[offset + 24 : offset + 32])[0]
        timestamp = struct.unpack("<Q", data[offset + 32 : offset + 40])[0]
        reason = struct.unpack("<L", data[offset + 40 : offset + 44])[0]
        source_info = struct.unpack("<L", data[offset + 44 : offset + 48])[0]
        security_id = struct.unpack("<L", data[offset + 48 : offset + 52])[0]
        file_attributes = struct.unpack("<L", data[offset + 52 : offset + 56])[0]

        # Extract filename (variable length, starts after the header)
        file_name_length = struct.unpack("<H", data[offset + 56 : offset + 58])[0]
        file_name_offset = struct.unpack("<H", data[offset + 58 : offset + 60])[0]

        # Calculate the offset where the filename starts
        filename_start = offset + file_name_offset

        # Extract the filename (as UTF-16)
        filename = ""
        if filename_start + file_name_length <= len(data):
            try:
                filename = data[filename_start : filename_start + file_name_length].decode("utf-16-le")
            except Exception as e:
                filename = f"<Decode Error: {data[filename_start:filename_start+file_name_length].hex()}>"
                if debug:
                    logger.debug(f"Error decoding filename: {e}")

        # Convert Windows timestamp (100-nanosecond intervals since Jan 1, 1601)
        # to Unix timestamp (seconds since Jan 1, 1970)
        try:
            # Windows timestamp is in 100-nanosecond intervals since Jan 1, 1601
            # 116444736000000000 = number of 100-nanosecond intervals from Jan 1, 1601 to Jan 1, 1970
            unix_time = (timestamp - 116444736000000000) / 10000000
            timestamp_str = datetime.fromtimestamp(unix_time, UTC).isoformat()
            timestamp_dt = datetime.fromtimestamp(unix_time, UTC)
        except Exception as e:
            timestamp_str = f"<Invalid: {timestamp}>"
            timestamp_dt = datetime.now(UTC)
            if debug:
                logger.debug(f"Error converting timestamp: {e}")

        # Create record dictionary
        record = {
            "record_length": record_length,
            "major_version": major_version,
            "minor_version": minor_version,
            "file_reference_number": f"{file_ref_num:016x}",  # Convert to hex string
            "parent_file_reference_number": f"{parent_ref_num:016x}",  # Convert to hex string
            "usn": usn,
            "timestamp": timestamp_str,
            "timestamp_dt": timestamp_dt,
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
        if debug:
            logger.debug(f"Error parsing USN record at offset {offset}: {e}")
        # Try to move to the next record based on record_length
        if record_length > 0 and offset + record_length <= len(data):
            return None, offset + record_length
        else:
            # If we can't determine a proper next offset, skip 4 bytes
            return None, offset + 4


def parse_usn_data(data: bytes, debug: bool = False) -> list[dict[str, Any]]:
    """
    Parse USN journal data into records.

    Args:
        data: The binary data from DeviceIoControl
        debug: Whether to print debug information

    Returns:
        List of parsed USN records
    """
    if not data or len(data) < 8:
        return []

    # First 8 bytes is the next USN
    next_usn = struct.unpack("<Q", data[:8])[0]
    if debug:
        logger.debug(f"Next USN from data: {next_usn}")

    records = []
    offset = 8  # Start after the next USN

    while offset < len(data):
        record, offset = parse_usn_record_v2(data, offset, debug)
        if record:
            records.append(record)

    return records


def open_volume(volume: str, debug: bool = False) -> int | None:
    """
    Open a volume for USN journal operations.

    Args:
        volume: Volume to open (e.g., "C:")
        debug: Whether to print debug information

    Returns:
        Volume handle or None if failed
    """
    if not IS_WINDOWS or not WIN32_AVAILABLE:
        if debug:
            logger.debug("Not on Windows or PyWin32 not available")
        return None

    # Standardize volume path
    if not volume.endswith(":"):
        volume = f"{volume}:"

    volume_path = f"\\\\.\\{volume}"
    if debug:
        logger.debug(f"Opening volume {volume_path}")

    # Try various volume path formats
    volume_path_variants = [
        volume_path,
        f"\\\\.\\{volume}",  # Physical drive syntax
        f"{volume}\\",  # Standard path
    ]

    # Try each variant until one works
    for path_variant in volume_path_variants:
        try:
            if debug:
                logger.debug(f"Trying volume path: {path_variant}")
            handle = win32file.CreateFile(
                path_variant,
                win32file.GENERIC_READ,
                win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                None,
                win32file.OPEN_EXISTING,
                win32file.FILE_ATTRIBUTE_NORMAL,
                None,
            )
            if debug:
                logger.debug(f"Successfully opened volume with path: {path_variant}")
            return handle
        except Exception as e:
            if debug:
                logger.debug(f"Failed to open volume with path {path_variant}: {e}")

    # If all variants failed
    logger.warning(f"Could not open volume {volume} with any path variant")
    return None


def query_journal_info_ctypes(
    handle: int,
    debug: bool = False,
) -> dict[str, Any] | None:
    """
    Query USN journal information using ctypes.

    Args:
        handle: Volume handle from open_volume()
        debug: Whether to print debug information

    Returns:
        Dictionary with journal information or None if failed
    """
    if not IS_WINDOWS:
        if debug:
            logger.debug("Not on Windows")
        return None

    if not handle or handle == -1:
        logger.error("Invalid volume handle")
        return None

    # Query USN journal info using ctypes
    try:
        # Create journal data structure and bytes returned
        journal_data = USN_JOURNAL_DATA()
        bytes_returned = wintypes.DWORD()

        # Call DeviceIoControl
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
            error = ctypes.get_last_error()
            if debug:
                logger.debug(f"DeviceIoControl failed with Win32 error code: {error}")
            raise ctypes.WinError(error)

        # Convert to dictionary
        journal_info = {
            "journal_id": journal_data.UsnJournalID,
            "first_usn": journal_data.FirstUsn,
            "next_usn": journal_data.NextUsn,
            "lowest_valid_usn": journal_data.LowestValidUsn,
            "max_usn": journal_data.MaxUsn,
            "max_size": journal_data.MaximumSize,
            "allocation_delta": journal_data.AllocationDelta,
        }

        if debug:
            logger.debug(f"Journal info (ctypes): {journal_info}")

        return journal_info

    except Exception as e:
        logger.error(f"Error querying USN journal with ctypes: {e}")
        return None


def query_journal_info(handle: int, debug: bool = False) -> dict[str, Any] | None:
    """
    Query USN journal information.

    Args:
        handle: Volume handle from open_volume()
        debug: Whether to print debug information

    Returns:
        Dictionary with journal information or None if failed
    """
    # First try with ctypes approach
    try:
        if debug:
            logger.debug("Trying to query journal info with ctypes")

        journal_info = query_journal_info_ctypes(handle, debug)
        if journal_info:
            return journal_info
    except Exception as e:
        if debug:
            logger.debug(f"Ctypes approach failed: {e}, falling back to PyWin32")

    # Fall back to PyWin32 if ctypes fails or not available
    if not IS_WINDOWS or not WIN32_AVAILABLE:
        if debug:
            logger.debug("Not on Windows or PyWin32 not available")
        return None

    if not handle:
        logger.error("Invalid volume handle")
        return None

    # Query USN journal info
    try:
        journal_data = win32file.DeviceIoControl(
            handle,
            FSCTL_QUERY_USN_JOURNAL,
            None,
            1024,
        )
        if debug:
            logger.debug(
                f"Successfully queried USN journal, received {len(journal_data)} bytes",
            )
            logger.debug(f"Raw journal data: {journal_data.hex()}")

        # Parse journal info
        journal_id = struct.unpack("<Q", journal_data[:8])[0]
        first_usn = struct.unpack("<Q", journal_data[8:16])[0]
        next_usn = struct.unpack("<Q", journal_data[16:24])[0]
        lowest_valid_usn = struct.unpack("<Q", journal_data[24:32])[0]
        max_usn = struct.unpack("<Q", journal_data[32:40])[0] if len(journal_data) >= 40 else 0
        max_size = struct.unpack("<Q", journal_data[40:48])[0] if len(journal_data) >= 48 else 0
        alloc_delta = struct.unpack("<Q", journal_data[48:56])[0] if len(journal_data) >= 56 else 0

        journal_info = {
            "journal_id": journal_id,
            "first_usn": first_usn,
            "next_usn": next_usn,
            "lowest_valid_usn": lowest_valid_usn,
            "max_usn": max_usn,
            "max_size": max_size,
            "allocation_delta": alloc_delta,
        }

        if debug:
            logger.debug(f"Journal info: {journal_info}")

        return journal_info
    except Exception as e:
        logger.error(f"Error querying USN journal: {e}")
        return None


def create_journal(
    handle: int,
    max_size: int = 32 * 1024 * 1024,
    allocation_delta: int = 4 * 1024 * 1024,
    debug: bool = False,
) -> bool:
    """
    Create a USN journal on the volume.

    Args:
        handle: Volume handle from open_volume()
        max_size: Maximum size of the journal in bytes (default: 32MB)
        allocation_delta: Allocation delta in bytes (default: 4MB)
        debug: Whether to print debug information

    Returns:
        True if successful, False if failed
    """
    if not IS_WINDOWS or not WIN32_AVAILABLE:
        if debug:
            logger.debug("Not on Windows or PyWin32 not available")
        return False

    if not handle:
        logger.error("Invalid volume handle")
        return False

    try:
        if debug:
            logger.debug(
                f"Creating USN journal with max_size={max_size}, delta={allocation_delta}",
            )

        # Create buffer for CREATE_USN_JOURNAL
        buffer = struct.pack("<QQ", max_size, allocation_delta)

        # Create the journal
        win32file.DeviceIoControl(handle, FSCTL_CREATE_USN_JOURNAL, buffer, 0)

        if debug:
            logger.debug("Successfully created USN journal")

        return True
    except Exception as e:
        logger.error(f"Error creating USN journal: {e}")
        return False


def read_journal_records_ctypes(
    handle: int,
    journal_id: int,
    start_usn: int,
    debug: bool = False,
) -> list[dict[str, Any]]:
    """
    Read records from the USN journal using ctypes approach.

    Args:
        handle: Volume handle from open_volume()
        journal_id: The USN journal ID
        start_usn: Starting USN to read from
        debug: Whether to print debug information

    Returns:
        List of USN records
    """
    if not IS_WINDOWS:
        if debug:
            logger.debug("Not on Windows")
        return []

    if not handle or handle == -1:
        logger.error("Invalid volume handle")
        return []

    records = []

    try:
        if debug:
            logger.debug(
                f"Reading USN journal with ctypes approach. JournalID={journal_id}, StartUSN={start_usn}",
            )

        # Create READ_USN_JOURNAL_DATA structure
        read_data = READ_USN_JOURNAL_DATA(
            StartUsn=start_usn,
            ReasonMask=0xFFFFFFFF,  # All reasons
            ReturnOnlyOnClose=0,
            Timeout=0,
            BytesToWaitFor=0,
            UsnJournalID=journal_id,
        )

        # Allocate buffer and bytes returned variable
        buffer_size = 65536
        buffer = ctypes.create_string_buffer(buffer_size)
        bytes_returned = wintypes.DWORD()

        # Call DeviceIoControl using ctypes
        if debug:
            logger.debug("Calling DeviceIoControl with FSCTL_READ_USN_JOURNAL")

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
            if debug:
                logger.debug(f"DeviceIoControl failed with Win32 error code: {error}")
            raise ctypes.WinError(error)

        if debug:
            logger.debug(f"Successfully read {bytes_returned.value} bytes using ctypes")
            if bytes_returned.value > 0:
                logger.debug(f"First 32 bytes: {buffer.raw[:32].hex()}")

        # First 8 bytes is NextUSN
        next_usn = struct.unpack("<Q", buffer.raw[:8])[0]
        if debug:
            logger.debug(f"Next USN: {next_usn}")

        # Start parsing at offset 8 (after NextUSN)
        offset = 8
        while offset < bytes_returned.value:
            # Read record length
            if offset + 4 > bytes_returned.value:
                break

            record_length = struct.unpack("<I", buffer.raw[offset : offset + 4])[0]
            if record_length == 0 or offset + record_length > bytes_returned.value:
                break

            # Parse the USN record
            try:
                # Use our existing parser
                record, next_offset = parse_usn_record_v2(buffer.raw, offset, debug)
                if record:
                    records.append(record)
                offset = next_offset
            except Exception as e:
                if debug:
                    logger.debug(f"Error parsing record at offset {offset}: {e}")
                # Skip this record
                offset += record_length if record_length > 0 else 4

        if debug:
            logger.debug(f"Found {len(records)} records using ctypes approach")

        return records

    except Exception as e:
        logger.warning(f"Error reading USN journal with ctypes: {e}")
        return []


def read_journal_records(
    handle: int,
    journal_info: dict[str, Any],
    start_usn: int | None = None,
    debug: bool = False,
) -> list[dict[str, Any]]:
    """
    Read records from the USN journal.

    Args:
        handle: Volume handle from open_volume()
        journal_info: Journal info from query_journal_info()
        start_usn: Starting USN to read from (default: recent entries)
        debug: Whether to print debug information

    Returns:
        List of USN records
    """
    if not IS_WINDOWS or not WIN32_AVAILABLE:
        if debug:
            logger.debug("Not on Windows or PyWin32 not available")
        return []

    if not handle:
        logger.error("Invalid volume handle")
        return []

    if not journal_info:
        logger.error("No journal info provided")
        return []

    # Use provided start_usn or default to something further back in time
    if start_usn is None:
        next_usn = journal_info.get("next_usn", 0)
        lowest_valid_usn = journal_info.get("lowest_valid_usn", 0)
        # Start from records further back (last 100,000 entries) to make sure we get some data
        start_usn = max(lowest_valid_usn, next_usn - 100000)

    records = []

    # Method 1: Try FSCTL_ENUM_USN_DATA first (recommended for newer Windows)
    try:
        if debug:
            logger.debug(f"Trying FSCTL_ENUM_USN_DATA with start_usn={start_usn}")

        # Create input buffer for ENUM_USN_DATA
        buffer_in = bytearray(28)  # 28 bytes for MFT_ENUM_DATA
        struct.pack_into(
            "<QQQHH",
            buffer_in,
            0,
            0,  # StartFileReferenceNumber
            start_usn,  # LowUsn
            0xFFFFFFFFFFFFFFFF,  # HighUsn
            2,
            2,
        )  # MinMajorVersion, MaxMajorVersion

        if debug:
            logger.debug(f"ENUM_USN_DATA input buffer: {buffer_in.hex()}")

        # Read journal data
        try:
            read_data = win32file.DeviceIoControl(
                handle,
                FSCTL_ENUM_USN_DATA,
                buffer_in,
                65536,
            )

            if debug:
                logger.debug(
                    f"Successfully read {len(read_data)} bytes using ENUM_USN_DATA",
                )
                if len(read_data) > 0:
                    logger.debug(f"First 32 bytes: {read_data[:32].hex()}")

            # Parse the records
            enum_records = parse_usn_data(read_data, debug)
            if debug:
                logger.debug(f"Found {len(enum_records)} records using ENUM_USN_DATA")

            records.extend(enum_records)

        except pywintypes.error as win_err:
            # Handle specific errors
            if win_err.winerror == 38:  # ERROR_HANDLE_EOF - no more records
                if debug:
                    logger.debug("No more USN records available (reached end of file)")

                # Try again with a lower USN if we have enough room
                if start_usn > 10000:
                    adjusted_start_usn = start_usn - 10000
                    if debug:
                        logger.debug(f"Trying lower start_usn={adjusted_start_usn}")

                    try:
                        # Update buffer with new USN
                        struct.pack_into(
                            "<QQQHH",
                            buffer_in,
                            0,
                            0,  # StartFileReferenceNumber
                            adjusted_start_usn,  # LowUsn
                            0xFFFFFFFFFFFFFFFF,  # HighUsn
                            2,
                            2,
                        )  # MinMajorVersion, MaxMajorVersion

                        # Try with adjusted start_usn
                        read_data = win32file.DeviceIoControl(
                            handle,
                            FSCTL_ENUM_USN_DATA,
                            buffer_in,
                            65536,
                        )

                        if debug:
                            logger.debug(
                                f"Successfully read {len(read_data)} bytes after adjusting USN",
                            )

                        # Parse and add records
                        enum_records = parse_usn_data(read_data, debug)
                        if debug:
                            logger.debug(
                                f"Found {len(enum_records)} records with adjusted USN",
                            )

                        records.extend(enum_records)
                    except Exception as retry_err:
                        if debug:
                            logger.debug(
                                f"Error retrying with adjusted USN: {retry_err}",
                            )
            else:
                logger.warning(
                    f"Error reading USN journal with ENUM_USN_DATA: {win_err}",
                )
    except Exception as e:
        logger.warning(f"General error with ENUM_USN_DATA: {e}")

    # Method 2: If ENUM_USN_DATA fails or returns no records, try READ_USN_JOURNAL
    if len(records) == 0:
        try:
            if debug:
                logger.debug(
                    f"Trying FSCTL_READ_USN_JOURNAL with start_usn={start_usn}",
                )

            # Create input buffer for READ_USN_JOURNAL
            # The complete structure requires more fields:
            # struct READ_USN_JOURNAL_DATA {
            #   DWORDLONG UsnJournalID;
            #   USN       StartUsn;
            #   DWORD     ReasonMask;
            #   DWORD     ReturnOnlyOnClose;
            #   DWORDLONG Timeout;
            #   DWORDLONG BytesToWaitFor;
            #   DWORDLONG UsnJournalOffset;
            #   DWORDLONG ReadFlags;
            # };
            journal_id = journal_info.get("journal_id", 0)

            # Try a different approach with a simpler structure first
            # Just the first 3 fields (may be all Windows needs)
            buffer_in = struct.pack(
                "<QQL",
                journal_id,  # UsnJournalID (8 bytes)
                start_usn,  # StartUsn (8 bytes)
                0xFFFFFFFF,
            )  # ReasonMask (4 bytes) - all reasons

            # Try with a similar approach to the GitHub example

            # Create a 36-byte buffer (matching the GitHub example)
            buffer = bytearray(36)  # 36 byte buffer initialized with zeros

            # Pack only the first two fields (JournalID and StartUSN)
            struct.pack_into(
                "<QQ",
                buffer,
                0,
                journal_id,
                start_usn,  # JournalID (8 bytes)
            )  # StartUSN (8 bytes)

            # The rest of the buffer is left as zeros

            if debug:
                logger.debug(
                    f"Using 36-byte buffer with first 16 bytes set: {buffer.hex()}",
                )

            # Use this as our only format to try
            buffer_formats = [
                {"buffer": buffer, "description": "36-byte buffer (GitHub approach)"},
            ]

            success = False

            for format_info in buffer_formats:
                if success:
                    break

                try:
                    if debug:
                        logger.debug(
                            f"Trying READ_USN_JOURNAL with format: {format_info['description']}",
                        )

                    # Use the pre-created buffer if it exists, otherwise create one
                    if "buffer" in format_info:
                        buffer_in = format_info["buffer"]
                    else:
                        # Create the buffer with this format (for backward compatibility)
                        buffer_in = struct.pack(
                            format_info["format"],
                            *format_info["args"],
                        )

                    if debug:
                        logger.debug(f"Buffer: {buffer_in.hex()}")

                    # Read journal data
                    read_data = win32file.DeviceIoControl(
                        handle,
                        FSCTL_READ_USN_JOURNAL,
                        buffer_in,
                        65536,
                    )

                    if debug:
                        logger.debug(
                            f"Successfully read {len(read_data)} bytes using READ_USN_JOURNAL",
                        )
                        if len(read_data) > 0:
                            logger.debug(f"First 32 bytes: {read_data[:32].hex()}")

                    # Parse the records
                    read_records = parse_usn_data(read_data, debug)
                    if debug:
                        logger.debug(
                            f"Found {len(read_records)} records using READ_USN_JOURNAL",
                        )

                    records.extend(read_records)
                    success = True

                    # If success, log which format worked
                    if debug:
                        logger.debug(f"Successful format: {format_info['description']}")

                except Exception as e:
                    if debug:
                        logger.debug(f"Format {format_info['description']} failed: {e}")

            # If all formats failed, raise the last error
            if not success:
                if debug:
                    logger.warning("All READ_USN_JOURNAL buffer formats failed")
                raise Exception("Failed to read USN journal with any buffer format")
        except Exception as e:
            logger.warning(f"Error reading USN journal with READ_USN_JOURNAL: {e}")

    return records


def get_open_volume_handle_ctypes(volume: str, debug: bool = False) -> int | None:
    """
    Open a handle to a volume using ctypes for direct Windows API access.

    Args:
        volume: Volume to open (e.g., "C:")
        debug: Whether to print debug information

    Returns:
        Volume handle or None if failed
    """
    if not IS_WINDOWS:
        logger.debug("Not on Windows")
        return None

    # Standardize volume path
    if not volume.endswith(":"):
        volume = f"{volume}:"

    volume_path = f"\\\\.\\{volume}"
    if debug:
        logger.debug(f"Opening volume {volume_path} with ctypes")

    try:
        # Open the volume using CreateFileW
        handle = ctypes.windll.kernel32.CreateFileW(
            volume_path,
            FILE_READ_DATA,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS,
            None,
        )

        if handle == -1 or handle == 0xFFFFFFFFFFFFFFFF:  # INVALID_HANDLE_VALUE
            error = ctypes.get_last_error()
            if debug:
                logger.debug(f"CreateFileW failed with Win32 error code: {error}")
            return None

        if debug:
            logger.debug(f"Successfully opened volume with ctypes, handle: {handle}")

        return handle

    except Exception as e:
        logger.error(f"Error opening volume with ctypes: {e}")
        return None


def get_usn_journal_records(
    volume: str,
    start_usn: int | None = None,
    debug: bool = False,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """
    Get records from the USN journal for a specific volume.

    Args:
        volume: Volume to query (e.g., "C:")
        start_usn: Starting USN to read from (default: recent entries)
        debug: Whether to print debug information

    Returns:
        Tuple of (journal_info, records) or (None, []) if failed
    """
    if not IS_WINDOWS:
        if debug:
            logger.debug("Not on Windows")
        return None, []

    # First try with ctypes (direct Windows API)
    ctypes_handle = None
    try:
        if debug:
            logger.debug("Trying to open volume and access USN journal using ctypes")

        # Open the volume with ctypes
        ctypes_handle = get_open_volume_handle_ctypes(volume, debug)
        if ctypes_handle:
            # Query journal info with ctypes
            journal_info = query_journal_info_ctypes(ctypes_handle, debug)
            if journal_info:
                # If we have journal info, try to read records with ctypes
                if start_usn is None:
                    next_usn = journal_info.get("next_usn", 0)
                    lowest_valid_usn = journal_info.get("lowest_valid_usn", 0)
                    # Start from records further back to make sure we get some data
                    start_usn = max(lowest_valid_usn, next_usn - 100000)

                journal_id = journal_info.get("journal_id", 0)
                records = read_journal_records_ctypes(
                    ctypes_handle,
                    journal_id,
                    start_usn,
                    debug,
                )

                # Close the handle
                if ctypes_handle:
                    ctypes.windll.kernel32.CloseHandle(ctypes_handle)

                if records:
                    if debug:
                        logger.debug(
                            f"Successfully read {len(records)} records using ctypes approach",
                        )
                    return journal_info, records
                elif debug:
                    logger.debug(
                        "No records found using ctypes approach, will try PyWin32",
                    )
    except Exception as e:
        if debug:
            logger.debug(f"Ctypes approach failed: {e}, will try PyWin32")
        # Close the handle if we have one
        if ctypes_handle:
            ctypes.windll.kernel32.CloseHandle(ctypes_handle)

    # Fall back to PyWin32 approach
    if not WIN32_AVAILABLE:
        if debug:
            logger.debug("PyWin32 not available for fallback. Ctypes approach failed.")
        return None, []

    # Open the volume with PyWin32
    handle = open_volume(volume, debug)
    if not handle:
        logger.error(f"Could not open volume {volume}")
        return None, []

    try:
        # Query journal info
        journal_info = query_journal_info(handle, debug)
        if not journal_info:
            # Try to create the journal
            if debug:
                logger.debug("Journal not found, attempting to create it")
            if create_journal(handle, debug=debug):
                # Query again after creation
                journal_info = query_journal_info(handle, debug)
                if not journal_info:
                    logger.error("Failed to query journal info after creation")
                    win32file.CloseHandle(handle)
                    return None, []
            else:
                logger.error("Failed to create USN journal")
                win32file.CloseHandle(handle)
                return None, []

        # Read the records
        records = read_journal_records(handle, journal_info, start_usn, debug)

        # Return the results
        return journal_info, records
    finally:
        # Always close the handle
        if handle:
            win32file.CloseHandle(handle)


def determine_activity_type(reason_flags: int) -> str:
    """
    Determine activity type from USN reason flags.

    Args:
        reason_flags: USN reason flags

    Returns:
        StorageActivityType as string
    """
    # Import only when needed to avoid circular imports
    from activity.collectors.storage.data_models.storage_activity_data_model import (
        StorageActivityType,
    )

    # First priority: file lifecycle events
    if reason_flags & USN_REASON_FILE_CREATE:
        return StorageActivityType.CREATE

    if reason_flags & USN_REASON_FILE_DELETE:
        return StorageActivityType.DELETE

    if reason_flags & USN_REASON_RENAME_OLD_NAME or reason_flags & USN_REASON_RENAME_NEW_NAME:
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


def create_test_files(
    volume: str,
    num_files: int = 3,
    debug: bool = False,
) -> list[str]:
    """
    Create test files on the specified volume to generate USN journal activity.

    Args:
        volume: Volume to create files on (e.g., "C:")
        num_files: Number of files to create
        debug: Whether to print debug information

    Returns:
        List of created file paths
    """
    if not IS_WINDOWS:
        if debug:
            logger.debug("Not on Windows, cannot create test files")
        return []

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

        if debug:
            logger.debug(f"Created test file: {filepath}")

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

        if debug:
            logger.debug(f"Created and renamed file: {orig_name} -> {new_name}")

    return created_files
