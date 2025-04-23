#!/usr/bin/env python3
"""
Background processor for file checksum generation.

This module demonstrates using the enhanced IndalekoFilePicker to perform
background checksum calculation on files in the database.

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
import sys
import time

# Ensure INDALEKO_ROOT is set
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position

from semantic.collectors.checksum.checksum import IndalekoSemanticChecksums
from semantic.recorders.checksum.recorder import ChecksumRecorder
from storage.i_object import IndalekoObject
from storage.known_attributes import StorageSemanticAttributes
from utils.db.db_file_picker import IndalekoFilePicker

# pylint: enable=wrong-import-position

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ChecksumBackgroundProcessor")


def process_file_checksums(
    file_obj: IndalekoObject, local_path: str,
) -> dict[str, str] | None:
    """
    Process a file with the checksum collector.

    Args:
        file_obj: The IndalekoObject to process
        local_path: The local path to the file

    Returns:
        Optional[Dict[str, str]]: Checksum information if successful, None otherwise
    """
    try:
        # Create a collector instance
        collector = IndalekoSemanticChecksums()

        # Process the file
        object_id = file_obj.get_object_id()
        logger.info(f"Processing checksums for {local_path} (ID: {object_id})")

        # Check if file exists and is accessible
        if not os.path.exists(local_path) or not os.access(local_path, os.R_OK):
            logger.warning(f"File {local_path} does not exist or is not readable")
            return None

        # Calculate checksums
        checksums = collector.compute_checksums(local_path)
        if not checksums:
            logger.warning(f"Failed to compute checksums for {local_path}")
            return None

        logger.info(
            f"Calculated checksums for {local_path}: MD5={checksums['md5'][:8]}...",
        )

        # Return the checksum information
        return checksums

    except Exception as e:
        logger.error(f"Error processing checksums for {local_path}: {e}")
        return None


def process_file_and_store(
    file_obj: IndalekoObject, local_path: str,
) -> dict[str, str] | None:
    """
    Process a file with the checksum collector and store results in the database.

    Args:
        file_obj: The IndalekoObject to process
        local_path: The local path to the file

    Returns:
        Optional[Dict[str, str]]: Checksum information if successful, None otherwise
    """
    try:
        # Create recorder instance which creates collector internally
        recorder = ChecksumRecorder()

        # Process the file
        object_id = file_obj.get_object_id()
        logger.info(f"Processing checksums for {local_path} (ID: {object_id})")

        # Check if file exists and is accessible
        if not os.path.exists(local_path) or not os.access(local_path, os.R_OK):
            logger.warning(f"File {local_path} does not exist or is not readable")
            return None

        # Calculate checksums and store them
        result = recorder.process_file(local_path, object_id)
        if not result:
            logger.warning(f"Failed to process checksums for {local_path}")
            return None

        # Extract checksums from the process result
        checksums = {
            "md5": result.get("md5", ""),
            "sha1": result.get("sha1", ""),
            "sha256": result.get("sha256", ""),
            "sha512": result.get("sha512", ""),
            "dropbox": result.get("dropbox", ""),
        }

        logger.info(f"Processed and stored checksums for {local_path}")

        # Return the checksum information
        return checksums

    except Exception as e:
        logger.error(f"Error processing and storing checksums for {local_path}: {e}")
        return None


def get_checksum_attribute_ids() -> list[str]:
    """
    Get all checksum-related semantic attribute IDs.

    Returns:
        List[str]: List of checksum attribute IDs
    """
    # Define the checksum attribute IDs
    # These should be updated to match the actual IDs used in the system
    return [
        StorageSemanticAttributes.STORAGE_ATTRIBUTES_CHECKSUM_MD5,
        StorageSemanticAttributes.STORAGE_ATTRIBUTES_CHECKSUM_SHA1,
        StorageSemanticAttributes.STORAGE_ATTRIBUTES_CHECKSUM_SHA256,
        StorageSemanticAttributes.STORAGE_ATTRIBUTES_CHECKSUM_SHA512,
        # Add Dropbox hash if available in StorageSemanticAttributes
    ]


def schedule_checksum_processing(
    count: int = 10,
    background: bool = True,
    batch_size: int = 50,
    max_age_days: int | None = None,
    min_last_processed_days: int | None = 30,
    run_duration: int | None = None,
    file_extensions: list[str] | None = None,
) -> tuple[int, int]:
    """
    Schedule checksum processing for files in the database.

    Args:
        count: Number of files to process in each batch
        background: If True, process in background, otherwise process immediately
        batch_size: Size of the batch for background processing
        max_age_days: Only process files modified within this many days
        min_last_processed_days: Only process files not processed in this many days
        run_duration: If set, run for this many seconds, otherwise run once
        file_extensions: Optional list of file extensions to filter by

    Returns:
        Tuple[int, int]: Number of files scheduled and processed
    """
    try:
        # Create file picker instance
        file_picker = IndalekoFilePicker()

        # Initialize counters
        total_scheduled = 0
        total_processed = 0

        # Get the semantic attribute IDs for checksums
        checksum_attr_ids = get_checksum_attribute_ids()

        # Process once or in a loop
        start_time = time.time()
        while True:
            # Select a random attribute ID from the checksum attributes
            # This helps distribute the work across different checksum types
            import random

            attr_id = random.choice(checksum_attr_ids)

            # Pick files that need checksum processing
            logger.info(f"Selecting up to {count} files for {attr_id} processing")
            files = file_picker.pick_files_for_semantic_processing(
                semantic_attribute_id=attr_id,
                count=count,
                max_age_days=max_age_days,
                min_last_processed_days=min_last_processed_days,
            )

            # Apply file extension filter if specified
            if file_extensions and len(file_extensions) > 0:
                filtered_files = []
                for file in files:
                    doc = file.serialize()
                    label = doc.get("Label", "")
                    if any(
                        label.lower().endswith(ext.lower()) for ext in file_extensions
                    ):
                        filtered_files.append(file)
                files = filtered_files

            num_files = len(files)
            logger.info(f"Found {num_files} files needing checksum processing")

            if num_files == 0:
                logger.info(
                    "No files found needing processing, waiting before retrying",
                )
                if run_duration is None:
                    break
                time.sleep(10)  # Wait before retrying
                continue

            # Process files
            if background:
                # Queue for background processing
                process_func = (
                    process_file_checksums if not background else process_file_and_store
                )
                queued = file_picker.queue_for_background_processing(
                    files=files,
                    process_func=process_func,
                    priority=3,  # Lower priority than MIME type (higher number = lower priority)
                    semantic_attribute_id=attr_id,
                )

                logger.info(f"Queued {queued} files for background checksum processing")
                total_scheduled += queued

            else:
                # Process immediately
                for file in files:
                    doc = file.serialize()
                    uri = doc.get("URI", "")
                    volume_parts = uri.split("Volume")

                    if len(volume_parts) >= 2:
                        volume_guid = f"Volume{volume_parts[1].split('\\')[0]}"
                        local_path = file_picker._uri_to_local_path(uri, volume_guid)

                        if local_path:
                            result = process_file_and_store(file, local_path)
                            if result:
                                total_processed += 1

                logger.info(f"Processed {total_processed} files directly")

            # Check if we should continue running
            if run_duration is None:
                break

            elapsed_time = time.time() - start_time
            if elapsed_time >= run_duration:
                logger.info(
                    f"Run duration of {run_duration} seconds exceeded, stopping",
                )
                break

            # Wait before processing next batch
            time.sleep(5)

        # Stop background processing if we're done
        if background and run_duration is None:
            file_picker.stop_background_processing(wait=True)

        return total_scheduled, total_processed

    except Exception as e:
        logger.error(f"Error scheduling checksum processing: {e}")
        return 0, 0


def main():
    """Main function for the checksum background processor"""
    parser = argparse.ArgumentParser(description="Background checksum processor")
    parser.add_argument(
        "--count", type=int, default=10, help="Number of files to process in each batch",
    )
    parser.add_argument(
        "--foreground",
        action="store_true",
        help="Process files in foreground instead of background",
    )
    parser.add_argument(
        "--batch-size", type=int, default=50, help="Size of the batch for processing",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=None,
        help="Only process files modified within this many days",
    )
    parser.add_argument(
        "--min-last-processed-days",
        type=int,
        default=30,
        help="Only process files not processed in this many days",
    )
    parser.add_argument(
        "--run-duration",
        type=int,
        default=None,
        help="Run for this many seconds, or indefinitely if not specified",
    )
    parser.add_argument(
        "--file-extensions",
        type=str,
        nargs="+",
        help="Only process files with these extensions",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug output")

    args = parser.parse_args()

    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run the processor
    logger.info("Starting checksum background processor")
    scheduled, processed = schedule_checksum_processing(
        count=args.count,
        background=not args.foreground,
        batch_size=args.batch_size,
        max_age_days=args.max_age_days,
        min_last_processed_days=args.min_last_processed_days,
        run_duration=args.run_duration,
        file_extensions=args.file_extensions,
    )

    # Print summary
    if args.foreground:
        logger.info(f"Checksum processor completed. Processed {processed} files.")
    else:
        logger.info(
            f"Checksum processor completed. Scheduled {scheduled} files for processing.",
        )


if __name__ == "__main__":
    main()
