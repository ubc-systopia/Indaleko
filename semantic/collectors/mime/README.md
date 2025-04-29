# Content-Based MIME Type Detector

## Overview

This component provides content-based MIME type detection for the Indaleko project. It determines file types by analyzing file content rather than relying solely on file extensions, which improves accuracy when files are misnamed or have no extension.

The MIME type detector follows Indaleko's collector/recorder pattern:
- **Collector**: Analyzes file content and determines the MIME type
- **Recorder**: Stores the detected MIME types in the Indaleko database

## Features

- Content-based file type detection using libmagic
- Comparison with extension-based MIME type detection
- Confidence scoring for detected MIME types
- Character encoding detection for text files
- Additional format-specific metadata extraction
- Categorization by type (text, image, audio, video, application)
- Special flags for containers, compressed, and encrypted formats
- Batch processing for directories
- Filtering by file extension
- Result summarization and export

## Usage

### Programmatic Usage

```python
from semantic.collectors.mime.mime_collector import IndalekoSemanticMimeType
from semantic.recorders.mime.recorder import MimeTypeRecorder

# Using the collector directly
collector = IndalekoSemanticMimeType()
mime_info = collector.detect_mime_type("path/to/file.xyz")
print(f"Detected: {mime_info['mime_type']} with confidence {mime_info['confidence']}")

# Using the recorder (which handles database operations)
recorder = MimeTypeRecorder()

# Process a single file
result = recorder.process_file("path/to/file.xyz")

# Process a directory
results = recorder.process_directory("path/to/directory", recursive=True)

# Filter by file extensions
results = recorder.process_directory("path/to/directory",
                                    recursive=True,
                                    file_extensions=[".jpg", ".png", ".gif"])

# Export results to JSON
recorder.export_results_to_json(results, "mime_results.json")

# Generate a summary
summary = recorder.summarize_results(results)
```

### Command-Line Usage

The recorder can be run directly as a command-line tool:

```bash
# Process a single file
python -m semantic.recorders.mime.recorder --file path/to/file.xyz

# Process a directory
python -m semantic.recorders.mime.recorder --directory path/to/directory

# Process a directory recursively
python -m semantic.recorders.mime.recorder --directory path/to/directory --recursive

# Filter by file extensions
python -m semantic.recorders.mime.recorder --directory path/to/directory --extensions .jpg .png .gif

# Export results to JSON
python -m semantic.recorders.mime.recorder --directory path/to/directory --output results.json

# Print summary
python -m semantic.recorders.mime.recorder --directory path/to/directory --summary
```

## Requirements

- Python 3.6+
- `python-magic` library for content-based MIME type detection
- `chardet` library (optional, for text encoding detection)

## Architecture

This component follows the Indaleko collector/recorder pattern:

1. **Collector (`IndalekoSemanticMimeType`)**:
   - Detects MIME types from file content
   - Computes confidence scores
   - Extracts format-specific metadata
   - Returns structured data model

2. **Recorder (`MimeTypeRecorder`)**:
   - Integrates with Indaleko database
   - Handles batch processing
   - Manages object lookup
   - Provides command-line interface
   - Exports and summarizes results

## Testing

Test scripts are provided:

- `test_mime_collector.py`: Tests for the MIME type collector
- `test_mime_recorder.py`: Tests for the MIME type recorder

Run the tests with:

```bash
python -m semantic.collectors.mime.test_mime_collector
python -m semantic.recorders.mime.test_mime_recorder
```
