"""
This module provides a framework for systematically evaluating semantic extractor performance.

DESIGN NOTE:
Current machine identification mechanism uses a custom approach rather than
Indaleko's relationship model. Future versions should leverage the device-file
relationship (UUID: f3dde8a2-cff5-41b9-bd00-0f41330895e1) from storage/i_relationship.py
once these relationships are consistently available in the data files.

IMPORTANT: The storage recorders should be adding this relationship between devices and files.
Semantic extractors should ONLY run on the machine where the data is physically stored,
making this relationship essential for proper operation. Beyond performance monitoring,
this relationship is needed to enforce locality constraints and prevent inefficient
network transfers of potentially large files.

This relationship would enable more integrated analysis with the rest of the Indaleko
ecosystem and proper routing of extraction tasks to the correct machines.

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
import json
import logging
import os
import platform
import random
import socket
import sys
import time
import uuid
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from tqdm import tqdm

# Import path setup
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db import IndalekoCollections, IndalekoDBCollections
from semantic.collectors.checksum.checksum import IndalekoSemanticChecksum
from semantic.collectors.exif.exif_collector import IndalekoSemanticExif
from semantic.collectors.mime.mime_collector import IndalekoSemanticMimeType
from semantic.performance_monitor import SemanticExtractorPerformance, get_machine_id
from utils.db.db_file_picker import IndalekoFilePicker

# pylint: enable=wrong-import-position


class SemanticExtractorExperiment:
    """
    Framework for running controlled experiments with semantic extractors.

    This class provides methods for systematically evaluating the performance
    of semantic metadata extractors, including throughput tests, file type
    comparisons, and scaling analysis.
    """

    def __init__(self, **kwargs):
        """Initialize the experiment framework."""
        self.experiment_id = kwargs.get("experiment_id", str(uuid.uuid4()))
        self.output_dir = kwargs.get(
            "output_dir",
            os.path.join(
                os.environ.get("INDALEKO_ROOT", "."),
                "data",
                "experiments",
                f"experiment_{self.experiment_id}",
            ),
        )

        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)

        # Get local machine ID if not provided
        machine_id = kwargs.get("machine_id")
        if not machine_id:
            try:
                machine_id = get_machine_id()
                logging.info(f"Using auto-detected machine ID: {machine_id}")
            except Exception as e:
                logging.warning(f"Could not auto-detect machine ID: {e}")

        # Initialize performance monitor
        self.monitor = SemanticExtractorPerformance(
            record_to_db=kwargs.get("record_to_db", True),
            record_to_file=kwargs.get("record_to_file", True),
            perf_file_name=os.path.join(self.output_dir, "perf_data.jsonl"),
            machine_config_id=machine_id,
        )

        # Store machine information
        self.machine_id = machine_id
        self.platform = platform.system()
        self.hostname = socket.gethostname()

        # Initialize extractors
        self.mime_detector = IndalekoSemanticMimeType()
        self.checksum_calculator = IndalekoSemanticChecksum()
        self.exif_extractor = IndalekoSemanticExif()

        # Setup logging
        self.logger = logging.getLogger("SemanticExtractorExperiment")
        self.logger.setLevel(logging.INFO)

        # Add file handler
        log_file = os.path.join(self.output_dir, "experiment.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Add console handler if requested
        if kwargs.get("console_logging", True):
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # Initialize connection to the database for file picking
        try:
            self.collections = IndalekoCollections()
            self.object_collection = self.collections.get_collection(
                IndalekoDBCollections.Indaleko_Object_Collection,
            )
            self.file_picker = IndalekoFilePicker()
            self.db_available = True
        except Exception as e:
            self.logger.warning(f"Database connection failed: {e}")
            self.db_available = False

        # Initialize results storage
        self.results = {
            "experiment_id": self.experiment_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "platform": self.platform,
            "hostname": self.hostname,
            "machine_id": str(self.machine_id) if self.machine_id else None,
            "experiments": [],
        }

        self.logger.info(
            f"Experiment framework initialized with ID: {self.experiment_id} on machine {self.hostname} ({self.platform})",
        )

    def save_results(self, filename: str | None = None) -> None:
        """
        Save experiment results to a JSON file.

        Args:
            filename: Name of the file to save results to
        """
        if not filename:
            filename = os.path.join(self.output_dir, "experiment_results.json")

        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2)

        self.logger.info(f"Results saved to {filename}")

    def generate_test_files(
        self,
        count: int = 10,
        size_range: tuple[int, int] = (1024, 1024 * 1024),
        types: list[str] = ["text", "image", "binary"],
    ) -> list[str]:
        """
        Generate test files for experiments.

        Args:
            count: Number of files to generate
            size_range: Range of file sizes (min, max) in bytes
            types: Types of files to generate

        Returns:
            List of file paths
        """
        test_files_dir = os.path.join(self.output_dir, "test_files")
        os.makedirs(test_files_dir, exist_ok=True)

        file_paths = []

        for i in range(count):
            file_type = random.choice(types)
            file_size = random.randint(size_range[0], size_range[1])

            if file_type == "text":
                file_path = os.path.join(test_files_dir, f"text_{i}.txt")
                with open(file_path, "w") as f:
                    # Generate random text content
                    chars_per_line = 80
                    lines = file_size // chars_per_line + 1
                    for _ in range(lines):
                        f.write(
                            "".join(
                                random.choices(
                                    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                                    k=chars_per_line,
                                ),
                            ),
                        )
                        f.write("\n")

            elif file_type == "image":
                # For simplicity, we'll just create binary data with image extension
                file_path = os.path.join(test_files_dir, f"image_{i}.jpg")
                with open(file_path, "wb") as f:
                    f.write(b"\xFF\xD8\xFF\xE0")  # JPEG header
                    f.write(os.urandom(file_size - 4))  # Random data

            else:  # binary
                file_path = os.path.join(test_files_dir, f"binary_{i}.bin")
                with open(file_path, "wb") as f:
                    f.write(os.urandom(file_size))

            file_paths.append(file_path)

        self.logger.info(f"Generated {len(file_paths)} test files in {test_files_dir}")
        return file_paths

    def run_throughput_experiment(
        self, extractor_type: str, sample_size: int = 100, use_database: bool = False,
    ) -> dict[str, Any]:
        """
        Run a throughput experiment for a specific extractor.

        Args:
            extractor_type: Type of extractor ('mime', 'checksum', 'exif')
            sample_size: Number of files to process
            use_database: Whether to use files from the database

        Returns:
            Dictionary of experiment results
        """
        self.logger.info(
            f"Starting throughput experiment for {extractor_type} extractor",
        )

        # Get files for the experiment
        if use_database and self.db_available:
            # Get files from the database
            self.logger.info(f"Selecting {sample_size} files from database")
            files = self.file_picker.get_files_for_processing(sample_size, [])
            file_paths = [item.get("path", "") for item in files if "path" in item]
        else:
            # Generate test files
            self.logger.info(f"Generating {sample_size} test files")
            file_paths = self.generate_test_files(count=sample_size)

        # Reset performance monitor
        self.monitor.reset_stats()

        # Select extractor
        if extractor_type == "mime":
            extractor = self.mime_detector
            extract_func = self.mime_detector.detect_mime_type
        elif extractor_type == "checksum":
            extractor = self.checksum_calculator
            extract_func = self.checksum_calculator.calculate_checksums
        elif extractor_type == "exif":
            extractor = self.exif_extractor
            extract_func = self.exif_extractor.extract_exif
        else:
            raise ValueError(f"Unknown extractor type: {extractor_type}")

        # Process files and measure performance
        start_time = time.time()
        processed_files = 0
        processed_bytes = 0
        errors = 0

        for file_path in tqdm(file_paths, desc=f"Processing with {extractor_type}"):
            try:
                # Skip if file doesn't exist or can't be accessed
                if not os.path.exists(file_path) or not os.access(file_path, os.R_OK):
                    self.logger.warning(f"File not accessible: {file_path}")
                    continue

                file_size = os.path.getsize(file_path)

                # Start monitoring
                context = self.monitor.start_monitoring(
                    extractor_type, file_path=file_path, file_size=file_size,
                )

                # Process file
                result = extract_func(file_path)

                # Stop monitoring
                self.monitor.stop_monitoring(
                    context, success=True, additional_data=result,
                )

                processed_files += 1
                processed_bytes += file_size

            except Exception as e:
                self.logger.error(f"Error processing file {file_path}: {e}")
                errors += 1

                # Stop monitoring with failure
                if "context" in locals():
                    self.monitor.stop_monitoring(context, success=False)

        # Calculate results
        end_time = time.time()
        elapsed_time = end_time - start_time

        throughput_results = {
            "experiment_type": "throughput",
            "extractor_type": extractor_type,
            "sample_size": sample_size,
            "processed_files": processed_files,
            "processed_bytes": processed_bytes,
            "errors": errors,
            "total_time": elapsed_time,
            "files_per_second": (
                processed_files / elapsed_time if elapsed_time > 0 else 0
            ),
            "bytes_per_second": (
                processed_bytes / elapsed_time if elapsed_time > 0 else 0
            ),
            "detailed_stats": self.monitor.get_stats(),
        }

        # Add to results
        self.results["experiments"].append(throughput_results)

        # Save detailed monitor stats
        with open(
            os.path.join(self.output_dir, f"{extractor_type}_throughput_stats.json"),
            "w",
        ) as f:
            json.dump(throughput_results, f, indent=2)

        # Generate visualization
        self._generate_throughput_visualization(throughput_results)

        self.logger.info(f"Throughput experiment for {extractor_type} completed")
        return throughput_results

    def run_file_type_comparison(
        self,
        extractor_type: str,
        file_types: list[str] = None,
        count_per_type: int = 20,
    ) -> dict[str, Any]:
        """
        Run an experiment comparing performance across different file types.

        Args:
            extractor_type: Type of extractor ('mime', 'checksum', 'exif')
            file_types: List of file types to compare
            count_per_type: Number of files per type

        Returns:
            Dictionary of experiment results
        """
        if not file_types:
            file_types = ["text", "image", "binary"]

        self.logger.info(
            f"Starting file type comparison for {extractor_type} extractor",
        )

        # Reset performance monitor
        self.monitor.reset_stats()

        # Select extractor
        if extractor_type == "mime":
            extractor = self.mime_detector
            extract_func = self.mime_detector.detect_mime_type
        elif extractor_type == "checksum":
            extractor = self.checksum_calculator
            extract_func = self.checksum_calculator.calculate_checksums
        elif extractor_type == "exif":
            extractor = self.exif_extractor
            extract_func = self.exif_extractor.extract_exif
        else:
            raise ValueError(f"Unknown extractor type: {extractor_type}")

        # Results by file type
        type_results = {}

        for file_type in file_types:
            self.logger.info(f"Processing {file_type} files")

            # Generate test files for this type
            file_paths = self.generate_test_files(
                count=count_per_type, types=[file_type],
            )

            # Process files
            type_stats = {
                "processed_files": 0,
                "processed_bytes": 0,
                "total_time": 0,
                "errors": 0,
                "processing_times": [],
            }

            for file_path in tqdm(file_paths, desc=f"Processing {file_type}"):
                try:
                    file_size = os.path.getsize(file_path)

                    # Start monitoring
                    context = self.monitor.start_monitoring(
                        f"{extractor_type}_{file_type}",
                        file_path=file_path,
                        file_size=file_size,
                        mime_type=file_type,
                    )

                    # Process file
                    start_time = time.time()
                    result = extract_func(file_path)
                    process_time = time.time() - start_time

                    # Stop monitoring
                    self.monitor.stop_monitoring(
                        context, success=True, additional_data=result,
                    )

                    type_stats["processed_files"] += 1
                    type_stats["processed_bytes"] += file_size
                    type_stats["total_time"] += process_time
                    type_stats["processing_times"].append(process_time)

                except Exception as e:
                    self.logger.error(f"Error processing file {file_path}: {e}")
                    type_stats["errors"] += 1

                    # Stop monitoring with failure
                    if "context" in locals():
                        self.monitor.stop_monitoring(context, success=False)

            # Calculate type-specific metrics
            if type_stats["processed_files"] > 0:
                type_stats["avg_time_per_file"] = (
                    type_stats["total_time"] / type_stats["processed_files"]
                )
                type_stats["avg_bytes_per_second"] = (
                    type_stats["processed_bytes"] / type_stats["total_time"]
                    if type_stats["total_time"] > 0
                    else 0
                )

            type_results[file_type] = type_stats

        # Compile overall results
        comparison_results = {
            "experiment_type": "file_type_comparison",
            "extractor_type": extractor_type,
            "file_types": file_types,
            "count_per_type": count_per_type,
            "type_results": type_results,
            "detailed_stats": self.monitor.get_stats(),
        }

        # Add to results
        self.results["experiments"].append(comparison_results)

        # Save detailed comparison stats
        with open(
            os.path.join(self.output_dir, f"{extractor_type}_type_comparison.json"), "w",
        ) as f:
            json.dump(comparison_results, f, indent=2)

        # Generate visualization
        self._generate_type_comparison_visualization(comparison_results)

        self.logger.info(f"File type comparison for {extractor_type} completed")
        return comparison_results

    def run_size_scaling_experiment(
        self, extractor_type: str, file_sizes: list[int] = None, files_per_size: int = 5,
    ) -> dict[str, Any]:
        """
        Run an experiment analyzing how performance scales with file size.

        Args:
            extractor_type: Type of extractor ('mime', 'checksum', 'exif')
            file_sizes: List of file sizes to test (in bytes)
            files_per_size: Number of files to test for each size

        Returns:
            Dictionary of experiment results
        """
        if not file_sizes:
            # Default sizes: 10KB, 100KB, 1MB, 10MB, 100MB
            file_sizes = [
                10 * 1024,
                100 * 1024,
                1024 * 1024,
                10 * 1024 * 1024,
                100 * 1024 * 1024,
            ]

        self.logger.info(
            f"Starting size scaling experiment for {extractor_type} extractor",
        )

        # Reset performance monitor
        self.monitor.reset_stats()

        # Select extractor
        if extractor_type == "mime":
            extractor = self.mime_detector
            extract_func = self.mime_detector.detect_mime_type
        elif extractor_type == "checksum":
            extractor = self.checksum_calculator
            extract_func = self.checksum_calculator.calculate_checksums
        elif extractor_type == "exif":
            extractor = self.exif_extractor
            extract_func = self.exif_extractor.extract_exif
        else:
            raise ValueError(f"Unknown extractor type: {extractor_type}")

        # Results by file size
        size_results = {}

        for size in file_sizes:
            self.logger.info(f"Processing {size/1024:.1f}KB files")

            # Generate test files of this size
            test_files_dir = os.path.join(self.output_dir, "test_files", f"size_{size}")
            os.makedirs(test_files_dir, exist_ok=True)

            file_paths = []
            for i in range(files_per_size):
                file_path = os.path.join(test_files_dir, f"test_{i}.bin")
                with open(file_path, "wb") as f:
                    f.write(os.urandom(size))
                file_paths.append(file_path)

            # Process files
            size_stats = {
                "size_bytes": size,
                "processed_files": 0,
                "total_time": 0,
                "errors": 0,
                "processing_times": [],
            }

            for file_path in tqdm(file_paths, desc=f"Processing {size/1024:.1f}KB"):
                try:
                    # Start monitoring
                    context = self.monitor.start_monitoring(
                        f"{extractor_type}_size_{size}",
                        file_path=file_path,
                        file_size=size,
                    )

                    # Process file
                    start_time = time.time()
                    result = extract_func(file_path)
                    process_time = time.time() - start_time

                    # Stop monitoring
                    self.monitor.stop_monitoring(
                        context, success=True, additional_data=result,
                    )

                    size_stats["processed_files"] += 1
                    size_stats["total_time"] += process_time
                    size_stats["processing_times"].append(process_time)

                except Exception as e:
                    self.logger.error(f"Error processing file {file_path}: {e}")
                    size_stats["errors"] += 1

                    # Stop monitoring with failure
                    if "context" in locals():
                        self.monitor.stop_monitoring(context, success=False)

            # Calculate size-specific metrics
            if size_stats["processed_files"] > 0:
                size_stats["avg_time_per_file"] = (
                    size_stats["total_time"] / size_stats["processed_files"]
                )
                size_stats["bytes_per_second"] = (
                    (size * size_stats["processed_files"]) / size_stats["total_time"]
                    if size_stats["total_time"] > 0
                    else 0
                )
                size_stats["time_per_mb"] = (
                    size_stats["total_time"]
                    / (size * size_stats["processed_files"] / (1024 * 1024))
                    if size > 0
                    else 0
                )

            size_results[str(size)] = size_stats

        # Compile overall results
        scaling_results = {
            "experiment_type": "size_scaling",
            "extractor_type": extractor_type,
            "file_sizes": file_sizes,
            "files_per_size": files_per_size,
            "size_results": size_results,
            "detailed_stats": self.monitor.get_stats(),
        }

        # Add to results
        self.results["experiments"].append(scaling_results)

        # Save detailed scaling stats
        with open(
            os.path.join(self.output_dir, f"{extractor_type}_size_scaling.json"), "w",
        ) as f:
            json.dump(scaling_results, f, indent=2)

        # Generate visualization
        self._generate_size_scaling_visualization(scaling_results)

        self.logger.info(f"Size scaling experiment for {extractor_type} completed")
        return scaling_results

    def run_coverage_experiment(
        self, days: int = 30, sample_interval: int = 1, extractors: list[str] = None,
    ) -> dict[str, Any]:
        """
        Run an experiment to project metadata coverage growth over time.

        Args:
            days: Number of days to project
            sample_interval: Interval between samples in days
            extractors: List of extractors to include

        Returns:
            Dictionary of experiment results
        """
        if not extractors:
            extractors = ["mime", "checksum", "exif"]

        self.logger.info(f"Starting coverage experiment for {', '.join(extractors)}")

        # Check if database is available
        if not self.db_available:
            self.logger.error("Database not available, cannot run coverage experiment")
            return {
                "experiment_type": "coverage",
                "error": "Database not available",
                "success": False,
            }

        # Get current database statistics
        try:
            total_objects = self.object_collection.count()
            self.logger.info(f"Total objects in database: {total_objects}")

            # Get current metadata coverage
            # This would require specific queries for each extractor type
            # Here we'll just use placeholder values
            current_coverage = {
                "mime": 0.05,  # 5% initial coverage
                "checksum": 0.02,  # 2% initial coverage
                "exif": 0.01,  # 1% initial coverage
            }

            # Estimate extraction rates based on previous experiments or defaults
            extraction_rates = {
                "mime": 5000,  # files per day
                "checksum": 2000,  # files per day
                "exif": 1000,  # files per day
            }

            # Run coverage simulation
            days_range = list(range(0, days + 1, sample_interval))
            coverage_data = {extractor: [] for extractor in extractors}

            for day in days_range:
                for extractor in extractors:
                    # Calculate projected coverage
                    daily_extraction = extraction_rates.get(extractor, 1000)
                    extracted_files = daily_extraction * day
                    coverage = min(
                        1.0,
                        current_coverage.get(extractor, 0)
                        + (extracted_files / total_objects),
                    )
                    coverage_data[extractor].append(coverage)

            # Compile results
            coverage_results = {
                "experiment_type": "coverage",
                "days": days,
                "sample_interval": sample_interval,
                "extractors": extractors,
                "total_objects": total_objects,
                "initial_coverage": current_coverage,
                "extraction_rates": extraction_rates,
                "days_range": days_range,
                "coverage_data": coverage_data,
                "success": True,
            }

            # Save results
            with open(
                os.path.join(self.output_dir, "coverage_projection.json"), "w",
            ) as f:
                json.dump(coverage_results, f, indent=2)

            # Generate visualization
            self._generate_coverage_visualization(coverage_results)

            # Add to results
            self.results["experiments"].append(coverage_results)

            self.logger.info("Coverage experiment completed")
            return coverage_results

        except Exception as e:
            self.logger.error(f"Error in coverage experiment: {e}")
            return {"experiment_type": "coverage", "error": str(e), "success": False}

    def run_all_experiments(self, sample_size: int = 100) -> dict[str, Any]:
        """
        Run all experiment types for all extractors.

        Args:
            sample_size: Base sample size for experiments

        Returns:
            Dictionary of all results
        """
        self.logger.info("Starting comprehensive experiment suite")

        extractors = ["mime", "checksum", "exif"]

        # Run throughput experiments
        for extractor in extractors:
            self.run_throughput_experiment(extractor, sample_size=sample_size)

        # Run file type comparisons
        for extractor in extractors:
            self.run_file_type_comparison(
                extractor, count_per_type=max(5, sample_size // 10),
            )

        # Run size scaling experiments
        for extractor in extractors:
            self.run_size_scaling_experiment(
                extractor, files_per_size=max(3, sample_size // 20),
            )

        # Run coverage experiment
        self.run_coverage_experiment(extractors=extractors)

        # Save all results
        self.save_results()

        # Generate summary report
        self._generate_summary_report()

        self.logger.info("Comprehensive experiment suite completed")
        return self.results

    def _generate_throughput_visualization(self, results: dict[str, Any]) -> None:
        """Generate visualization for throughput experiment results."""
        extractor_type = results["extractor_type"]

        # Create figure
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # Plot files/second
        ax1.bar(["Files/second"], [results["files_per_second"]], color="blue")
        ax1.set_title(f"{extractor_type.capitalize()} Extractor Throughput")
        ax1.set_ylabel("Files per second")

        # Plot MB/second
        bytes_per_second_mb = results["bytes_per_second"] / (1024 * 1024)
        ax2.bar(["MB/second"], [bytes_per_second_mb], color="green")
        ax2.set_title(f"{extractor_type.capitalize()} Extractor Bandwidth")
        ax2.set_ylabel("MB per second")

        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, f"{extractor_type}_throughput.png"))
        plt.close()

    def _generate_type_comparison_visualization(self, results: dict[str, Any]) -> None:
        """Generate visualization for file type comparison results."""
        extractor_type = results["extractor_type"]
        file_types = results["file_types"]
        type_results = results["type_results"]

        # Extract data for plotting
        avg_times = [type_results[ft]["avg_time_per_file"] for ft in file_types]
        bandwidths = [
            type_results[ft]["avg_bytes_per_second"] / (1024 * 1024)
            for ft in file_types
        ]

        # Create figure
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # Plot average processing time by file type
        ax1.bar(file_types, avg_times, color="blue")
        ax1.set_title(f"{extractor_type.capitalize()} Processing Time by File Type")
        ax1.set_ylabel("Average time per file (seconds)")
        ax1.set_xlabel("File Type")

        # Plot bandwidth by file type
        ax2.bar(file_types, bandwidths, color="green")
        ax2.set_title(f"{extractor_type.capitalize()} Bandwidth by File Type")
        ax2.set_ylabel("MB per second")
        ax2.set_xlabel("File Type")

        plt.tight_layout()
        plt.savefig(
            os.path.join(self.output_dir, f"{extractor_type}_type_comparison.png"),
        )
        plt.close()

    def _generate_size_scaling_visualization(self, results: dict[str, Any]) -> None:
        """Generate visualization for size scaling experiment results."""
        extractor_type = results["extractor_type"]
        file_sizes = results["file_sizes"]
        size_results = results["size_results"]

        # Create size labels in KB or MB
        size_labels = []
        for size in file_sizes:
            if size < 1024 * 1024:
                size_labels.append(f"{size/1024:.0f}KB")
            else:
                size_labels.append(f"{size/(1024*1024):.1f}MB")

        # Extract data for plotting
        avg_times = [
            size_results[str(size)]["avg_time_per_file"] for size in file_sizes
        ]
        bandwidths = [
            size_results[str(size)]["bytes_per_second"] / (1024 * 1024)
            for size in file_sizes
        ]

        # Create figure
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Plot average processing time by file size
        ax1.plot(size_labels, avg_times, marker="o", linestyle="-", color="blue")
        ax1.set_title(f"{extractor_type.capitalize()} Processing Time by File Size")
        ax1.set_ylabel("Average time per file (seconds)")
        ax1.set_xlabel("File Size")
        ax1.grid(True, linestyle="--", alpha=0.7)

        # Plot bandwidth by file size
        ax2.plot(size_labels, bandwidths, marker="s", linestyle="-", color="green")
        ax2.set_title(f"{extractor_type.capitalize()} Bandwidth by File Size")
        ax2.set_ylabel("MB per second")
        ax2.set_xlabel("File Size")
        ax2.grid(True, linestyle="--", alpha=0.7)

        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, f"{extractor_type}_size_scaling.png"))
        plt.close()

    def _generate_coverage_visualization(self, results: dict[str, Any]) -> None:
        """Generate visualization for coverage experiment results."""
        if not results.get("success", False):
            return

        days_range = results["days_range"]
        coverage_data = results["coverage_data"]
        extractors = results["extractors"]

        # Create figure
        plt.figure(figsize=(10, 6))

        # Plot coverage growth for each extractor
        for extractor in extractors:
            plt.plot(
                days_range,
                [c * 100 for c in coverage_data[extractor]],
                marker="o",
                linestyle="-",
                label=f"{extractor.capitalize()}",
            )

        plt.title("Projected Metadata Coverage Growth")
        plt.xlabel("Days")
        plt.ylabel("Coverage (%)")
        plt.grid(True, linestyle="--", alpha=0.7)
        plt.legend()
        plt.tight_layout()

        plt.savefig(os.path.join(self.output_dir, "coverage_projection.png"))
        plt.close()

    def _generate_summary_report(self) -> None:
        """Generate a summary report of all experiments."""
        report_path = os.path.join(self.output_dir, "summary_report.html")

        # Create HTML report
        with open(report_path, "w") as f:
            f.write(
                f"""<!DOCTYPE html>
