# Multi-Checksum Generator - Recorder Component

This directory contains the recorder component of the Multi-Checksum Generator for Indaleko, which processes files to compute multiple checksums and stores the results in the Indaleko database.

## Overview

The checksum recorder works in conjunction with the checksum collector to create a complete pipeline:

1. **Collector Component**: Implements the checksum computation and formatting (located in `/semantic/collectors/checksum/`)
2. **Recorder Component**: Processes files, invokes the collector, and stores the results

## Features

- **Multiple Checksum Algorithms**: Computes MD5, SHA1, SHA256, SHA512, and Dropbox Content Hash
- **Performance Optimized**: Uses memory mapping and chunked processing for large files
- **Flexible Processing Options**:
  - Process individual files
  - Process entire directories (recursive or non-recursive)
  - Batch process files from a configuration file
- **Data Caching**: Avoids reprocessing already processed files in a session
- **Database Integration**: Prepares data for upload to ArangoDB

## Usage

```python
from semantic.recorders.checksum.recorder import ChecksumRecorder

# Process a single file
recorder = ChecksumRecorder()
object_id = "467de59f-fe7f-4cdd-b5b8-0256e090ed04"  # UUID of the file in Indaleko
result = recorder.process_file("/path/to/file.txt", object_id)

# Process a directory
recorder.process_directory("/path/to/directory", recursive=True)

# Batch processing
file_list = [
    {"path": "/path/to/file1.txt", "object_id": "uuid1"},
    {"path": "/path/to/file2.txt", "object_id": "uuid2"}
]
recorder.batch_process_files(file_list)
```

## Command-Line Interface

The recorder can also be used from the command line:

```bash
# Process a single file
python -m semantic.recorders.checksum.recorder file /path/to/file.txt

# Process a directory (recursive)
python -m semantic.recorders.checksum.recorder directory /path/to/directory --recursive

# Batch processing from a JSON file
python -m semantic.recorders.checksum.recorder batch /path/to/batch.json

# Upload to database (not yet implemented)
python -m semantic.recorders.checksum.recorder upload --config /path/to/db_config.json
```

## JSON Output Format

The recorder produces JSONL (JSON Lines) files with one JSON object per line. Each object follows this structure:

```json
{
  "Record": {
    "SourceIdentifier": {
      "Identifier": "de7ff1c7-2550-4cb3-9538-775f9464746e",
      "Version": "1.0"
    },
    "Timestamp": "2025-04-10T12:34:56Z",
    "Attributes": {},
    "Data": ""
  },
  "Timestamp": "2025-04-10T12:34:56Z",
  "ObjectIdentifier": "467de59f-fe7f-4cdd-b5b8-0256e090ed04",
  "RelatedObjects": ["467de59f-fe7f-4cdd-b5b8-0256e090ed04"],
  "SemanticAttributes": [
    {
      "Identifier": {
        "Identifier": "de41cd6f-5468-4eba-8493-428c5791c23e",
        "Label": "MD5 Checksum"
      },
      "Value": "d41d8cd98f00b204e9800998ecf8427e"
    },
    {
      "Identifier": {
        "Identifier": "e2c803f8-a362-4d9b-b026-757e3af9c3d8",
        "Label": "SHA1 Checksum"
      },
      "Value": "da39a3ee5e6b4b0d3255bfef95601890afd80709"
    },
    // Additional checksum attributes...
  ]
}
```

## Integration with Indaleko

This recorder integrates with Indaleko's semantic data framework by:

1. Creating proper semantic attribute records for each checksum type
2. Using UUIDs for unique identification of checksum types and data records
3. Following the standard Indaleko data model structure for ArangoDB compatibility
4. Preparing data in JSON format for database upload

## Testing

To run the tests for the checksum recorder:

```bash
python -m semantic.recorders.checksum.test_checksum_recorder
```
