#!/usr/bin/env python3
"""
Integrated NTFS Activity Collection and Recording Script (CLI Template Version).

This script provides an integrated approach to collecting and recording NTFS
activities while maintaining proper separation of concerns. It follows the
wrapper pattern where the recorder wraps the collector but maintains proper
separation of responsibilities:
1. The collector only collects data
2. The recorder only handles processing and storage

For long-running data collection (days or weeks), this integrated approach
is more convenient while still maintaining architectural integrity.

This implementation uses the Indaleko CLI Template framework.

Usage:
    python run_ntfs_activity_v2.py --duration 168 --volumes C: --interval 30

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

# Import the new logging setup
try:
    from utils.logging_setup import setup_logging
except ImportError:
    # Fallback if the new logging system isn't available
    def setup_logging():
        """Fallback logging setup if the new system isn't available."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler()]
        )


# Bootstrap project root so imports work properly
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).resolve().parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.append(str(current_path))

# Import CLI framework components
# Import collector and recorder classes
from activity.collectors.storage.ntfs.usn_journal_collector import (
    NtfsUsnJournalCollector,
)
from activity.recorders.storage.ntfs.tiered.hot.recorder import NtfsHotTierRecorder
from constants.values import IndalekoConstants
from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
from utils.cli.handlermixin import IndalekoHandlermixin
from utils.cli.runner import IndalekoCLIRunner


# Constants
DEFAULT_DB_PATH = Path(IndalekoConstants.default_config_dir)
DEFAULT_DB_CONFIG_PATH = DEFAULT_DB_PATH / IndalekoConstants.default_db_config_file_name


