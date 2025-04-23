"""
Test script for the ExifRecorder.

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

from icecream import ic
from PIL import Image
from PIL.PngImagePlugin import PngInfo

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",
)

# Indaleko imports
from semantic.recorders.exif.recorder import ExifRecorder, IndalekoJSONEncoder


def create_test_images():
    """Create temporary test image files with EXIF data."""
    temp_dir = tempfile.mkdtemp()

    files = []

    # Create a simple JPEG image with EXIF data
    jpeg_path = os.path.join(temp_dir, "test_image.jpg")
    img = Image.new("RGB", (100, 100), color="red")

    # Add EXIF data
    exif_data = {
        0x010F: "Test Camera",  # Make
        0x0110: "Test Model",  # Model
        0x0112: 1,  # Orientation
        0x8827: 100,  # ISO Speed
        0x9003: "2023:07:15 14:22:36",  # DateTimeOriginal
    }

    # Save with EXIF data
    img.save(jpeg_path, exif=Image.Exif.from_dict(exif_data))
    files.append(jpeg_path)

    # Create a PNG with some metadata
    png_path = os.path.join(temp_dir, "test_image.png")
    img = Image.new("RGB", (100, 100), color="blue")

    # Add metadata
    metadata = PngInfo()
    metadata.add_text("Author", "Test Author")
    metadata.add_text("Software", "Test Software")
    metadata.add_text("Copyright", "Test Copyright")

    # Save with metadata
    img.save(png_path, pnginfo=metadata)
    files.append(png_path)

    # Create a nested directory with another image
    nested_dir = os.path.join(temp_dir, "nested")
    os.makedirs(nested_dir)

    # Create another JPEG in the nested directory
    nested_jpeg_path = os.path.join(nested_dir, "nested_test_image.jpg")
    img = Image.new("RGB", (200, 200), color="green")
    img.save(nested_jpeg_path)
    files.append(nested_jpeg_path)

    return temp_dir, files


def cleanup_test_files(temp_dir):
    """Clean up temporary test files."""
    import shutil

    shutil.rmtree(temp_dir)


def test_process_single_file(temp_dir, files):
    """Test processing a single image file."""
    ic("Testing single file processing...")

    # Create output file path
    output_file = os.path.join(temp_dir, "single_file_output.jsonl")

    # Create recorder
    recorder = ExifRecorder(output_file)

    # Process a single file (the JPEG file should have EXIF data)
    file_path = files[0]
    object_id = uuid.uuid4()

    # Process with recorder
    result = recorder.process_file(file_path, object_id)

    # Verify result
    assert result is not None, "Processing should succeed for a file with EXIF data"

    # Write the result to the output file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(result, cls=IndalekoJSONEncoder) + "\n")

    # Verify file was created and contains valid JSON
    with open(output_file, encoding="utf-8") as f:
        output_data = json.loads(f.read())

    # Check if basic EXIF data was extracted
    if "camera" in output_data and output_data["camera"] is not None:
        ic("Camera information detected:", output_data["camera"])
    else:
        ic("No camera information detected")

    ic("Single file processing test passed!")
    return output_data


def test_process_directory(temp_dir):
    """Test processing an entire directory of images."""
    ic("Testing directory processing...")

    # Create output file path
    output_file = os.path.join(temp_dir, "directory_output.jsonl")

    # Create recorder
    recorder = ExifRecorder(output_file)

    # Process the directory with all image types
    recorder.process_directory(temp_dir, recursive=True)

    # Verify file was created
    assert os.path.exists(output_file), "Output file should be created"

    # Count the number of entries
    entry_count = 0
    with open(output_file, encoding="utf-8") as f:
        for line in f:
            entry_count += 1

    # We should have entries for images with EXIF data (not all images will have it)
    ic(f"Directory processing generated {entry_count} entries")
    ic("Directory processing test passed!")


def test_batch_processing(temp_dir, files):
    """Test batch processing of image files."""
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
    recorder = ExifRecorder(output_file)

    # Process batch
    recorder.batch_process_files(batch_data)

    # Verify file was created
    assert os.path.exists(output_file), "Output file should be created"

    # Count the number of entries
    entry_count = 0
    with open(output_file, encoding="utf-8") as f:
        for line in f:
            entry_count += 1

    # We should have entries for images with EXIF data (not all images will have it)
    ic(f"Batch processing generated {entry_count} entries")
    ic("Batch processing test passed!")


def main():
    """Main test function."""
    ic("Running EXIF Recorder Tests")

    # Create test files
    temp_dir, files = create_test_images()

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