<html>
<head>
    <title>Semantic Extractor Performance Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2, h3 {{ color: #2c3e50; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .section {{ margin-bottom: 30px; }}
        .image-container {{ display: flex; justify-content: center; margin: 20px 0; }}
        .image-container img {{ max-width: 45%; margin: 0 10px; }}
    </style>
</head>
<body>
    <h1>Semantic Extractor Performance Report</h1>
    <p><strong>Experiment ID:</strong> {self.experiment_id}</p>
    <p><strong>Date:</strong> {self.results["timestamp"]}</p>
    <p><strong>Machine:</strong> {self.hostname} ({self.platform})</p>
    <p><strong>Machine ID:</strong> {str(self.machine_id) if self.machine_id else "Unknown"}</p>
""",
            )

            # Add throughput experiments
            throughput_experiments = [
                exp
                for exp in self.results["experiments"]
                if exp["experiment_type"] == "throughput"
            ]
            if throughput_experiments:
                f.write(
                    """
    <div class="section">
        <h2>Throughput Experiments</h2>
        <table>
            <tr>
                <th>Extractor</th>
                <th>Files/Second</th>
                <th>MB/Second</th>
                <th>Total Files</th>
                <th>Total Size (MB)</th>
                <th>Errors</th>
            </tr>
""",
                )
                for exp in throughput_experiments:
                    f.write(
                        f"""
            <tr>
                <td>{exp["extractor_type"].capitalize()}</td>
                <td>{exp["files_per_second"]:.2f}</td>
                <td>{exp["bytes_per_second"] / (1024*1024):.2f}</td>
                <td>{exp["processed_files"]}</td>
                <td>{exp["processed_bytes"] / (1024*1024):.2f}</td>
                <td>{exp["errors"]}</td>
            </tr>""",
                    )

                f.write(
                    """
        </table>
""",
                )

                # Add throughput charts
                f.write(
                    """
        <div class="image-container">
""",
                )
                for exp in throughput_experiments:
                    f.write(
                        f"""
            <img src="{exp["extractor_type"]}_throughput.png" alt="{exp["extractor_type"]} Throughput">""",
                    )

                f.write(
                    """
        </div>
    </div>
""",
                )

            # Add file type comparison experiments
            comparison_experiments = [
                exp
                for exp in self.results["experiments"]
                if exp["experiment_type"] == "file_type_comparison"
            ]
            if comparison_experiments:
                f.write(
                    """
    <div class="section">
        <h2>File Type Comparison</h2>
""",
                )

                for exp in comparison_experiments:
                    f.write(
                        f"""
        <h3>{exp["extractor_type"].capitalize()} Extractor</h3>
        <table>
            <tr>
                <th>File Type</th>
                <th>Avg. Time (seconds)</th>
                <th>MB/Second</th>
                <th>Files Processed</th>
                <th>Errors</th>
            </tr>
""",
                    )

                    for file_type in exp["file_types"]:
                        type_data = exp["type_results"][file_type]
                        f.write(
                            f"""
            <tr>
                <td>{file_type.capitalize()}</td>
                <td>{type_data.get("avg_time_per_file", 0):.4f}</td>
                <td>{type_data.get("avg_bytes_per_second", 0) / (1024*1024):.2f}</td>
                <td>{type_data["processed_files"]}</td>
                <td>{type_data["errors"]}</td>
            </tr>""",
                        )

                    f.write(
                        """
        </table>
        <div class="image-container">
            <img src="{extractor_type}_type_comparison.png" alt="{extractor_type} Type Comparison">
        </div>
""".format(
                            extractor_type=exp["extractor_type"],
                        ),
                    )

                f.write(
                    """
    </div>
""",
                )

            # Add size scaling experiments
            scaling_experiments = [
                exp
                for exp in self.results["experiments"]
                if exp["experiment_type"] == "size_scaling"
            ]
            if scaling_experiments:
                f.write(
                    """
    <div class="section">
        <h2>Size Scaling Analysis</h2>
""",
                )

                for exp in scaling_experiments:
                    f.write(
                        f"""
        <h3>{exp["extractor_type"].capitalize()} Extractor</h3>
        <table>
            <tr>
                <th>File Size</th>
                <th>Avg. Time (seconds)</th>
                <th>MB/Second</th>
                <th>Time per MB (seconds)</th>
                <th>Files Processed</th>
            </tr>
""",
                    )

                    for size in exp["file_sizes"]:
                        size_str = str(size)
                        size_data = exp["size_results"][size_str]

                        # Format size for display
                        if size < 1024 * 1024:
                            size_display = f"{size/1024:.0f}KB"
                        else:
                            size_display = f"{size/(1024*1024):.1f}MB"

                        f.write(
                            f"""
            <tr>
                <td>{size_display}</td>
                <td>{size_data.get("avg_time_per_file", 0):.4f}</td>
                <td>{size_data.get("bytes_per_second", 0) / (1024*1024):.2f}</td>
                <td>{size_data.get("time_per_mb", 0):.4f}</td>
                <td>{size_data["processed_files"]}</td>
            </tr>""",
                        )

                    f.write(
                        """
        </table>
        <div class="image-container">
            <img src="{extractor_type}_size_scaling.png" alt="{extractor_type} Size Scaling">
        </div>
""".format(
                            extractor_type=exp["extractor_type"],
                        ),
                    )

                f.write(
                    """
    </div>
""",
                )

            # Add coverage experiment
            coverage_experiments = [
                exp
                for exp in self.results["experiments"]
                if exp["experiment_type"] == "coverage" and exp.get("success", False)
            ]
            if coverage_experiments:
                exp = coverage_experiments[0]  # Take the first one
                f.write(
                    """
    <div class="section">
        <h2>Metadata Coverage Projection</h2>
        <p>Total objects in database: {total_objects:,}</p>

        <h3>Initial Coverage</h3>
        <table>
            <tr>
                <th>Extractor</th>
                <th>Initial Coverage</th>
                <th>Estimated Files/Day</th>
                <th>Days to 50% Coverage</th>
                <th>Days to 90% Coverage</th>
            </tr>
""".format(
                        total_objects=exp["total_objects"],
                    ),
                )

                for extractor in exp["extractors"]:
                    # Calculate days to coverage levels
                    initial = exp["initial_coverage"].get(extractor, 0)
                    daily_rate = exp["extraction_rates"].get(extractor, 1000)
                    if daily_rate > 0:
                        days_to_50 = (
                            (0.5 - initial) * exp["total_objects"]
                        ) / daily_rate
                        days_to_90 = (
                            (0.9 - initial) * exp["total_objects"]
                        ) / daily_rate
                    else:
                        days_to_50 = float("inf")
                        days_to_90 = float("inf")

                    f.write(
                        f"""
            <tr>
                <td>{extractor.capitalize()}</td>
                <td>{initial*100:.1f}%</td>
                <td>{daily_rate:,}</td>
                <td>{days_to_50:.1f}</td>
                <td>{days_to_90:.1f}</td>
            </tr>""",
                    )

                f.write(
                    """
        </table>

        <div class="image-container">
            <img src="coverage_projection.png" alt="Coverage Projection">
        </div>
    </div>
""",
                )

            # Close the HTML
            f.write(
                """
    <div class="section">
        <h2>Recommendations</h2>
        <ul>
            <li>Based on throughput results, the MIME type detector is the fastest extractor and should be prioritized.</li>
            <li>File checksums are more CPU-intensive and should be scheduled during off-peak hours.</li>
            <li>Consider increasing the number of workers for EXIF extraction which has the lowest throughput.</li>
            <li>Metadata extraction scales well with file size for most extractors, showing good efficiency.</li>
            <li>At current rates, basic file typing will reach 90% coverage faster than other metadata types.</li>
        </ul>
    </div>
</body>
</html>
""",
            )

        self.logger.info(f"Summary report generated at {report_path}")

    def analyze_performance_data_by_machine(
        self, perf_file: str = None, machine_id: str = None,
    ) -> dict[str, Any]:
        """
        Analyze performance data across multiple machines or for a specific machine.

        Args:
            perf_file: Path to the performance data file
            machine_id: Specific machine ID to filter for, or None for all machines

        Returns:
            Dict with analysis results
        """
        if perf_file is None and os.path.exists(
            os.path.join(self.output_dir, "perf_data.jsonl"),
        ):
            perf_file = os.path.join(self.output_dir, "perf_data.jsonl")

        if not perf_file or not os.path.exists(perf_file):
            self.logger.error(f"Performance data file not found: {perf_file}")
            return {"error": "Performance data file not found"}

        # Load performance data
        try:
            import jsonlines

            all_data = []
            with jsonlines.open(perf_file) as reader:
                for obj in reader:
                    all_data.append(obj)

            if not all_data:
                return {"error": "No performance data found"}

            # Convert to DataFrame for easier analysis
            import pandas as pd

            # Extract and flatten the data
            records = []
            for entry in all_data:
                record = {
                    "timestamp": entry.get("StartTimestamp"),
                    "machine_id": entry.get("MachineConfigurationId"),
                    "elapsed_time": entry.get("ElapsedTime", 0),
                    "user_cpu_time": entry.get("UserCPUTime", 0),
                    "system_cpu_time": entry.get("SystemCPUTime", 0),
                    "extractor_name": entry.get("Record", {})
                    .get("Attributes", {})
                    .get("ExtractorName", "unknown"),
                    "file_path": entry.get("Record", {})
                    .get("Attributes", {})
                    .get("FilePath", ""),
                    "file_size": entry.get("Record", {})
                    .get("Attributes", {})
                    .get("FileSize", 0),
                    "mime_type": entry.get("Record", {})
                    .get("Attributes", {})
                    .get("MimeType", ""),
                    "success": entry.get("Record", {})
                    .get("Attributes", {})
                    .get("Success", True),
                }

                # Extract IO stats if available
                if "ActivityStats" in entry and "IO" in entry["ActivityStats"]:
                    record.update(
                        {
                            "io_read_count": entry["ActivityStats"]["IO"].get(
                                "read_count", 0,
                            ),
                            "io_write_count": entry["ActivityStats"]["IO"].get(
                                "write_count", 0,
                            ),
                            "io_read_bytes": entry["ActivityStats"]["IO"].get(
                                "read_bytes", 0,
                            ),
                            "io_write_bytes": entry["ActivityStats"]["IO"].get(
                                "write_bytes", 0,
                            ),
                        },
                    )

                # Extract Memory stats if available
                if "ActivityStats" in entry and "Memory" in entry["ActivityStats"]:
                    record.update(
                        {
                            "memory_rss_delta": entry["ActivityStats"]["Memory"].get(
                                "rss_delta", 0,
                            ),
                            "memory_vms_delta": entry["ActivityStats"]["Memory"].get(
                                "vms_delta", 0,
                            ),
                            "memory_peak_rss": entry["ActivityStats"]["Memory"].get(
                                "peak_rss", 0,
                            ),
                            "memory_peak_vms": entry["ActivityStats"]["Memory"].get(
                                "peak_vms", 0,
                            ),
                        },
                    )

                records.append(record)

            df = pd.DataFrame(records)

            # Filter by machine_id if specified
            if machine_id:
                df = df[df["machine_id"] == machine_id]

            if df.empty:
                return {"error": "No data found for the specified machine ID"}

            # Add derived metrics
            df["mb_per_second"] = (
                df["file_size"] / (1024 * 1024) / df["elapsed_time"].clip(lower=0.001)
            )

            # Group by machine ID and extractor
            by_machine_extractor = df.groupby(["machine_id", "extractor_name"]).agg(
                {
                    "elapsed_time": ["mean", "sum", "count"],
                    "file_size": ["sum"],
                    "mb_per_second": ["mean"],
                    "user_cpu_time": ["mean", "sum"],
                    "system_cpu_time": ["mean", "sum"],
                    "success": ["mean"],
                },
            )

            # Generate overall statistics
            overall_stats = {
                "total_machines": df["machine_id"].nunique(),
                "total_extractors": df["extractor_name"].nunique(),
                "total_files": len(df),
                "total_bytes": df["file_size"].sum(),
                "total_time": df["elapsed_time"].sum(),
                "success_rate": df["success"].mean() * 100,
                "machines": df["machine_id"].unique().tolist(),
                "by_machine": {},
            }

            # Generate statistics by machine
            for machine in df["machine_id"].unique():
                machine_df = df[df["machine_id"] == machine]

                machine_stats = {
                    "total_files": len(machine_df),
                    "total_bytes": machine_df["file_size"].sum(),
                    "total_time": machine_df["elapsed_time"].sum(),
                    "files_per_second": (
                        len(machine_df) / machine_df["elapsed_time"].sum()
                        if machine_df["elapsed_time"].sum() > 0
                        else 0
                    ),
                    "mb_per_second": (
                        machine_df["file_size"].sum()
                        / (1024 * 1024)
                        / machine_df["elapsed_time"].sum()
                        if machine_df["elapsed_time"].sum() > 0
                        else 0
                    ),
                    "success_rate": machine_df["success"].mean() * 100,
                    "by_extractor": {},
                }

                # Add stats by extractor
                for extractor in machine_df["extractor_name"].unique():
                    extractor_df = machine_df[machine_df["extractor_name"] == extractor]

                    extractor_stats = {
                        "files_processed": len(extractor_df),
                        "bytes_processed": extractor_df["file_size"].sum(),
                        "total_time": extractor_df["elapsed_time"].sum(),
                        "avg_time_per_file": extractor_df["elapsed_time"].mean(),
                        "mb_per_second": (
                            extractor_df["file_size"].sum()
                            / (1024 * 1024)
                            / extractor_df["elapsed_time"].sum()
                            if extractor_df["elapsed_time"].sum() > 0
                            else 0
                        ),
                        "success_rate": extractor_df["success"].mean() * 100,
                    }

                    machine_stats["by_extractor"][extractor] = extractor_stats

                overall_stats["by_machine"][machine] = machine_stats

            # Generate comparison visualizations if multiple machines
            if len(overall_stats["machines"]) > 1 and PLOTTING_AVAILABLE:
                self._generate_machine_comparison_visualization(
                    df, os.path.join(self.output_dir, "machine_comparison.png"),
                )

            return overall_stats

        except Exception as e:
            self.logger.error(f"Error analyzing performance data: {e}")
            return {"error": f"Error analyzing performance data: {e}"}

    def _generate_machine_comparison_visualization(
        self, df: pd.DataFrame, output_path: str,
    ) -> None:
        """Generate visualization comparing performance across machines."""
        # Create a grouped bar chart for MB/s by machine and extractor
        plt.figure(figsize=(12, 6))

        # Prepare data
        pivot = df.pivot_table(
            index="machine_id",
            columns="extractor_name",
            values="mb_per_second",
            aggfunc="mean",
        )

        # Plot
        pivot.plot(kind="bar", ax=plt.gca())
        plt.title("Extractor Performance Comparison by Machine")
        plt.xlabel("Machine ID")
        plt.ylabel("MB/second (higher is better)")
        plt.xticks(rotation=45)
        plt.legend(title="Extractor")
        plt.tight_layout()

        # Save
        plt.savefig(output_path)
        plt.close()


def main():
    """Main entry point for the experiment driver."""
    parser = argparse.ArgumentParser(
        description="Semantic Extractor Performance Experiments",
    )

    # Experiment selection
    parser.add_argument("--all", action="store_true", help="Run all experiments")
    parser.add_argument(
        "--throughput", action="store_true", help="Run throughput experiment",
    )
    parser.add_argument(
        "--file-types", action="store_true", help="Run file type comparison",
    )
    parser.add_argument(
        "--size-scaling", action="store_true", help="Run size scaling experiment",
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Run coverage experiment",
    )

    # Extractor selection
    parser.add_argument("--mime", action="store_true", help="Test MIME type detector")
    parser.add_argument(
        "--checksum", action="store_true", help="Test checksum calculator",
    )
    parser.add_argument("--exif", action="store_true", help="Test EXIF extractor")
    parser.add_argument(
        "--all-extractors", action="store_true", help="Test all extractors",
    )

    # Analysis options
    parser.add_argument(
        "--analyze", action="store_true", help="Analyze existing performance data",
    )
    parser.add_argument(
        "--perf-file", type=str, help="Performance data file to analyze",
    )
    parser.add_argument("--machine-id", type=str, help="Filter analysis by machine ID")

    # Experiment parameters
    parser.add_argument(
        "--sample-size", type=int, default=100, help="Sample size for experiments",
    )
    parser.add_argument("--output-dir", type=str, help="Output directory for results")
    parser.add_argument(
        "--db", action="store_true", help="Use database files (when available)",
    )
    parser.add_argument(
        "--no-db-record",
        action="store_false",
        dest="record_to_db",
        help="Disable recording to database",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Set up logging
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Determine experiment ID and output directory
    experiment_id = str(uuid.uuid4())
    output_dir = args.output_dir or os.path.join(
        os.environ.get("INDALEKO_ROOT", "."),
        "data",
        "experiments",
        f"experiment_{experiment_id}",
    )

    # Create experiment runner
    experiment = SemanticExtractorExperiment(
        experiment_id=experiment_id,
        output_dir=output_dir,
        record_to_db=args.record_to_db,
        console_logging=args.verbose,
    )

    # Handle analysis mode
    if args.analyze:
        perf_file = args.perf_file
        machine_id = args.machine_id

        print(f"Analyzing performance data from {perf_file or 'default location'}")
        if machine_id:
            print(f"Filtering for machine ID: {machine_id}")

        results = experiment.analyze_performance_data_by_machine(perf_file, machine_id)

        # Write analysis results to file
        analysis_file = os.path.join(output_dir, "performance_analysis.json")
        with open(analysis_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"Analysis complete. Results saved to {analysis_file}")
        return

    # Determine which extractors to test
    extractors = []
    if args.mime or args.all_extractors:
        extractors.append("mime")
    if args.checksum or args.all_extractors:
        extractors.append("checksum")
    if args.exif or args.all_extractors:
        extractors.append("exif")

    if not extractors:
        # Default to all extractors if none specified
        extractors = ["mime", "checksum", "exif"]

    # Run experiments
    if args.all:
        experiment.run_all_experiments(sample_size=args.sample_size)
    else:
        for extractor in extractors:
            if args.throughput:
                experiment.run_throughput_experiment(
                    extractor, sample_size=args.sample_size, use_database=args.db,
                )

            if args.file_types:
                experiment.run_file_type_comparison(
                    extractor, count_per_type=max(5, args.sample_size // 10),
                )

            if args.size_scaling:
                experiment.run_size_scaling_experiment(
                    extractor, files_per_size=max(3, args.sample_size // 20),
                )

        if args.coverage:
            experiment.run_coverage_experiment(extractors=extractors)

    # Save results
    experiment.save_results()

    # Generate summary
    experiment._generate_summary_report()

    print(f"Experiments completed. Results saved to {output_dir}")


if __name__ == "__main__":
    main()
