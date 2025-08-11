#!/usr/bin/env python3
"""
Unified background processor for semantic metadata extraction.

This module provides a centralized way to run multiple semantic extractors
in the background at low priority. It uses the enhanced IndalekoFilePicker
to find files in the database that are locally accessible and need processing.

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
import json
import logging
import os
import signal
import sys
import threading
import time

from datetime import UTC, datetime
from typing import Any


# Ensure INDALEKO_ROOT is set
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from semantic.collectors.checksum.background_processor import (
    schedule_checksum_processing,
)
from semantic.collectors.exif.background_processor import schedule_exif_processing

# Import specialized processors
from semantic.collectors.mime.background_processor import schedule_mime_processing
from utils.db.db_file_picker import IndalekoFilePicker


# Try to import unstructured processor if available
try:
    from semantic.collectors.unstructured.IndalekoUnstructured_Main import (
        process_file as process_unstructured,
    )

    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False
# pylint: enable=wrong-import-position

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(os.path.dirname(__file__), "semantic_processor.log"),
        ),
    ],
)
logger = logging.getLogger("IndalekoBgProcessor")


# Available processor types
class ProcessorType:
    """Enumeration of available semantic processor types."""

    MIME = "mime"
    CHECKSUM = "checksum"
    EXIF = "exif"
    UNSTRUCTURED = "unstructured"

    @staticmethod
    def get_all() -> list[str]:
        """Get all available processor types."""
        return [
            ProcessorType.MIME,
            ProcessorType.CHECKSUM,
            ProcessorType.EXIF,
            ProcessorType.UNSTRUCTURED,
        ]

    @staticmethod
    def get_enabled() -> list[str]:
        """Get all enabled processor types."""
        enabled = [ProcessorType.MIME, ProcessorType.CHECKSUM, ProcessorType.EXIF]
        if UNSTRUCTURED_AVAILABLE:
            enabled.append(ProcessorType.UNSTRUCTURED)
        return enabled


class BackgroundProcessorManager:
    """
    Manages multiple background semantic processors running concurrently.
    Coordinates resources and ensures fair allocation across different
    semantic extraction tasks.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize the background processor manager.

        Args:
            config: Configuration dictionary with processor settings
        """
        self.config = config
        self.file_picker = IndalekoFilePicker()
        self.should_stop = threading.Event()
        self.processors: dict[str, threading.Thread] = {}
        self.stats: dict[str, dict[str, int]] = {}

        # Configure each processor type
        for processor_type in ProcessorType.get_enabled():
            self.stats[processor_type] = {
                "scheduled": 0,
                "processed": 0,
                "errors": 0,
                "last_run": 0,
            }

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, sig, frame) -> None:
        """Handle termination signals."""
        logger.info(f"Received signal {sig}, shutting down...")
        self.stop()

    def start(self) -> None:
        """Start all enabled background processors."""
        logger.info("Starting background processor manager")

        # Start processor threads
        for processor_type in self.config.get(
            "processors",
            ProcessorType.get_enabled(),
        ):
            if processor_type not in ProcessorType.get_enabled():
                logger.warning(
                    f"Processor type {processor_type} is not enabled or available",
                )
                continue

            # Create and start the processor thread
            thread = threading.Thread(
                target=self._run_processor,
                args=(processor_type,),
                daemon=True,
                name=f"Indaleko-{processor_type.capitalize()}Processor",
            )
            self.processors[processor_type] = thread
            thread.start()
            logger.info(f"Started {processor_type} processor thread")

    def stop(self) -> None:
        """Stop all background processors."""
        logger.info("Stopping background processors...")
        self.should_stop.set()

        # Wait for all processor threads to terminate
        for processor_type, thread in self.processors.items():
            if thread.is_alive():
                logger.info(f"Waiting for {processor_type} processor to terminate...")
                thread.join(timeout=10.0)
                if thread.is_alive():
                    logger.warning(
                        f"{processor_type} processor did not terminate gracefully",
                    )

        # Stop the file picker's background processing
        self.file_picker.stop_background_processing(wait=True)

        # Log final statistics
        self._log_statistics()

    def _run_processor(self, processor_type: str) -> None:
        """
        Run a specific type of processor in a loop.

        Args:
            processor_type: The type of processor to run
        """
        logger.info(f"Starting {processor_type} processor loop")

        # Get processor-specific config
        processor_config = self.config.get(processor_type, {})

        # Main processing loop
        while not self.should_stop.is_set():
            try:
                # Check if it's time to run this processor
                current_time = time.time()
                min_interval = processor_config.get(
                    "interval",
                    300,
                )  # Default: 5 minutes

                if current_time - self.stats[processor_type]["last_run"] < min_interval:
                    # Not time yet, sleep and continue
                    time.sleep(1)
                    continue

                # Execute the appropriate processor
                scheduled, processed = self._execute_processor(processor_type)

                # Update statistics
                self.stats[processor_type]["scheduled"] += scheduled
                self.stats[processor_type]["processed"] += processed
                self.stats[processor_type]["last_run"] = current_time

                # Log progress
                logger.info(
                    f"{processor_type} processor: scheduled={scheduled}, total_scheduled={self.stats[processor_type]['scheduled']}",
                )

                # Sleep before next execution
                if scheduled == 0:
                    # If nothing to process, wait longer
                    sleep_time = min(3600, min_interval * 2)  # Max: 1 hour
                else:
                    sleep_time = min_interval

                # Sleep with periodic checks for stop signal
                for _ in range(0, sleep_time, 5):
                    if self.should_stop.is_set():
                        break
                    time.sleep(min(5, sleep_time))

            except Exception as e:
                logger.error(f"Error in {processor_type} processor: {e}", exc_info=True)
                self.stats[processor_type]["errors"] += 1
                time.sleep(60)  # Wait before retry after error

    def _execute_processor(self, processor_type: str) -> tuple[int, int]:
        """
        Execute a specific processor type.

        Args:
            processor_type: The type of processor to execute

        Returns:
            Tuple[int, int]: Number of files scheduled and processed
        """
        # Get processor-specific config
        processor_config = self.config.get(processor_type, {})

        # Common parameters
        count = processor_config.get("batch_size", 10)
        max_age_days = processor_config.get("max_age_days", None)
        min_last_processed_days = processor_config.get("min_last_processed_days", 30)

        # Execute the appropriate processor
        if processor_type == ProcessorType.MIME:
            return schedule_mime_processing(
                count=count,
                background=True,
                max_age_days=max_age_days,
                min_last_processed_days=min_last_processed_days,
                run_duration=None,
            )
        if processor_type == ProcessorType.CHECKSUM:
            file_extensions = processor_config.get("file_extensions", None)
            return schedule_checksum_processing(
                count=count,
                background=True,
                max_age_days=max_age_days,
                min_last_processed_days=min_last_processed_days,
                run_duration=None,
                file_extensions=file_extensions,
            )
        if processor_type == ProcessorType.EXIF:
            return schedule_exif_processing(
                count=count,
                background=True,
                max_age_days=max_age_days,
                min_last_processed_days=min_last_processed_days,
                run_duration=None,
            )
        if processor_type == ProcessorType.UNSTRUCTURED and UNSTRUCTURED_AVAILABLE:
            # Unstructured processing is not yet implemented as a background processor
            # This is a placeholder for future implementation
            logger.warning("Unstructured background processing not yet implemented")
            return 0, 0
        logger.warning(f"Unknown processor type: {processor_type}")
        return 0, 0

    def _log_statistics(self) -> None:
        """Log processor statistics."""
        logger.info("Background processor statistics:")
        for processor_type, stats in self.stats.items():
            logger.info(
                f"  {processor_type}: scheduled={stats['scheduled']}, processed={stats['processed']}, errors={stats['errors']}",
            )

    def save_statistics(self, file_path: str) -> None:
        """
        Save processor statistics to a JSON file.

        Args:
            file_path: Path to the output file
        """
        try:
            # Prepare stats with timestamp
            output_stats = {
                "timestamp": datetime.now(UTC).isoformat(),
                "processors": self.stats,
            }

            # Write to file
            with open(file_path, "w") as f:
                json.dump(output_stats, f, indent=2)

            logger.info(f"Statistics saved to {file_path}")

        except Exception as e:
            logger.exception(f"Error saving statistics: {e}")


def load_config(config_file: str | None = None) -> dict[str, Any]:
    """
    Load configuration from a JSON file or use defaults.

    Args:
        config_file: Path to the configuration file

    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    # Default configuration
    default_config = {
        "processors": ProcessorType.get_enabled(),
        "mime": {
            "batch_size": 20,
            "interval": 300,  # 5 minutes
            "min_last_processed_days": 30,
        },
        "checksum": {
            "batch_size": 10,
            "interval": 600,  # 10 minutes
            "min_last_processed_days": 60,
            "file_extensions": [".pdf", ".docx", ".xlsx", ".pptx", ".zip", ".exe"],
        },
        "unstructured": {
            "batch_size": 5,
            "interval": 1800,  # 30 minutes
            "min_last_processed_days": 90,
            "file_extensions": [".pdf", ".docx", ".txt", ".md", ".html"],
        },
        "exif": {
            "batch_size": 15,
            "interval": 900,  # 15 minutes
            "min_last_processed_days": 45,
            "file_extensions": [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".heic"],
        },
    }

    # If no config file specified, use defaults
    if not config_file:
        return default_config

    try:
        # Load configuration from file
        with open(config_file) as f:
            user_config = json.load(f)

        # Merge with defaults
        for key, value in user_config.items():
            if key in default_config and isinstance(default_config[key], dict) and isinstance(value, dict):
                # Merge dictionaries
                default_config[key].update(value)
            else:
                # Replace value
                default_config[key] = value

        return default_config

    except Exception as e:
        logger.exception(f"Error loading configuration: {e}, using defaults")
        return default_config


