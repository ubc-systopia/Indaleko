#!/usr/bin/env python3
"""
NTFS Activity Generator for Indaleko.

This script runs the NTFS USN Journal collector continuously to collect file system
activity data and optionally feed it to the hot tier recorder. It can run for a specified
duration or until manually interrupted.

Usage:
    python activity_generator.py --duration 24 --output activities.jsonl --volumes C:
    python activity_generator.py --duration 24 --record-hot-tier --interval 60

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
import datetime
import logging
import os
import signal
import sys
import time

from datetime import datetime, timedelta
from typing import Any


# Configure environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import collector and recorder classes
from activity.collectors.storage.ntfs.usn_journal_collector import (
    NtfsUsnJournalCollector,
)


try:
    from activity.recorders.storage.ntfs.tiered.hot.recorder import NtfsHotTierRecorder

    HAS_HOT_TIER = True
except ImportError:
    HAS_HOT_TIER = False


class NtfsActivityGenerator:
    """
    Generates and collects NTFS file system activity data continuously.

    This class wraps the NtfsUsnJournalCollector to collect activity data at regular
    intervals and optionally record it to the hot tier database, or save to JSONL files.
    """

    def __init__(self, **kwargs) -> None:
        """
        Initialize the activity generator.

        Args:
            volumes: List of volumes to monitor
            output_dir: Directory to store output files
            interval: Collection interval in seconds
            record_hot_tier: Whether to record to hot tier
            max_file_size: Maximum JSONL file size in MB before rotation
            verbose: Whether to enable verbose logging
        """
        # Set up logging
        self.verbose = kwargs.get("verbose", False)
        log_level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger("NtfsActivityGenerator")

        # File output parameters
        self.output_dir = kwargs.get("output_dir", "data/ntfs_activity")
        self.max_file_size = kwargs.get("max_file_size", 100) * 1024 * 1024  # Convert MB to bytes
        self.output_file = None
        self.current_file_size = 0

        # Create output directory if needed
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)

        # Collection parameters
        self.interval = kwargs.get("interval", 30)  # Default: collect every 30 seconds
        self.volumes = kwargs.get("volumes", ["C:"])
        self.record_hot_tier = kwargs.get("record_hot_tier", False)

        # Runtime state
        self.running = False
        self.start_time = None
        self.end_time = None
        self.duration = kwargs.get("duration", 24)  # Hours
        self.activity_count = 0
        self.cycle_count = 0

        # Initialize collector
        self.collector = NtfsUsnJournalCollector(
            volumes=self.volumes,
            verbose=self.verbose,
        )

        # Initialize recorder if requested
        self.recorder = None
        if self.record_hot_tier:
            if not HAS_HOT_TIER:
                self.logger.error("Hot tier recorder not available - import failed")
                raise ImportError("Hot tier recorder module not available")

            # Use simple initialization with default database config
            self.recorder = NtfsHotTierRecorder(
                ttl_days=7,  # Longer TTL to ensure data sticks around
                debug=self.verbose,
            )
            self.logger.info("Hot tier recorder initialized")

        # Set up signal handlers for graceful termination
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.logger.info(
            f"Initialized NtfsActivityGenerator for volumes: {', '.join(self.volumes)}",
        )

    def _signal_handler(self, sig, frame) -> None:
        """Handle termination signals gracefully."""
        self.logger.info(f"Received signal {sig}, shutting down...")
        self.running = False

    def _get_output_filename(self) -> str:
        """Generate a unique output filename based on current timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.output_dir, f"ntfs_activity_{timestamp}.jsonl")

    def _rotate_output_file(self) -> None:
        """Rotate the output file if it exceeds the maximum size."""
        if self.output_file and self.current_file_size >= self.max_file_size:
            self.logger.info(
                f"Rotating output file (size: {self.current_file_size / (1024*1024):.2f} MB)",
            )
            self.output_file.close()
            self.output_file = None
            self.current_file_size = 0

        if not self.output_file:
            filename = self._get_output_filename()
            self.logger.info(f"Creating new output file: {filename}")
            self.output_file = open(filename, "w", encoding="utf-8")
            self.current_file_size = 0

    def _write_activities_to_file(self, activities: list[dict[str, Any]]) -> None:
        """Write activities to the output file."""
        import json

        if not activities:
            return

        self._rotate_output_file()

        for activity in activities:
            line = json.dumps(activity.model_dump(mode="json"))
            self.output_file.write(line + "\n")
            self.current_file_size += len(line) + 1

        self.output_file.flush()

    def _record_activities_to_hot_tier(self, activities: list[dict[str, Any]]) -> int:
        """Record activities to hot tier database."""
        if not self.recorder or not activities:
            return 0

        try:
            # Store activities and get activity IDs
            activity_ids = self.recorder.store_activities(activities)
            return len(activity_ids)
        except Exception as e:
            self.logger.exception(f"Error recording activities to hot tier: {e}")
            return 0

    def start(self) -> None:
        """Start the activity generator and run until duration expires or interrupted."""
        self.running = True
        self.start_time = datetime.now()

        if self.duration:
            self.end_time = self.start_time + timedelta(hours=self.duration)
            self.logger.info(
                f"Starting activity generator, will run until {self.end_time}",
            )
        else:
            self.logger.info(
                "Starting activity generator, will run until manually stopped",
            )

        # No initialization needed for NtfsUsnJournalCollector, it's done in __init__
        self.logger.info("Collector ready for data collection")

        # Main collection loop
        while self.running:
            # Check if duration has expired
            if self.end_time and datetime.now() >= self.end_time:
                self.logger.info(
                    f"Duration ({self.duration} hours) has expired, stopping",
                )
                self.running = False
                break

            cycle_start = time.time()
            self.cycle_count += 1

            try:
                # Collect activities
                self.logger.info(f"Collecting activities (cycle {self.cycle_count})...")
                activities = self.collector.collect_activities()

                # Process activities
                if activities:
                    activity_count = len(activities)
                    self.activity_count += activity_count

                    self.logger.info(
                        f"Collected {activity_count} activities (total: {self.activity_count})",
                    )

                    # Record to database if requested
                    if self.record_hot_tier:
                        recorded = self._record_activities_to_hot_tier(activities)
                        self.logger.info(
                            f"Recorded {recorded}/{activity_count} activities to hot tier",
                        )

                    # Write to file
                    self._write_activities_to_file(activities)
                else:
                    self.logger.info("No new activities collected")

                # Calculate next cycle timing
                cycle_duration = time.time() - cycle_start
                if cycle_duration < self.interval:
                    # Sleep for the remainder of the interval
                    sleep_time = self.interval - cycle_duration
                    self.logger.debug(f"Sleeping for {sleep_time:.2f} seconds")
                    time.sleep(sleep_time)

            except Exception as e:
                self.logger.error(f"Error in collection cycle: {e}", exc_info=True)
                # Sleep a bit to avoid rapid error loops
                time.sleep(5)

        # Cleanup
        self.stop()

    def stop(self) -> None:
        """Stop the activity generator and clean up resources."""
        self.logger.info("Stopping activity generator...")

        # NtfsUsnJournalCollector doesn't need closing
        self.logger.info("Collector resources released")

        # Close output file
        if self.output_file:
            self.output_file.close()
            self.output_file = None

        # Calculate and log stats
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds() / 3600  # Hours

        self.logger.info("Activity generation summary:")
        self.logger.info(f"- Duration: {duration:.2f} hours")
        self.logger.info(f"- Total cycles: {self.cycle_count}")
        self.logger.info(f"- Total activities: {self.activity_count}")
        self.logger.info(
            f"- Activities per hour: {self.activity_count / max(1, duration):.2f}",
        )
        self.logger.info(
            f"- Activities per cycle: {self.activity_count / max(1, self.cycle_count):.2f}",
        )

        self.logger.info("Activity generator stopped")


def main() -> None:
    """Main entry point for the script."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="NTFS Activity Generator")
    parser.add_argument(
        "--volumes",
        type=str,
        nargs="+",
        default=["C:"],
        help="Volumes to monitor for NTFS activity (default: C:)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=24,
        help="Duration to run in hours (default: 24 hours, 0 for unlimited)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Collection interval in seconds (default: 30)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/ntfs_activity",
        help="Directory to store output files (default: data/ntfs_activity)",
    )
    parser.add_argument(
        "--max-file-size",
        type=int,
        default=100,
        help="Maximum JSONL file size in MB before rotation (default: 100)",
    )
    parser.add_argument(
        "--record-hot-tier",
        action="store_true",
        help="Record activities to hot tier database",
    )
    # Removed db-config-path parameter as it caused issues with database initialization
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Create and start generator
    try:
        generator = NtfsActivityGenerator(
            volumes=args.volumes,
            duration=args.duration,
            interval=args.interval,
            output_dir=args.output_dir,
            max_file_size=args.max_file_size,
            record_hot_tier=args.record_hot_tier,
            db_config_path=args.db_config_path,
            verbose=args.verbose,
        )

        generator.start()
    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
