#!/usr/bin/env python3
"""
Indaleko Project - Unstructured Semantic Processor

This module provides a unified interface for collecting and recording semantic
metadata using unstructured.io. It coordinates the collector and recorder
components and provides performance monitoring.

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
import mimetypes
import os
import pathlib
import sys
import time
import uuid
from datetime import UTC, datetime
from typing import Any

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from Indaleko import Indaleko
from semantic.collectors.unstructured.data_models.input import (
    UnstructuredInputDataModel,
)
from semantic.collectors.unstructured.unstructured_collector import (
    UnstructuredCollector,
)
from semantic.performance_monitor import (
    SemanticExtractorPerformance,
    monitor_semantic_extraction,
)
from semantic.recorders.unstructured.unstructured_recorder import UnstructuredRecorder


class UnstructuredProcessor:
    """
    Unified processor for semantic metadata extraction using unstructured.io.

    This class coordinates the collector and recorder components, providing
    a simplified interface for collecting and recording semantic metadata.
    """

    def __init__(self, **kwargs):
        """
        Initialize the UnstructuredProcessor.

        Args:
            max_file_size_mb (int, optional): Maximum file size in MB to process
            batch_size (int, optional): Number of files to process in each batch
            docker_memory (str, optional): Memory limit for Docker container (e.g., "8g")
            skip_docker_pull (bool, optional): Skip pulling Docker image (for offline use)
            collection_name (str, optional): Name of the collection to store data in
            skip_db_connection (bool, optional): Skip database connection
            enable_performance_monitoring (bool, optional): Enable performance monitoring
            db_config (IndalekoDBConfig, optional): Database configuration
        """
        # Set up logging
        self._logger = logging.getLogger(f"{self.__class__.__name__}")
        self._logger.setLevel(logging.INFO)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)

            # Add file handler
            log_dir = os.path.join(Indaleko.default_data_dir, "logs")
            os.makedirs(log_dir, exist_ok=True)
            file_handler = logging.FileHandler(
                os.path.join(
                    log_dir,
                    f"unstructured_processor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
                ),
            )
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

        # Initialize performance monitoring
        self._perf_monitor = SemanticExtractorPerformance()
        self._enable_monitoring = kwargs.get("enable_performance_monitoring", True)
        if self._enable_monitoring:
            self._perf_monitor.enable()

        # Initialize collector
        self._collector = UnstructuredCollector(
            batch_size=kwargs.get("batch_size", 20),
            max_file_size_mb=kwargs.get("max_file_size_mb", 50),
            skip_docker_pull=kwargs.get("skip_docker_pull", False),
            docker_memory=kwargs.get("docker_memory", "8g"),
            enable_performance_monitoring=self._enable_monitoring,
        )

        # Initialize recorder
        self._recorder = UnstructuredRecorder(
            collector=self._collector,
            collection_name=kwargs.get("collection_name", "SemanticContent"),
            skip_db_connection=kwargs.get("skip_db_connection", False),
            db_config=kwargs.get("db_config"),
            enable_performance_monitoring=self._enable_monitoring,
        )

        self._logger.info("UnstructuredProcessor initialized")

    @monitor_semantic_extraction(
        extractor_name="UnstructuredProcessor.process_directory",
    )
    def process_directory(
        self,
        directory_path: str,
        recursive: bool = True,
        file_extensions: list[str] | None = None,
        skip_larger_than_mb: int | None = None,
    ) -> dict[str, Any]:
        """
        Process all files in a directory.

        Args:
            directory_path: Path to the directory to process
            recursive: Whether to process subdirectories recursively
            file_extensions: List of file extensions to process (e.g., [".pdf", ".docx"])
            skip_larger_than_mb: Skip files larger than this size in MB (overrides collector setting)

        Returns:
            Dict[str, Any]: Result statistics
        """
        self._logger.info(
            f"Processing directory: {directory_path} (recursive={recursive})",
        )

        # Check if directory exists
        if not os.path.isdir(directory_path):
            self._logger.error(f"Directory not found: {directory_path}")
            return {"error": "Directory not found", "path": directory_path}

        # Normalize file extensions
        if file_extensions:
            file_extensions = [ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in file_extensions]

        # Find files
        start_time = time.time()
        files = self._find_files(
            directory_path,
            recursive,
            file_extensions,
            skip_larger_than_mb,
        )

        if not files:
            self._logger.warning(f"No suitable files found in {directory_path}")
            return {"status": "no_files", "directory": directory_path, "files_found": 0}

        self._logger.info(f"Found {len(files)} files to process")

        # Create input models
        input_models = [
            UnstructuredInputDataModel(
                ObjectIdentifier=uuid.uuid4(),
                LocalPath=file_path,
                ModificationTimestamp=datetime.fromtimestamp(
                    os.path.getmtime(file_path),
                    UTC,
                ),
                Length=os.path.getsize(file_path),
                Checksum=None,  # We don't calculate checksum here for performance
            )
            for file_path in files
        ]

        # Collect data
        data = self._collector.collect_data(input_models)

        # Record data
        if data:
            success = self._recorder.store_data(data)
            status = "success" if success else "database_error"
        else:
            status = "collection_error"

        end_time = time.time()
        elapsed_time = end_time - start_time

        # Get performance statistics
        perf_stats = self._perf_monitor.get_statistics()

        result = {
            "status": status,
            "directory": directory_path,
            "files_found": len(files),
            "files_processed": len(data),
            "elapsed_time": elapsed_time,
            "performance": perf_stats,
        }

        self._logger.info(
            f"Directory processing complete: {result['status']} ({result['files_processed']}/{result['files_found']} files)",
        )

        return result

    @monitor_semantic_extraction(extractor_name="UnstructuredProcessor.process_files")
    def process_files(self, file_paths: list[str]) -> dict[str, Any]:
        """
        Process a specific list of files.

        Args:
            file_paths: List of file paths to process

        Returns:
            Dict[str, Any]: Result statistics
        """
        self._logger.info(f"Processing {len(file_paths)} files")

        # Filter valid files
        valid_files = [path for path in file_paths if os.path.isfile(path)]

        if not valid_files:
            self._logger.warning("No valid files found in the input list")
            return {"status": "no_files", "files_found": 0}

        self._logger.info(f"Found {len(valid_files)} valid files to process")

        # Create input models
        input_models = [
            UnstructuredInputDataModel(
                ObjectIdentifier=uuid.uuid4(),
                LocalPath=file_path,
                ModificationTimestamp=datetime.fromtimestamp(
                    os.path.getmtime(file_path),
                    UTC,
                ),
                Length=os.path.getsize(file_path),
                Checksum=None,  # We don't calculate checksum here for performance
            )
            for file_path in valid_files
        ]

        # Process data
        start_time = time.time()
        data = self._collector.collect_data(input_models)

        # Record data
        if data:
            success = self._recorder.store_data(data)
            status = "success" if success else "database_error"
        else:
            status = "collection_error"

        end_time = time.time()
        elapsed_time = end_time - start_time

        # Get performance statistics
        perf_stats = self._perf_monitor.get_statistics()

        result = {
            "status": status,
            "files_found": len(valid_files),
            "files_processed": len(data),
            "elapsed_time": elapsed_time,
            "performance": perf_stats,
        }

        self._logger.info(
            f"File processing complete: {result['status']} ({result['files_processed']}/{result['files_found']} files)",
        )

        return result

    @monitor_semantic_extraction(extractor_name="UnstructuredProcessor.process_pdf")
    def process_pdf(self, pdf_path: str) -> dict[str, Any]:
        """
        Process a single PDF file with optimized settings.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dict[str, Any]: Result statistics and extracted content
        """
        self._logger.info(f"Processing PDF file: {pdf_path}")

        # Check if file exists and is a PDF
        if not os.path.isfile(pdf_path):
            self._logger.error(f"File not found: {pdf_path}")
            return {"error": "File not found", "path": pdf_path}

        # Check MIME type
        mime_type, _ = mimetypes.guess_type(pdf_path)
        if mime_type != "application/pdf":
            self._logger.error(f"File is not a PDF: {pdf_path} (detected: {mime_type})")
            return {
                "error": "File is not a PDF",
                "path": pdf_path,
                "mime_type": mime_type,
            }

        # Create input model
        input_model = UnstructuredInputDataModel(
            ObjectIdentifier=uuid.uuid4(),
            LocalPath=pdf_path,
            ModificationTimestamp=datetime.fromtimestamp(
                os.path.getmtime(pdf_path),
                UTC,
            ),
            Length=os.path.getsize(pdf_path),
            Checksum=None,  # We don't calculate checksum here for performance
        )

        # Process data
        start_time = time.time()
        data = self._collector.collect_data([input_model])

        # Record data
        if data:
            success = self._recorder.store_data(data)
            status = "success" if success else "database_error"

            # Extract content for return
            content = self._extract_pdf_content(data[0])
        else:
            status = "collection_error"
            content = {}

        end_time = time.time()
        elapsed_time = end_time - start_time

        # Get performance statistics
        perf_stats = self._perf_monitor.get_statistics()

        result = {
            "status": status,
            "file": pdf_path,
            "object_id": str(input_model.ObjectIdentifier),
            "elapsed_time": elapsed_time,
            "content": content,
            "performance": perf_stats,
        }

        self._logger.info(f"PDF processing complete: {result['status']}")

        return result

    def _find_files(
        self,
        directory: str,
        recursive: bool,
        extensions: list[str] | None,
        max_size_mb: int | None,
    ) -> list[str]:
        """
        Find files in a directory.

        Args:
            directory: Directory to search
            recursive: Whether to search recursively
            extensions: List of file extensions to include
            max_size_mb: Maximum file size in MB

        Returns:
            List[str]: List of file paths
        """
        max_size_bytes = max_size_mb * 1024 * 1024 if max_size_mb else None
        if max_size_bytes is None and hasattr(self._collector, "_max_file_size_mb"):
            max_size_bytes = self._collector._max_file_size_mb * 1024 * 1024

        files = []

        try:
            if recursive:
                for root, _, filenames in os.walk(directory):
                    for filename in filenames:
                        file_path = os.path.join(root, filename)
                        if self._is_valid_file(file_path, extensions, max_size_bytes):
                            files.append(file_path)
            else:
                for item in os.listdir(directory):
                    file_path = os.path.join(directory, item)
                    if os.path.isfile(file_path) and self._is_valid_file(
                        file_path,
                        extensions,
                        max_size_bytes,
                    ):
                        files.append(file_path)
        except Exception as e:
            self._logger.error(f"Error finding files: {e!s}")

        return files

    def _is_valid_file(
        self,
        file_path: str,
        extensions: list[str] | None,
        max_size_bytes: int | None,
    ) -> bool:
        """
        Check if a file is valid for processing.

        Args:
            file_path: Path to the file
            extensions: List of valid extensions
            max_size_bytes: Maximum file size in bytes

        Returns:
            bool: True if the file is valid, False otherwise
        """
        try:
            # Check if the file exists
            if not os.path.isfile(file_path):
                return False

            # Check file extension
            if extensions:
                file_ext = pathlib.Path(file_path).suffix.lower()
                if file_ext not in extensions:
                    return False

            # Check file size
            if max_size_bytes:
                file_size = os.path.getsize(file_path)
                if file_size > max_size_bytes:
                    return False

            # Check MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type not in self._collector.SUPPORTED_FILE_TYPES:
                return False

            return True
        except Exception as e:
            self._logger.warning(f"Error checking file {file_path}: {e!s}")
            return False

    def _extract_pdf_content(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Extract and organize content from PDF data.

        Args:
            data: PDF data from collector

        Returns:
            Dict[str, Any]: Extracted content
        """
        result = {
            "title": None,
            "text": [],
            "tables": [],
            "figures": [],
            "pages": {},
            "metadata": {},
        }

        try:
            elements = data.get("Unstructured", [])

            # Extract text by type
            for element in elements:
                element_type = element.get("type")
                text = element.get("text", "")
                metadata = element.get("metadata", {})

                # Store metadata
                if element_type == "Title" and result["title"] is None:
                    result["title"] = text

                # Get page number
                page_number = metadata.get("page_number")
                if page_number is not None:
                    if page_number not in result["pages"]:
                        result["pages"][page_number] = []
                    result["pages"][page_number].append(text)

                # Categorize by type
                if element_type in ["Title", "NarrativeText", "Text", "Paragraph"]:
                    result["text"].append(text)
                elif element_type in ["Table"]:
                    result["tables"].append(text)
                elif element_type in ["Figure", "Image", "FigureCaption"]:
                    result["figures"].append(text)

            # Extract metadata
            first_element = elements[0] if elements else {}
            first_metadata = first_element.get("metadata", {})

            if first_metadata:
                result["metadata"] = {
                    "filetype": first_metadata.get("filetype"),
                    "languages": first_metadata.get("languages", []),
                    "last_modified": first_metadata.get("last_modified"),
                }

            # Clean up pages structure
            result["pages"] = dict(sorted(result["pages"].items()))

        except Exception as e:
            self._logger.error(f"Error extracting PDF content: {e!s}")

        return result

    def get_performance_statistics(self) -> dict[str, Any]:
        """
        Get performance statistics from the processor.

        Returns:
            Dict[str, Any]: Performance statistics
        """
        return self._perf_monitor.get_statistics()

    def get_collector(self) -> UnstructuredCollector:
        """
        Get the collector instance.

        Returns:
            UnstructuredCollector: Collector instance
        """
        return self._collector

    def get_recorder(self) -> UnstructuredRecorder:
        """
        Get the recorder instance.

        Returns:
            UnstructuredRecorder: Recorder instance
        """
        return self._recorder


