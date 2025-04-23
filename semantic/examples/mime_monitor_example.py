"""
Example demonstrating performance monitoring with the MIME type detector.

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
import uuid
from typing import Any

# Import path setup
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position

from semantic.collectors.mime.mime_collector import IndalekoSemanticMimeType
from semantic.performance_monitor import (
    SemanticExtractorPerformance,
    monitor_semantic_extraction,
)

# pylint: enable=wrong-import-position


class MonitoredMimeDetector:
    """MIME detector with integrated performance monitoring."""

    def __init__(self):
        """Initialize the monitored MIME detector."""
        self.mime_detector = IndalekoSemanticMimeType()
        self.monitor = SemanticExtractorPerformance()
        self._provider_id = uuid.UUID("f9a1b2c3-d4e5-4f6a-8b7c-9d0e1f2a3b4c")

    @monitor_semantic_extraction(extractor_name="MonitoredMimeDetector.detect")
    def detect_mime_type(self, file_path: str) -> dict[str, Any]:
        """
        Detect MIME type with performance monitoring.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with MIME type information
        """
        return self.mime_detector.detect_mime_type(file_path)

    def process_directory(
        self, directory: str, recursive: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Process all files in a directory.

        Args:
            directory: Directory to process
            recursive: Whether to process subdirectories

        Returns:
            List of results with MIME type information
        """
        results = []

        # Start monitoring the batch operation
        batch_context = self.monitor.start_monitoring(
            extractor_name="MonitoredMimeDetector.batch", file_path=directory,
        )

        try:
            # Get list of files
            if recursive:
                files = []
                for root, _, filenames in os.walk(directory):
                    for filename in filenames:
                        files.append(os.path.join(root, filename))
            else:
                files = [
                    os.path.join(directory, f)
                    for f in os.listdir(directory)
                    if os.path.isfile(os.path.join(directory, f))
                ]

            # Process each file
            for file_path in files:
                try:
                    # Skip if not accessible
                    if not os.access(file_path, os.R_OK):
                        logging.warning(f"File not accessible: {file_path}")
                        continue

                    # Detect MIME type
                    mime_info = self.detect_mime_type(file_path)

                    # Add file path to result
                    mime_info["file_path"] = file_path

                    # Add to results
                    results.append(mime_info)

                except Exception as e:
                    logging.exception(f"Error processing {file_path}: {e}")

            # Stop monitoring with success
            self.monitor.stop_monitoring(
                batch_context,
                success=True,
                additional_data={
                    "files_processed": len(files),
                    "successful_detections": len(results),
                },
            )

            return results

        except Exception as e:
            logging.exception(f"Error processing directory {directory}: {e}")

            # Stop monitoring with failure
            self.monitor.stop_monitoring(batch_context, success=False)

            return results

    def get_performance_stats(self) -> dict[str, Any]:
        """
        Get performance statistics.

        Returns:
            Dictionary with performance statistics
        """
        return self.monitor.get_stats()


def main():
    """Main entry point for the example."""
    parser = argparse.ArgumentParser(
        description="MIME Type Detector with Performance Monitoring",
    )

    parser.add_argument("--dir", type=str, required=True, help="Directory to process")
    parser.add_argument(
        "--recursive", action="store_true", help="Process subdirectories",
    )
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")
    parser.add_argument("--output", type=str, help="Output file for results")
    parser.add_argument("--stats", action="store_true", help="Print performance stats")

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create detector
    detector = MonitoredMimeDetector()

    # Process directory
    print(f"Processing directory: {args.dir}")
    start_time = time.time()
    results = detector.process_directory(args.dir, args.recursive)
    end_time = time.time()

    # Print results summary
    print(f"Processed {len(results)} files in {end_time - start_time:.2f} seconds")

    # Print file type statistics
    mime_counts = {}
    for result in results:
        mime_type = result["mime_type"]
        mime_counts[mime_type] = mime_counts.get(mime_type, 0) + 1

    print("\nMIME Type Distribution:")
    for mime_type, count in sorted(
        mime_counts.items(), key=lambda x: x[1], reverse=True,
    ):
        print(f"  {mime_type}: {count} files")

    # Print performance stats if requested
    if args.stats:
        stats = detector.get_performance_stats()
        print("\nPerformance Statistics:")
        print(f"  Total Files: {stats['total_files']}")
        print(f"  Total Processing Time: {stats['total_processing_time']:.2f} seconds")

        if stats["total_files"] > 0:
            print(
                f"  Average Time per File: {stats['avg_processing_time']:.4f} seconds",
            )
            print(f"  Files per Second: {stats['files_per_second']:.2f}")
            print(f"  MB per Second: {stats['bytes_per_second'] / (1024*1024):.2f}")

        print("\nFile Type Statistics:")
        for mime_type, type_stats in stats.get("file_type_stats", {}).items():
            if type_stats["count"] > 0:
                avg_time = type_stats["total_time"] / type_stats["count"]
                print(
                    f"  {mime_type}: {type_stats['count']} files, {avg_time:.4f} seconds avg",
                )

    # Write results to file if requested
    if args.output:
        import json

        with open(args.output, "w") as f:
            json.dump(
                {"results": results, "stats": detector.get_performance_stats()},
                f,
                indent=2,
            )
        print(f"\nResults written to {args.output}")


if __name__ == "__main__":
    main()
