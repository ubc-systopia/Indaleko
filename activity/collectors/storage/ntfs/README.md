# NTFS Storage Activity Collector/Recorder for Indaleko

This module provides a standardized implementation of storage activity collection and recording for NTFS file systems, following Indaleko's collector/recorder pattern. It monitors the NTFS USN Journal to track file system activity on Windows systems and stores the activity data in the Indaleko database.

## Features

- Real-time monitoring of file system activity through the NTFS USN Journal
- Detection of file activities with detailed metadata:
  - Creation, modification, deletion, renaming, and security changes
  - Timestamps, process information, and reason flags
  - Full file paths and directory structure awareness
- Comprehensive filtering capabilities:
  - By process, path, extension, activity type, etc.
  - Time-range based queries
- Standardized implementation that follows the same pattern as other storage providers
- Full integration with Indaleko's activity tracking system
- Rich semantic attributes for effective querying and classification
- Database storage with comprehensive query capabilities
- Configurable collection parameters and filtering options

## Architecture

This implementation follows Indaleko's standardized collector/recorder pattern:

### Collector (`NtfsStorageActivityCollector`)

The collector is responsible for gathering raw NTFS file system activities from the USN Journal:

- Monitors one or more NTFS volumes for file system changes
- Processes USN Journal records into standardized activity models
- Filters activities based on configurable criteria
- Provides access to collected activities for recording or analysis

### Recorder (`NtfsStorageActivityRecorder`)

The recorder is responsible for storing and querying the collected activities:

- Stores collected activities in the Indaleko database
- Adds semantic attributes for classification and querying
- Provides comprehensive query capabilities by various criteria
- Generates statistics and analytics on the stored activities

### Data Models

The implementation uses standardized data models for consistent representation:

- `BaseStorageActivityData`: Common base for all storage activities
- `NtfsStorageActivityData`: NTFS-specific extension with USN information
- `StorageActivityMetadata`: Metadata about activity collection
- `StorageActivityType`: Enumeration of activity types (create, modify, delete, etc.)
- `StorageItemType`: Enumeration of item types (file, directory, etc.)
- `StorageProviderType`: Enumeration of provider types (NTFS, Dropbox, etc.)

## Usage

### Basic Monitoring

```python
from activity.collectors.storage.ntfs.ntfs_collector import NtfsStorageActivityCollector
from activity.recorders.storage.ntfs.ntfs_recorder import NtfsStorageActivityRecorder

# Create a collector for drive C:
collector = NtfsStorageActivityCollector(
    volumes=["C:"],
    include_close_events=False,  # Exclude file close events to reduce noise
    auto_start=True,             # Start monitoring immediately
    filters={
        "excluded_paths": ["C:\\Windows\\", "C:\\Program Files\\"],
        "excluded_extensions": ["tmp", "temp", "log"]
    }
)

# Create a recorder that uses the collector
recorder = NtfsStorageActivityRecorder(
    collector=collector,
    collection_name="NtfsStorageActivity"  # Optional custom collection name
)

# Let it collect some activities
import time
print("Monitoring NTFS activities for 60 seconds...")
time.sleep(60)

# Store collected activities
activities = collector.get_activities()
activity_ids = recorder.store_activities(activities)
print(f"Stored {len(activity_ids)} activities")

# Stop monitoring when done
collector.stop_monitoring()
```

### Database Querying

```python
# Query activities by type
create_activities = recorder.get_activities_by_type(
    activity_type=StorageActivityType.CREATE,
    limit=10
)

# Query activities by file path
file_activities = recorder.get_activities_by_path(
    file_path="C:\\Users\\JohnDoe\\Documents\\important.docx"
)

# Query activities by time range
from datetime import datetime, timedelta
start_time = datetime.now(timezone.utc) - timedelta(hours=1)
end_time = datetime.now(timezone.utc)
recent_activities = recorder.get_activities_by_time_range(
    start_time=start_time,
    end_time=end_time
)

# Query activities by volume
c_drive_activities = recorder.get_activities_by_volume(
    volume="C:"
)

# Query activities by file reference number (NTFS-specific)
file_ref_activities = recorder.get_activities_by_file_reference(
    file_reference="1234567890"
)

# Query activities by USN reason flags (NTFS-specific)
import win32file
reason_activities = recorder.get_activities_by_reason_flags(
    reason_flags=win32file.USN_REASON_FILE_CREATE | win32file.USN_REASON_FILE_DELETE,
    match_all=False  # Match any of the flags, not all
)
```

### Statistics and Analytics

```python
# Get basic statistics
stats = recorder.get_activity_statistics()
print(f"Total activities: {stats['total_count']}")
print("Activities by type:")
for activity_type, count in stats.get("by_type", {}).items():
    print(f"  {activity_type}: {count}")

# Get NTFS-specific statistics
ntfs_stats = recorder.get_ntfs_specific_statistics()
print("Activities by volume:")
for volume, count in ntfs_stats.get("by_volume", {}).items():
    print(f"  {volume}: {count}")
print("Top reason flags:")
for reason, count in list(ntfs_stats.get("by_reason_flags", {}).items())[:5]:
    print(f"  {reason}: {count}")
```

