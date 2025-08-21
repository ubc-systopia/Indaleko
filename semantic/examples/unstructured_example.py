#!/usr/bin/env python3
"""
Indaleko Project - Unstructured Processor Example.

This example demonstrates how to use the UnstructuredProcessor to extract
semantic data from PDF and other documents.

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
import os
import sys

from datetime import datetime


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from semantic.processors.unstructured_processor import UnstructuredProcessor


def example_process_pdf(pdf_path, skip_db=True):
    """
    Example of processing a single PDF file.

    Args:
        pdf_path (str): Path to a PDF file
        skip_db (bool): Whether to skip database connection
    """
    # Create processor with performance monitoring
    processor = UnstructuredProcessor(
        skip_db_connection=skip_db,
        enable_performance_monitoring=True,
    )

    # Process the PDF
    datetime.now()
    result = processor.process_pdf(pdf_path)
    datetime.now()

    # Display results

    # Display content summary
    content = result.get("content", {})
    if content:

        # Text summary
        text_count = len(content.get("text", []))
        if text_count > 0:
            pass

        # Tables and figures

        # Pages
        content.get("pages", {})

        # Languages
        content.get("metadata", {}).get("languages", [])

    # Display performance statistics
    perf_stats = result.get("performance", {})
    if perf_stats:

        # Operation details
        for _op_stats in perf_stats.get("operations", {}).values():
            pass

    return result


def example_process_directory(directory_path, skip_db=True):
    """
    Example of processing all documents in a directory.

    Args:
        directory_path (str): Path to a directory
        skip_db (bool): Whether to skip database connection
    """
    # Create processor with performance monitoring
    processor = UnstructuredProcessor(
        skip_db_connection=skip_db,
        enable_performance_monitoring=True,
        batch_size=5,  # Process files in small batches
    )

    # Process the directory, filtering for PDFs and DOCX files
    datetime.now()
    result = processor.process_directory(
        directory_path=directory_path,
        recursive=True,
        file_extensions=[".pdf", ".docx"],
        skip_larger_than_mb=20,  # Skip files larger than 20MB
    )
    datetime.now()

    # Display results

    # Display performance statistics
    perf_stats = result.get("performance", {})
    if perf_stats:
        pass

    return result


def compare_extractor_performance(directory_path, skip_db=True):
    """
    Run experiments to compare performance across different file types.

    Args:
        directory_path (str): Path to a directory with various file types
        skip_db (bool): Whether to skip database connection
    """
    # Create processor with performance monitoring
    processor = UnstructuredProcessor(
        skip_db_connection=skip_db,
        enable_performance_monitoring=True,
        batch_size=1,  # Process one file at a time for accurate measurements
    )

    # Group files by file extension
    file_groups = {}
    for root, _, files in os.walk(directory_path):
        for filename in files:
            _, ext = os.path.splitext(filename)
            ext = ext.lower()

            if ext in [".pdf", ".docx", ".xlsx", ".txt", ".md", ".html"]:
                file_path = os.path.join(root, filename)

                if ext not in file_groups:
                    file_groups[ext] = []

                # Only collect at most 5 files of each type
                if len(file_groups[ext]) < 5:
                    file_groups[ext].append(file_path)

    # Process each file type and collect performance data
    results = {}

    for ext, files in file_groups.items():
        if not files:
            continue


        # Reset performance stats before each file type
        processor._perf_monitor.reset_statistics()

        # Process files
        processor.process_files(files)

        # Collect performance statistics
        perf_stats = processor._perf_monitor.get_statistics()
        results[ext] = {
            "file_count": len(files),
            "total_time": perf_stats.get("total_elapsed_time", 0),
            "avg_time_per_file": perf_stats.get("total_elapsed_time", 0) / len(files),
            "avg_cpu": perf_stats.get("avg_cpu_percent", 0),
            "avg_memory": perf_stats.get("avg_memory_mb", 0),
            "operations": perf_stats.get("operations", {}),
        }

    # Display comparison results

    for ext, _stats in sorted(results.items()):
        pass

    return results


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="Unstructured Processor Example")
    parser.add_argument("--pdf", help="Path to a PDF file to process")
    parser.add_argument("--dir", help="Path to a directory to process")
    parser.add_argument(
        "--experiment",
        action="store_true",
        help="Run a performance experiment",
    )
    parser.add_argument(
        "--use-db",
        action="store_true",
        help="Connect to the database for storage",
    )

    args = parser.parse_args()

    if not (args.pdf or args.dir or args.experiment):
        parser.print_help()
        return

    if args.pdf:
        example_process_pdf(args.pdf, skip_db=not args.use_db)

    if args.dir:
        example_process_directory(args.dir, skip_db=not args.use_db)

    if args.experiment and args.dir:
        compare_extractor_performance(args.dir, skip_db=not args.use_db)


if __name__ == "__main__":
    main()
