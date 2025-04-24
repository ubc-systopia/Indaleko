import argparse
import ctypes
import platform
import struct
import sys
from ctypes import wintypes
from datetime import UTC, datetime

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
    """Convert Windows FILETIME to Python datetime with timezone information."""
    epoch_diff = 116444736000000000  # 100ns intervals from 1601 to 1970
    timestamp = (filetime - epoch_diff) / 10000000  # Convert to seconds
    if timestamp < 0:
        return datetime(1601, 1, 1, tzinfo=UTC)
    return datetime.fromtimestamp(timestamp, tz=UTC)


class UsnJournalReader:
    """
    A class to read and access the USN journal on Windows NTFS volumes.

    This class handles opening the volume, querying the journal metadata,
    reading journal entries, and managing the handle lifecycle.
    """

    def __init__(self, volume="C:", verbose=False):
        """
        Initialize the USN journal reader for a specific volume.

        Args:
            volume: The volume to access (e.g., "C:" or "D:")
            verbose: Whether to print verbose debugging information
        """
        self.verbose = verbose

        # Format the volume path properly
        if not volume.endswith(":"):
            volume = f"{volume}:"
        self.volume = volume
        self.volume_path = f"\\\\.\\{volume}"

        # Initialize handle
        self.handle = None
        self.journal_data = None

        if self.verbose:
            print(f"UsnJournalReader initialized for volume: {self.volume}")
            print(f"Using volume path: {self.volume_path}")
            print(f"Running with administrator privileges: {is_admin()}")

    def open(self):
        """
        Open the volume handle and query journal information.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.handle = self._get_volume_handle()
            self.journal_data = self._query_usn_journal()

            if self.verbose:
                print(f"Successfully opened volume {self.volume}")
                print(f"Journal ID: {self.journal_data.UsnJournalID}")
                print(f"First USN: {self.journal_data.FirstUsn}")
                print(f"Next USN: {self.journal_data.NextUsn}")
                print(f"Lowest Valid USN: {self.journal_data.LowestValidUsn}")

            return True
        except Exception as e:
            print(f"Error opening USN journal: {e}")
            self.close()
            return False

    def close(self):
        """Close the volume handle if it's open."""
        if self.handle:
            try:
                ctypes.windll.kernel32.CloseHandle(self.handle)
                if self.verbose:
                    print(f"Closed handle for volume {self.volume}")
            except Exception as e:
                print(f"Error closing handle: {e}")
            finally:
                self.handle = None
                self.journal_data = None

    def read_records(self, start_usn=None, max_records=50):
        """
        Read USN journal records.

        Args:
            start_usn: Starting USN (if None, will use the journal's FirstUsn)
            max_records: Maximum number of records to retrieve

        Returns:
            Tuple containing (list of USN record dictionaries, next_usn)
        """
        if not self.handle or not self.journal_data:
            if not self.open():
                return [], None

        try:
            # Use provided start_usn or default to FirstUsn
            # If start_usn is before the lowest valid USN, use the lowest valid USN
            if start_usn is None:
                start_usn = self.journal_data.FirstUsn
            else:
                # Use max to ensure we're within valid range
                start_usn = max(start_usn, self.journal_data.LowestValidUsn)

            if self.verbose:
                print(f"Starting from USN: {start_usn}")

            # Read USN journal
            buffer, bytes_returned = self._read_usn_journal(
                self.journal_data.UsnJournalID,
                start_usn,
            )

            if self.verbose:
                print(f"Read {bytes_returned} bytes from USN journal")

            # Get the next USN from the buffer
            next_usn = None
            if bytes_returned >= 8:
                next_usn = struct.unpack_from("<Q", buffer, 0)[0]

            # Parse records
            records = []
            offset = 8  # Skip first 8 bytes (NextUsn)
            records_found = 0

            while offset < bytes_returned and records_found < max_records:
                record = self._parse_usn_record(buffer, offset, bytes_returned)
                if record is None:
                    break

                records.append(record)
                records_found += 1

                offset += struct.unpack_from("<I", buffer, offset)[0]

            if self.verbose:
                print(f"Found {records_found} records")

            return records, next_usn

        except Exception as e:
            print(f"Error reading USN journal records: {e}")
            return [], None

    def _get_volume_handle(self):
        """Open a handle to the specified volume."""
        handle = ctypes.windll.kernel32.CreateFileW(
            self.volume_path,
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

    def _query_usn_journal(self):
        """Query the USN journal for metadata."""
        journal_data = USN_JOURNAL_DATA()
        bytes_returned = wintypes.DWORD()

        success = ctypes.windll.kernel32.DeviceIoControl(
            self.handle,
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

    def _read_usn_journal(self, journal_id, start_usn):
        """
        Read USN journal entries.

        This method handles the case where requested journal entries have been deleted
        due to journal rotation (circular buffer).
        """
        # Maximum number of retries for handle issues
        max_retries = 1
        retries = 0

        # Check if the requested USN is below the first valid USN
        # If so, immediately use the low water mark instead of retrying with an invalid USN
        if self.journal_data and start_usn < self.journal_data.FirstUsn:
            print(
                f"Requested USN {start_usn} is below First USN {self.journal_data.FirstUsn}",
            )
            print(f"Using First USN {self.journal_data.FirstUsn} as the starting point")

            # Update the starting USN to use the first valid USN
            start_usn = self.journal_data.FirstUsn

            # Return special buffer with the new starting USN
            empty_buffer = ctypes.create_string_buffer(8)
            struct.pack_into("<Q", empty_buffer, 0, start_usn)
            return empty_buffer, 8

        while retries <= max_retries:
            read_data = READ_USN_JOURNAL_DATA(
                StartUsn=start_usn,
                ReasonMask=0xFFFFFFFF,  # All reasons
                ReturnOnlyOnClose=0,
                Timeout=0,
                BytesToWaitFor=0,
                UsnJournalID=journal_id,
            )
            buffer_size = 4096
            buffer = ctypes.create_string_buffer(buffer_size)
            bytes_returned = wintypes.DWORD()

            try:
                success = ctypes.windll.kernel32.DeviceIoControl(
                    self.handle,
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

                    # Error 0 can happen when the handle is invalid or when there are no records
                    if error == 0 and retries < max_retries:
                        # Check if handle is still valid by trying to query the journal again
                        try:
                            self.close()  # Close the current handle
                            self.open()  # Try to reopen and get a fresh handle

                            # If we get here, the handle was invalid but we've recovered
                            if self.verbose:
                                print(
                                    "Handle was invalid but has been successfully reopened",
                                )

                            # Increment retry counter and continue to next iteration
                            retries += 1
                            continue
                        except Exception as recover_error:
                            if self.verbose:
                                print(
                                    f"Failed to recover from error 0: {recover_error}",
                                )
                            # Return empty results, allowing the collector to handle this gracefully
                            return buffer, 0

                    # Error 0x18 (ERROR_NO_MORE_FILES) can happen when there are no new records
                    if error == 0x18:
                        if self.verbose:
                            print(
                                f"No more USN records found after position {start_usn}",
                            )
                        return buffer, 0

                    # Error 0xC0000023 (STATUS_BUFFER_TOO_SMALL) or 0x7A (ERROR_INSUFFICIENT_BUFFER)
                    if error in (0xC0000023, 0x7A):
                        if self.verbose:
                            print(
                                "Buffer too small for USN records, need to increase buffer size",
                            )
                        raise BufferError("USN journal buffer too small")

                    # Try to get the NTSTATUS code if possible (for better diagnostics)
                    nt_status = None
                    try:
                        # Use GetLastErrorEx if available (Windows 10+)
                        if hasattr(ctypes.windll.kernel32, "GetLastWin32ErrorEx"):
                            error_ex = ctypes.c_ulong()
                            nt_status = ctypes.windll.kernel32.GetLastWin32ErrorEx(
                                ctypes.byref(error_ex),
                            )
                            error_ex = error_ex.value
                            nt_status_str = f"NT Status: 0x{nt_status:08X}"
                        else:
                            nt_status_str = "NT Status: Not available"
                    except Exception:
                        nt_status_str = "NT Status: Error retrieving"

                    # Log more detailed error information (only once per error type)
                    # This reduces verbosity while still providing diagnostic info
                    error_msg = f"DeviceIoControl failed with Win32 error code: {error} (0x{error:X}), {nt_status_str}"
                    if error == 0 and self.journal_data:
                        # For error 0, include USN journal state for diagnostics
                        error_msg += (
                            f"\nJournal info - ID: {self.journal_data.UsnJournalID}, "
                        )
                        error_msg += f"First USN: {self.journal_data.FirstUsn}, "
                        error_msg += f"Next USN: {self.journal_data.NextUsn}, "
                        error_msg += (
                            f"Lowest Valid USN: {self.journal_data.LowestValidUsn}, "
                        )
                        error_msg += f"Requested USN: {start_usn}"

                    print(error_msg)

                    # Create a more informative Win32 error
                    if error == 0:
                        error_obj = OSError(f"USN Journal Error: {error_msg}")
                        error_obj.winerror = error
                        raise error_obj
                    else:
                        raise ctypes.WinError(error)

                # If we get here, the operation was successful
                return buffer, bytes_returned.value

            except OSError as e:
                # Handle ERROR_JOURNAL_ENTRY_DELETED (0x570) or STATUS_JOURNAL_ENTRY_DELETED
                # This happens when the requested USN is too old and has been overwritten
                if (
                    getattr(e, "winerror", 0) == 0x570
                    or str(e).find("journal entry has been deleted") != -1
                ):
                    if self.verbose:
                        print(
                            f"Journal entry at USN {start_usn} has been deleted due to journal rotation",
                        )
                        print(
                            f"Resetting to lowest valid USN: {self.journal_data.LowestValidUsn}",
                        )

                    # Return empty buffer but with special metadata for the collector to handle
                    empty_buffer = ctypes.create_string_buffer(8)
                    struct.pack_into(
                        "<Q",
                        empty_buffer,
                        0,
                        self.journal_data.LowestValidUsn,
                    )
                    return empty_buffer, 8

                # Re-raise other Windows errors
                raise

        # If we've exhausted retries, return empty results
        return buffer, 0

    def _parse_usn_record(self, buffer, offset, bytes_returned):
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
        attributes = [
            name
            for flag, name in ATTRIBUTE_FLAGS.items()
            if record.FileAttributes & flag
        ]
        timestamp = filetime_to_datetime(record.TimeStamp)

        return {
            "USN": record.Usn,
            "FileName": filename,
            "Timestamp": timestamp,
            "Reasons": reasons,
            "Attributes": attributes,
            "FileReferenceNumber": record.FileReferenceNumber,
            "ParentFileReferenceNumber": record.ParentFileReferenceNumber,
        }

    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False  # Don't suppress exceptions


def main():
    # Add argument parsing for better integration
    parser = argparse.ArgumentParser(description="USN Journal Reader")
    parser.add_argument(
        "--volume",
        type=str,
        default="C:",
        help="Volume to query (default: C:)",
    )
    parser.add_argument(
        "--start-usn",
        type=int,
        help="Starting USN (default: first USN in journal)",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=50,
        help="Maximum number of records to retrieve (default: 50)",
    )
    parser.add_argument("--verbose", action="store_true", help="Show verbose output")
    args = parser.parse_args()

    if not is_admin():
        print("This script must be run with administrative privileges.")
        sys.exit(1)

    # Check Windows version
    win_version = platform.win32_ver()[0]
    print(
        f"Running on Windows {win_version}. Note: USN journal behavior may vary across versions.",
    )

    # Use UsnJournalReader class with context manager
    with UsnJournalReader(volume=args.volume, verbose=args.verbose) as reader:
        records, next_usn = reader.read_records(
            start_usn=args.start_usn,
            max_records=args.max_records,
        )

        # Display the records
        for record in records:
            print(f"\nUSN: {record['USN']}")
            print(f"File: {record['FileName']}")
            print(f"Timestamp: {record['Timestamp']}")
            print(f"Reasons: {', '.join(record['Reasons'])}")
            print(f"Attributes: {', '.join(record['Attributes'])}")
            print(f"FileRef: {record['FileReferenceNumber']}")
            print(f"ParentFileRef: {record['ParentFileReferenceNumber']}")

        if next_usn:
            print(f"\nNext USN position: {next_usn}")


if __name__ == "__main__":
    main()
