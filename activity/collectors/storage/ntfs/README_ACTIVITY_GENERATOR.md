# NTFS Activity Generator

## Overview

The NTFS Activity Generator is a tool designed to collect NTFS file system activity data continuously over a specified period. It utilizes the USN Journal to monitor file system changes efficiently and can store activity data in both JSONL files and the Indaleko hot tier database.

This tool is particularly useful for:

- Building a comprehensive dataset of file system activities for testing and development
- Collecting realistic activity data to populate the Indaleko cognitive memory system
- Training machine learning models on real file usage patterns
- Long-term activity monitoring for security and compliance purposes

## Features

- **Continuous Collection**: Monitors file system activities continuously for hours or days
- **Multiple Volumes**: Supports monitoring multiple NTFS volumes simultaneously
- **File Rotation**: Automatically rotates output files based on configurable size limits
- **Database Integration**: Optionally records activities to the Indaleko hot tier database
- **Configurable Intervals**: Adjustable collection interval for different performance needs
- **Graceful Termination**: Handles signals (Ctrl+C) properly for clean shutdown
- **Detailed Statistics**: Provides summary statistics upon completion

## Requirements

- Windows OS (or Windows Subsystem for Linux with admin privileges)
- Python 3.8 or higher
- Administrator privileges (required for USN journal access)
- Indaleko environment setup (if database recording is enabled)

## Installation

The NTFS Activity Generator is included as part of the Indaleko project. No additional installation is required beyond the standard Indaleko setup.

## Usage

### Basic Usage

The simplest way to run the activity generator is using the provided convenience scripts:

**Windows:**
```cmd
collect_ntfs_activity.bat
```

**Linux/WSL:**
```bash
./collect_ntfs_activity.sh
```

These scripts use default parameters (24-hour duration on C: drive, 30-second collection interval).

### Command-line Options

For more control, you can use the following command-line options:

| Option | Description | Default |
|--------|-------------|---------|
| `--volumes` | Comma-separated list of volumes to monitor | `C:` |
| `--duration` | Collection duration in hours (0 for unlimited) | `24` |
| `--interval` | Collection interval in seconds | `30` |
| `--output-dir` | Directory to store output files | `data/ntfs_activity` |
| `--max-file-size` | Maximum JSONL file size in MB before rotation | `100` |
| `--record-hot-tier` | Record activities to hot tier database | `false` |
| `--verbose` | Enable verbose logging | `false` |
| `--db-config-path` | Path to database configuration file | `config/db_config.json` |

### Examples

**Monitor C: and D: drives for 48 hours:**
```cmd
collect_ntfs_activity.bat --volumes C:,D: --duration 48
```

**Collect with 60-second intervals and record to database:**
```cmd
collect_ntfs_activity.bat --interval 60 --record-hot-tier
```

**Run with verbose logging:**
```cmd
collect_ntfs_activity.bat --verbose
```

**Specify a custom output directory:**
```cmd
collect_ntfs_activity.bat --output-dir "D:\ntfs_data"
```

## Output Format

The activity generator produces JSONL files containing NTFS activity records. Each line represents a single activity event in JSON format with the following key fields:

- `activity_id`: Unique identifier for the activity
- `timestamp`: ISO 8601 timestamp with UTC timezone
- `activity_type`: Type of activity (create, modify, delete, etc.)
- `file_reference_number`: NTFS file reference number
- `file_path`: Full path to the file
- `file_name`: Name of the file
- `volume_name`: Volume name (e.g., "C:")
- `is_directory`: Whether the item is a directory
- `provider_type`: "ntfs" for all records
- `attributes`: Additional metadata including USN reason flags

### Example Record

```json
{
  "activity_id": "f3a7b2e1-6d9c-4e5f-8a3b-2c1d0e9f8a7b",
  "timestamp": "2024-04-21T14:32:15.123456+00:00",
  "activity_type": "create",
  "file_reference_number": "12345678",
  "parent_file_reference_number": "87654321",
  "file_name": "example.txt",
  "file_path": "C:\\Users\\UserName\\Documents\\example.txt",
  "volume_name": "C:",
  "is_directory": false,
  "provider_type": "ntfs",
  "provider_id": "7d8f5a92-35c7-41e6-b13d-6c4e89e7f2a5",
  "item_type": "file",
  "attributes": {
    "usn_reason_flags": ["FILE_CREATE", "CLOSE"],
    "usn_record_number": 123456789
  }
}
```

## Database Integration

When `--record-hot-tier` is enabled, the activity generator also records activities to the Indaleko hot tier database. This enables:

- Automatic entity mapping (tracking files across rename operations)
- TTL-based expiration (configurable, default 4 days)
- Importance scoring for cognitive relevance
- Integration with Indaleko's query tools
- Transition to warm tier for long-term storage

The hot tier database uses the `NtfsHotTierRecorder` which manages the activities in a ArangoDB collection.

## Advanced Usage

### Direct Python Interface

You can also use the activity generator directly from Python:

```python
from activity.collectors.storage.ntfs.activity_generator import NtfsActivityGenerator

# Create generator
generator = NtfsActivityGenerator(
    volumes=["C:", "D:"],
    duration=48,
    interval=60,
    output_dir="data/ntfs_activity",
    max_file_size=100,
    record_hot_tier=True,
    verbose=True
)

# Start collection
generator.start()
```

### Processing JSONL Files

To process the generated JSONL files later:

```python
from activity.recorders.storage.ntfs.tiered.hot.recorder import NtfsHotTierRecorder

recorder = NtfsHotTierRecorder(
    ttl_days=4,
    collection_name="ntfs_activities_hot",
    entity_collection_name="file_entities",
    db_config_path="config/db_config.json"
)

# Process file
activity_ids = recorder.process_jsonl_file("data/ntfs_activity/ntfs_activity_20240421_143215.jsonl")
print(f"Processed {len(activity_ids)} activities")
```

## Architecture

The NTFS Activity Generator consists of two main components:

1. **NtfsUsnJournalCollector**: Collects raw USN journal entries and converts them to standardized data models
2. **NtfsActivityGenerator**: Manages the collection lifecycle, file rotation, and database integration

### Collection Process

1. The generator initializes the USN journal collector for specified volumes
2. At configurable intervals, it collects new USN records
3. Records are converted to `NtfsStorageActivityData` models
4. Activities are written to JSONL files and optionally stored in the database
5. File rotation occurs when size limits are reached
6. Collection continues until the specified duration is reached

### Error Handling

The activity generator implements comprehensive error handling:

- Graceful signal handling (Ctrl+C)
- Exception catching and logging
- Auto-recovery from transient errors
- File rotation to avoid data loss on failures

## Performance Considerations

- **Collection Interval**: Adjusting the interval allows balancing between collection granularity and system load
- **File Size Limits**: Smaller file size limits reduce memory usage but increase filesystem operations
- **Multiple Volumes**: Monitoring many volumes may increase CPU usage
- **Database Recording**: Enabling database recording increases resource usage but provides richer functionality

## Troubleshooting

**Common Issue: Permission Denied**
- Ensure you're running with Administrator privileges
- Check filesystem permissions on the output directory

**Common Issue: Collection Interval Too Short**
- If you see excessive CPU usage, increase the collection interval
- 30-60 seconds is typically adequate for most use cases

**Common Issue: Database Recording Fails**
- Verify database configuration file path
- Check database connectivity
- Ensure ArangoDB is running

## License

Project Indaleko  
Copyright (C) 2024-2025 Tony Mason

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
