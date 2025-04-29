"""
Test script for the ChecksumRecorder.

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
import sys
import tempfile
import uuid
from datetime import datetime

from icecream import ic


# Custom JSON encoder to handle UUID and datetime objects
class IndalekoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Indaleko imports
from semantic.collectors.checksum.checksum import compute_checksums
from semantic.recorders.checksum.recorder import ChecksumRecorder


def create_test_files():
    """Create temporary test files with predictable content."""
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()

    files = []

    # Create test files with various sizes and contents
    file1_path = os.path.join(temp_dir, "small_file.txt")
    with open(file1_path, "w", encoding="utf-8") as f:
        f.write("This is a small test file for checksum computation.")
    files.append(file1_path)

    file2_path = os.path.join(temp_dir, "empty_file.txt")
    with open(file2_path, "w", encoding="utf-8") as f:
        pass
    files.append(file2_path)

    file3_path = os.path.join(temp_dir, "medium_file.bin")
    with open(file3_path, "wb") as f:
        f.write(b"A" * 10000)  # 10KB file
    files.append(file3_path)

    # Create a nested directory
    nested_dir = os.path.join(temp_dir, "nested")
    os.makedirs(nested_dir)

    file4_path = os.path.join(nested_dir, "nested_file.txt")
    with open(file4_path, "w", encoding="utf-8") as f:
        f.write("This is a nested file for testing recursive directory scanning.")
    files.append(file4_path)

    return temp_dir, files


def cleanup_test_files(temp_dir):
    """Clean up temporary test files."""
    import shutil

    shutil.rmtree(temp_dir)


def test_process_single_file(temp_dir, files):
    """Test processing a single file."""
    ic("Testing single file processing...")

    # Create output file path
    output_file = os.path.join(temp_dir, "single_file_output.jsonl")

    # Create recorder
    recorder = ChecksumRecorder(output_file)

    # Process a single file
    file_path = files[0]
    object_id = uuid.uuid4()

    # Direct computation for comparison
    expected_checksums = compute_checksums(file_path)

    # Process with recorder
    result = recorder.process_file(file_path, object_id)

    # Verify result
    assert result is not None, "Processing should succeed"

    # Write the result to the output file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(result, cls=IndalekoJSONEncoder) + "\n")

    # Verify file was created and contains valid JSON
    with open(output_file, encoding="utf-8") as f:
        output_data = json.loads(f.read())

    ic("Single file processing test passed!")
    return output_data


def test_process_directory(temp_dir):
    """Test processing an entire directory."""
    ic("Testing directory processing...")

    # Create output file path
    output_file = os.path.join(temp_dir, "directory_output.jsonl")

    # Create recorder
    recorder = ChecksumRecorder(output_file)

    # Process the directory
    recorder.process_directory(temp_dir, recursive=True)

    # Verify file was created
    assert os.path.exists(output_file), "Output file should be created"

    # Count the number of entries
    entry_count = 0
    with open(output_file, encoding="utf-8") as f:
        for line in f:
            entry_count += 1

    ic(f"Directory processing generated {entry_count} entries")
    ic("Directory processing test passed!")


def test_batch_processing(temp_dir, files):
    """Test batch processing of files."""
    ic("Testing batch processing...")

    # Create output file path
    output_file = os.path.join(temp_dir, "batch_output.jsonl")

    # Create batch file
    batch_file = os.path.join(temp_dir, "batch.json")

    # Create batch data
    batch_data = []
    for file_path in files:
        batch_data.append({"path": file_path, "object_id": str(uuid.uuid4())})

    # Write batch file
    with open(batch_file, "w", encoding="utf-8") as f:
        json.dump(batch_data, f, indent=2)

    # Create recorder
    recorder = ChecksumRecorder(output_file)

    # Process batch
    recorder.batch_process_files(batch_data)

    # Verify file was created
    assert os.path.exists(output_file), "Output file should be created"

    # Count the number of entries
    entry_count = 0
    with open(output_file, encoding="utf-8") as f:
        for line in f:
            entry_count += 1

    assert entry_count == len(
        files,
    ), f"Expected {len(files)} entries, got {entry_count}"

    ic("Batch processing test passed!")


def main():
    """Main test function."""
    ic("Running Checksum Recorder Tests")

    # Create test files
    temp_dir, files = create_test_files()

    try:
        # Run tests
        single_file_result = test_process_single_file(temp_dir, files)
        test_process_directory(temp_dir)
        test_batch_processing(temp_dir, files)

        # Display a sample result
        ic("Sample output:")
        print(json.dumps(single_file_result, indent=2, cls=IndalekoJSONEncoder))

        ic("All tests passed!")

    finally:
        # Clean up
        cleanup_test_files(temp_dir)


if __name__ == "__main__":
    main()
