"""
Simple test script for the Indaleko MIME type detector.

This script demonstrates the use of the MIME type detector without depending
on the registration services.

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

from pathlib import Path


# Setup proper environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import Indaleko components
from semantic.collectors.mime.mime_collector import IndalekoSemanticMimeType


def process_file(file_path) -> None:
    """Process a single file and show its MIME type."""
    collector = IndalekoSemanticMimeType()
    try:
        result = collector.detect_mime_type(file_path)

        if result.get("encoding"):
            pass

        if result.get("additional_metadata"):
            for _key, _value in result["additional_metadata"].items():
                pass

        # Show category classification
        if "type_category" in result:
            pass

    except Exception:
        pass


def process_directory(directory_path, recursive=False, extensions=None) -> None:
    """Process all files in a directory, optionally filtering by extension."""
    collector = IndalekoSemanticMimeType()
    path = Path(directory_path)

    if not path.exists() or not path.is_dir():
        return

    # Filter by extensions if provided
    if extensions:
        extensions = [ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions]

    # Define the glob pattern based on recursion
    glob_pattern = "**/*" if recursive else "*"

    # Count processed files
    total_files = 0
    mime_types = {}

    # Process files
    for file_path in path.glob(glob_pattern):
        if file_path.is_file():
            # Filter by extension if required
            if extensions and file_path.suffix.lower() not in extensions:
                continue

            try:
                result = collector.detect_mime_type(str(file_path))
                mime_type = result["mime_type"]

                # Count MIME types
                mime_types[mime_type] = mime_types.get(mime_type, 0) + 1
                total_files += 1

                # Print progress for every 10 files
                if total_files % 10 == 0:
                    pass

            except Exception:
                pass

    # Print summary
    for mime_type, count in sorted(
        mime_types.items(),
        key=lambda x: x[1],
        reverse=True,
    ):
        (count / total_files) * 100 if total_files > 0 else 0


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Indaleko MIME Type Detector")

    # Create subparsers for file and directory commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # File command
    file_parser = subparsers.add_parser("file", help="Process a single file")
    file_parser.add_argument("file_path", help="Path to the file to process")

    # Directory command
    dir_parser = subparsers.add_parser(
        "directory",
        help="Process all files in a directory",
    )
    dir_parser.add_argument("directory_path", help="Path to the directory to process")
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
        help="Filter by file extensions (e.g., .jpg .png)",
    )

    # Debug mode
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    # Check for required command
    if not args.command:
        parser.print_help()
        return

    # Process based on command
    if args.command == "file":
        process_file(args.file_path)
    elif args.command == "directory":
        process_directory(args.directory_path, args.recursive, args.extensions)


if __name__ == "__main__":
    main()
