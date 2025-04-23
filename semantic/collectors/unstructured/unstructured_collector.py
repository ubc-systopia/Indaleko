#!/usr/bin/env python3
"""
Indaleko Project - Unstructured Semantic Collector

This module implements a semantic metadata collector using the unstructured.io library.
It extracts semantic content from various document types (PDF, DOCX, etc.) following
the Indaleko collector/recorder pattern and supports performance monitoring.

Note: Semantic extractors should only run on machines where data is physically
stored. Storage recorders should add device-file relationships (UUID:
f3dde8a2-cff5-41b9-bd00-0f41330895e1) between files and the machines
where they're stored.

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

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from Indaleko import Indaleko
from semantic.characteristics import SemanticDataCharacteristics
from semantic.collectors.semantic_collector import SemanticCollectorBase
from semantic.collectors.unstructured.data_models.embedded import (
    UnstructuredEmbeddedDataModel,
)
from semantic.collectors.unstructured.data_models.input import (
    UnstructuredInputDataModel,
)
from semantic.performance_monitor import (
    SemanticExtractorPerformance,
    monitor_semantic_extraction,
)
from utils.misc.string_similarity import fuzzy_string_match


class UnstructuredCollector(SemanticCollectorBase):
    """
    Collector for semantic metadata extraction using unstructured.io.

    This collector uses Docker to run the unstructured.io library, which can
    extract text and metadata from various document types. It follows the
    Indaleko collector pattern and integrates with the performance monitoring
    framework.
    """

    # Constants for the collector
    PROVIDER_ID = uuid.UUID("31764240-1397-4cd2-9c74-b332a0ff1b72")
    COLLECTOR_NAME = "Unstructured.io Semantic Collector"
    DESCRIPTION = "Extracts semantic content from documents using unstructured.io"

    # Docker configuration
    DOCKER_IMAGE = "downloads.unstructured.io/unstructured-io/unstructured"
    DOCKER_TAG = "latest"
    CONTAINER_BASE_NAME = "unstructured_io_latest"

    # Supported file types (MIME types)
    SUPPORTED_FILE_TYPES = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
        "application/msword",  # DOC
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # XLSX
        "application/vnd.ms-excel",  # XLS
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # PPTX
        "application/vnd.ms-powerpoint",  # PPT
        "text/plain",
        "text/html",
        "text/markdown",
        "application/rtf",
        "image/jpeg",
        "image/png",
    }

    # File size limits
    MAX_FILE_SIZE_MB = 50  # Skip files larger than this

    def __init__(self, **kwargs):
        """
        Initialize the UnstructuredCollector.

        Args:
            data_dir (str, optional): Directory for storing temporary files and outputs
            max_file_size_mb (int, optional): Maximum file size in MB to process
            batch_size (int, optional): Number of files to process in each batch
            docker_memory (str, optional): Memory limit for Docker container (e.g., "8g")
            provider_id (uuid.UUID, optional): Override the default provider ID
            collector_name (str, optional): Override the default collector name
            skip_docker_pull (bool, optional): Skip pulling Docker image (for offline use)
            enable_performance_monitoring (bool, optional): Enable performance monitoring
        """
        self._name = kwargs.get("collector_name", self.COLLECTOR_NAME)
        self._provider_id = kwargs.get("provider_id", self.PROVIDER_ID)
        self._description = self.DESCRIPTION

        # Configuration
        self._data_dir = kwargs.get("data_dir", Indaleko.default_data_dir)
        self._max_file_size_mb = kwargs.get("max_file_size_mb", self.MAX_FILE_SIZE_MB)
        self._batch_size = kwargs.get("batch_size", 20)
        self._docker_memory = kwargs.get("docker_memory", "8g")
        self._skip_docker_pull = kwargs.get("skip_docker_pull", False)

        # Performance monitoring
        self._perf_monitor = SemanticExtractorPerformance()
        self._enable_monitoring = kwargs.get("enable_performance_monitoring", True)
        if self._enable_monitoring:
            self._perf_monitor.enable()

        # Set up logging
        self._logger = logging.getLogger(f"{self.__class__.__name__}")
        self._logger.setLevel(logging.INFO)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)

            # Add file handler
            os.makedirs(os.path.join(self._data_dir, "logs"), exist_ok=True)
            file_handler = logging.FileHandler(
                os.path.join(self._data_dir, "logs", f"unstructured_collector_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
            )
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

        # Prepare working directories
        self._temp_dir = tempfile.mkdtemp(prefix="indaleko_unstructured_")
        self._input_dir = os.path.join(self._temp_dir, "input")
        self._output_dir = os.path.join(self._temp_dir, "output")
        self._script_dir = os.path.join(self._temp_dir, "scripts")

        os.makedirs(self._input_dir, exist_ok=True)
        os.makedirs(self._output_dir, exist_ok=True)
        os.makedirs(self._script_dir, exist_ok=True)

        self._processed_files = set()
        self._data = []

        # Docker checks
        if not self._skip_docker_pull:
            self._check_docker_available()

    def __del__(self):
        """Clean up temporary resources when the collector is destroyed."""
        try:
            if hasattr(self, '_temp_dir') and os.path.exists(self._temp_dir):
                shutil.rmtree(self._temp_dir)
        except Exception as e:
            if hasattr(self, '_logger'):
                self._logger.error(f"Error cleaning up temporary directory: {e}")

    def get_collector_characteristics(self) -> SemanticDataCharacteristics:
        """
        Get the characteristics of the collector.

        Returns:
            SemanticDataCharacteristics: Characteristics of the collector
        """
        characteristics = SemanticDataCharacteristics()
        characteristics.add_supported_file_types(self.SUPPORTED_FILE_TYPES)
        characteristics.set_name(self._name)
        characteristics.set_provider_id(self._provider_id)
        return characteristics

    def get_collector_name(self) -> str:
        """
        Get the name of the collector.

        Returns:
            str: Name of the collector
        """
        return self._name

    def get_provider_id(self) -> uuid.UUID:
        """
        Get the provider ID for the collector.

        Returns:
            uuid.UUID: Provider ID for the collector
        """
        return self._provider_id

    def get_description(self) -> str:
        """
        Get a description of the collector.

        Returns:
            str: Description of the collector
        """
        return self._description

    def get_data(self) -> List[Dict[str, Any]]:
        """
        Get the collected data.

        Returns:
            List[Dict[str, Any]]: Collected data
        """
        return self._data

    @monitor_semantic_extraction(extractor_name="UnstructuredCollector.collect_data")
    def collect_data(self, input_files: List[UnstructuredInputDataModel]) -> List[Dict[str, Any]]:
        """
        Collect semantic data from the specified files.

        Args:
            input_files: List of input file models to process

        Returns:
            List[Dict[str, Any]]: Collected data
        """
        self._logger.info(f"Collecting data from {len(input_files)} files")
        self._data = []

        # Filter files
        filtered_files = self._filter_files(input_files)
        if not filtered_files:
            self._logger.warning("No files to process after filtering")
            return []

        # Process files in batches
        for i in range(0, len(filtered_files), self._batch_size):
            batch = filtered_files[i:i + self._batch_size]
            self._logger.info(f"Processing batch {i//self._batch_size + 1} with {len(batch)} files")
            batch_data = self._process_batch(batch)
            self._data.extend(batch_data)

        self._logger.info(f"Collected data from {len(self._data)} files")
        return self._data

    @monitor_semantic_extraction(extractor_name="UnstructuredCollector.retrieve_data")
    def retrieve_data(self, data_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve specific data by ID.

        Args:
            data_id: ID of the data to retrieve

        Returns:
            Optional[Dict[str, Any]]: Retrieved data, or None if not found
        """
        for item in self._data:
            if str(item.get("ObjectIdentifier", "")) == data_id:
                return item
        return None

    def get_cursor(self) -> Any:
        """
        Get a cursor for the collected data.

        Returns:
            Any: Cursor for the collected data
        """
        return len(self._data)

    def cache_duration(self) -> int:
        """
        Get the cache duration for the collected data.

        Returns:
            int: Cache duration in seconds
        """
        return 3600  # 1 hour

    def get_json_schema(self) -> Dict[str, Any]:
        """
        Get the JSON schema for the collected data.

        Returns:
            Dict[str, Any]: JSON schema
        """
        return UnstructuredEmbeddedDataModel.model_json_schema()

    def process_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process raw collected data.

        Args:
            raw_data: Raw data to process

        Returns:
            List[Dict[str, Any]]: Processed data
        """
        return raw_data

    def store_data(self, data: List[Dict[str, Any]]) -> bool:
        """
        Store processed data.

        Args:
            data: Processed data to store

        Returns:
            bool: True if successful, False otherwise
        """
        # This method is usually implemented by the recorder
        return True

    @monitor_semantic_extraction(extractor_name="UnstructuredCollector._filter_files")
    def _filter_files(self, input_files: List[UnstructuredInputDataModel]) -> List[UnstructuredInputDataModel]:
        """
        Filter files based on type, size, and previous processing.

        Args:
            input_files: Files to filter

        Returns:
            List[UnstructuredInputDataModel]: Filtered files
        """
        filtered_files = []

        for file_model in input_files:
            # Skip previously processed files
            if str(file_model.ObjectIdentifier) in self._processed_files:
                self._logger.debug(f"Skipping previously processed file: {file_model.LocalPath}")
                continue

            # Check if file exists
            if not os.path.exists(file_model.LocalPath):
                self._logger.warning(f"File not found: {file_model.LocalPath}")
                continue

            # Check file size
            file_size_mb = file_model.Length / (1024 * 1024)
            if file_size_mb > self._max_file_size_mb:
                self._logger.warning(
                    f"Skipping file exceeding size limit ({file_size_mb:.2f} MB > {self._max_file_size_mb} MB): {file_model.LocalPath}",
                )
                continue

            # Determine file type
            mime_type = self._get_file_mime_type(file_model.LocalPath)
            if mime_type not in self.SUPPORTED_FILE_TYPES:
                self._logger.warning(f"Unsupported file type ({mime_type}): {file_model.LocalPath}")
                continue

            filtered_files.append(file_model)

        self._logger.info(f"Filtered {len(input_files)} files to {len(filtered_files)} for processing")
        return filtered_files

    def _get_file_mime_type(self, file_path: str) -> str:
        """
        Get the MIME type of a file.

        Args:
            file_path: Path to the file

        Returns:
            str: MIME type of the file
        """
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "application/octet-stream"

    @monitor_semantic_extraction(extractor_name="UnstructuredCollector._process_batch")
    def _process_batch(self, batch: List[UnstructuredInputDataModel]) -> List[Dict[str, Any]]:
        """
        Process a batch of files using unstructured.io via Docker.

        Args:
            batch: Batch of files to process

        Returns:
            List[Dict[str, Any]]: Processed data
        """
        # Create symbolic links to files in input directory
        self._prepare_input_directory(batch)

        # Create processing script
        script_path = self._create_processing_script()

        # Run Docker container
        batch_id = str(uuid.uuid4())[:8]
        container_name = f"{self.CONTAINER_BASE_NAME}_{batch_id}"
        output_prefix = f"output_{batch_id}"

        # Prepare volume mounts
        volumes = [
            {"host": self._input_dir, "container": "/app/input"},
            {"host": self._output_dir, "container": "/app/output"},
            {"host": self._script_dir, "container": "/app/scripts"},
            # Mount the Indaleko root directory to get the processor script
            {"host": os.environ.get("INDALEKO_ROOT"), "container": "/app/indaleko"},
        ]

        try:
            # Pull Docker image if needed
            if not self._skip_docker_pull and not self._check_image_exists():
                self._pull_docker_image()

            # Run Docker container
            success = self._run_docker_container(container_name, volumes, script_path, output_prefix)
            if not success:
                self._logger.error("Failed to process batch with Docker container")
                return []

            # Parse output data
            output_jsonl = os.path.join(self._output_dir, f"{output_prefix}.jsonl")
            if not os.path.exists(output_jsonl):
                self._logger.error(f"Output file not found: {output_jsonl}")
                return []

            # Read output data
            processed_data = self._parse_output_file(output_jsonl, batch)

            # Update processed files
            for file_model in batch:
                self._processed_files.add(str(file_model.ObjectIdentifier))

            return processed_data

        except Exception as e:
            self._logger.error(f"Error processing batch: {str(e)}", exc_info=True)
            return []

    def _prepare_input_directory(self, batch: List[UnstructuredInputDataModel]) -> None:
        """
        Prepare input directory by creating symbolic links to files.

        Args:
            batch: Batch of files to prepare
        """
        # Clear input directory
        for item in os.listdir(self._input_dir):
            os.remove(os.path.join(self._input_dir, item))

        # Create symbolic links
        for file_model in batch:
            try:
                source_path = os.path.abspath(file_model.LocalPath)
                filename = f"{file_model.ObjectIdentifier}_{os.path.basename(file_model.LocalPath)}"
                target_path = os.path.join(self._input_dir, filename)

                # On Windows, we may need to copy the file instead of symlink
                if os.name == "nt":
                    shutil.copy2(source_path, target_path)
                else:
                    os.symlink(source_path, target_path)

                self._logger.debug(f"Prepared input file: {filename}")
            except Exception as e:
                self._logger.error(f"Error preparing input file {file_model.LocalPath}: {str(e)}")

    def _create_processing_script(self) -> str:
        """
        Create a Python script to process files with unstructured.io.

        Returns:
            str: Path to the created script
        """
        script_content = """
