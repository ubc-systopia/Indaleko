# MIME Type Recorder for Indaleko

## Overview

This component handles recording and storing content-based MIME type information in the Indaleko database. It works with the corresponding MIME type collector to create a complete detection and recording pipeline.

## Features

- Records content-based MIME type information in the Indaleko database
- Handles batch processing of multiple files
- Directory scanning with recursive options
- Filtering by file extension
- Progress reporting for large batches
- Export of results to JSON
- Result summarization and statistics

## Usage

### Programmatic Usage

```python
from semantic.recorders.mime.recorder import MimeTypeRecorder

# Initialize the recorder
recorder = MimeTypeRecorder()

# Process a single file
result = recorder.process_file("path/to/file.xyz")

# Process a batch of files
file_list = ["file1.txt", "file2.html", "file3.pdf"]
results = recorder.batch_process_files(file_list)

# Process a directory
results = recorder.process_directory("path/to/directory", recursive=True)

# Process only certain file types
results = recorder.process_directory(
    "path/to/directory",
    recursive=True,
    file_extensions=[".jpg", ".png", ".gif"]
)

# Export results to JSON
recorder.export_results_to_json(results, "mime_results.json")

# Generate summary statistics
summary = recorder.summarize_results(results)
print(f"Processed {summary['total_files']} files")
print(f"Average confidence: {summary['avg_confidence']:.2f}")
```

### Command-Line Usage

The recorder can be run as a standalone command-line tool:

```bash
# Process a single file
python -m semantic.recorders.mime.recorder --file path/to/file.xyz

# Process a directory
python -m semantic.recorders.mime.recorder --directory path/to/directory

# Process recursively
python -m semantic.recorders.mime.recorder --directory path/to/directory --recursive

# Filter by file extensions
python -m semantic.recorders.mime.recorder --directory path/to/directory --extensions .jpg .png .gif

# Export results to JSON
python -m semantic.recorders.mime.recorder --directory path/to/directory --output results.json

# Print summary
python -m semantic.recorders.mime.recorder --directory path/to/directory --summary

# Enable verbose output
python -m semantic.recorders.mime.recorder --directory path/to/directory --verbose
```

## Database Integration

The recorder integrates with the Indaleko database system to store MIME type information as semantic characteristics. It uses the following UUID-defined characteristics:

- `SEMANTIC_MIME_TYPE`: The content-based MIME type
- `SEMANTIC_MIME_TYPE_FROM_EXTENSION`: MIME type guessed from file extension
- `SEMANTIC_MIME_CONFIDENCE`: Detection confidence level
- `SEMANTIC_MIME_ENCODING`: Character encoding for text files
- Category flags: `IS_TEXT`, `IS_IMAGE`, `IS_AUDIO`, `IS_VIDEO`, `IS_APPLICATION`
- Special flags: `IS_CONTAINER`, `IS_COMPRESSED`, `IS_ENCRYPTED`

## Testing

Run the test script to verify recorder functionality:

```bash
python -m semantic.recorders.mime.test_mime_recorder
```

The test creates synthetic test files of various types and verifies the recorder can:
- Process individual files correctly
- Handle batch processing
- Process directories with and without recursion
- Filter by file extension
- Export results to JSON
- Generate accurate summaries