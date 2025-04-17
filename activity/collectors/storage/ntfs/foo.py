import ctypes
import struct
import platform
from ctypes import wintypes
from datetime import datetime

# Windows API constants
FSCTL_QUERY_USN_JOURNAL = 0x900f4
FSCTL_READ_USN_JOURNAL = 0x900bb
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
    0x80000000: "CLOSE"
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
    0x00004000: "ENCRYPTED"
}

# Define USN_JOURNAL_DATA structure
class USN_JOURNAL_DATA(ctypes.Structure):
    _fields_ = [
        ("UsnJournalID", ctypes.c_ulonglong),  # 64-bit unsigned
        ("FirstUsn", ctypes.c_longlong),       # 64-bit signed
        ("NextUsn", ctypes.c_longlong),
        ("LowestValidUsn", ctypes.c_longlong),
        ("MaxUsn", ctypes.c_longlong),
        ("MaximumSize", ctypes.c_ulonglong),
        ("AllocationDelta", ctypes.c_ulonglong)
    ]

# Define READ_USN_JOURNAL_DATA structure (V0 for compatibility)
class READ_USN_JOURNAL_DATA(ctypes.Structure):
    _fields_ = [
        ("StartUsn", ctypes.c_longlong),
        ("ReasonMask", wintypes.DWORD),
        ("ReturnOnlyOnClose", wintypes.DWORD),
        ("Timeout", ctypes.c_ulonglong),
        ("BytesToWaitFor", ctypes.c_ulonglong),
        ("UsnJournalID", ctypes.c_ulonglong)
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
        ("FileName", wintypes.WCHAR * 1)  # Variable length
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
        None
    )
    if handle == -1:
        raise ctypes.WinError()
    return handle

def query_usn_journal(handle):
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
        None
    )
    if not success:
        raise ctypes.WinError()

    return journal_data

def read_usn_journal(handle, journal_id, start_usn):
    """Read USN journal entries."""
    read_data = READ_USN_JOURNAL_DATA(
        StartUsn=start_usn,
        ReasonMask=0xFFFFFFFF,  # All reasons
        ReturnOnlyOnClose=0,
        Timeout=0,
        BytesToWaitFor=0,
        UsnJournalID=journal_id
    )
    buffer_size = 4096
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
        None
    )
    if not success:
        error = ctypes.get_last_error()
        print(f"DeviceIoControl failed with Win32 error code: {error}")
        raise ctypes.WinError(error)

    return buffer, bytes_returned.value

def parse_usn_record(buffer, offset, bytes_returned):
    """Parse a USN record from the buffer."""
    if offset + 4 > bytes_returned:
        return None

    record_length = struct.unpack_from("<I", buffer, offset)[0]
    if record_length == 0 or offset + record_length > bytes_returned:
        return None

    record = USN_RECORD.from_buffer_copy(buffer[offset:offset + record_length])

    filename_offset = record.FileNameOffset
    filename_length = record.FileNameLength
    filename_end = filename_offset + filename_length
    if filename_end > record_length:
        return None

    try:
        filename = buffer[offset + filename_offset:offset + filename_end].decode('utf-16-le', errors='replace')
    except UnicodeDecodeError:
        filename = "<invalid filename>"

    reasons = [name for flag, name in REASON_FLAGS.items() if record.Reason & flag]
    attributes = [name for flag, name in ATTRIBUTE_FLAGS.items() if record.FileAttributes & flag]
    timestamp = filetime_to_datetime(record.TimeStamp)

    return {
        "USN": record.Usn,
        "FileName": filename,
        "Timestamp": timestamp,
        "Reasons": reasons,
        "Attributes": attributes,
        "FileReferenceNumber": record.FileReferenceNumber,
        "ParentFileReferenceNumber": record.ParentFileReferenceNumber
    }

def main():
    if not is_admin():
        print("This script must be run with administrative privileges.")
        return

    # Check Windows version
    win_version = platform.win32_ver()[0]
    print(f"Running on Windows {win_version}. Note: USN journal behavior may vary across versions.")

    volume_path = "\\\\.\\C:"  # Adjust for desired volume
    try:
        # Open volume handle
        handle = get_volume_handle(volume_path)

        try:
            # Query USN journal
            journal_data = query_usn_journal(handle)
            print(f"Journal ID: {journal_data.UsnJournalID}")
            print(f"First USN: {journal_data.FirstUsn}")
            print(f"Next USN: {journal_data.NextUsn}")

            # Read USN journal
            buffer, bytes_returned = read_usn_journal(handle, journal_data.UsnJournalID, journal_data.FirstUsn)

            # Parse records
            offset = 8  # Skip first 8 bytes (NextUsn)
            while offset < bytes_returned:
                record = parse_usn_record(buffer, offset, bytes_returned)
                if record is None:
                    break
                print(f"\nUSN: {record['USN']}")
                print(f"File: {record['FileName']}")
                print(f"Timestamp: {record['Timestamp']}")
                print(f"Reasons: {', '.join(record['Reasons'])}")
                print(f"Attributes: {', '.join(record['Attributes'])}")
                print(f"FileRef: {record['FileReferenceNumber']}")
                print(f"ParentFileRef: {record['ParentFileReferenceNumber']}")

                offset += struct.unpack_from("<I", buffer, offset)[0]

        finally:
            ctypes.windll.kernel32.CloseHandle(handle)

    except WindowsError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
