# NTFS Activity Recorder for Indaleko

This component records file system activities tracked by the NTFS Activity Collector into the Indaleko database. It provides storage, querying, and analysis capabilities for file system events, with special handling for email attachments and dynamic storage updates.

## Features

- Database storage for NTFS file system activities
- Semantic attribute management for effective querying
- Special handling for email attachments
- Optional integration with storage objects for dynamic updates
- Comprehensive querying capabilities:
  - By file path, process, activity type, time range, etc.
  - Advanced analytics and statistics

## Core Functionality

The NTFS Activity Recorder connects to the Indaleko database and manages a collection specifically for file system activities. It implements the standard Indaleko recorder pattern and provides the following key capabilities:

### Activity Storage

The recorder stores activities in the database with full semantic attributes to facilitate rich querying. Each activity includes:

- Activity type (create, modify, delete, rename, etc.)
- File metadata (path, name, volume, etc.)
- Process information (process ID, name)
- Timestamps and USN information
- For email attachments: source email, sender, confidence score, etc.

### Database Querying

The recorder provides numerous methods for querying the stored activities:

```python
# Get activities by file path
file_activities = recorder.get_activities_by_file_path("C:\\Users\\JohnDoe\\Documents\\report.docx")

# Get activities by process
outlook_activities = recorder.get_activities_by_process("outlook.exe")

# Get activities by time range
from datetime import datetime, timedelta
start_time = datetime.now() - timedelta(hours=1)
end_time = datetime.now()
recent_activities = recorder.get_activities_by_time_range(start_time, end_time)

# Get activities by type
create_activities = recorder.get_activities_by_type("create")

# Get email attachment activities
attachments = recorder.get_email_attachment_activities(min_confidence=0.7)
```

### Storage Integration

When configured, the recorder can update storage objects in real-time as file activities are detected:

```python
# Create a recorder with storage updates enabled
recorder = NtfsActivityRecorder(
    collector=ntfs_collector,
    update_storage_objects=True
)

# All stored activities will automatically update corresponding storage objects
```

### Statistics and Analytics

The recorder can generate statistics about the recorded activities:

```python
# Get activity statistics
stats = recorder.get_activity_statistics()

# Display statistics
print(f"Total activities: {stats['total_count']}")
print("Activities by type:")
for activity_type, count in stats.get("by_type", {}).items():
    print(f"  {activity_type}: {count}")
```

## Database Schema

Activities are stored with the following structure:

```json
{
  "RecordType": "NTFS_Activity",
  "Data": {
    "activity_id": "uuid-string",
    "activity_type": "create|modify|delete|rename|...",
    "file_name": "example.docx",
    "file_path": "C:\\Users\\JohnDoe\\Documents\\example.docx",
    "volume_name": "C:",
    "timestamp": "2024-04-10T15:30:45.123456Z",
    "process_name": "outlook.exe",
    "process_id": 1234,
    "is_directory": false,
    "confidence_score": 0.95,  // For email attachments
    "email_source": "sender@example.com",  // For email attachments
    "email_subject": "Document Attached",  // For email attachments
    "...: "..."  // Other fields
  },
  "SourceId": {
    "SourceID": "uuid-string",
    "SourceIdName": "NTFS Activity Recorder",
    "SourceDescription": "Records file system activities from the NTFS USN Journal",
    "SourceVersion": "1.0.0"
  },
  "SemanticAttributes": [
    {
      "AttributeId": "uuid-string",
      "Name": "NTFS Activity",
      "Value": true,
      "Description": "Activity from the NTFS USN Journal"
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

## Semantic Attributes

The recorder uses the following semantic attributes to enrich the activities:

- **NTFS_ACTIVITY**: Basic attribute for all USN Journal activities
- **FILE_ACTIVITY**: Indicates the activity relates to a file operation
- **ACTIVITY_TYPE_***: Specific attributes for each activity type (CREATE, MODIFY, etc.)
- **DIRECTORY_CHANGE** / **FILE_CHANGE**: Differentiates directory vs. file operations
- **PROCESS_INITIATED**: Indicates the activity has a known process association
- **EMAIL_ATTACHMENT**: Identifies activities related to email attachments
- **HIGH/MEDIUM/LOW_CONFIDENCE_EMAIL_ATTACHMENT**: Confidence level for attachment detection

## Usage Examples

### Basic Setup and Recording

```python
from activity.collectors.ntfs_activity.ntfs_activity_collector import NtfsActivityCollector
from activity.recorders.ntfs_activity.ntfs_activity_recorder import NtfsActivityRecorder

# Create a collector
collector = NtfsActivityCollector(
    volumes=["C:"],
    auto_start=True
)

# Create a recorder
recorder = NtfsActivityRecorder(
    collector=collector,
    collection_name="FileActivities"
)

# Collect activities for a while
import time
time.sleep(60)  # Wait for activities to be collected

# Store activities in the database
activities = collector.get_activities()
recorder.store_activities(activities)
```

### Querying and Analysis

```python
# Get all create activities for a specific file
file_path = "C:\\Users\\JohnDoe\\Documents\\important.docx"
file_creates = recorder.query_activities({
    "activity_type": "create",
    "file_path": file_path
})

# Get all email attachment activities with high confidence
email_attachments = recorder.query_activities({
    "confidence_score": {"$gte": 0.8}
})

# Get most active processes
stats = recorder.get_activity_statistics()
process_stats = stats.get("by_process", [])
for proc in process_stats[:5]:  # Top 5 processes
    print(f"{proc['process']}: {proc['count']} activities")
```

### Real-time Monitoring and Recording

```python
# Create collector and recorder with auto-connect
collector = NtfsActivityCollector(
    volumes=["C:"],
    auto_start=True
)

recorder = NtfsActivityRecorder(
    collector=collector,
    auto_connect=True
)

# Set up a loop to periodically store new activities
try:
    while True:
        # Get all activities that haven't been stored yet
        new_activities = collector.get_activities(
            filters={"stored": False}
        )

        # Store the activities
        if new_activities:
            recorder.store_activities(new_activities)
            print(f"Stored {len(new_activities)} new activities")

            # Mark activities as stored
            for activity in new_activities:
                activity.stored = True

        # Wait before checking again
        time.sleep(30)
except KeyboardInterrupt:
    print("Monitoring stopped")
```

## Integration with Storage Objects

The recorder can dynamically update storage objects as file activities are detected. This keeps the storage metadata up-to-date without requiring full rescans:

```python
# Enable storage updates in the recorder
recorder = NtfsActivityRecorder(
    collector=collector,
    update_storage_objects=True
)

# Now when activities are stored, corresponding storage objects will be updated
recorder.store_activities(collector.get_activities())
```

When a file is created, modified, deleted, or renamed, the recorder will:

1. Look up the corresponding storage object in the database
2. Update its metadata with the new information
3. Create a relationship between the file and the activity
4. Add appropriate semantic attributes to the storage object

This enables powerful queries like:

- Finding all files modified by a specific process
- Identifying files that were saved from email attachments
- Tracking the history of changes to a specific file

## Security Considerations

- The recorder requires access to the Indaleko database
- When updating storage objects, the recorder needs write access to those collections
- Access to the USN Journal requires administrative privileges on Windows
- Email attachment tracking requires access to Outlook and may expose sensitive email information
