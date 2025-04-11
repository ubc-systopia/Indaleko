#!/usr/bin/env python3
"""
Background processor for MIME type detection.

This module demonstrates using the enhanced IndalekoFilePicker to perform
background MIME type detection on files in the database.

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

import os
import sys
import time
import argparse
import logging
from typing import Optional, Tuple, Dict, Any

# Ensure INDALEKO_ROOT is set
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from storage.i_object import IndalekoObject
from storage.known_attributes import StorageSemanticAttributes
from utils.db.db_file_picker import IndalekoFilePicker
from semantic.collectors.mime.mime_collector import IndalekoSemanticMimeType
from semantic.recorders.mime.recorder import MimeTypeRecorder
from icecream import ic
# pylint: enable=wrong-import-position

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MimeBackgroundProcessor")


def process_file_mime(file_obj: IndalekoObject, local_path: str) -> Optional[Dict[str, Any]]:
    """
    Process a file with the MIME type collector.
    
    Args:
        file_obj: The IndalekoObject to process
        local_path: The local path to the file
        
    Returns:
        Optional[Dict[str, Any]]: MIME type information if successful, None otherwise
    """
    try:
        # Create a collector instance
        collector = IndalekoSemanticMimeType()
        
        # Process the file
        object_id = file_obj.get_object_id()
        logger.info(f"Processing MIME type for {local_path} (ID: {object_id})")
        
        # Check if file exists and is accessible
        if not os.path.exists(local_path) or not os.access(local_path, os.R_OK):
            logger.warning(f"File {local_path} does not exist or is not readable")
            return None
            
        # Detect MIME type
        mime_info = collector.detect_mime_type(local_path)
        logger.info(f"Detected MIME type: {mime_info['mime_type']} for {local_path}")
        
        # Return the MIME type information
        return mime_info
        
    except Exception as e:
        logger.error(f"Error processing MIME type for {local_path}: {e}")
        return None


def process_file_and_store(file_obj: IndalekoObject, local_path: str) -> Optional[Dict[str, Any]]:
    """
    Process a file with the MIME type collector and store results in the database.
    
    Args:
        file_obj: The IndalekoObject to process
        local_path: The local path to the file
        
    Returns:
        Optional[Dict[str, Any]]: MIME type information if successful, None otherwise
    """
    try:
        # Create collector and recorder instances
        collector = IndalekoSemanticMimeType()
        recorder = MimeTypeRecorder()
        
        # Process the file
        object_id = file_obj.get_object_id()
        logger.info(f"Processing MIME type for {local_path} (ID: {object_id})")
        
        # Check if file exists and is accessible
        if not os.path.exists(local_path) or not os.access(local_path, os.R_OK):
            logger.warning(f"File {local_path} does not exist or is not readable")
            return None
            
        # Create a MIME record
        mime_record = collector.create_mime_record(local_path, object_id)
        if not mime_record:
            logger.warning(f"Failed to create MIME record for {local_path}")
            return None
            
        # Store the record
        recorder.store_mime_data([mime_record])
        
        # Return the MIME type information
        return {
            "mime_type": mime_record["mime_type"],
            "confidence": mime_record.get("confidence", 100)
        }
        
    except Exception as e:
        logger.error(f"Error processing and storing MIME type for {local_path}: {e}")
        return None


def schedule_mime_processing(
    count: int = 10,
    background: bool = True,
    batch_size: int = 100,
    max_age_days: Optional[int] = None,
    min_last_processed_days: Optional[int] = 30,
    run_duration: Optional[int] = None
) -> Tuple[int, int]:
    """
    Schedule MIME type processing for files in the database.
    
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
        
        # Get the semantic attribute ID for MIME type from content
        mime_type_attr_id = StorageSemanticAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_CONTENT
        
        # Process once or in a loop
        start_time = time.time()
        while True:
            # Pick files that need MIME type processing
            logger.info(f"Selecting up to {count} files for MIME type processing")
            files = file_picker.pick_files_for_semantic_processing(
                semantic_attribute_id=mime_type_attr_id,
                count=count,
                max_age_days=max_age_days,
                min_last_processed_days=min_last_processed_days
            )
            
            num_files = len(files)
            logger.info(f"Found {num_files} files needing MIME type processing")
            
            if num_files == 0:
                logger.info("No files found needing processing, waiting before retrying")
                if run_duration is None:
                    break
                time.sleep(10)  # Wait before retrying
                continue
                
            # Process files
            if background:
                # Queue for background processing
                process_func = process_file_mime if not background else process_file_and_store
                queued = file_picker.queue_for_background_processing(
                    files=files,
                    process_func=process_func,
                    priority=2,
                    semantic_attribute_id=mime_type_attr_id
                )
                
                logger.info(f"Queued {queued} files for background MIME type processing")
                total_scheduled += queued
                
            else:
                # Process immediately
                for file in files:
                    doc = file.serialize()
                    uri = doc.get('URI', '')
                    volume_parts = uri.split('Volume')
                    
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
                logger.info(f"Run duration of {run_duration} seconds exceeded, stopping")
                break
                
            # Wait before processing next batch
            time.sleep(5)
            
        # Stop background processing if we're done
        if background and run_duration is None:
            file_picker.stop_background_processing(wait=True)
            
        return total_scheduled, total_processed
        
    except Exception as e:
        logger.error(f"Error scheduling MIME processing: {e}")
        return 0, 0


def main():
    """Main function for the MIME type background processor"""
    parser = argparse.ArgumentParser(description="Background MIME type processor")
    parser.add_argument(
        "--count", 
        type=int, 
        default=10, 
        help="Number of files to process in each batch"
    )
    parser.add_argument(
        "--foreground", 
        action="store_true", 
        help="Process files in foreground instead of background"
    )
    parser.add_argument(
        "--batch-size", 
        type=int, 
        default=100, 
        help="Size of the batch for processing"
    )
    parser.add_argument(
        "--max-age-days", 
        type=int, 
        default=None, 
        help="Only process files modified within this many days"
    )
    parser.add_argument(
        "--min-last-processed-days", 
        type=int, 
        default=30, 
        help="Only process files not processed in this many days"
    )
    parser.add_argument(
        "--run-duration", 
        type=int, 
        default=None, 
        help="Run for this many seconds, or indefinitely if not specified"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug output"
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        
    # Run the processor
    logger.info("Starting MIME type background processor")
    scheduled, processed = schedule_mime_processing(
        count=args.count,
        background=not args.foreground,
        batch_size=args.batch_size,
        max_age_days=args.max_age_days,
        min_last_processed_days=args.min_last_processed_days,
        run_duration=args.run_duration
    )
    
    # Print summary
    if args.foreground:
        logger.info(f"MIME type processor completed. Processed {processed} files.")
    else:
        logger.info(f"MIME type processor completed. Scheduled {scheduled} files for processing.")
    

if __name__ == "__main__":
    main()