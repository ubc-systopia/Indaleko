#!/usr/bin/env python
"""
Integrated NTFS Activity Collection and Recording Script.

This script provides an integrated approach to collecting and recording NTFS
activities while maintaining proper separation of concerns. It follows the
wrapper pattern where the recorder wraps the collector but maintains proper
separation of responsibilities:
1. The collector only collects data
2. The recorder only handles processing and storage

For long-running data collection (days or weeks), this integrated approach
is more convenient while still maintaining architectural integrity.

Usage:
    python run_ntfs_activity.py --duration 168 --volumes C: --interval 30

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
import signal
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).resolve().parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.append(str(current_path))

# Import collector and recorder classes
from activity.collectors.storage.ntfs.usn_journal_collector import (
    NtfsUsnJournalCollector,
)
from activity.recorders.storage.ntfs.tiered.hot.recorder import NtfsHotTierRecorder
from constants.values import IndalekoConstants

# Create default DB config path using pathlib.Path
DEFAULT_DB_CONFIG_PATH = Path(IndalekoConstants.default_config_dir) / IndalekoConstants.default_db_config_file_name


class IntegratedNtfsActivityRunner:
    """
    Integrated runner that properly wraps the collector with a recorder.

    This class maintains separation of concerns but provides a convenient
    integrated interface for continuous data collection.
    """

    def __init__(self, **kwargs):
        """
        Initialize the integrated runner.

        Args:
            volumes: List of volumes to monitor
            interval: Collection interval in seconds
            db_config_path: Path to database configuration
            ttl_days: Number of days to keep data in hot tier
            backup_to_files: Whether to also backup data to JSONL files
            output_dir: Directory for file backups (if enabled)
            verbose: Whether to enable verbose logging
        """
        # Set up logging: console + file
        self.verbose = kwargs.get("verbose", False)
        log_level = logging.DEBUG if self.verbose else logging.INFO
        # Configure root logger
        import socket
        from logging import Formatter
        from logging.handlers import RotatingFileHandler

        from utils.logging.file_namer import build_indaleko_log_name

        root = logging.getLogger()
        root.setLevel(log_level)
        fmt = Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(log_level)
        ch.setFormatter(fmt)
        root.addHandler(ch)
        # File handler
        log_dir = kwargs.get("log_dir", "logs")
        os.makedirs(log_dir, exist_ok=True)
        machine_id = kwargs.get("machine_id") or socket.gethostname()
        ts = datetime.now(UTC).strftime("%Y_%m_%dT%H#%M#%S.%fZ")
        fname = build_indaleko_log_name(
            platform="Windows",
            service="ntfs_activity_collector",
            machine_uuid=machine_id,
            timestamp=datetime.now(UTC),
        )
        log_path = os.path.join(log_dir, fname)
        fh = RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        fh.setLevel(log_level)
        fh.setFormatter(fmt)
        root.addHandler(fh)
        # Use named logger
        self.logger = logging.getLogger("IntegratedNtfsActivityRunner")

        # Runtime parameters
        self.volumes = kwargs.get("volumes", ["C:"])
        self.interval = kwargs.get("interval", 30)
        self.duration = kwargs.get("duration", 24)  # Hours
        self.backup_to_files = kwargs.get("backup_to_files", True)
        self.running = False
        self.start_time = None
        self.end_time = None
        self.activity_count = 0
        self.cycle_count = 0

        # Setup file output if backups enabled
        self.output_file = None
        self.current_file_size = 0
        if self.backup_to_files:
            self.output_dir = kwargs.get("output_dir", "data/ntfs_activity")
            self.max_file_size = kwargs.get("max_file_size", 100) * 1024 * 1024  # MB to bytes

            # Create output directory if needed
            os.makedirs(self.output_dir, exist_ok=True)

        # Setup state file path for collector
        state_file_path = os.path.join(
            kwargs.get("output_dir", "data/ntfs_activity"),
            "ntfs_state.json",
        )

        # Initialize collector (only responsible for collecting data)
        self.logger.info(
            f"Initializing NTFS USN Journal collector for volumes: {', '.join(self.volumes)}",
        )
        self.collector = NtfsUsnJournalCollector(
            volumes=self.volumes,
            state_file=state_file_path,
            use_state_file=kwargs.get("use_state_file", False),
            verbose=self.verbose,
        )

        # Track errors for auto-reset purposes
        self.consecutive_errors = 0
        self.consecutive_empty_results = 0
        self.auto_reset_enabled = kwargs.get("auto_reset", True)
        self.error_threshold = kwargs.get("error_threshold", 3)
        self.empty_results_threshold = kwargs.get("empty_results_threshold", 3)

        # Initialize recorder (only responsible for processing and storing data)
        self.logger.info("Initializing hot tier recorder")

        # Setup recorder configuration with only the essential parameters
        # Collection name will be determined by the registration service
        recorder_config = {
            "ttl_days": kwargs.get("ttl_days", 4),
            "db_config_path": kwargs.get("db_config_path", str(DEFAULT_DB_CONFIG_PATH)),
            "debug": self.verbose,
        }

        try:
            self.recorder = NtfsHotTierRecorder(**recorder_config)
            self.logger.info("Hot tier recorder initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize recorder: {e!s}")
            self.logger.warning("Will continue with file output only")
            self.recorder = None
            self.backup_to_files = True  # Force file backup if recorder fails

        # Set up signal handlers for graceful termination
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.logger.info("Integrated NTFS activity runner initialized")

    def _signal_handler(self, sig, frame):
        """Handle termination signals gracefully."""
        self.logger.info(f"Received signal {sig}, shutting down...")
        self.running = False

    def _get_output_filename(self) -> str:
        """Generate a unique output filename based on current timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.output_dir, f"ntfs_activity_{timestamp}.jsonl")

    def _rotate_output_file(self):
        """Rotate the output file if it exceeds the maximum size."""
        if not self.backup_to_files:
            return

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

    def _write_activities_to_file(self, activities: list[dict[str, Any]]):
        """Write activities to backup file if enabled."""
        if not self.backup_to_files or not activities:
            return

        import json

        self._rotate_output_file()

        for activity in activities:
            line = json.dumps(activity.model_dump(mode="json"))
            self.output_file.write(line + "\n")
            self.current_file_size += len(line) + 1

        self.output_file.flush()
        self.logger.debug(f"Wrote {len(activities)} activities to backup file")

    def _record_activities(self, activities: list) -> int:
        """
        Record activities using the recorder.

        This maintains separation of concerns by only having the recorder
        handle database operations.

        Args:
            activities: List of activities to record

        Returns:
            Number of successfully recorded activities
        """
        if not self.recorder or not activities:
            return 0

        try:
            # The recorder handles all database operations
            activity_ids = self.recorder.store_activities(activities)
            return len(activity_ids)
        except Exception as e:
            self.logger.error(f"Error recording activities: {e!s}")
            if self.verbose:
                self.logger.exception("Detailed error:")
            return 0

    def start(self):
        """Start the integrated collection and recording process."""
        self.running = True
        self.start_time = datetime.now(UTC)  # Use timezone-aware datetime

        if self.duration:
            self.end_time = self.start_time + timedelta(hours=self.duration)
            self.logger.info(
                f"Starting integrated runner, will run until {self.end_time}",
            )
        else:
            self.logger.info(
                "Starting integrated runner, will run until manually stopped",
            )

        # Main collection and recording loop
        while self.running:
            # Check if duration has expired - ensure timezone-aware comparison
            current_time = datetime.now(UTC)
            if self.end_time and current_time >= self.end_time:
                self.logger.info(
                    f"Duration ({self.duration} hours) has expired, stopping",
                )
                self.running = False
                break

            cycle_start = time.time()
            self.cycle_count += 1

            try:
                # Collect activities (collector's responsibility)
                self.logger.info(f"Collecting activities (cycle {self.cycle_count})...")
                try:
                    activities = self.collector.collect_activities()

                    # Reset consecutive error counter on success
                    self.consecutive_errors = 0

                    # Process activities if any
                    if activities:
                        # Reset consecutive empty results counter
                        self.consecutive_empty_results = 0

                        activity_count = len(activities)
                        self.activity_count += activity_count

                        self.logger.info(
                            f"Collected {activity_count} activities (total: {self.activity_count})",
                        )

                        # Record to database (recorder's responsibility)
                        if self.recorder:
                            recorded = self._record_activities(activities)
                            self.logger.info(
                                f"Recorded {recorded}/{activity_count} activities to hot tier",
                            )

                        # Backup to file if enabled
                        if self.backup_to_files:
                            self._write_activities_to_file(activities)
                            self.logger.debug(
                                f"Backed up {activity_count} activities to file",
                            )
                    else:
                        self.logger.info("No new activities collected")

                        # Increment consecutive empty results counter
                        self.consecutive_empty_results += 1

                        # Check if we should reset state due to persistent empty results
                        if self.auto_reset_enabled and self.consecutive_empty_results >= self.empty_results_threshold:
                            self.logger.warning(
                                f"No activities for {self.consecutive_empty_results} consecutive cycles - resetting collector state",
                            )
                            self.collector.reset_state()
                            self.consecutive_empty_results = 0
                except RecursionError:
                    # Handle recursion errors specifically with proper diagnostics
                    self.logger.warning(
                        "Maximum recursion depth exceeded in USN Journal processing",
                    )

                    # Log more details about the recursion error at debug level
                    import traceback

                    recursion_trace = traceback.format_exc()
                    self.logger.debug(f"Recursion error details: {recursion_trace}")

                    # For recursion errors, reset state more aggressively
                    if self.auto_reset_enabled:
                        self.logger.warning(
                            "Recursion error detected - resetting collector state to recover",
                        )
                        self.collector.reset_state()
                        self.consecutive_errors = 0
                        # Skip normal error handling
                        continue

                except Exception as collection_error:
                    # Log other errors normally with full details
                    self.logger.error(
                        f"Error collecting activities: {collection_error}",
                    )

                    # Include stack trace for debugging
                    if self.verbose:
                        import traceback

                        error_trace = traceback.format_exc()
                        self.logger.debug(f"Error details: {error_trace}")

                    # Increment consecutive error counter
                    self.consecutive_errors += 1

                    # Check if we should reset state due to persistent errors
                    if self.auto_reset_enabled and self.consecutive_errors >= self.error_threshold:
                        self.logger.warning(
                            f"{self.consecutive_errors} consecutive collection errors - resetting collector state",
                        )
                        self.collector.reset_state()
                        self.consecutive_errors = 0

                # Calculate next cycle timing
                cycle_duration = time.time() - cycle_start
                if cycle_duration < self.interval:
                    # Sleep for the remainder of the interval
                    sleep_time = self.interval - cycle_duration
                    self.logger.debug(f"Sleeping for {sleep_time:.2f} seconds")
                    time.sleep(sleep_time)

            except Exception as e:
                self.logger.error(f"Error in collection/recording cycle: {e!s}")
                if self.verbose:
                    self.logger.exception("Detailed error:")
                # Sleep a bit to avoid rapid error loops
                time.sleep(5)

        # Cleanup
        self.stop()

    def stop(self):
        """Stop the integrated runner and clean up resources."""
        self.logger.info("Stopping integrated NTFS activity runner...")

        # Close output file if open
        if hasattr(self, "output_file") and self.output_file:
            self.output_file.close()
            self.output_file = None
            self.logger.info("Closed output file")

        # Calculate and log stats
        end_time = datetime.now(UTC)  # Use timezone-aware datetime

        # Ensure both datetimes have timezone information
        if not hasattr(self, "start_time"):
            self.start_time = end_time - timedelta(
                seconds=1,
            )  # Fallback if start_time not set
        elif self.start_time.tzinfo is None:
            self.start_time = self.start_time.replace(tzinfo=UTC)

        duration = (end_time - self.start_time).total_seconds() / 3600  # Hours

        self.logger.info("Activity collection and recording summary:")
        self.logger.info(f"- Duration: {duration:.2f} hours")
        self.logger.info(f"- Total cycles: {self.cycle_count}")
        self.logger.info(f"- Total activities: {self.activity_count}")
        self.logger.info(
            f"- Activities per hour: {self.activity_count / max(1, duration):.2f}",
        )
        self.logger.info(
            f"- Activities per cycle: {self.activity_count / max(1, self.cycle_count):.2f}",
        )

        # Get hot tier statistics if available
        if self.recorder:
            try:
                stats = self.recorder.get_hot_tier_statistics()
                self.logger.info("Hot tier statistics:")
                if "total_count" in stats:
                    self.logger.info(f"- Total records: {stats['total_count']}")
                if "by_type" in stats:
                    self.logger.info("- Activity types:")
                    for activity_type, count in stats["by_type"].items():
                        self.logger.info(f"  - {activity_type}: {count}")
            except Exception as e:
                self.logger.error(f"Failed to retrieve hot tier statistics: {e!s}")

        self.logger.info("Integrated NTFS activity runner stopped")


