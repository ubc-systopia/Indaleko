"""
This module handles processing and recording EXIF metadata from image files.

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

# Standard imports
import os
import sys
import datetime
import json
import argparse
import uuid
import logging
from typing import Dict, List, Optional, Any, Union

# Third-party imports
from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Indaleko imports
from Indaleko import Indaleko
from semantic.data_models.base_data_model import BaseSemanticDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.i_uuid import IndalekoUUIDDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from semantic.characteristics import SemanticDataCharacteristics
from semantic.collectors.exif.exif_collector import ExifCollector
from semantic.collectors.exif.data_model import ExifDataModel
import semantic.recorders.exif.characteristics as ExifCharacteristics


# Custom JSON encoder to handle UUID and datetime objects
class IndalekoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


class ExifRecorder:
    """
    Recorder for EXIF metadata from image files.
    
    This class handles the recording of EXIF metadata, processing image files to
    extract metadata and storing the results in Indaleko's database.
    """

    # Unique identifier for this recorder
    recorder_uuid = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    
    def __init__(self, output_path: Optional[str] = None):
        """
        Initialize the EXIF metadata recorder.
        
        Args:
            output_path: Optional path for output. If not provided, uses default location.
        """
        self.collector = ExifCollector()
        self.output_file = output_path or os.path.join(
            Indaleko.default_data_dir, "semantic", "exif_data.jsonl"
        )
        self.recording_date = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        
        # Cache for already processed files
        self.processed_files = set()
        
    def process_file(self, file_path: str, object_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        """
        Process a file to extract EXIF metadata.
        
        Args:
            file_path: Path to the image file
            object_id: UUID of the file in Indaleko
            
        Returns:
            Dict[str, Any]: Extracted EXIF data or None if processing fails
        """
        # Skip if already processed
        if file_path in self.processed_files:
            logging.info(f"Skipping already processed file: {file_path}")
            return None
            
        # Make sure the file exists
        if not os.path.exists(file_path):
            logging.warning(f"File not found: {file_path}")
            return None
            
        # Convert string UUID to UUID object if needed
        if isinstance(object_id, str):
            object_id = uuid.UUID(object_id)
            
        # Extract EXIF data
        try:
            exif_data = self.collector.extract_exif_from_file(file_path, object_id)
            if not exif_data:
                return None
                
            # Mark as processed
            self.processed_files.add(file_path)
            
            return exif_data.model_dump()
            
        except Exception as e:
            logging.error(f"Error processing EXIF data from {file_path}: {e}")
            return None
            
    def batch_process_files(self, file_list: List[Dict[str, Any]]) -> None:
        """
        Process multiple files and save the results.
        
        Args:
            file_list: List of dictionaries with 'path' and 'object_id' keys
        """
        total_files = len(file_list)
        logging.info(f"Beginning batch processing of {total_files} files")
        processed_count = 0
        error_count = 0
        last_percent = 0
        
        with open(self.output_file, "w", encoding="utf-8") as jsonl_output:
            for i, file_info in enumerate(file_list):
                # Progress reporting
                current_percent = int((i / total_files) * 100)
                if current_percent > last_percent and current_percent % 5 == 0:
                    print(f"Progress: {current_percent}% ({i}/{total_files})")
                    last_percent = current_percent
                
                if "path" not in file_info or "object_id" not in file_info:
                    logging.warning(f"Missing path or object_id in file info: {file_info}")
                    error_count += 1
                    continue
                    
                exif_data = self.process_file(file_info["path"], file_info["object_id"])
                if exif_data:
                    jsonl_output.write(json.dumps(exif_data, cls=IndalekoJSONEncoder) + "\n")
                    processed_count += 1
                else:
                    error_count += 1
                    
        logging.info(f"Batch processing complete. Processed: {processed_count}, Errors: {error_count}")
        print(f"Processing complete. Processed: {processed_count}, Errors: {error_count}")
        print(f"Output file: {self.output_file}")
        
    def process_directory(self, directory_path: str, recursive: bool = True, file_extensions: Optional[List[str]] = None) -> None:
        """
        Process all image files in a directory.
        
        Args:
            directory_path: Path to the directory
            recursive: Whether to process subdirectories
            file_extensions: Optional list of file extensions to process. If None, processes all supported image formats.
        """
        print(f"Processing directory: {directory_path}, recursive: {recursive}")
        logging.info(f"Processing directory: {directory_path}, recursive: {recursive}")
        
        # Default image extensions if not specified
        if file_extensions is None:
            file_extensions = ['.jpg', '.jpeg', '.tif', '.tiff', '.png', '.heic', '.heif', '.nef', '.cr2', '.dng']
            
        # Convert extensions to lowercase for case-insensitive matching
        file_extensions = [ext.lower() for ext in file_extensions]
        
        file_list = []
        
        print("Discovering image files...")
        # First, discover all image files
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                _, ext = os.path.splitext(file_path.lower())
                
                # Skip non-image files
                if ext not in file_extensions:
                    continue
                    
                # Skip files that can't be read or don't exist
                if not os.path.exists(file_path) or not os.access(file_path, os.R_OK):
                    continue
                    
                file_list.append({
                    "path": file_path,
                    "object_id": uuid.uuid4()  # Note: In a real system, would look up the existing object ID
                })
                
            if not recursive:
                break
                
        print(f"Found {len(file_list)} image files. Beginning EXIF extraction...")
        self.batch_process_files(file_list)
        
    def upload_to_database(self, db_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Upload the processed EXIF data to the database.
        
        Args:
            db_config: Optional database configuration
        """
        # This would be implemented to connect to ArangoDB and upload the data
        # For now, we just have a placeholder since DB integration requires specific configuration
        logging.info("Database upload functionality not yet implemented")
        logging.info(f"Data ready for upload at: {self.output_file}")


