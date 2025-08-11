#!/usr/bin/env python
"""
Minimal USN Journal test.

This is the most basic possible test for USN journal functionality.
"""

import os
import struct
import sys
import time

import win32file


# Define constants
FSCTL_QUERY_USN_JOURNAL = 0x000900F4
FSCTL_CREATE_USN_JOURNAL = 0x000900E7
FSCTL_READ_USN_JOURNAL = 0x000900BB


def main() -> int | None:
    """Basic USN test."""
    # Try to open the C: volume
    volume_path = "\\\\.\\C:"

    try:
        handle = win32file.CreateFile(
            volume_path,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
            None,
            win32file.OPEN_EXISTING,
            win32file.FILE_ATTRIBUTE_NORMAL,
            None,
        )
    except Exception:
        return 1

    try:
        # Try to query the USN journal
        try:
            result = win32file.DeviceIoControl(
                handle,
                FSCTL_QUERY_USN_JOURNAL,
                None,
                1024,
            )

            # Extract journal ID and first USN
            struct.unpack("<Q", result[:8])[0]
            first_usn = struct.unpack("<Q", result[8:16])[0]
        except Exception:

            # Try to create the journal
            try:
                max_size = 32 * 1024 * 1024
                allocation_delta = 4 * 1024 * 1024
                buffer_in = struct.pack("<QQ", max_size, allocation_delta)

                result = win32file.DeviceIoControl(
                    handle,
                    FSCTL_CREATE_USN_JOURNAL,
                    buffer_in,
                    0,
                )

                # Now query again
                result = win32file.DeviceIoControl(
                    handle,
                    FSCTL_QUERY_USN_JOURNAL,
                    None,
                    1024,
                )

                # Extract journal ID and first USN
                struct.unpack("<Q", result[:8])[0]
                first_usn = struct.unpack("<Q", result[8:16])[0]
            except Exception:
                return 1

        # Create a test file
        test_dir = "C:\\Indaleko_Test"
        if not os.path.exists(test_dir):
            os.makedirs(test_dir, exist_ok=True)

        test_file = os.path.join(test_dir, f"minimal_test_{int(time.time())}.txt")
        with open(test_file, "w") as f:
            f.write(f"Test file created at {time.time()}\n")

        # Wait a moment
        time.sleep(1)

        # Read USN records
        try:
            # Create the MFT_ENUM_DATA structure for the journal
            # The format is specific and must be exactly correct
            # Structure is:
            # - StartFileReferenceNumber (8 bytes, ULONGLONG)
            # - LowUsn (8 bytes, ULONGLONG)
            # - HighUsn (8 bytes, ULONGLONG)
            # - MinMajorVersion (2 bytes, USHORT)
            # - MaxMajorVersion (2 bytes, USHORT)

            # Make a different buffer format that works better with DeviceIoControl
            from array import array

            buffer_in = array("B", 32 * [0])  # 32 bytes buffer filled with zeros

            # Fill the buffer with proper values
            # StartFileReferenceNumber = 0 (start from beginning)
            struct.pack_into("<Q", buffer_in, 0, 0)
            # LowUsn = first_usn
            struct.pack_into("<Q", buffer_in, 8, first_usn)
            # HighUsn = 0xFFFFFFFFFFFFFFFF (max value)
            struct.pack_into("<Q", buffer_in, 16, 0xFFFFFFFFFFFFFFFF)
            # MinMajorVersion = 2, MaxMajorVersion = 2
            struct.pack_into("<HH", buffer_in, 24, 2, 2)


            # Read the journal with correct structure
            result = win32file.DeviceIoControl(
                handle,
                FSCTL_READ_USN_JOURNAL,
                buffer_in,
                65536,
            )


            # Extract next USN
            struct.unpack("<Q", result[:8])[0]

            # Basic information about the data
            if len(result) > 8:
                pass
            else:
                pass

            return 0
        except Exception:
            return 1

    finally:
        # Close handle
        win32file.CloseHandle(handle)


if __name__ == "__main__":
    result = main()
    sys.exit(result)
