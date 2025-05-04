#!/usr/bin/env python3
"""
Test batch processing for the Indaleko assistant CLI.

This script creates a test batch file with sample queries and runs the assistant CLI
in batch mode to verify that cursor serialization works correctly.

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

import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))


def create_test_batch_file():
    """Create a test batch file with sample queries."""
    # Create a temporary file for the test batch
    fd, path = tempfile.mkstemp(suffix=".txt")

    # Sample queries
    queries = [
        "# Test batch file for Indaleko assistant CLI",
        "# Each line is processed as a separate query",
        "",
        "find all PDF files",
        "show me files modified in the last week",
        "list all files larger than 10MB",
        "find all documents with 'project' in the content",
        "show recent activities on files in the Documents folder",
        "find files with both 'report' and 'finance' in their name",
        "show me files I shared with someone else",
        "find files with location data from Seattle",
        "list files accessed between January and March",
    ]

    # Write queries to the file
    with os.fdopen(fd, "w") as f:
        for query in queries:
            f.write(f"{query}\n")

    return path


def run_batch_test(batch_file_path):
    """Run the assistant CLI in batch mode with the test batch file."""
    output_file = tempfile.mktemp(suffix=".json")

    # Build the command - using command string instead of list
    cmd = f"{sys.executable} -m query.assistants.cli --verbose --output {output_file} --summarize {batch_file_path}"

    print(f"Running: {cmd}")

    # Run the command with shell=True
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    # Capture output
    stdout, stderr = process.communicate()

    print("\nStandard Output:")
    print(stdout)

    if stderr:
        print("\nStandard Error:")
        print(stderr)

    # Check if output file was created and has content
    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        print(f"\nOutput file created successfully: {output_file}")
        print(f"File size: {os.path.getsize(output_file)} bytes")

        # Read the first 500 characters to verify content
        with open(output_file) as f:
            content = f.read(500)
            print("\nOutput file preview:")
            print(f"{content}...")
    else:
        print(f"\nOutput file empty or not created: {output_file}")

    return process.returncode


def main():
    """Main function."""
    print("Creating test batch file...")
    batch_file_path = create_test_batch_file()
    print(f"Test batch file created: {batch_file_path}")

    print("\nRunning batch test...")
    return_code = run_batch_test(batch_file_path)

    print(f"\nTest completed with return code: {return_code}")

    # Clean up
    os.unlink(batch_file_path)
    print(f"Cleaned up test batch file: {batch_file_path}")


if __name__ == "__main__":
    main()
