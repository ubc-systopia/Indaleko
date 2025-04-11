# EXIF Metadata Extractor for Indaleko

This semantic extractor processes image files to extract EXIF and other metadata, making it available for searching and analysis within Indaleko.

## Features

- Extracts comprehensive metadata from image files:
  - **Camera Information**: Make, model, serial number, lens details
  - **Capture Settings**: Exposure, aperture, ISO, focal length, date/time
  - **GPS Data**: Location coordinates, altitude, timestamps
  - **Image Information**: Dimensions, bit depth, orientation, software, copyright

- Supports multiple image formats:
  - JPEG / JFIF (.jpg, .jpeg)
  - TIFF (.tif, .tiff)
  - PNG (.png) - limited metadata
  - RAW formats (.nef, .cr2, .dng)
  - HEIF/HEIC (.heic, .heif)
  
- Performance optimizations:
  - In-memory processing with minimal file I/O
  - Caching to avoid reprocessing
  - Smart filtering of image files during directory scans
  - Progress reporting for batch processing

## Usage

```python
from semantic.recorders.exif.recorder import ExifRecorder

# Process a single image file
recorder = ExifRecorder()
object_id = "467de59f-fe7f-4cdd-b5b8-0256e090ed04"  # UUID of the file in Indaleko
exif_data = recorder.process_file("/path/to/image.jpg", object_id)

# Process all images in a directory
recorder.process_directory("/path/to/image/directory", recursive=True)

# Process only specific image formats
recorder.process_directory(
    "/path/to/image/directory",
    recursive=True,
    file_extensions=['.jpg', '.png']
)
```

## Command Line Interface

The EXIF extractor can also be used from the command line:

```bash
# Process a single image file
python -m semantic.recorders.exif.recorder file /path/to/image.jpg

# Process all images in a directory
python -m semantic.recorders.exif.recorder directory /path/to/directory --recursive

# Process only specific image formats
python -m semantic.recorders.exif.recorder directory /path/to/directory --recursive --extensions .jpg .png

# Process images from a batch file (JSON list of paths and object IDs)
python -m semantic.recorders.exif.recorder batch /path/to/batch.json

# Upload processed data to database (when implemented)
python -m semantic.recorders.exif.recorder upload --config /path/to/db_config.json
```

## Architecture

The EXIF metadata extraction is implemented in two main components:

1. **Collector (semantic/collectors/exif/exif_collector.py)**:
   - Handles the low-level extraction of EXIF data from image files
   - Normalizes data into a consistent structure
   - Parses coordinates, timestamps, and specialized formats
   - Maps raw EXIF tags to semantic attributes

2. **Recorder (semantic/recorders/exif/recorder.py)**:
   - Coordinates processing of files and directories
   - Manages object IDs and database integration
   - Handles batch processing and progress reporting
   - Formats data for storage in ArangoDB

## Data Model

The EXIF metadata is structured into several components:

- `camera`: Camera make, model, serial number, lens information
- `capture_settings`: Exposure time, f-number, ISO, focal length, timestamp
- `gps`: Latitude, longitude, altitude, timestamp
- `image_info`: Dimensions, bit depth, orientation, software, copyright
- `raw_exif`: Complete dictionary of all extracted EXIF tags

Each component is optional and will only be included if relevant data was found in the image.

## Testing

Run the included test script to verify functionality:

```bash
python -m semantic.recorders.exif.test_exif_recorder
```

The test script:
1. Creates test images with EXIF data
2. Processes them with the extractor
3. Verifies that the extracted data is complete and accurate