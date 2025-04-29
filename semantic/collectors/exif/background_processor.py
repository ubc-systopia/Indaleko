#!/usr/bin/env python3
"""
Background processor for EXIF metadata extraction.

This module demonstrates using the enhanced IndalekoFilePicker to perform
background EXIF metadata extraction on image files in the database.

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
from typing import Any

# Ensure INDALEKO_ROOT is set
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position

import semantic.recorders.exif.characteristics as ExifCharacteristics
from semantic.collectors.exif.exif_collector import ExifCollector
from semantic.recorders.exif.recorder import ExifRecorder
from storage.i_object import IndalekoObject
from utils.db.db_file_picker import IndalekoFilePicker

# pylint: enable=wrong-import-position

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ExifBackgroundProcessor")

# Define supported image extensions
SUPPORTED_IMAGE_EXTENSIONS = [
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".png",
    ".heic",
    ".heif",
    ".nef",
    ".cr2",
    ".dng",
]


def process_file_exif(
    file_obj: IndalekoObject,
    local_path: str,
) -> dict[str, Any] | None:
    """
    Process a file with the EXIF metadata collector.

    Args:
        file_obj: The IndalekoObject to process
        local_path: The local path to the file

    Returns:
        Optional[Dict[str, Any]]: EXIF data if successful, None otherwise
    """
    try:
        # Check if file extension is supported
        _, ext = os.path.splitext(local_path.lower())
        if ext not in SUPPORTED_IMAGE_EXTENSIONS:
            logger.debug(f"Skipping unsupported file type {ext}: {local_path}")
            return None

        # Create a collector instance
        collector = ExifCollector()

        # Process the file
        object_id = file_obj.get_object_id()
        logger.info(f"Processing EXIF metadata for {local_path} (ID: {object_id})")

        # Check if file exists and is accessible
        if not os.path.exists(local_path) or not os.access(local_path, os.R_OK):
            logger.warning(f"File {local_path} does not exist or is not readable")
            return None

        # Extract EXIF data
        exif_data = collector.extract_exif_from_file(local_path, object_id)
        if not exif_data:
            logger.info(f"No EXIF data found in {local_path}")
            return None

        logger.info(f"Extracted EXIF data from {local_path}")

        # Return the EXIF data
        return exif_data.model_dump()

    except Exception as e:
        logger.error(f"Error processing EXIF metadata for {local_path}: {e}")
        return None


def process_file_and_store(
    file_obj: IndalekoObject,
    local_path: str,
) -> dict[str, Any] | None:
    """
    Process a file with the EXIF collector and store results in the database.

    Args:
        file_obj: The IndalekoObject to process
        local_path: The local path to the file

    Returns:
        Optional[Dict[str, Any]]: EXIF data if successful, None otherwise
    """
    try:
        # Check if file extension is supported
        _, ext = os.path.splitext(local_path.lower())
        if ext not in SUPPORTED_IMAGE_EXTENSIONS:
            logger.debug(f"Skipping unsupported file type {ext}: {local_path}")
            return None

        # Create recorder instance (which creates collector internally)
        recorder = ExifRecorder()

        # Process the file
        object_id = file_obj.get_object_id()
        logger.info(f"Processing EXIF metadata for {local_path} (ID: {object_id})")

        # Check if file exists and is accessible
        if not os.path.exists(local_path) or not os.access(local_path, os.R_OK):
            logger.warning(f"File {local_path} does not exist or is not readable")
            return None

        # Extract and store EXIF data
        exif_data = recorder.process_file(local_path, object_id)
        if not exif_data:
            logger.info(f"No EXIF data found in {local_path}")
            return None

        logger.info(f"Processed and stored EXIF data for {local_path}")

        # Return the EXIF data
        return exif_data

    except Exception as e:
        logger.error(
            f"Error processing and storing EXIF metadata for {local_path}: {e}",
        )
        return None


def get_exif_attribute_ids() -> list[str]:
    """
    Get all EXIF-related semantic attribute IDs.

    Returns:
        List[str]: List of EXIF attribute IDs
    """
    # Define the EXIF attribute IDs that we want to check
    # These are the primary ones we care about for processing prioritization
    return [
        # Main EXIF data identifier
        ExifCharacteristics.SEMANTIC_EXIF_DATA,
        # Camera information
        ExifCharacteristics.SEMANTIC_EXIF_CAMERA_MAKE,
        ExifCharacteristics.SEMANTIC_EXIF_CAMERA_MODEL,
        # GPS data
        ExifCharacteristics.SEMANTIC_EXIF_GPS_LATITUDE,
        ExifCharacteristics.SEMANTIC_EXIF_GPS_LONGITUDE,
        # Capture settings
        ExifCharacteristics.SEMANTIC_EXIF_DATETIME_ORIGINAL,
        # Image information
        ExifCharacteristics.SEMANTIC_EXIF_IMAGE_WIDTH,
        ExifCharacteristics.SEMANTIC_EXIF_IMAGE_HEIGHT,
    ]


def schedule_exif_processing(
    count: int = 15,
    background: bool = True,
    batch_size: int = 100,
    max_age_days: int | None = None,
    min_last_processed_days: int | None = 45,
    run_duration: int | None = None,
) -> tuple[int, int]:
    """
    Schedule EXIF metadata processing for image files in the database.

    Args:
        count: Number of files to process in each batch
        background: If True, process in background, otherwise process immediately
        batch_size: Size of the batch for background processing
        max_age_days: Only process files modified within this many days
        min_last_processed_days: Only process files not processed in this many days
        run_duration: If set, run for this many seconds, otherwise run once

    Returns:
        Tuple[int, int]: Number of files scheduled and processed
    """
    try:
        # Create file picker instance
        file_picker = IndalekoFilePicker()

        # Initialize counters
        total_scheduled = 0
        total_processed = 0

        # Get the semantic attribute IDs for EXIF
        exif_attr_ids = get_exif_attribute_ids()

        # Process once or in a loop
        start_time = time.time()
        while True:
            # Select a random attribute ID from the EXIF attributes
            # This helps distribute the work across different EXIF attributes
            import random

            attr_id = random.choice(exif_attr_ids)

            # Pick files that need EXIF processing
            logger.info(f"Selecting up to {count} image files for {attr_id} processing")
            files = file_picker.pick_files_for_semantic_processing(
                semantic_attribute_id=attr_id,
                count=count,
                max_age_days=max_age_days,
                min_last_processed_days=min_last_processed_days,
            )

            # Filter for supported image file types
            filtered_files = []
            for file in files:
                doc = file.serialize()
                label = doc.get("Label", "")
                if any(label.lower().endswith(ext) for ext in SUPPORTED_IMAGE_EXTENSIONS):
                    filtered_files.append(file)

            files = filtered_files
            num_files = len(files)
            logger.info(f"Found {num_files} image files needing EXIF processing")

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
                process_func = process_file_exif if not background else process_file_and_store
                queued = file_picker.queue_for_background_processing(
                    files=files,
                    process_func=process_func,
                    priority=2,  # Same priority as MIME type
                    semantic_attribute_id=attr_id,
                )

                logger.info(f"Queued {queued} files for background EXIF processing")
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
        logger.error(f"Error scheduling EXIF processing: {e}")
        return 0, 0


def main():
    """Main function for the EXIF metadata background processor"""
    parser = argparse.ArgumentParser(description="Background EXIF metadata processor")
    parser.add_argument(
        "--count",
        type=int,
        default=15,
        help="Number of files to process in each batch",
    )
    parser.add_argument(
        "--foreground",
        action="store_true",
        help="Process files in foreground instead of background",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Size of the batch for processing",
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
        default=45,
        help="Only process files not processed in this many days",
    )
    parser.add_argument(
        "--run-duration",
        type=int,
        default=None,
        help="Run for this many seconds, or indefinitely if not specified",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug output")

    args = parser.parse_args()

    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run the processor
    logger.info("Starting EXIF metadata background processor")
    scheduled, processed = schedule_exif_processing(
        count=args.count,
        background=not args.foreground,
        batch_size=args.batch_size,
        max_age_days=args.max_age_days,
        min_last_processed_days=args.min_last_processed_days,
        run_duration=args.run_duration,
    )

    # Print summary
    if args.foreground:
        logger.info(f"EXIF metadata processor completed. Processed {processed} files.")
    else:
        logger.info(
            f"EXIF metadata processor completed. Scheduled {scheduled} files for processing.",
        )


if __name__ == "__main__":
    main()