def main():
    """Main function for testing the UnstructuredProcessor."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Indaleko Unstructured Semantic Processor",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Directory command
    dir_parser = subparsers.add_parser("dir", help="Process files in a directory")
    dir_parser.add_argument("path", help="Directory path to process")
    dir_parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Process subdirectories recursively",
    )
    dir_parser.add_argument(
        "--extensions",
        "-e",
        nargs="+",
        help="File extensions to process (e.g., pdf docx)",
    )
    dir_parser.add_argument(
        "--max-size",
        "-m",
        type=int,
        help="Skip files larger than this size in MB",
    )
    dir_parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Skip database connection",
    )

    # Files command
    files_parser = subparsers.add_parser("files", help="Process specific files")
    files_parser.add_argument("files", nargs="+", help="File paths to process")
    files_parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Skip database connection",
    )

    # PDF command
    pdf_parser = subparsers.add_parser("pdf", help="Process a single PDF file")
    pdf_parser.add_argument("file", help="PDF file path to process")
    pdf_parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Skip database connection",
    )
    pdf_parser.add_argument(
        "--output",
        "-o",
        help="Output JSON file for extracted content",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Create processor
    processor = UnstructuredProcessor(
        skip_db_connection=args.skip_db if hasattr(args, "skip_db") else False,
        enable_performance_monitoring=True,
    )

    # Process command
    if args.command == "dir":
        result = processor.process_directory(
            directory_path=args.path,
            recursive=args.recursive,
            file_extensions=args.extensions,
            skip_larger_than_mb=args.max_size,
        )
    elif args.command == "files":
        result = processor.process_files(file_paths=args.files)
    elif args.command == "pdf":
        result = processor.process_pdf(pdf_path=args.file)

        # Write extracted content to output file if specified
        if hasattr(args, "output") and args.output and "content" in result:
            with open(args.output, "w") as f:
                json.dump(result["content"], f, indent=2)
            print(f"Extracted content written to {args.output}")

    # Print results
    if "performance" in result:
        performance = result.pop("performance")
        print(json.dumps(result, indent=2))
        print("\nPerformance statistics:")
        print(json.dumps(performance, indent=2))
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
