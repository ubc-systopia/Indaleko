#!/usr/bin/env python
"""
USN Journal Test V2.

This script tests USN journal access using a different approach.
It builds several structures using the pywin32 API in a more documented way.
"""

import os
import struct
import sys
import time
from ctypes import *
from datetime import datetime

import pywintypes
import win32file

# Constants for USN journal operations
# Documented at https://learn.microsoft.com/en-us/windows/win32/api/winioctl/ni-winioctl-fsctl_query_usn_journal
FSCTL_QUERY_USN_JOURNAL = 0x000900F4
# Documented at https://learn.microsoft.com/en-us/windows/win32/api/winioctl/ni-winioctl-fsctl_create_usn_journal
FSCTL_CREATE_USN_JOURNAL = 0x000900E7
# Documented at https://learn.microsoft.com/en-us/windows/win32/api/winioctl/ni-winioctl-fsctl_enum_usn_data
FSCTL_ENUM_USN_DATA = 0x000900B3  # Using this instead of READ_USN_JOURNAL


def main():
    """Test USN journal access with an alternative method."""
    print("USN Journal Test V2")
    print("==================")

    volume_path = "\\\\.\\C:"
    print(f"Opening volume {volume_path}...")

    try:
        # Open the volume
        handle = win32file.CreateFile(
            volume_path,
            win32file.GENERIC_READ,  # Using only READ access
            win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
            None,
            win32file.OPEN_EXISTING,
            win32file.FILE_ATTRIBUTE_NORMAL,
            None,
        )
        print("Successfully opened volume")
    except Exception as e:
        print(f"ERROR: Failed to open volume: {e}")
        return 1

    try:
        # Query the USN journal
        print("\nQuerying USN journal...")
        try:
            # Create output buffer to receive data
            buffer_out = bytearray(1024)

            result = win32file.DeviceIoControl(
                handle,
                FSCTL_QUERY_USN_JOURNAL,
                None,  # No input buffer needed
                buffer_out,
            )

            print("Successfully queried the USN journal")

            # Extract basic information
            if len(result) >= 8:
                journal_id = struct.unpack("<Q", result[:8])[0]
                print(f"Journal ID: {journal_id}")
            else:
                print("Warning: Could not extract journal ID")
                journal_id = 0

            if len(result) >= 16:
                first_usn = struct.unpack("<Q", result[8:16])[0]
                print(f"First USN: {first_usn}")
            else:
                print("Warning: Could not extract first USN")
                first_usn = 0

            if len(result) >= 24:
                next_usn = struct.unpack("<Q", result[16:24])[0]
                print(f"Next USN: {next_usn}")
        except Exception as e:
            print(f"ERROR: Failed to query USN journal: {e}")
            return 1

        # Create a test file to generate journal activity
        print("\nCreating test file...")
        test_dir = "C:\\Indaleko_Test"
        os.makedirs(test_dir, exist_ok=True)

        test_file = os.path.join(test_dir, f"test_v2_{int(time.time())}.txt")
        with open(test_file, "w") as f:
            f.write(f"Test file created at {datetime.now()}\n")
        print(f"Created test file: {test_file}")

        # Wait a moment for journal to update
        time.sleep(1)

        # Try to enumerate USN data
        print("\nEnumerating USN data...")
        try:
            # Create a buffer for MFT_ENUM_DATA structure
            # Format:
            # - StartFileReferenceNumber (8 bytes) - 0
            # - LowUsn (8 bytes) - first_usn
            # - HighUsn (8 bytes) - 0xFFFFFFFFFFFFFFFF (max value)
            # - MinMajorVersion (2 bytes) - 2
            # - MaxMajorVersion (2 bytes) - 2
            buffer_in = bytearray(28)
            struct.pack_into(
                "<QQQHH",
                buffer_in,
                0,
                0,
                first_usn,
                0xFFFFFFFFFFFFFFFF,
                2,
                2,
            )

            # Output buffer to receive data
            buffer_out = bytearray(4096)

            try:
                result = win32file.DeviceIoControl(
                    handle,
                    FSCTL_ENUM_USN_DATA,
                    buffer_in,
                    buffer_out,
                )
                print("Successfully read data from USN journal")
            except pywintypes.error as win_err:
                if win_err.winerror == 38:  # ERROR_HANDLE_EOF
                    print(
                        "No new USN records available (reached end of file) - this is normal",
                    )
                    # Create an empty result to continue processing
                    result = bytearray(8)  # 8 bytes for next file ref
                    struct.pack_into("<Q", result, 0, 0)  # Next file ref is 0
                else:
                    raise

            print(f"Successfully read {len(result)} bytes from USN journal")

            # Simple analysis of the data
            if len(result) > 8:
                next_file_ref = struct.unpack("<Q", result[:8])[0]
                print(f"Next file reference: {next_file_ref}")

                # The rest of the buffer contains USN_RECORD structures
                # Each record starts with a record length
                # This parsing is simplified and may not be complete
                offset = 8
                record_count = 0

                while offset < len(result):
                    # Extract record length
                    if offset + 4 <= len(result):
                        record_length = struct.unpack(
                            "<L",
                            result[offset : offset + 4],
                        )[0]
                        if record_length == 0:
                            break

                        print(f"\nRecord {record_count+1}:")
                        print(f"  Record length: {record_length}")

                        # Simple extraction of filename if possible
                        # USN_RECORD structure has filename at variable offset
                        if offset + 58 <= len(result):
                            # Extract filename length and offset
                            file_name_length = struct.unpack(
                                "<H",
                                result[offset + 58 : offset + 60],
                            )[0]
                            file_name_offset = struct.unpack(
                                "<H",
                                result[offset + 60 : offset + 62],
                            )[0]

                            # Extract filename if possible
                            if offset + file_name_offset + file_name_length <= len(
                                result,
                            ):
                                try:
                                    file_name_bytes = result[
                                        offset + file_name_offset : offset + file_name_offset + file_name_length
                                    ]
                                    file_name = file_name_bytes.decode("utf-16-le")
                                    print(f"  Filename: {file_name}")
                                except Exception as e:
                                    print(f"  Error extracting filename: {e}")

                        # Move to next record
                        offset += record_length
                        record_count += 1
                    else:
                        break

                print(f"\nFound {record_count} records")
            else:
                print("No USN record data found")

        except Exception as e:
            print(f"ERROR: Failed to enumerate USN data: {e}")
            print(f"Error class: {e.__class__.__name__}")
            if hasattr(e, "winerror"):
                print(f"Win32 error code: {e.winerror}")
            return 1

        print("\nTest completed successfully")
        return 0

    finally:
        # Close the volume handle
        win32file.CloseHandle(handle)
        print("Closed volume handle")


if __name__ == "__main__":
    try:
        result = main()
        sys.exit(result)
    except Exception as e:
        print(f"Unhandled error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
