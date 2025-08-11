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

    volume_path = "\\\\.\\C:"

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
    except Exception:
        return 1

    try:
        # Query the USN journal
        try:
            # Create output buffer to receive data
            buffer_out = bytearray(1024)

            result = win32file.DeviceIoControl(
                handle,
                FSCTL_QUERY_USN_JOURNAL,
                None,  # No input buffer needed
                buffer_out,
            )


            # Extract basic information
            struct.unpack("<Q", result[:8])[0] if len(result) >= 8 else 0

            first_usn = struct.unpack("<Q", result[8:16])[0] if len(result) >= 16 else 0

            if len(result) >= 24:
                struct.unpack("<Q", result[16:24])[0]
        except Exception:
            return 1

        # Create a test file to generate journal activity
        test_dir = "C:\\Indaleko_Test"
        os.makedirs(test_dir, exist_ok=True)

        test_file = os.path.join(test_dir, f"test_v2_{int(time.time())}.txt")
        with open(test_file, "w") as f:
            f.write(f"Test file created at {datetime.now()}\n")

        # Wait a moment for journal to update
        time.sleep(1)

        # Try to enumerate USN data
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
            except pywintypes.error as win_err:
                if win_err.winerror == 38:  # ERROR_HANDLE_EOF
                    # Create an empty result to continue processing
                    result = bytearray(8)  # 8 bytes for next file ref
                    struct.pack_into("<Q", result, 0, 0)  # Next file ref is 0
                else:
                    raise


            # Simple analysis of the data
            if len(result) > 8:
                struct.unpack("<Q", result[:8])[0]

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
                                    file_name_bytes.decode("utf-16-le")
                                except Exception:
                                    pass

                        # Move to next record
                        offset += record_length
                        record_count += 1
                    else:
                        break

            else:
                pass

        except Exception as e:
            if hasattr(e, "winerror"):
                pass
            return 1

        return 0

    finally:
        # Close the volume handle
        win32file.CloseHandle(handle)


if __name__ == "__main__":
    try:
        result = main()
        sys.exit(result)
    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(1)
