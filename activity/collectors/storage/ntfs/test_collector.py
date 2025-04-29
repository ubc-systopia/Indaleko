#!/usr/bin/env python
"""
Simple test script for the NtfsStorageActivityCollector.

This script provides a minimal, standalone test for the NTFS
storage activity collector without dependencies on other components.

Usage:
    python test_collector.py --volume C: --duration 60

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
import logging
import os
import random
import sys
import time
import traceback

# Standard Python check for Windows platform
IS_WINDOWS = sys.platform.startswith("win")

# Set up Indaleko root
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


# Import local modules with error handling
try:
    # Try imports required for the collector
    from activity.collectors.storage.ntfs.ntfs_collector import (
        NtfsStorageActivityCollector,
    )
except ImportError as e:
    print(f"ERROR: Could not import required modules: {e}")
    print(
        "Make sure you're running from the right directory or check your Python path.",
    )
    sys.exit(1)


def create_test_file(volume_path):
    """
    Create a simple test file to trigger USN journal activity.

    Args:
        volume_path: Path to the volume (e.g., "C:")

    Returns:
        Path to the created file or None if creation failed
    """
    try:
        # Create test directory
        test_dir = os.path.join(volume_path, "Indaleko_Test")
        os.makedirs(test_dir, exist_ok=True)

        # Create test file
        filename = os.path.join(test_dir, f"test_file_{int(time.time())}.txt")
        with open(filename, "w") as f:
            f.write(f"Test file created at {time.time()}\n")
            f.write(f"Random data: {random.randint(1000, 9999)}\n")

        print(f"Created test file: {filename}")
        return filename
    except Exception as e:
        print(f"Error creating test file: {e}")
        return None


def main():
    """Main function to run the collector test."""
    parser = argparse.ArgumentParser(description="Test the NTFS activity collector")
    parser.add_argument("--volume", default="C:", help="Volume to monitor (e.g., C:)")
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Duration in seconds to run the test (0 for continuous)",
    )
    parser.add_argument("--mock", action="store_true", help="Use mock data")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Basic log configuration
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Print configuration
    print("=== NTFS Collector Test ===")
    print(f"Volume: {args.volume}")
    print(f"Duration: {args.duration} seconds")
    print(f"Mock mode: {args.mock}")
    print(f"Debug logging: {args.debug}")
    print(f"Running on Windows: {IS_WINDOWS}")
    print("-------------------------")

    try:
        # Create the collector
        collector = NtfsStorageActivityCollector(
            volumes=[args.volume],
            auto_start=False,
            mock=args.mock,
            debug=args.debug,
        )

        # Start monitoring
        print("Starting NTFS activity monitoring...")
        collector.start_monitoring()

        # Create a test file to ensure some activity
        if IS_WINDOWS and not args.mock:
            try:
                create_test_file(args.volume)
            except Exception as e:
                print(f"Warning: Could not create test file: {e}")

        # Wait for specified duration or run continuously
        if args.duration > 0:
            print(f"Monitoring for {args.duration} seconds...")
            time.sleep(args.duration / 2)  # Sleep for half the time

            # Create another test file halfway through
            if IS_WINDOWS and not args.mock:
                try:
                    create_test_file(args.volume)
                except Exception as e:
                    print(f"Warning: Could not create second test file: {e}")

            time.sleep(args.duration / 2)  # Sleep for the remaining time
        else:
            print("Monitoring continuously. Press Ctrl+C to stop...")
            try:
                while True:
                    time.sleep(10)
                    # Create a test file every 10 seconds if on Windows
                    if IS_WINDOWS and not args.mock:
                        try:
                            create_test_file(args.volume)
                        except Exception:
                            pass
            except KeyboardInterrupt:
                print("\nMonitoring stopped by user.")

        # Get the activities
        activities = collector.get_activities()

        # Print activity summary
        print("\n=== Activity Summary ===")
        print(f"Total activities collected: {len(activities)}")

        # Count by type
        activity_counts = {}
        for activity in activities:
            activity_type = str(activity.activity_type)
            if activity_type in activity_counts:
                activity_counts[activity_type] += 1
            else:
                activity_counts[activity_type] = 1

        # Print type counts
        if activity_counts:
            print("\nActivities by type:")
            for activity_type, count in activity_counts.items():
                print(f"  {activity_type}: {count}")

        # Show some recent activities
        if activities:
            print("\nMost recent activities:")
            for i, activity in enumerate(activities[-min(5, len(activities)) :]):
                activity_type = getattr(activity, "activity_type", "Unknown")
                file_name = getattr(activity, "file_name", "Unknown")
                print(f"  {i+1}. {activity_type} - {file_name}")
                if hasattr(activity, "file_path"):
                    print(f"     Path: {activity.file_path}")
        else:
            print("\nNo activities were detected.")
            print("If running on Windows, check that the USN journal is working.")
            print("If not on Windows, make sure you're using --mock mode.")

        # Stop monitoring
        collector.stop_monitoring()
        print("\nNTFS monitoring stopped.")

    except Exception as e:
        print(f"Error running collector test: {e}")
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    # Check if we're on Windows or using mock mode
    if not IS_WINDOWS:
        print("WARNING: This script is designed for Windows systems with NTFS.")
        print("         Use --mock when running on non-Windows platforms.")

    # Check for required Windows dependencies if on Windows
    if IS_WINDOWS:
        try:
            import pywintypes
            import win32api
            import win32con
            import win32file
        except ImportError:
            print("ERROR: This test requires the pywin32 package on Windows.")
            print("       Please install it using: pip install pywin32")
            sys.exit(1)

    # Run the main function
    exit_code = main()
    sys.exit(exit_code)