def main():
    """Main entry point for the EXIF recorder."""
    parser = argparse.ArgumentParser(description="Indaleko EXIF Metadata Recorder")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Subparser for processing a single file
    parser_file = subparsers.add_parser("file", help="Process a single image file")
    parser_file.add_argument("path", help="Path to the image file")
    parser_file.add_argument("--id", help="Object ID (if not provided, will generate a new UUID)")
    
    # Subparser for processing a directory
    parser_dir = subparsers.add_parser("directory", help="Process all image files in a directory")
    parser_dir.add_argument("path", help="Path to the directory")
    parser_dir.add_argument("--recursive", action="store_true", help="Process subdirectories")
    parser_dir.add_argument("--extensions", nargs="+", help="File extensions to process (e.g. .jpg .png)")
    
    # Subparser for batch processing
    parser_batch = subparsers.add_parser("batch", help="Process a batch of files from a JSON file")
    parser_batch.add_argument("file", help="Path to JSON file with file information")
    
    # Subparser for uploading to database
    parser_upload = subparsers.add_parser("upload", help="Upload processed data to the database")
    parser_upload.add_argument("--config", help="Path to database configuration file")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Create recorder
    recorder = ExifRecorder()
    
    # Execute command
    if args.command == "file":
        object_id = args.id if args.id else str(uuid.uuid4())
        file_data = recorder.process_file(args.path, object_id)
        if file_data:
            with open(recorder.output_file, "w", encoding="utf-8") as f:
                f.write(json.dumps(file_data, cls=IndalekoJSONEncoder) + "\n")
            print(f"File processed successfully: {args.path}")
            print(f"Output saved to: {recorder.output_file}")
        else:
            print(f"Error processing file: {args.path}")
            
    elif args.command == "directory":
        recorder.process_directory(
            args.path, 
            recursive=args.recursive,
            file_extensions=args.extensions
        )
        
    elif args.command == "batch":
        with open(args.file, "r", encoding="utf-8") as f:
            file_list = json.load(f)
        recorder.batch_process_files(file_list)
        
    elif args.command == "upload":
        config = None
        if args.config:
            with open(args.config, "r", encoding="utf-8") as f:
                config = json.load(f)
        recorder.upload_to_database(config)
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()