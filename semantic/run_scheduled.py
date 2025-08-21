#!/usr/bin/env python3
"""
Scheduled semantic metadata extraction for Indaleko.

This module provides a framework for running semantic extractors on a schedule
with resource control, state persistence, and incremental processing.

Usage:
    python -m semantic.run_scheduled --all
    python -m semantic.run_scheduled --extractors mime,checksum
    python -m semantic.run_scheduled --all --max-cpu 30 --max-memory 1024

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
import gc
import json
import logging
import os
import platform
import time
import traceback

from typing import Any

import psutil

# Import Indaleko database connection
from semantic.collectors.checksum.checksum import IndalekoSemanticChecksums

# Import our extractors
from semantic.collectors.mime.mime_collector import IndalekoSemanticMimeType
from semantic.recorders.checksum.recorder import ChecksumRecorder
from semantic.recorders.mime.recorder import MimeTypeRecorder


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("semantic.scheduler")

# Define default configuration
DEFAULT_CONFIG = {
    "resources": {"max_cpu_percent": 30, "max_memory_mb": 1024, "nice_level": 19},
    "extractors": {
        "mime": {
            "enabled": True,
            "batch_size": 500,
            "interval_seconds": 10,
            "file_extensions": ["*"],
        },
        "checksum": {
            "enabled": True,
            "batch_size": 200,
            "interval_seconds": 30,
            "file_extensions": [".pdf", ".docx", ".xlsx", ".jpg", ".png"],
        },
    },
    "processing": {
        "max_run_time_seconds": 14400,  # 4 hours
        "log_level": "INFO",
        "state_file": "data/semantic/processing_state.json",
    },
    "database": {"connection_retries": 3, "batch_commit_size": 50},
}


def ensure_directory_exists(file_path: str) -> None:
    """Ensure the directory for the given file path exists."""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """Load configuration from file or use defaults."""
    if not config_path:
        config_path = os.path.join("semantic", "config", "linux_scheduler.json")

    config = DEFAULT_CONFIG.copy()

    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                file_config = json.load(f)

            # Deep merge the configs
            for key, value in file_config.items():
                if isinstance(value, dict) and key in config and isinstance(config[key], dict):
                    config[key].update(value)
                else:
                    config[key] = value

            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.exception(f"Error loading configuration from {config_path}: {e}")
            logger.info("Using default configuration")
    else:
        logger.info(
            f"Configuration file {config_path} not found, using default configuration",
        )

        # Create default config file for future use
        try:
            ensure_directory_exists(config_path)
            with open(config_path, "w") as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
            logger.info(f"Created default configuration file at {config_path}")
        except Exception as e:
            logger.exception(f"Could not create default configuration file: {e}")

    return config


def load_state(state_file: str) -> dict[str, Any]:
    """Load processing state from file."""
    if os.path.exists(state_file):
        try:
            with open(state_file) as f:
                return json.load(f)
        except Exception as e:
            logger.exception(f"Error loading state file {state_file}: {e}")

    # Return default state if file doesn't exist or error occurred
    return {
        "last_run": datetime.datetime.now(datetime.UTC).isoformat(),
        "extractors": {
            "mime": {
                "last_run": datetime.datetime.now(datetime.UTC).isoformat(),
                "processed_files": 0,
                "skipped_files": 0,
                "error_files": 0,
                "last_file_id": None,
            },
            "checksum": {
                "last_run": datetime.datetime.now(datetime.UTC).isoformat(),
                "processed_files": 0,
                "skipped_files": 0,
                "error_files": 0,
                "last_file_id": None,
            },
        },
        "database": {
            "last_connection": datetime.datetime.now(datetime.UTC).isoformat(),
            "total_records": 0,
        },
    }


def save_state(state: dict[str, Any], state_file: str) -> None:
    """Save processing state to file."""
    try:
        ensure_directory_exists(state_file)
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
        logger.debug(f"Saved state to {state_file}")
    except Exception as e:
        logger.exception(f"Error saving state to {state_file}: {e}")


def set_process_priority() -> None:
    """Set process to lowest priority to minimize system impact."""
    try:
        if platform.system() == "Linux":
            os.nice(19)  # Lowest priority on Linux
            logger.debug("Set process nice level to 19")
        elif platform.system() == "Windows":
            import win32con
            import win32process

            handle = win32process.GetCurrentProcess()
            win32process.SetPriorityClass(handle, win32con.IDLE_PRIORITY_CLASS)
            logger.debug("Set process priority to IDLE_PRIORITY_CLASS")
    except Exception as e:
        logger.warning(f"Could not set process priority: {e}")


def check_resource_usage(max_cpu: int, max_memory: int) -> bool:
    """
    Check if resource usage is within limits.
    Returns True if processing can continue, False if it should pause.
    """
    process = psutil.Process(os.getpid())

    # Check CPU usage
    cpu_percent = process.cpu_percent(interval=0.5)
    if cpu_percent > max_cpu:
        logger.debug(f"CPU usage {cpu_percent:.1f}% exceeds limit {max_cpu}%, pausing")
        return False

    # Check memory usage
    memory_info = process.memory_info()
    memory_mb = memory_info.rss / (1024 * 1024)
    if memory_mb > max_memory:
        logger.debug(
            f"Memory usage {memory_mb:.1f}MB exceeds limit {max_memory}MB, forcing garbage collection",
        )
        gc.collect()
        # Recheck after garbage collection
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)
        if memory_mb > max_memory:
            logger.debug(
                f"Memory usage {memory_mb:.1f}MB still exceeds limit after GC, pausing",
            )
            return False

    return True


def get_file_batch_from_database(
    extractor_type: str,
    batch_size: int,
    config: dict[str, Any],
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Get a batch of files from the database that need semantic processing.
    Returns a list of files with their paths and object IDs.
    """
    # TODO: Implement actual database query
    # This is a placeholder implementation

    # For now, return an empty list - we'll implement the actual query later
    # when we have direct database access
    logger.info(
        f"Would query database for {batch_size} files for {extractor_type} processing",
    )
    return []