def main():
    """Main entry point for the integrated runner."""
    parser = argparse.ArgumentParser(
        description="Integrated NTFS Activity Collection and Recording",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Collection parameters
    parser.add_argument(
        "--volumes",
        type=str,
        nargs="+",
        default=["C:"],
        help="Volumes to monitor for NTFS activity",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=24,
        help="Duration to run in hours (0 for unlimited)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=15,
        help="Collection interval in seconds",
    )

    # Recorder parameters
    parser.add_argument(
        "--ttl-days",
        type=int,
        default=4,
        help="Number of days to keep data in hot tier",
    )
    parser.add_argument(
        "--db-config-path",
        type=str,
        default=str(DEFAULT_DB_CONFIG_PATH),
        help="Path to the database configuration file",
    )

    # File backup parameters
    parser.add_argument(
        "--no-file-backup",
        action="store_true",
        help="Disable backup to files (database only)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/ntfs_activity",
        help="Directory for file backups (if enabled)",
    )
    parser.add_argument(
        "--max-file-size",
        type=int,
        default=100,
        help="Maximum backup file size in MB before rotation",
    )

    # General parameters
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    # Logging parameters
    parser.add_argument(
        "--log-dir",
        type=str,
        default="logs",
        help="Directory to write log files to",
    )
    parser.add_argument(
        "--machine-id",
        type=str,
        default=None,
        help="Machine UUID for log naming (overrides auto-detection)",
    )

    # Auto-reset parameters
    parser.add_argument(
        "--no-auto-reset",
        action="store_true",
        help="Disable automatic state reset on persistent errors",
    )
    parser.add_argument(
        "--error-threshold",
        type=int,
        default=3,
        help="Number of consecutive errors before automatic state reset (default: 3)",
    )
    parser.add_argument(
        "--empty-threshold",
        type=int,
        default=3,
        help="Number of consecutive empty results before automatic state reset (default: 3)",
    )

    # State file parameters
    parser.add_argument(
        "--use-state-file",
        action="store_true",
        help="Enable state file persistence (disabled by default)",
    )

    args = parser.parse_args()

    # Prepare configuration
    config = {
        "volumes": args.volumes,
        "duration": args.duration,
        "interval": args.interval,
        "ttl_days": args.ttl_days,
        "db_config_path": args.db_config_path,
        "backup_to_files": not args.no_file_backup,
        "output_dir": args.output_dir,
        "max_file_size": args.max_file_size,
        "verbose": args.verbose,
        # Log file settings
        "log_dir": args.log_dir,
        "machine_id": args.machine_id,
        "auto_reset": not args.no_auto_reset,
        "error_threshold": args.error_threshold,
        "empty_results_threshold": args.empty_threshold,
        "use_state_file": (args.use_state_file if hasattr(args, "use_state_file") else False),
    }

    # Display configuration
    print("\n============================================================")
    print("     Integrated NTFS Activity Collection and Recording")
    print("============================================================\n")
    print(f"Volumes:           {', '.join(args.volumes)}")
    print(f"Duration:          {args.duration} hours")
    print(f"Interval:          {args.interval} seconds")
    print(f"TTL:               {args.ttl_days} days")
    print(f"File Backup:       {'Disabled' if args.no_file_backup else 'Enabled'}")
    if not args.no_file_backup:
        print(f"Output Directory:  {args.output_dir}")
        print(f"Max File Size:     {args.max_file_size} MB")
    print(f"Database Config:   {args.db_config_path}")
    print(f"Verbose:           {args.verbose}")
    print(f"Auto Reset:        {'Disabled' if args.no_auto_reset else 'Enabled'}")
    if not args.no_auto_reset:
        print(f"  Error Threshold:   {args.error_threshold} consecutive errors")
        print(f"  Empty Threshold:   {args.empty_threshold} consecutive empty results")
    print(
        f"State File:        {'Enabled' if getattr(args, 'use_state_file', False) else 'Disabled'}",
    )
    print("\nPress Ctrl+C to stop at any time...")

    try:
        # Create and start the integrated runner
        runner = IntegratedNtfsActivityRunner(**config)
        runner.start()
    except Exception as e:
        print(f"Error running integrated NTFS activity runner: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
