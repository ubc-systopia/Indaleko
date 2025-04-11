"""
This implements a recorder for storing MIME type data in the Indaleko database.

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

# standard imports
import argparse
import json
import logging
import mimetypes
import os
import random
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

# third-party imports
from icecream import ic
from tqdm import tqdm

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Indaleko imports
# pylint: disable=wrong-import-position
from data_models.i_uuid import IndalekoUUIDDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.service_identifier import IndalekoServiceIdentifierDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from data_models.timestamp import IndalekoTimestampDataModel

from semantic.collectors.mime.mime_collector import IndalekoSemanticMimeType
from semantic.recorders.mime.characteristics import (
    SEMANTIC_MIME_TYPE,
    SEMANTIC_MIME_CONFIDENCE,
    SEMANTIC_MIME_TYPE_FROM_EXTENSION,
    SEMANTIC_MIME_ENCODING,
    SEMANTIC_MIME_IS_TEXT,
    SEMANTIC_MIME_IS_IMAGE,
    SEMANTIC_MIME_IS_AUDIO,
    SEMANTIC_MIME_IS_VIDEO,
    SEMANTIC_MIME_IS_APPLICATION,
    SEMANTIC_MIME_IS_CONTAINER,
    SEMANTIC_MIME_IS_COMPRESSED,
    SEMANTIC_MIME_IS_ENCRYPTED,
)

# pylint: enable=wrong-import-position


class IndalekoJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for Indaleko data models"""

    def default(self, obj):
        """Override default to handle UUID and datetime objects"""
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class MimeTypeRecorder:
    """Class for recording MIME type information to Indaleko database"""

    def __init__(self, db_config: Optional[Dict] = None):
        """
        Initialize the MIME type recorder.
        
        Args:
            db_config (Optional[Dict]): Database configuration
        """
        self._collector = IndalekoSemanticMimeType()
        self._service_id = uuid.UUID("b3c7a9d5-4e6f-8d2a-1c9e-7f4b6d3a5e8c")
        self._logger = logging.getLogger("MimeTypeRecorder")
        self._db_config = db_config
        self._db_connection = None
        
        # Setup logging
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)
            
        # Initialize file extensions to MIME types mapping
        mimetypes.init()
        
        # Connect to database if config is provided
        if db_config:
            self._connect_to_db()
            
    def _connect_to_db(self):
        """Connect to the Indaleko database"""
        try:
            # TODO: Implement database connection
            self._logger.info("Database connection would be established here.")
            # For now, we'll skip actual DB connection since it's not implemented
            self._db_connection = True
        except Exception as e:
            self._logger.error(f"Failed to connect to database: {e}")
            traceback.print_exc()
    
    def lookup_object_by_path(self, file_path: str) -> Optional[uuid.UUID]:
        """
        Lookup an object identifier based on file path.
        
        Args:
            file_path (str): The path to the file
            
        Returns:
            Optional[uuid.UUID]: The object identifier if found, None otherwise
        """
        # TODO: Implement actual lookup from database
        # For now, generate a deterministic UUID based on the file path
        # This is just for testing purposes
        return uuid.uuid5(uuid.NAMESPACE_URL, f"file://{os.path.abspath(file_path)}")

    def process_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Process a single file to detect and record MIME type.
        
        Args:
            file_path (str): Path to the file to process
            
        Returns:
            Optional[Dict[str, Any]]: The recorded data if successful, None otherwise
        """
        try:
            # Check if file exists
            if not os.path.isfile(file_path):
                self._logger.warning(f"File does not exist: {file_path}")
                return None
                
            # Get object ID for file
            object_id = self.lookup_object_by_path(file_path)
            if not object_id:
                self._logger.warning(f"Failed to lookup object ID for: {file_path}")
                return None
            
            # Get MIME type data
            mime_data = self._collector.get_mime_type_for_file(file_path, object_id)
            
            # If connected to database, store the data
            if self._db_connection:
                # TODO: Implement storing to database
                self._logger.debug(f"Would store MIME data for {file_path} to database")
                
            return mime_data
        except Exception as e:
            self._logger.error(f"Error processing file {file_path}: {e}")
            traceback.print_exc()
            return None

    def batch_process_files(self, file_list: List[str]) -> List[Dict[str, Any]]:
        """
        Process a batch of files.
        
        Args:
            file_list (List[str]): List of file paths to process
            
        Returns:
            List[Dict[str, Any]]: List of successfully processed file data
        """
        results = []
        
        with tqdm(total=len(file_list), desc="Processing files", unit="file") as pbar:
            for file_path in file_list:
                result = self.process_file(file_path)
                if result:
                    results.append(result)
                pbar.update(1)
                
        return results

    def process_directory(self, directory_path: str, recursive: bool = True, 
                         file_extensions: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Process all files in a directory.
        
        Args:
            directory_path (str): Path to the directory to process
            recursive (bool): Whether to process subdirectories
            file_extensions (Optional[List[str]]): List of file extensions to process
            
        Returns:
            List[Dict[str, Any]]: List of successfully processed file data
        """
        # Normalize path
        directory_path = os.path.abspath(directory_path)
        
        # Check if directory exists
        if not os.path.isdir(directory_path):
            self._logger.error(f"Directory does not exist: {directory_path}")
            return []
            
        # Collect file paths
        file_list = []
        
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                
                # Skip files with unwanted extensions if filter is provided
                if file_extensions:
                    if not any(file.lower().endswith(ext.lower()) for ext in file_extensions):
                        continue
                        
                file_list.append(file_path)
                
            if not recursive:
                break
                
        # Process the files
        self._logger.info(f"Found {len(file_list)} files to process in {directory_path}")
        return self.batch_process_files(file_list)

    def export_results_to_json(self, results: List[Dict[str, Any]], output_file: str) -> None:
        """
        Export processing results to a JSON file.
        
        Args:
            results (List[Dict[str, Any]]): The results to export
            output_file (str): Path to the output file
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, cls=IndalekoJSONEncoder, indent=2)
            self._logger.info(f"Exported {len(results)} results to {output_file}")
        except Exception as e:
            self._logger.error(f"Error exporting results to {output_file}: {e}")
            traceback.print_exc()

    def summarize_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a summary of processing results.
        
        Args:
            results (List[Dict[str, Any]]): The results to summarize
            
        Returns:
            Dict[str, Any]: Summary statistics
        """
        if not results:
            return {"total_files": 0}
            
        # Count files by MIME type
        mime_type_counts = {}
        confidence_sum = 0
        confidence_count = 0
        extension_match_count = 0
        
        for result in results:
            mime_type = result.get("mime_type", "unknown")
            if mime_type in mime_type_counts:
                mime_type_counts[mime_type] += 1
            else:
                mime_type_counts[mime_type] = 1
                
            # Track confidence
            confidence = result.get("confidence", 0)
            if confidence > 0:
                confidence_sum += confidence
                confidence_count += 1
                
            # Track extension matches
            if result.get("mime_type") == result.get("mime_type_from_extension"):
                extension_match_count += 1
                
        return {
            "total_files": len(results),
            "mime_type_counts": mime_type_counts,
            "avg_confidence": confidence_sum / confidence_count if confidence_count > 0 else 0,
            "extension_match_percentage": (extension_match_count / len(results)) * 100 if results else 0
        }


