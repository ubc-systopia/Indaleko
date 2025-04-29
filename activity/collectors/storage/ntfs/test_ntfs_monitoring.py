#!/usr/bin/env python
"""
NTFS Storage Activity Monitoring Test Tool.

This script provides a command-line tool for testing and diagnosing the NTFS
USN journal monitoring functionality in Indaleko.

Features:
- Real-time monitoring of NTFS file system activity
- Forced generation of test file activities
- Diagnostic output for troubleshooting
- Verbose logging of USN journal records

Usage:
    python test_ntfs_monitoring.py --volume C: --duration 60 --debug
    python test_ntfs_monitoring.py --volume C: --force-activity --interval 5

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
import threading
import time
import traceback
from datetime import datetime

# Ensure we can import from the main Indaleko package
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import the collector and recorder
from activity.collectors.storage.ntfs.ntfs_collector import NtfsStorageActivityCollector


def generate_file_activity(volume, stop_event, interval=5):
    """
    Generate real file activity on the specified volume.

    Args:
        volume: The volume to create files on (e.g., "C:")
        stop_event: Threading event to signal when to stop
        interval: Interval between file operations in seconds
    """
    logger = logging.getLogger("FileActivityGenerator")

    # Create test directory
    test_dir = os.path.join(volume, "Indaleko_Test")
    if not os.path.exists(test_dir):
        try:
            os.makedirs(test_dir, exist_ok=True)
            logger.info(f"Created test directory {test_dir}")
        except Exception as e:
            logger.error(f"Failed to create test directory: {e}")
            return

    # File operations to perform in a cycle
    operation_count = 0
    while not stop_event.is_set():
        try:
            timestamp = int(time.time())
            operation = operation_count % 3

            if operation == 0:  # Create file
                filename = os.path.join(test_dir, f"test_file_{timestamp}.txt")
                with open(filename, "w") as f:
                    f.write(f"Test file created at {datetime.now()}\n")
                    f.write(f"Random content: {random.randint(1000, 9999)}\n")
                logger.info(f"Created file: {filename}")

            elif operation == 1:  # Modify file
                files = [f for f in os.listdir(test_dir) if f.startswith("test_file_") and f.endswith(".txt")]
                if files:
                    random_file = random.choice(files)
                    filepath = os.path.join(test_dir, random_file)
                    with open(filepath, "a") as f:
                        f.write(f"Modified at {datetime.now()}\n")
                        f.write(f"More random content: {random.randint(1000, 9999)}\n")
                    logger.info(f"Modified file: {filepath}")

            elif operation == 2:  # Rename or delete
                files = [f for f in os.listdir(test_dir) if f.startswith("test_file_") and f.endswith(".txt")]
                if len(files) > 5:  # Keep file count reasonable
                    action = random.choice(["rename", "delete"])
                    random_file = random.choice(files)
                    filepath = os.path.join(test_dir, random_file)

                    if action == "rename":
                        new_name = os.path.join(test_dir, f"renamed_{random_file}")
                        os.rename(filepath, new_name)
                        logger.info(f"Renamed file: {filepath} to {new_name}")
                    else:
                        os.remove(filepath)
                        logger.info(f"Deleted file: {filepath}")

            operation_count += 1
            time.sleep(interval)
        except Exception as e:
            logger.error(f"Error generating file activity: {e}")
            time.sleep(interval)


def main():
    """Main function that runs the test tool."""
    parser = argparse.ArgumentParser(
        description="NTFS Storage Activity Monitoring Test Tool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Add general arguments
    parser.add_argument(
        "--volume",
        type=str,
        default="C:",
        help="Volume to monitor (e.g., 'C:', 'D:')",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Monitoring duration in seconds (0 = run until Ctrl+C)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output of detected activities",
    )

    # Add monitoring options
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Monitoring interval in seconds",
    )
    parser.add_argument(
        "--include-close",
        action="store_true",
        help="Include file close events",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock data even on Windows",
    )
    parser.add_argument(
        "--no-volume-guids",
        action="store_true",
        help="Use drive letters instead of volume GUIDs",
    )

    # Add test options
    parser.add_argument(
        "--force-activity",
        action="store_true",
        help="Force file activity generation for testing",
    )
    parser.add_argument(
        "--activity-interval",
        type=float,
        default=5.0,
        help="Interval between forced file activities in seconds",
    )

    # Parse arguments
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=log_level, format=log_format)
    logger = logging.getLogger("NtfsMonitoringTest")

    # Display configuration
    logger.info("=== NTFS Storage Activity Monitoring Test ===")
    logger.info(f"Volume: {args.volume}")
    logger.info(
        f"Duration: {args.duration if args.duration > 0 else 'Until Ctrl+C'} seconds",
    )
    logger.info(f"Debug mode: {'Enabled' if args.debug else 'Disabled'}")
    logger.info(f"Verbose output: {'Enabled' if args.verbose else 'Disabled'}")
    logger.info(f"Monitor interval: {args.interval} seconds")
    logger.info(f"Include close events: {'Yes' if args.include_close else 'No'}")
    logger.info(f"Mock data: {'Yes' if args.mock else 'No'}")
    logger.info(f"Use volume GUIDs: {'No' if args.no_volume_guids else 'Yes'}")
    logger.info(f"Force activity generation: {'Yes' if args.force_activity else 'No'}")
    if args.force_activity:
        logger.info(f"Activity generation interval: {args.activity_interval} seconds")

    # Start activity monitoring
    try:
        # Configure the collector with settings from arguments
        collector_args = {
            "volumes": [args.volume],
            "monitor_interval": args.interval,
            "include_close_events": args.include_close,
            "use_volume_guids": not args.no_volume_guids,
            "debug": args.debug,
            "mock": args.mock,
            "auto_start": False,  # We'll start it manually
        }

        # Create the collector
        collector = NtfsStorageActivityCollector(**collector_args)
        logger.info(f"Created NTFS Storage Activity Collector for volume {args.volume}")

        # Start monitoring
        collector.start_monitoring()
        logger.info("Started monitoring NTFS activities")

        # Create a stop event for clean shutdown
        stop_event = threading.Event()

        # Start file activity generator if requested
        activity_thread = None
        if args.force_activity:
            logger.info(
                f"Starting file activity generator with interval {args.activity_interval}s",
            )
            activity_thread = threading.Thread(
                target=generate_file_activity,
                args=(args.volume, stop_event, args.activity_interval),
                daemon=True,
            )
            activity_thread.start()

        # Monitoring loop
        try:
            if args.duration > 0:
                # Run for specified duration
                logger.info(f"Monitoring for {args.duration} seconds...")

                start_time = time.time()
                end_time = start_time + args.duration

                while time.time() < end_time:
                    # Get current activities
                    activities = collector.get_activities()

                    # Display activity counts
                    activity_counts = {}
                    for activity in activities:
                        activity_type = str(activity.activity_type)
                        if activity_type in activity_counts:
                            activity_counts[activity_type] += 1
                        else:
                            activity_counts[activity_type] = 1

                    # Only log if we have activities or in verbose mode
                    if activities or args.verbose:
                        logger.info(f"Current activity count: {len(activities)}")
                        if activity_counts:
                            logger.info(f"Activities by type: {activity_counts}")

                        # Print the most recent activities in verbose mode
                        if args.verbose and activities:
                            logger.info("Recent activities (showing up to 5):")
                            for i, activity in enumerate(activities[-5:]):
                                logger.info(
                                    f"  {i+1}. [{activity.activity_type}] {activity.file_name}",
                                )
                                if hasattr(activity, "file_path"):
                                    logger.info(f"     Path: {activity.file_path}")

                    # Sleep before checking again
                    time.sleep(1)
            else:
                # Run until Ctrl+C
                logger.info("Monitoring until Ctrl+C is pressed...")

                # Print initial header
                print("\nNTFS Activity Monitor - Press Ctrl+C to stop")
                print("=" * 80)

                activity_interval = max(
                    1,
                    int(args.interval * 2),
                )  # Display update interval
                last_count = 0

                while True:
                    try:
                        # Get current activities
                        activities = collector.get_activities()

                        # Calculate new activities since last check
                        new_count = len(activities) - last_count

                        # Print activity summary if there are new activities
                        if new_count > 0 or args.verbose:
                            print(
                                f"\nTotal activities: {len(activities)} (new: {new_count})",
                            )

                            # Calculate counts by type
                            activity_counts = {}
                            for activity in activities:
                                activity_type = str(activity.activity_type)
                                if activity_type in activity_counts:
                                    activity_counts[activity_type] += 1
                                else:
                                    activity_counts[activity_type] = 1

                            # Print counts by type
                            if activity_counts:
                                print("Activities by type:")
                                for activity_type, count in activity_counts.items():
                                    print(f"  {activity_type}: {count}")

                            # Print the most recent activities (up to 5)
                            if activities:
                                print("\nMost recent activities:")
                                for i, activity in enumerate(
                                    activities[-min(5, len(activities)) :],
                                ):
                                    timestamp = (
                                        activity.timestamp.strftime("%H:%M:%S")
                                        if hasattr(activity, "timestamp")
                                        else "Unknown"
                                    )
                                    filename = activity.file_name if hasattr(activity, "file_name") else "Unknown"
                                    activity_type = (
                                        activity.activity_type if hasattr(activity, "activity_type") else "Unknown"
                                    )

                                    print(
                                        f"  {i+1}. [{timestamp}] [{activity_type}] {filename}",
                                    )

                            # Update last count
                            last_count = len(activities)

                        # Sleep before next update
                        time.sleep(activity_interval)
                    except KeyboardInterrupt:
                        print("\nMonitoring stopped by user")
                        break
                    except Exception as e:
                        logger.error(f"Error in monitoring loop: {e}")
                        time.sleep(activity_interval)

        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")

    except Exception as e:
        logger.error(f"Error setting up NTFS monitoring: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Clean shutdown
        logger.info("Shutting down...")

        # Signal activity generator to stop
        if args.force_activity:
            stop_event.set()
            if activity_thread:
                activity_thread.join(timeout=2)

        # Stop collector
        try:
            if "collector" in locals() and collector:
                collector.stop_monitoring()
                logger.info("NTFS monitoring stopped")
        except Exception as e:
            logger.error(f"Error stopping collector: {e}")

    logger.info("Test completed")


if __name__ == "__main__":
    try:
        # Check if we're running on Windows
        if not sys.platform.startswith("win"):
            print("WARNING: This script is designed for Windows systems with NTFS.")
            print("         It may not work correctly on other platforms.")

        # Check for required dependencies
        try:
            import pywintypes
            import win32api
            import win32con
            import win32file
        except ImportError:
            print("ERROR: This test module requires the pywin32 package.")
            print("       Please install it using: pip install pywin32")
            sys.exit(1)

        main()
    except Exception as e:
        print(f"ERROR: {e}")
        print("An unexpected error occurred:")
        traceback.print_exc()
        sys.exit(1)