def main() -> None:
    """Main function for the unified background processor."""
    parser = argparse.ArgumentParser(
        description="Indaleko Semantic Background Processor",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to configuration file",
    )
    parser.add_argument(
        "--processors",
        type=str,
        nargs="+",
        choices=ProcessorType.get_all(),
        help="Processor types to enable",
    )
    parser.add_argument(
        "--run-time",
        type=int,
        default=0,
        help="Run for this many seconds, or indefinitely if 0",
    )
    parser.add_argument(
        "--stats-file",
        type=str,
        default="semantic_processor_stats.json",
        help="Path to statistics output file",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug output")

    args = parser.parse_args()

    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load configuration
    config = load_config(args.config)

    # Override processors if specified
    if args.processors:
        config["processors"] = args.processors

    # Create and start the processor manager
    manager = BackgroundProcessorManager(config)
    manager.start()

    try:
        # Run for specified time or indefinitely
        if args.run_time > 0:
            logger.info(f"Running for {args.run_time} seconds")
            time.sleep(args.run_time)
            manager.stop()
        else:
            # Run indefinitely until interrupt
            logger.info("Running indefinitely until interrupted")
            while True:
                time.sleep(60)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        # Ensure manager is stopped
        manager.stop()

        # Save statistics
        if args.stats_file:
            manager.save_statistics(args.stats_file)

    logger.info("Background processor completed")


if __name__ == "__main__":
    main()