def main():
    """Command-line interface for the MIME type recorder"""
    parser = argparse.ArgumentParser(description="Indaleko MIME Type Recorder")
    
    # Required arguments
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--file', '-f', help='Process a single file')
    group.add_argument('--directory', '-d', help='Process a directory')
    
    # Optional arguments
    parser.add_argument('--recursive', '-r', action='store_true', 
                        help='Process subdirectories recursively')
    parser.add_argument('--extensions', '-e', nargs='+', 
                        help='Only process files with these extensions')
    parser.add_argument('--output', '-o', help='Output file for results (JSON)')
    parser.add_argument('--summary', '-s', action='store_true', 
                        help='Print summary of results')
    parser.add_argument('--verbose', '-v', action='store_true', 
                        help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Create recorder
    recorder = MimeTypeRecorder()
    
    # Set logging level
    if args.verbose:
        recorder._logger.setLevel(logging.DEBUG)
    
    results = []
    
    # Process input
    if args.file:
        result = recorder.process_file(args.file)
        if result:
            results = [result]
    else:  # args.directory
        results = recorder.process_directory(
            args.directory, 
            recursive=args.recursive,
            file_extensions=args.extensions
        )
    
    # Output results
    if args.output:
        recorder.export_results_to_json(results, args.output)
    
    # Print summary
    if args.summary or not args.output:
        summary = recorder.summarize_results(results)
        print(f"\nMIME Type Detection Summary:")
        print(f"  Total files processed: {summary['total_files']}")
        print(f"  Average confidence: {summary['avg_confidence']:.2f}")
        print(f"  Extension match rate: {summary['extension_match_percentage']:.1f}%")
        print("\nMIME Type Distribution:")
        for mime_type, count in sorted(summary['mime_type_counts'].items(), 
                                      key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {mime_type}: {count} files")


if __name__ == "__main__":
    main()