def process_mime_batch(
    files: list[dict[str, Any]],
    config: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, int]:
    """Process a batch of files with the MIME type extractor."""
    IndalekoSemanticMimeType()
    recorder = MimeTypeRecorder()

    results = {"processed": 0, "skipped": 0, "errors": 0}

    for file_info in files:
        file_path = file_info.get("path")
        object_id = file_info.get("object_id")

        if not file_path or not object_id or not os.path.exists(file_path):
            results["skipped"] += 1
            continue

        try:
            # Check resource usage before processing
            if not check_resource_usage(
                config["resources"]["max_cpu_percent"],
                config["resources"]["max_memory_mb"],
            ):
                time.sleep(1)  # Pause briefly if resources are constrained

            # Process the file
            result = recorder.process_file(file_path, object_id=object_id)

            if result:
                results["processed"] += 1
                state["extractors"]["mime"]["last_file_id"] = object_id
            else:
                results["skipped"] += 1

        except Exception as e:
            logger.exception(f"Error processing MIME type for {file_path}: {e}")
            results["errors"] += 1

    # Update state
    state["extractors"]["mime"]["processed_files"] += results["processed"]
    state["extractors"]["mime"]["skipped_files"] += results["skipped"]
    state["extractors"]["mime"]["error_files"] += results["errors"]
    state["extractors"]["mime"]["last_run"] = datetime.datetime.now(
        datetime.UTC,
    ).isoformat()

    return results


