"""
Simple test script for the Indaleko Checksum Generator.

This script demonstrates the use of the checksum generator without depending
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
import time
from pathlib import Path

# Setup proper environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import Indaleko components
from semantic.collectors.checksum.checksum import compute_checksums


def format_bytes(size):
    """Format byte size to human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0 or unit == "TB":
            return f"{size:.2f} {unit}"
        size /= 1024.0


def process_file(file_path, verbose=False):
    """Process a single file and show its checksums."""
    try:
        # Get file size
        file_size = os.path.getsize(file_path)

        # Measure time for checksum calculation
        start_time = time.time()
        checksums = compute_checksums(file_path)
        end_time = time.time()

        elapsed_time = end_time - start_time

        print(f"\nChecksum Results for: {file_path}")
        print(f"File size: {format_bytes(file_size)}")
        print(f"Computation time: {elapsed_time:.3f} seconds")

        print("\nChecksums:")
        print(f"  MD5:     {checksums['MD5']}")
        print(f"  SHA1:    {checksums['SHA1']}")
        print(f"  SHA256:  {checksums['SHA256']}")

        if verbose:
            print(f"  SHA512:  {checksums['SHA512']}")
            print(f"  Dropbox: {checksums['Dropbox']}")

        # Calculate throughput
        if elapsed_time > 0:
            throughput = file_size / elapsed_time / 1024 / 1024  # MB/s
            print(f"\nProcessing throughput: {throughput:.2f} MB/s")

    except Exception as e:
        print(f"Error processing {file_path}: {e!s}")


def process_directory(directory_path, recursive=False, extensions=None, verbose=False):
    """Process all files in a directory, optionally filtering by extension."""
    path = Path(directory_path)

    if not path.exists() or not path.is_dir():
        print(f"Error: {directory_path} is not a valid directory")
        return

    # Filter by extensions if provided
    if extensions:
        extensions = [
            ext.lower() if ext.startswith(".") else f".{ext.lower()}"
            for ext in extensions
        ]
        print(f"Filtering by extensions: {', '.join(extensions)}")

    # Define the glob pattern based on recursion
    glob_pattern = "**/*" if recursive else "*"

    # Count processed files
    total_files = 0
    total_size = 0
    total_time = 0

    # Process files
    for file_path in path.glob(glob_pattern):
        if file_path.is_file():
            # Filter by extension if required
            if extensions and file_path.suffix.lower() not in extensions:
                continue

            try:
                file_size = os.path.getsize(str(file_path))

                # Skip empty files
                if file_size == 0:
                    continue

                # Measure time for checksum calculation
                start_time = time.time()
                compute_checksums(str(file_path))
                end_time = time.time()

                elapsed_time = end_time - start_time

                total_files += 1
                total_size += file_size
                total_time += elapsed_time

                # Print progress
                print(
                    f"Processing {total_files} files: {file_path.name} ({format_bytes(file_size)}) - {elapsed_time:.2f}s",
                    end="\r",
                )

            except Exception as e:
                print(f"\nError processing {file_path}: {e!s}")

    # Print summary
    print(f"\n\nProcessed {total_files} files in {directory_path}")
    print(f"Total data processed: {format_bytes(total_size)}")
    print(f"Total processing time: {total_time:.2f} seconds")

    if total_time > 0:
        avg_throughput = total_size / total_time / 1024 / 1024  # MB/s
        print(f"Average throughput: {avg_throughput:.2f} MB/s")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Indaleko Checksum Generator")

    # Create subparsers for file and directory commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # File command
    file_parser = subparsers.add_parser("file", help="Process a single file")
    file_parser.add_argument("file_path", help="Path to the file to process")
    file_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show all checksum types",
    )

    # Directory command
    dir_parser = subparsers.add_parser(
        "directory", help="Process all files in a directory",
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
    dir_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed information",
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
        process_file(args.file_path, args.verbose)
    elif args.command == "directory":
        process_directory(
            args.directory_path, args.recursive, args.extensions, args.verbose,
        )


if __name__ == "__main__":
    main()