import os
import sys
import json
import logging
from datetime import datetime
import glob
from unstructured.partition.auto import partition
from unstructured.staging.base import elements_to_json

# Configuration
INPUT_DIR = "/app/input"
OUTPUT_DIR = "/app/output"
OUTPUT_PREFIX = sys.argv[1] if len(sys.argv) > 1 else "output"

# Setup logging
log_file = os.path.join(OUTPUT_DIR, f"{OUTPUT_PREFIX}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("unstructured_processor")

def process_files():
    """Process all files in the input directory"""
    all_elements = []

    # Get all files in input directory
    input_files = glob.glob(os.path.join(INPUT_DIR, "*"))
    logger.info(f"Found {len(input_files)} files to process")

    for file_path in input_files:
        try:
            # Extract file UUID from filename
            filename = os.path.basename(file_path)
            file_uuid = filename.split("_")[0]

            # Partition the document and extract elements
            logger.info(f"Processing file: {filename}")
            elements = partition(filename=file_path)

            # Add file UUID to metadata
            for element in elements:
                if not hasattr(element, "metadata"):
                    element.metadata = {}
                element.metadata["file_uuid"] = file_uuid

            all_elements.extend(elements)
            logger.info(f"Extracted {len(elements)} elements from {filename}")
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {str(e)}")

    # Save the extracted elements to JSON and JSONL
    json_path = os.path.join(OUTPUT_DIR, f"{OUTPUT_PREFIX}.json")
    jsonl_path = os.path.join(OUTPUT_DIR, f"{OUTPUT_PREFIX}.jsonl")

    elements_to_json(all_elements, filename=json_path)
    logger.info(f"Saved JSON output to {json_path}")

    # Convert JSON to JSONL
    try:
        with open(json_path, "r") as json_file, open(jsonl_path, "w") as jsonl_file:
            data = json.load(json_file)
            for entry in data:
                jsonl_file.write(json.dumps(entry) + "\\n")
        logger.info(f"Converted JSON to JSONL: {jsonl_path}")
    except Exception as e:
        logger.error(f"Failed to convert JSON to JSONL: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting unstructured.io processing")
    process_files()
    logger.info("Finished processing")
"""

        script_path = os.path.join(self._script_dir, "process_files.py")
        with open(script_path, "w") as f:
            f.write(script_content)

        return script_path

    def _check_docker_available(self) -> bool:
        """
        Check if Docker is available.

        Returns:
            bool: True if Docker is available, False otherwise
        """
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                self._logger.error("Docker is not available. Please install Docker to use this collector.")
                return False
            return True
        except Exception as e:
            self._logger.error(f"Error checking Docker availability: {str(e)}")
            return False

    def _check_image_exists(self) -> bool:
        """
        Check if the Docker image exists locally.

        Returns:
            bool: True if the image exists, False otherwise
        """
        try:
            result = subprocess.run(
                ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
                capture_output=True,
                text=True,
                check=True,
            )
            images = result.stdout.splitlines()
            image_full_name = f"{self.DOCKER_IMAGE}:{self.DOCKER_TAG}"
            return image_full_name in images
        except Exception as e:
            self._logger.error(f"Error checking Docker image: {str(e)}")
            return False

    def _pull_docker_image(self) -> bool:
        """
        Pull the Docker image.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self._logger.info(f"Pulling Docker image {self.DOCKER_IMAGE}:{self.DOCKER_TAG}...")
            result = subprocess.run(
                ["docker", "pull", f"{self.DOCKER_IMAGE}:{self.DOCKER_TAG}"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                self._logger.error(f"Failed to pull Docker image: {result.stderr}")
                return False
            self._logger.info("Docker image pulled successfully")
            return True
        except Exception as e:
            self._logger.error(f"Error pulling Docker image: {str(e)}")
            return False

    def _run_docker_container(
        self,
        container_name: str,
        volumes: List[Dict[str, str]],
        script_path: str,
        output_prefix: str,
    ) -> bool:
        """
        Run the Docker container to process files.

        Args:
            container_name: Name for the Docker container
            volumes: List of volume mounts
            script_path: Path to the processing script
            output_prefix: Prefix for output files

        Returns:
            bool: True if successful, False otherwise
        """
        # Remove existing container if it exists
        try:
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception:
            pass

        # Prepare volume mount arguments
        volume_args = []
        for volume in volumes:
            volume_args.extend(["-v", f"{volume['host']}:{volume['container']}"])

        # Prepare container command
        command = [
            "docker", "run",
            "--rm",
            "--name", container_name,
            "--memory", self._docker_memory,
            *volume_args,
            f"{self.DOCKER_IMAGE}:{self.DOCKER_TAG}",
            "python", "/app/scripts/process_files.py", output_prefix,
        ]

        try:
            self._logger.info(f"Running Docker container: {container_name}")
            start_time = time.time()

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Process output in real-time
            stdout, stderr = process.communicate()

            end_time = time.time()
            elapsed_time = end_time - start_time

            if process.returncode != 0:
                self._logger.error(f"Docker container failed (return code {process.returncode}): {stderr}")
                return False

            self._logger.info(f"Docker container completed successfully in {elapsed_time:.2f} seconds")
            return True

        except Exception as e:
            self._logger.error(f"Error running Docker container: {str(e)}")
            return False

    def _parse_output_file(
        self,
        output_file: str,
        batch: List[UnstructuredInputDataModel],
    ) -> List[Dict[str, Any]]:
        """
        Parse the output file from unstructured.io.

        Args:
            output_file: Path to the output file
            batch: Batch of input files

        Returns:
            List[Dict[str, Any]]: Parsed data
        """
        # Create mapping of file UUIDs to input models
        file_map = {str(model.ObjectIdentifier): model for model in batch}

        # Group elements by file UUID
        file_elements = {}

        try:
            with open(output_file, "r") as f:
                for line in f:
                    try:
                        element = json.loads(line)
                        file_uuid = element.get("metadata", {}).get("file_uuid", "unknown")

                        if file_uuid not in file_elements:
                            file_elements[file_uuid] = []

                        file_elements[file_uuid].append(element)
                    except json.JSONDecodeError as e:
                        self._logger.warning(f"Error parsing output line: {str(e)}")

            # Create result objects
            results = []
            for file_uuid, elements in file_elements.items():
                if file_uuid in file_map:
                    input_model = file_map[file_uuid]
                    result = {
                        "ObjectIdentifier": str(input_model.ObjectIdentifier),
                        "LocalPath": input_model.LocalPath,
                        "ModificationTimestamp": input_model.ModificationTimestamp.isoformat(),
                        "Length": input_model.Length,
                        "Checksum": input_model.Checksum,
                        "Unstructured": elements,
                        "ExtractorName": self._name,
                        "ProcessedTimestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    results.append(result)

            self._logger.info(f"Parsed {len(results)} results from output file")
            return results

        except Exception as e:
            self._logger.error(f"Error parsing output file: {str(e)}")
            return []


def main():
    """Main function for testing the UnstructuredCollector."""
    import argparse

    parser = argparse.ArgumentParser(description="Indaleko Unstructured Semantic Collector")
    parser.add_argument("--dir", help="Directory containing files to process")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size for processing")
    parser.add_argument("--max-size", type=int, default=50, help="Maximum file size in MB")
    parser.add_argument("--no-pull", action="store_true", help="Skip Docker image pulling")
    parser.add_argument("--memory", default="8g", help="Docker container memory limit")

    args = parser.parse_args()

    if not args.dir:
        print("Error: Directory not specified. Use --dir to specify a directory.")
        return

    # Create collector
    collector = UnstructuredCollector(
        batch_size=args.batch_size,
        max_file_size_mb=args.max_size,
        skip_docker_pull=args.no_pull,
        docker_memory=args.memory,
        enable_performance_monitoring=True,
    )

    # Prepare input files
    input_files = []
    for root, _, files in os.walk(args.dir):
        for file in files:
            file_path = os.path.join(root, file)

            if not os.path.isfile(file_path):
                continue

            # Create input model
            input_model = UnstructuredInputDataModel(
                ObjectIdentifier=uuid.uuid4(),
                LocalPath=file_path,
                ModificationTimestamp=datetime.fromtimestamp(os.path.getmtime(file_path), timezone.utc),
                Length=os.path.getsize(file_path),
                Checksum=None,  # We don't calculate checksum for this test
            )

            input_files.append(input_model)

    print(f"Found {len(input_files)} files to process")

    # Collect data
    data = collector.collect_data(input_files)

    # Print results
    print(f"Processed {len(data)} files")
    print("Performance statistics:")
    print(json.dumps(collector._perf_monitor.get_statistics(), indent=2))

    # Write results to file
    output_file = os.path.join(os.getcwd(), "unstructured_output.json")
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Output written to {output_file}")


if __name__ == "__main__":
    main()