def process_checksum_batch(
    files: list[dict[str, Any]],
    config: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, int]:
    """Process a batch of files with the Checksum extractor."""
    IndalekoSemanticChecksums()
    recorder = ChecksumRecorder()

    results = {"processed": 0, "skipped": 0, "errors": 0}

    for file_info in files:
        file_path = file_info.get("path")
        object_id = file_info.get("object_id")

        if not file_path or not object_id or not os.path.exists(file_path):
            results["skipped"] += 1
            continue

        try:
            # Check resource usage before processing
            if not check_resource_usage(
                config["resources"]["max_cpu_percent"],
                config["resources"]["max_memory_mb"],
            ):
                time.sleep(1)  # Pause briefly if resources are constrained

            # Process the file
            result = recorder.process_file(file_path, object_id=object_id)

            if result:
                results["processed"] += 1
                state["extractors"]["checksum"]["last_file_id"] = object_id
            else:
                results["skipped"] += 1

        except Exception as e:
            logger.exception(f"Error processing checksums for {file_path}: {e}")
            results["errors"] += 1

    # Update state
    state["extractors"]["checksum"]["processed_files"] += results["processed"]
    state["extractors"]["checksum"]["skipped_files"] += results["skipped"]
    state["extractors"]["checksum"]["error_files"] += results["errors"]
    state["extractors"]["checksum"]["last_run"] = datetime.datetime.now(
        datetime.UTC,
    ).isoformat()

    return results


