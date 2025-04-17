#!/usr/bin/env python
"""
Minimal USN Journal test.

This is the most basic possible test for USN journal functionality.
"""

import os
import sys
import win32file
import struct
import time

# Define constants
FSCTL_QUERY_USN_JOURNAL = 0x000900f4
FSCTL_CREATE_USN_JOURNAL = 0x000900e7
FSCTL_READ_USN_JOURNAL = 0x000900bb

def main():
    """Basic USN test."""
    print("Minimal USN Journal Test")
    print("=======================")
    
    # Try to open the C: volume
    print("Opening volume...")
    volume_path = "\\\\.\\C:"
    
    try:
        handle = win32file.CreateFile(
            volume_path,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
            None,
            win32file.OPEN_EXISTING,
            win32file.FILE_ATTRIBUTE_NORMAL,
            None
        )
        print(f"SUCCESS: Opened volume {volume_path}")
    except Exception as e:
        print(f"ERROR: Failed to open volume: {e}")
        return 1
    
    try:
        # Try to query the USN journal
        print("\nQuerying USN journal...")
        try:
            result = win32file.DeviceIoControl(
                handle,
                FSCTL_QUERY_USN_JOURNAL,
                None,
                1024
            )
            print("SUCCESS: USN journal query successful")
            
            # Extract journal ID and first USN
            journal_id = struct.unpack("<Q", result[:8])[0]
            first_usn = struct.unpack("<Q", result[8:16])[0]
            print(f"Journal ID: {journal_id}")
            print(f"First USN: {first_usn}")
        except Exception as e:
            print(f"ERROR: Failed to query USN journal: {e}")
            
            # Try to create the journal
            print("\nTrying to create USN journal...")
            try:
                max_size = 32 * 1024 * 1024
                allocation_delta = 4 * 1024 * 1024
                buffer_in = struct.pack("<QQ", max_size, allocation_delta)
                
                result = win32file.DeviceIoControl(
                    handle,
                    FSCTL_CREATE_USN_JOURNAL,
                    buffer_in,
                    0
                )
                print("SUCCESS: USN journal created")
                
                # Now query again
                result = win32file.DeviceIoControl(
                    handle,
                    FSCTL_QUERY_USN_JOURNAL,
                    None,
                    1024
                )
                print("SUCCESS: USN journal query successful after creation")
                
                # Extract journal ID and first USN
                journal_id = struct.unpack("<Q", result[:8])[0]
                first_usn = struct.unpack("<Q", result[8:16])[0]
                print(f"Journal ID: {journal_id}")
                print(f"First USN: {first_usn}")
            except Exception as e2:
                print(f"ERROR: Failed to create USN journal: {e2}")
                return 1
        
        # Create a test file
        print("\nCreating test file...")
        test_dir = "C:\\Indaleko_Test"
        if not os.path.exists(test_dir):
            os.makedirs(test_dir, exist_ok=True)
        
        test_file = os.path.join(test_dir, f"minimal_test_{int(time.time())}.txt")
        with open(test_file, 'w') as f:
            f.write(f"Test file created at {time.time()}\n")
        print(f"Created test file: {test_file}")
        
        # Wait a moment
        print("Waiting for USN journal to update...")
        time.sleep(1)
        
        # Read USN records
        print("\nReading USN journal records...")
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
            buffer_in = array('B', 32 * [0])  # 32 bytes buffer filled with zeros
            
            # Fill the buffer with proper values
            # StartFileReferenceNumber = 0 (start from beginning)
            struct.pack_into('<Q', buffer_in, 0, 0)
            # LowUsn = first_usn
            struct.pack_into('<Q', buffer_in, 8, first_usn)
            # HighUsn = 0xFFFFFFFFFFFFFFFF (max value)
            struct.pack_into('<Q', buffer_in, 16, 0xFFFFFFFFFFFFFFFF)
            # MinMajorVersion = 2, MaxMajorVersion = 2
            struct.pack_into('<HH', buffer_in, 24, 2, 2)
            
            print(f"Created buffer: {buffer_in.tobytes().hex()}")
            
            # Read the journal with correct structure
            result = win32file.DeviceIoControl(
                handle,
                FSCTL_READ_USN_JOURNAL,
                buffer_in,
                65536
            )
            
            print(f"Read {len(result)} bytes from USN journal")
            
            # Extract next USN
            next_usn = struct.unpack("<Q", result[:8])[0]
            print(f"Next USN: {next_usn}")
            
            # Basic information about the data
            if len(result) > 8:
                print(f"Journal contains {len(result) - 8} bytes of record data")
                print("Basic data dump (first 64 bytes):")
                print(result[:64].hex())
            else:
                print("No record data available")
                
            print("\nTest completed successfully")
            return 0
        except Exception as e:
            print(f"ERROR: Failed to read USN journal: {e}")
            return 1
            
    finally:
        # Close handle
        win32file.CloseHandle(handle)
        print("Closed volume handle")

if __name__ == "__main__":
    result = main()
    sys.exit(result)