class IntegratedNtfsActivityRunner:
    """
    Integrated runner that properly wraps the collector with a recorder.

    This class maintains separation of concerns but provides a convenient
    integrated interface for continuous data collection.
    """

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        """
        Initialize the integrated runner.

        Args:
            **kwargs: Configuration options including:
                volumes: List of volumes to monitor
                interval: Collection interval in seconds
                db_config_path: Path to database configuration
                ttl_days: Number of days to keep data in hot tier
                backup_to_files: Whether to also backup data to JSONL files
                output_dir: Directory for file backups (if enabled)
                verbose: Whether to enable verbose logging
                logger: Optional logger instance to use
                use_state_file: Whether to use state file for persistence
                auto_reset: Whether to enable auto-reset on errors
                error_threshold: Number of consecutive errors before reset
                empty_results_threshold: Number of empty results before reset
        """
        # Set up logging: console + file
        self.verbose = kwargs.get("verbose", False)

        # Use existing logger if provided or create a new one with appropriate level
        self.logger = kwargs.get("logger", logging.getLogger("IntegratedNtfsActivityRunner"))
        if self.verbose:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

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
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        # Setup state file path for collector
        output_dir = Path(kwargs.get("output_dir", "data/ntfs_activity"))
        state_file_path = str(output_dir / "ntfs_state.json")

        # Initialize collector (only responsible for collecting data)
        self.logger.info(
            "Initializing NTFS USN Journal collector for volumes: %s",
            ", ".join(self.volumes),
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
        except (ValueError, ConnectionError, FileNotFoundError):
            # Handle specific expected errors
            self.logger.exception("Failed to initialize recorder")
            self.logger.warning("Will continue with file output only")
            self.recorder = None
            self.backup_to_files = True  # Force file backup if recorder fails
        except Exception:  # pylint: disable=broad-except
            # Fall back for unexpected errors
            self.logger.exception("Unexpected error initializing recorder")
            self.logger.warning("Will continue with file output only")
            self.recorder = None
            self.backup_to_files = True  # Force file backup if recorder fails

        # Set up signal handlers for graceful termination
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.logger.info("Integrated NTFS activity runner initialized")

    def _signal_handler(self, sig: int, _: Any) -> None:  # frame parameter unused
        """
        Handle termination signals gracefully.

        Args:
            sig: Signal number
            _: Current stack frame (unused)
        """
        self.logger.info("Received signal %d, shutting down...", sig)
        self.running = False

    def _get_output_filename(self) -> str:
        """Generate a unique output filename based on current timestamp."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        return str(Path(self.output_dir) / f"ntfs_activity_{timestamp}.jsonl")

    def _rotate_output_file(self) -> None:
        """Rotate the output file if it exceeds the maximum size."""
        if not self.backup_to_files:
            return

        # Close the current file if it's too large
        if self.output_file and self.current_file_size >= self.max_file_size:
            self.logger.info(
                "Rotating output file (size: %.2f MB)",
                self.current_file_size / (1024 * 1024),
            )
            self.output_file.close()
            self.output_file = None
            self.current_file_size = 0

        # Create a new file if needed
        if not self.output_file:
            filename = self._get_output_filename()
            self.logger.info("Creating new output file: %s", filename)
            # Use Path.open() as recommended by linter
            output_path = Path(filename)
            self.output_file = output_path.open("w", encoding="utf-8")
            self.current_file_size = 0

    def _write_activities_to_file(self, activities: list[dict[str, Any]]) -> None:
        """
        Write activities to backup file if enabled.

        Args:
            activities: List of activity data to write
        """
        if not self.backup_to_files or not activities:
            return

        import json

        self._rotate_output_file()

        for activity in activities:
            line = json.dumps(activity.model_dump(mode="json"))
            self.output_file.write(line + "\n")
            self.current_file_size += len(line) + 1

        self.output_file.flush()
        self.logger.debug("Wrote %d activities to backup file", len(activities))

    def _record_activities(self, activities: list[Any]) -> int:
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
        except (ValueError, ConnectionError) as err:
            # Handle expected errors using exception to capture the stack trace
            self.logger.exception("Error recording activities: %s", err)
            return 0
        except Exception:  # pylint: disable=broad-except
            # Fall back for unexpected errors
            self.logger.exception("Unexpected error recording activities")
            return 0

    def start(self) -> None:
        """Start the integrated collection and recording process."""
        self.running = True
        self.start_time = datetime.now(UTC)  # Use timezone-aware datetime

        if self.duration:
            self.end_time = self.start_time + timedelta(hours=self.duration)
            self.logger.info(
                "Starting integrated runner, will run until %s",
                self.end_time,
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
                    "Duration (%.2f hours) has expired, stopping",
                    self.duration,
                )
                self.running = False
                break

            cycle_start = time.time()
            self.cycle_count += 1

            try:
                # Collect activities (collector's responsibility)
                self.logger.info("Collecting activities (cycle %d)...", self.cycle_count)
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
                            "Collected %d activities (total: %d)",
                            activity_count,
                            self.activity_count,
                        )

                        # Record to database (recorder's responsibility)
                        if self.recorder:
                            recorded = self._record_activities(activities)
                            self.logger.info(
                                "Recorded %d/%d activities to hot tier",
                                recorded,
                                activity_count,
                            )

                        # Backup to file if enabled
                        if self.backup_to_files:
                            self._write_activities_to_file(activities)
                            self.logger.debug(
                                "Backed up %d activities to file",
                                activity_count,
                            )
                    else:
                        self.logger.info("No new activities collected")

                        # Increment consecutive empty results counter
                        self.consecutive_empty_results += 1

                        # Check if we should reset state due to persistent empty results
                        if self.auto_reset_enabled and self.consecutive_empty_results >= self.empty_results_threshold:
                            self.logger.warning(
                                "No activities for %d consecutive cycles - resetting collector state",
                                self.consecutive_empty_results,
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
                    self.logger.debug("Recursion error details: %s", recursion_trace)

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
                    # Log errors with stack trace
                    self.logger.exception(
                        "Error collecting activities: %s",
                        collection_error,
                    )

                    # Increment consecutive error counter
                    self.consecutive_errors += 1

                    # Check if we should reset state due to persistent errors
                    if self.auto_reset_enabled and self.consecutive_errors >= self.error_threshold:
                        self.logger.warning(
                            "%d consecutive collection errors - resetting collector state",
                            self.consecutive_errors,
                        )
                        self.collector.reset_state()
                        self.consecutive_errors = 0

                # Calculate next cycle timing
                cycle_duration = time.time() - cycle_start
                if cycle_duration < self.interval:
                    # Sleep for the remainder of the interval
                    sleep_time = self.interval - cycle_duration
                    self.logger.debug("Sleeping for %.2f seconds", sleep_time)
                    time.sleep(sleep_time)

            except Exception as e:
                # Use exception to capture the stack trace
                self.logger.exception("Error in collection/recording cycle: %s", e)
                # Sleep a bit to avoid rapid error loops
                time.sleep(5)

        # Cleanup
        self.stop()

    def stop(self) -> None:
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
        self.logger.info("- Duration: %.2f hours", duration)
        self.logger.info("- Total cycles: %d", self.cycle_count)
        self.logger.info("- Total activities: %d", self.activity_count)
        self.logger.info(
            "- Activities per hour: %.2f",
            self.activity_count / max(1, duration),
        )
        self.logger.info(
            "- Activities per cycle: %.2f",
            self.activity_count / max(1, self.cycle_count),
        )

        # Get hot tier statistics if available
        if self.recorder:
            try:
                stats = self.recorder.get_hot_tier_statistics()
                self.logger.info("Hot tier statistics:")
                if "total_count" in stats:
                    self.logger.info("- Total records: %d", stats["total_count"])
                if "by_type" in stats:
                    self.logger.info("- Activity types:")
                    for activity_type, count in stats["by_type"].items():
                        self.logger.info("  - %s: %d", activity_type, count)
            except Exception as err:
                self.logger.exception("Failed to retrieve hot tier statistics: %s", err)

        self.logger.info("Integrated NTFS activity runner stopped")


class NtfsActivityHandlerMixin(IndalekoHandlermixin):
    """Handler mixin for the NTFS Activity Runner CLI."""

    @staticmethod
    def get_platform_name() -> str:
        """Get the platform name."""
        import platform

        return platform.system()

    @staticmethod
    def get_pre_parser() -> argparse.ArgumentParser | None:
        """Define initial arguments."""
        parser = argparse.ArgumentParser(add_help=False)

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
            help="Number of consecutive errors before automatic state reset",
        )
        parser.add_argument(
            "--empty-threshold",
            type=int,
            default=3,
            help="Number of consecutive empty results before automatic state reset",
        )

        # State file parameters
        parser.add_argument(
            "--use-state-file",
            action="store_true",
            help="Enable state file persistence (disabled by default)",
        )

        return parser

    @staticmethod
    def get_additional_parameters(pre_parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        """Add additional parameters to the parser."""
        return pre_parser

    @staticmethod
    def setup_logging(args: argparse.Namespace, **_: dict[str, Any]) -> None:  # kwargs unused
        """Configure logging based on parsed args."""
        # Logging is now handled by the central setup_logging function
        # We only need to customize the log level based on debug flag
        if args.debug:
            # Set the root logger to DEBUG level if --debug is specified
            logging.getLogger().setLevel(logging.DEBUG)
            
        # Create a logger for this module
        logger = logging.getLogger(__name__)
        logger.info("NTFS Activity Collector V2 logging initialized")

    @staticmethod
    def load_configuration(kwargs: dict[str, Any]) -> None:
        """Load tool-specific configuration."""

    @staticmethod
    def get_default_file(data_directory: str | Path, candidates: list[str | Path]) -> str | None:
        """Pick the preferred file from a list of candidates."""
        if isinstance(data_directory, str):
            data_directory = Path(data_directory)
        if not data_directory.exists():
            return None
        if not candidates:
            return None
        # Find valid files from candidates
        valid_files = []
        for fname in candidates:
            file_path = data_directory / fname
            if file_path.is_file():
                valid_files.append(file_path)
        if not valid_files:
            return None
        return str(max(valid_files, key=lambda f: f.stat().st_mtime).name)

    @staticmethod
    def find_db_config_files(config_dir: str | Path) -> list[str] | None:
        """Find database configuration files."""
        from constants.values import IndalekoConstants
        from utils.misc.file_name_management import find_candidate_files

        if not Path(config_dir).exists():
            return None
        return [
            fname
            for fname, _ in find_candidate_files(["db"], str(config_dir))
            if fname.startswith(IndalekoConstants.default_prefix) and fname.endswith(".ini")
        ]

    @staticmethod
    def find_machine_config_files(
        config_dir: str | Path,
        platform: str | None = None,
        machine_id: str | None = None,
    ) -> list[str] | None:
        """Find machine configuration files."""
        from utils.misc.file_name_management import find_candidate_files

        if not Path(config_dir).exists():
            return None
        if platform is None:
            return []
        filters = ["_machine_config"]
        if machine_id:
            filters.append(machine_id)
        if platform:
            filters.append(platform)
        # Filter for JSON files
        candidates = find_candidate_files(filters, str(config_dir))
        return [fname for fname, _ in candidates if fname.endswith(".json")]

    @staticmethod
    def find_data_files(
        data_dir: str | Path,
        keys: dict[str, str],
        prefix: str,
        suffix: str,
    ) -> list[str] | None:
        """Find data files."""
        from utils.misc.file_name_management import find_candidate_files

        if not Path(data_dir).exists():
            return None
        # the hyphen at the end ensures we don't pick up partial matches
        selection_keys = [f"{key}={value}-" for key, value in keys.items()]
        # Get candidates from selection keys
        candidates = find_candidate_files(selection_keys, str(data_dir))
        result = []
        # Filter candidates that match all criteria
        for fname, _ in candidates:
            if fname.startswith(prefix) and fname.endswith(suffix) and all(key in fname for key in selection_keys):
                result.append(fname)
        return result

    @staticmethod
    def generate_output_file_name(keys: dict[str, str]) -> str:
        """Generate an output file name."""
        from utils.misc.file_name_management import generate_file_name

        kwargs = {
            "platform": keys.get("Platform", "unknown"),
            "service": keys.get("FileServiceName", "ntfs_activity"),
            "timestamp": keys.get("Timestamp", datetime.now(UTC).isoformat()),
        }
        if (
            "MachineConfigFileKeys" in keys
            and keys["MachineConfigFileKeys"]
            and "machine" in keys["MachineConfigFileKeys"]
        ):
            kwargs["machine"] = keys["MachineConfigFileKeys"]["machine"]
        if keys.get("StorageId"):
            kwargs["storage"] = keys["StorageId"]
        if keys.get("UserId"):
            kwargs["userid"] = keys["UserId"]
        if "suffix" not in keys:
            kwargs["suffix"] = "jsonl"
        return generate_file_name(**kwargs)

    @staticmethod
    def generate_log_file_name(keys: dict[str, str]) -> str:
        """Generate a log file name."""
        from utils.misc.file_name_management import generate_file_name

        kwargs = {
            "service": keys.get("FileServiceName", "ntfs_activity"),
            "timestamp": keys.get("Timestamp", datetime.now(UTC).isoformat()),
        }
        if "Platform" in keys:
            kwargs["platform"] = keys["Platform"]
        if (
            "MachineConfigFileKeys" in keys
            and keys["MachineConfigFileKeys"]
            and "machine" in keys["MachineConfigFileKeys"]
        ):
            kwargs["machine"] = keys["MachineConfigFileKeys"]["machine"]
        if "suffix" not in keys:
            kwargs["suffix"] = "log"
        return generate_file_name(**kwargs)

    @staticmethod
    def generate_perf_file_name(keys: dict[str, str]) -> str:
        """Generate a performance file name."""
        from utils.misc.file_name_management import generate_file_name

        kwargs = {
            "service": keys.get("FileServiceName", "ntfs_activity") + "_perf",
            "timestamp": keys.get("Timestamp", datetime.now(UTC).isoformat()),
        }
        if "Platform" in keys:
            kwargs["platform"] = keys["Platform"]
        if (
            "MachineConfigFileKeys" in keys
            and keys["MachineConfigFileKeys"]
            and "machine" in keys["MachineConfigFileKeys"]
        ):
            kwargs["machine"] = keys["MachineConfigFileKeys"]["machine"]
        return generate_file_name(**kwargs)

    @staticmethod
    def load_machine_config(_: dict[str, str]) -> None:
        """Load a machine configuration."""
        # This is a stub - not needed for this specific implementation
        return

    @staticmethod
    def extract_filename_metadata(file_name: str) -> dict:
        """Parse the file name."""
        from utils.misc.file_name_management import extract_keys_from_file_name

        return extract_keys_from_file_name(file_name=file_name)

    @staticmethod
    def get_storage_identifier(pre_args: dict[str, Any]) -> str | None:
        """Get the storage identifier."""
        return pre_args.get("storage_id") if hasattr(pre_args, "storage_id") else None

    @staticmethod
    def get_user_identifier(pre_args: dict[str, Any]) -> str | None:
        """Get the user identifier."""
        return pre_args.get("user_id") if hasattr(pre_args, "user_id") else None

    @staticmethod
    def performance_configuration(_kwargs: dict[str, Any]) -> bool:
        """Configure performance recording."""
        return False  # Disable performance recording for now

    @staticmethod
    def run(kwargs: dict[str, Any]) -> None:
        """Main entry point for CLI execution."""
        args = kwargs.get("args")

        # Platform check at the very beginning
        import platform

        # Create a dedicated logger for this method
        logger = logging.getLogger(__name__)

        if platform.system() != "Windows" and not args.debug:
            logger.error("ERROR: This tool requires Windows to run.")
            logger.error("You can use --debug to run in test mode on non-Windows platforms.")
            sys.exit(1)

        # Configure logging for better display in CLI
        config_logger = logging.getLogger("config")

        # Display configuration banner
        config_logger.info("\n============================================================")
        config_logger.info("     Integrated NTFS Activity Collection and Recording (v2)")
        config_logger.info("============================================================\n")
        config_logger.info("Volumes:           %s", ", ".join(args.volumes))
        config_logger.info("Duration:          %s hours", args.duration)
        config_logger.info("Interval:          %s seconds", args.interval)
        config_logger.info("TTL:               %s days", args.ttl_days)
        backup_status = "Disabled" if args.no_file_backup else "Enabled"
        config_logger.info("File Backup:       %s", backup_status)

        if not args.no_file_backup:
            config_logger.info("Output Directory:  %s", args.output_dir)
            config_logger.info("Max File Size:     %s MB", args.max_file_size)

        config_logger.info("Database Config:   %s", args.db_config_path)
        config_logger.info("Verbose:           %s", args.debug)
        config_logger.info("Auto Reset:        %s", "Disabled" if args.no_auto_reset else "Enabled")

        if not args.no_auto_reset:
            config_logger.info("  Error Threshold:   %s consecutive errors", args.error_threshold)
            config_logger.info(
                "  Empty Threshold:   %s consecutive empty results",
                args.empty_threshold,
            )

        state_file_status = "Enabled" if getattr(args, "use_state_file", False) else "Disabled"
        config_logger.info("State File:        %s", state_file_status)
        config_logger.info("\nPress Ctrl+C to stop at any time...")

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
            "verbose": args.debug,
            # Log file settings
            "log_dir": args.logdir,
            "machine_id": getattr(args, "machine_id", None),
            "auto_reset": not args.no_auto_reset,
            "error_threshold": args.error_threshold,
            "empty_results_threshold": args.empty_threshold,
            "use_state_file": (args.use_state_file if hasattr(args, "use_state_file") else False),
        }

        try:
            # Create and start the integrated runner
            runner = IntegratedNtfsActivityRunner(**config)
            runner.start()
        except Exception:  # pylint: disable=broad-except
            # Use logger.exception which automatically includes traceback
            logger.exception("Error running integrated NTFS activity runner")
            sys.exit(1)

    @staticmethod
    def performance_recording(_kwargs: dict[str, Any]) -> None:
        """Hook for recording performance after run()."""

    @staticmethod
    def cleanup(_kwargs: dict[str, Any]) -> None:
        """Cleanup hook."""


def run_ntfs_activity(kwargs: dict) -> None:
    """Wrapper to invoke the handler mixin's run method."""
    NtfsActivityHandlerMixin.run(kwargs)


def main() -> None:
    """Main entrypoint for the NTFS activity collector v2."""
    # Configure logging (console + file with rotation) before running
    setup_logging()
    
    cli_data = IndalekoBaseCliDataModel(
        RegistrationServiceName="NtfsActivityCollector",
        FileServiceName="ntfs_activity_v2",
        InputFileKeys={"svc": "ntfs_activity", "plt": "Windows"},
    )
    runner = IndalekoCLIRunner(
        cli_data=cli_data,
        handler_mixin=NtfsActivityHandlerMixin(),
        features=IndalekoBaseCLI.cli_features(input=False),  # Disable input file handling
        Run=run_ntfs_activity,
        RunParameters={},
    )
    runner.run()


if __name__ == "__main__":
    main()