def run_scheduled_extraction(args: argparse.Namespace) -> None:
    """Run scheduled semantic extraction based on configuration and arguments."""
    # Load configuration
    config = load_config(args.config)

    # Update config with command-line arguments
    if args.max_cpu:
        config["resources"]["max_cpu_percent"] = args.max_cpu
    if args.max_memory:
        config["resources"]["max_memory_mb"] = args.max_memory
    if args.batch_size:
        for extractor in config["extractors"]:
            config["extractors"][extractor]["batch_size"] = args.batch_size
    if args.run_time:
        config["processing"]["max_run_time_seconds"] = args.run_time

    # Set log level
    if args.debug:
        logger.setLevel(logging.DEBUG)
        config["processing"]["log_level"] = "DEBUG"
    else:
        log_level = getattr(logging, config["processing"]["log_level"])
        logger.setLevel(log_level)

    # Set process priority
    set_process_priority()

    # Load state
    state_file = config["processing"]["state_file"]
    state = load_state(state_file)

    if args.reset_state:
        # Reset state if requested
        state = {
            "last_run": datetime.datetime.now(datetime.UTC).isoformat(),
            "extractors": {
                "mime": {
                    "last_run": datetime.datetime.now(
                        datetime.UTC,
                    ).isoformat(),
                    "processed_files": 0,
                    "skipped_files": 0,
                    "error_files": 0,
                    "last_file_id": None,
                },
                "checksum": {
                    "last_run": datetime.datetime.now(
                        datetime.UTC,
                    ).isoformat(),
                    "processed_files": 0,
                    "skipped_files": 0,
                    "error_files": 0,
                    "last_file_id": None,
                },
            },
            "database": {
                "last_connection": datetime.datetime.now(
                    datetime.UTC,
                ).isoformat(),
                "total_records": 0,
            },
        }
        logger.info("Reset processing state")

    # Determine which extractors to run
    extractors_to_run = []
    if args.all:
        # Run all enabled extractors
        for extractor, settings in config["extractors"].items():
            if settings.get("enabled", False):
                extractors_to_run.append(extractor)
    elif args.extractors:
        # Run specific extractors
        requested = args.extractors.split(",")
        for extractor in requested:
            if extractor in config["extractors"] and config["extractors"][extractor].get("enabled", False):
                extractors_to_run.append(extractor)
            else:
                logger.warning(
                    f"Extractor '{extractor}' is not enabled or doesn't exist",
                )

    if not extractors_to_run:
        logger.error("No extractors selected to run")
        return

    logger.info(
        f"Starting scheduled semantic extraction with extractors: {', '.join(extractors_to_run)}",
    )
    logger.info(
        f"CPU limit: {config['resources']['max_cpu_percent']}%, Memory limit: {config['resources']['max_memory_mb']}MB",
    )

    # Set up processing timeout
    start_time = time.time()
    max_run_time = config["processing"]["max_run_time_seconds"]

    try:
        # Main processing loop
        while time.time() - start_time < max_run_time:
            for extractor in extractors_to_run:
                if time.time() - start_time >= max_run_time:
                    logger.info(f"Reached maximum run time of {max_run_time} seconds")
                    break

                logger.info(f"Processing batch for {extractor}")

                # Get batch size from config
                batch_size = config["extractors"][extractor]["batch_size"]

                # Get batch of files to process
                files = get_file_batch_from_database(
                    extractor,
                    batch_size,
                    config,
                    state,
                )

                if not files:
                    logger.info(f"No files to process for {extractor}")
                    continue

                # Process batch based on extractor type
                if extractor == "mime":
                    results = process_mime_batch(files, config, state)
                elif extractor == "checksum":
                    results = process_checksum_batch(files, config, state)
                else:
                    logger.warning(f"Unknown extractor: {extractor}")
                    continue

                # Log results
                logger.info(
                    f"{extractor} batch processed: {results['processed']} processed, {results['skipped']} skipped, {results['errors']} errors",
                )

                # Save state after each batch
                save_state(state, state_file)

                # Wait for interval between batches
                interval = config["extractors"][extractor]["interval_seconds"]
                time.sleep(interval)

            # Add a short sleep to prevent tight loop if no files are found
            if not any(
                files for files in [get_file_batch_from_database(e, 1, config, state) for e in extractors_to_run]
            ):
                logger.info("No more files to process, waiting 60 seconds")
                time.sleep(60)

                # If we've gone through all extractors and found no files, we can exit
                if all(not get_file_batch_from_database(e, 1, config, state) for e in extractors_to_run):
                    logger.info("No more files to process for any extractor, finishing")
                    break
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
    except Exception as e:
        logger.exception(f"Error during processing: {e}")
        logger.debug(traceback.format_exc())
    finally:
        # Update last run time
        state["last_run"] = datetime.datetime.now(datetime.UTC).isoformat()

        # Save final state
        save_state(state, state_file)

        # Log summary
        duration = time.time() - start_time
        logger.info(f"Processing completed in {duration:.1f} seconds")
        for extractor in extractors_to_run:
            stats = state["extractors"].get(extractor, {})
            logger.info(
                f"{extractor} total: {stats.get('processed_files', 0)} processed, {stats.get('skipped_files', 0)} skipped, {stats.get('error_files', 0)} errors",
            )


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Scheduled semantic metadata extraction for Indaleko",
    )

    # Extractor selection
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Run all enabled extractors")
    group.add_argument(
        "--extractors",
        type=str,
        help="Comma-separated list of extractors to run (mime,checksum)",
    )

    # Configuration options
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument(
        "--max-cpu",
        type=int,
        help="Maximum CPU usage percentage (0-100)",
    )
    parser.add_argument("--max-memory", type=int, help="Maximum memory usage in MB")
    parser.add_argument("--batch-size", type=int, help="Batch size for processing")
    parser.add_argument("--run-time", type=int, help="Maximum run time in seconds")

    # State management
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Reset processing state",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current processing status and exit",
    )

    # Logging
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    # Testing
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode with sample files",
    )
    parser.add_argument(
        "--directory",
        type=str,
        help="Process files in this directory (with --test)",
    )

    args = parser.parse_args()

    if args.status:
        # Just show status and exit
        config = load_config(args.config)
        load_state(config["processing"]["state_file"])
        return

    if args.test:
        # Run in test mode with sample files or specified directory
        logger.info("Running in test mode")
        # TODO: Implement test mode
        return

    # Run normal processing
    run_scheduled_extraction(args)


if __name__ == "__main__":
    main()