### Real-time Monitoring and Recording

```python
# Create collector and recorder
collector = NtfsStorageActivityCollector(
    volumes=["C:"],
    auto_start=True
)

recorder = NtfsStorageActivityRecorder(
    collector=collector
)

# Set up a loop to periodically store new activities
try:
    while True:
        # Store current activities
        activity_ids = recorder.collect_and_store_activities()
        print(f"Stored {len(activity_ids)} new activities")
            
        # Wait before checking again
        time.sleep(30)
except KeyboardInterrupt:
    print("Monitoring stopped")
    recorder.stop_monitoring()
```

## Example Script

The package includes a complete example script at `/activity/collectors/storage/examples/ntfs_example.py`:

```bash
# Basic usage
python -m activity.collectors.storage.examples.ntfs_example

# Monitor specific volumes
python -m activity.collectors.storage.examples.ntfs_example --volumes C:,D:

# Monitor for a specific duration
python -m activity.collectors.storage.examples.ntfs_example --duration 300  # 5 minutes

# Filter by activity types
python -m activity.collectors.storage.examples.ntfs_example --filter-types CREATE,MODIFY,DELETE

# Enable debug mode
python -m activity.collectors.storage.examples.ntfs_example --debug
```

## Implementation Details

This implementation uses several Windows APIs:

- **USN Journal API**: For tracking file system changes
- **Windows File Information**: For resolving file references to paths
- **Process Management**: For correlating file activities with processes

The component is designed for minimal performance impact, with configurable filters to reduce noise and focus on relevant activity.

## Limitations

- Windows-only: The USN Journal is specific to NTFS
- Requires administrative privileges to access the USN Journal
- Not all processes can be reliably associated with file activities
- USN Journal has a finite size; very high activity volumes may cause events to be missed

## Future Enhancements

- Integration with ETW (Event Tracing for Windows) for better process correlation
- Support for non-NTFS filesystems through alternative tracking mechanisms
- Additional heuristics for file activity classification
- Machine learning-based confidence scoring for activity detection
- Integration with Outlook for email attachment tracking (see the old implementation for reference)

## Semantic Attributes

The implementation uses the following semantic attributes to enrich the activities:

- **STORAGE_ACTIVITY**: Basic attribute for all storage activities
- **FILE_CREATE**: Indicates file creation activity
- **FILE_MODIFY**: Indicates file modification activity
- **FILE_DELETE**: Indicates file deletion activity
- **FILE_RENAME**: Indicates file rename activity
- **SECURITY_CHANGE**: Indicates security/permission changes
- **STORAGE_NTFS**: Identifies activities specifically from NTFS
- **DIRECTORY_OPERATION** / **FILE_OPERATION**: Differentiates directory vs. file operations

## Database Schema

Activities are stored with the following structure:

```json
{
  "RecordType": "StorageActivity",
  "Data": {
    "activity_id": "uuid-string",
    "activity_type": "create|modify|delete|rename|...",
    "file_name": "example.docx",
    "file_path": "C:\\Users\\JohnDoe\\Documents\\example.docx",
    "volume_name": "C:",
    "timestamp": "2024-04-10T15:30:45.123456Z",
    "process_name": "example.exe",
    "process_id": 1234,
    "item_type": "file|directory",
    "file_reference_number": "1234567890",
    "parent_file_reference_number": "0987654321",
    "reason_flags": 1,
    "usn": 12345,
    "provider_type": "ntfs",
    "provider_id": "uuid-string"
  },
  "SourceId": {
    "SourceID": "uuid-string",
    "SourceIdName": "NTFS Storage Activity Recorder",
    "SourceDescription": "Records storage activities from the NTFS file system",
    "SourceVersion": "1.0.0"
  },
  "SemanticAttributes": [
    {
      "Identifier": "uuid-string",
      "Label": "Storage Activity",
      "Description": "Activity related to storage operations"
    },
    {
      "Identifier": "uuid-string",
      "Label": "NTFS Storage Activity",
      "Description": "Storage activity from NTFS file system"
    },
    // Other semantic attributes
  ],
  "Timestamp": {
    "CreationTime": "2024-04-10T15:30:46.123456Z",
    "ModificationTime": "2024-04-10T15:30:46.123456Z",
    "AccessTime": "2024-04-10T15:30:46.123456Z"
  },
  "RecordId": "uuid-string"
}
```

## Notes on the New Implementation

This implementation replaces the previous NTFS activity collector/recorder (which can still be found in the git history). The key improvements are:

1. Follows the standardized storage activity collector/recorder pattern
2. Provides a consistent approach across different storage providers
3. Uses common base classes for collectors and recorders
4. Standardized data models and semantic attributes
5. Better integration with the overall Indaleko architecture
6. More extensible for future storage providers

## See Also

- Other storage providers: Dropbox, OneDrive, Google Drive (TBD)
- Storage collection base classes
- Storage activity documentation
- Semantic attributes documentation