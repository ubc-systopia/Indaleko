"""
This module handles processing and recording multi-checksum data.

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

# Custom JSON encoder to handle UUID and datetime objects
class IndalekoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

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
from semantic.collectors.checksum.checksum import IndalekoSemanticChecksums, compute_checksums
from semantic.collectors.checksum.data_model import SemanticChecksumDataModel
import semantic.recorders.checksum.characteristics as ChecksumDataCharacteristics
from utils.misc.data_management import encode_binary_data


class ChecksumRecorder:
    """
    Recorder for file checksums.
    
    This class handles the recording of checksum data, processing files to 
    compute multiple checksum types (MD5, SHA1, SHA256, SHA512, Dropbox) and
    storing the results in Indaleko's database.
    """

    # Unique identifier for this recorder
    recorder_uuid = "de7ff1c7-2550-4cb3-9538-775f9464746e"
    
    def __init__(self, output_path: Optional[str] = None):
        """
        Initialize the checksum recorder.
        
        Args:
            output_path: Optional path for output. If not provided, uses default location.
        """
        self.collector = IndalekoSemanticChecksums()
        self.output_file = output_path or os.path.join(
            Indaleko.default_data_dir, "semantic", "checksum_data.jsonl"
        )
        self.recording_date = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        
        # Initialize attribute mappings
        self.checksum_attributes = {
            "MD5": ChecksumDataCharacteristics.SEMANTIC_CHECKSUM_MD5,
            "SHA1": ChecksumDataCharacteristics.SEMANTIC_CHECKSUM_SHA1,
            "SHA256": ChecksumDataCharacteristics.SEMANTIC_CHECKSUM_SHA256,
            "SHA512": ChecksumDataCharacteristics.SEMANTIC_CHECKSUM_SHA512,
            "Dropbox": ChecksumDataCharacteristics.SEMANTIC_CHECKSUM_DROPBOX_SHA2,
        }
        
        # Cache for already processed files
        self.processed_files = set()
        
    def create_semantic_record(self, object_id: uuid.UUID) -> IndalekoRecordDataModel:
        """
        Create a basic record for the current checksum data.
        
        Args:
            object_id: The UUID of the file object
            
        Returns:
            IndalekoRecordDataModel: Record model for checksums
        """
        return IndalekoRecordDataModel(
            SourceIdentifier=IndalekoSourceIdentifierDataModel(
                Identifier=str(self.recorder_uuid),
                Version="1.0"
            ),
            Timestamp=datetime.datetime.now(datetime.timezone.utc),
            Attributes={},
            Data=""
        )
        
    def create_semantic_attributes(self, checksums: Dict[str, str]) -> List[IndalekoSemanticAttributeDataModel]:
        """
        Convert checksums into semantic attributes.
        
        Args:
            checksums: Dictionary of checksums with algorithm as key
            
        Returns:
            List[IndalekoSemanticAttributeDataModel]: List of semantic attributes
        """
        attributes = []
        
        for algo, value in checksums.items():
            if algo in self.checksum_attributes:
                uuid_value = self.checksum_attributes[algo]
                attributes.append(
                    IndalekoSemanticAttributeDataModel(
                        Identifier=IndalekoUUIDDataModel(
                            Identifier=uuid_value,
                            Label=f"{algo} Checksum"
                        ),
                        Value=value
                    )
                )
        
        return attributes
    
    def process_file(self, file_path: str, object_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        """
        Process a file to compute and format checksum data.
        
        Args:
            file_path: Path to the file
            object_id: UUID of the file in Indaleko
            
        Returns:
            Dict[str, Any]: Semantic data model for checksums
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
            
        # Compute checksums
        try:
            checksums = compute_checksums(file_path)
        except Exception as e:
            logging.error(f"Error computing checksums for {file_path}: {e}")
            return None
            
        # Create semantic attributes
        semantic_attributes = self.create_semantic_attributes(checksums)
        
        # Create the final semantic data model
        checksum_data = BaseSemanticDataModel(
            Record=self.create_semantic_record(object_id),
            Timestamp=datetime.datetime.now(datetime.timezone.utc),
            ObjectIdentifier=object_id,
            RelatedObjects=[object_id],
            SemanticAttributes=semantic_attributes
        )
        
        # Mark as processed
        self.processed_files.add(file_path)
        
        return checksum_data.model_dump()
        
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
                    
                checksum_data = self.process_file(file_info["path"], file_info["object_id"])
                if checksum_data:
                    jsonl_output.write(json.dumps(checksum_data, cls=IndalekoJSONEncoder) + "\n")
                    processed_count += 1
                else:
                    error_count += 1
                    
        logging.info(f"Batch processing complete. Processed: {processed_count}, Errors: {error_count}")
        print(f"Processing complete. Processed: {processed_count}, Errors: {error_count}")
        print(f"Output file: {self.output_file}")
        
    def process_directory(self, directory_path: str, recursive: bool = True) -> None:
        """
        Process all files in a directory.
        
        Args:
            directory_path: Path to the directory
            recursive: Whether to process subdirectories
        """
        print(f"Processing directory: {directory_path}, recursive: {recursive}")
        logging.info(f"Processing directory: {directory_path}, recursive: {recursive}")
        
        file_list = []
        
        print("Discovering files...")
        # First, discover all files
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                # Skip files that can't be read or don't exist
                if not os.path.exists(file_path) or not os.access(file_path, os.R_OK):
                    continue
                    
                file_list.append({
                    "path": file_path,
                    "object_id": uuid.uuid4()  # Note: In a real system, would look up the existing object ID
                })
                
            if not recursive:
                break
        
        print(f"Found {len(file_list)} files. Beginning checksum computation...")
        self.batch_process_files(file_list)
        
    def upload_to_database(self, db_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Upload the processed checksum data to the database.
        
        Args:
            db_config: Optional database configuration
        """
        # This would be implemented to connect to ArangoDB and upload the data
        # For now, we just have a placeholder since DB integration requires specific configuration
        logging.info("Database upload functionality not yet implemented")
        logging.info(f"Data ready for upload at: {self.output_file}")


def main():
    """Main entry point for the checksum recorder."""
    parser = argparse.ArgumentParser(description="Indaleko Multi-Checksum Recorder")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Subparser for processing a single file
    parser_file = subparsers.add_parser("file", help="Process a single file")
    parser_file.add_argument("path", help="Path to the file")
    parser_file.add_argument("--id", help="Object ID (if not provided, will generate a new UUID)")
    
    # Subparser for processing a directory
    parser_dir = subparsers.add_parser("directory", help="Process all files in a directory")
    parser_dir.add_argument("path", help="Path to the directory")
    parser_dir.add_argument("--recursive", action="store_true", help="Process subdirectories")
    
    # Subparser for batch processing
    parser_batch = subparsers.add_parser("batch", help="Process a batch of files from a JSON file")
    parser_batch.add_argument("file", help="Path to JSON file with file information")
    
    # Subparser for uploading to database
    parser_upload = subparsers.add_parser("upload", help="Upload processed data to the database")
    parser_upload.add_argument("--config", help="Path to database configuration file")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Create recorder
    recorder = ChecksumRecorder()
    
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
        recorder.process_directory(args.path, args.recursive)
        
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