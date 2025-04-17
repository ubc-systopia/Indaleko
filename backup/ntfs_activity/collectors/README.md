# NTFS Activity Generator for Indaleko

This component monitors the NTFS USN Journal to track file system activity on Windows systems. It provides a comprehensive view of file creation, modification, deletion, and renaming operations, with special handling for email attachments.

## Features

- Real-time monitoring of file system activity through the NTFS USN Journal
- Detection of file activities with detailed metadata:
  - Creation, modification, deletion, renaming, and security changes
  - Timestamps, process information, and reason flags
  - Full file paths and directory structure awareness
- Special email attachment tracking:
  - Identification of saved Outlook attachments
  - Correlation between saved files and their source emails
  - Confidence scoring for attachment detection
- Storage metadata updates:
  - Optional integration with the storage system to update file metadata
  - Real-time tracking of file changes for up-to-date storage information
- Comprehensive filtering capabilities:
  - By process, path, extension, activity type, etc.
  - Time-range based queries

## Components

### Collector

The `NtfsActivityCollector` monitors the USN Journal on NTFS volumes and processes the events into a structured activity feed. It runs in the background, capturing file system events as they occur.

```python
from activity.collectors.ntfs_activity.ntfs_activity_collector import NtfsActivityCollector

# Create a collector for drive C:
collector = NtfsActivityCollector(
    volumes=["C:"],
    include_close_events=False,  # Exclude file close events to reduce noise
    auto_start=True              # Start monitoring immediately
)

# Get recent file creation activities
create_activities = collector.get_activities_by_type("create")
```

### Recorder

The `NtfsActivityRecorder` stores file system activities in the Indaleko database and provides querying capabilities. It can also optionally update storage objects to maintain real-time file metadata.

```python
from activity.recorders.ntfs_activity.ntfs_activity_recorder import NtfsActivityRecorder

# Create a recorder with the collector
recorder = NtfsActivityRecorder(
    collector=collector,
    collection_name="FileActivities",
    update_storage_objects=True  # Update storage metadata when files change
)

# Store activities in the database
recorder.store_activities(collector.get_activities())

# Query activities by file path
file_activities = recorder.get_activities_by_file_path("C:\\Users\\JohnDoe\\Documents\\important.docx")
```

### Outlook Attachment Tracker

The `OutlookAttachmentTracker` specializes in identifying files saved from Outlook email attachments. It connects to Outlook via COM and correlates saved files with their source emails.

```python
from activity.collectors.ntfs_activity.outlook_attachment_tracker import OutlookAttachmentTracker

# Create a tracker with the collector
tracker = OutlookAttachmentTracker(
    ntfs_collector=collector,
    auto_start=True
)

# Get files that were identified as email attachments
email_attachments = tracker.get_matched_activities()
```

## Usage

### Basic Monitoring

```python
# Start monitoring file system activity
collector = NtfsActivityCollector(
    volumes=["C:"],
    filters={
        "excluded_paths": ["C:\\Windows\\", "C:\\Program Files\\"],
        "excluded_extensions": ["tmp", "temp", "log"]
    },
    auto_start=True
)

# Print summary of activities after some time
print(f"Collected {len(collector._activities)} file system activities")
```

### Email Attachment Tracking

```python
# Create a tracker
tracker = OutlookAttachmentTracker(ntfs_collector=collector)

# Start tracking
tracker.start_tracking()

# Get attachments after some time
attachments = tracker.get_matched_activities()
print(f"Identified {len(attachments)} saved email attachments")
```

### Database Storage and Querying

```python
# Create a recorder
recorder = NtfsActivityRecorder(collector=collector)

# Store activities
recorder.store_activities(collector.get_activities())

# Query for recent file creations
created_files = recorder.get_activities_by_type("create", limit=10)

# Query for activities in a time range
from datetime import datetime, timedelta
start_time = datetime.now() - timedelta(hours=1)
end_time = datetime.now()
recent_activities = recorder.get_activities_by_time_range(start_time, end_time)
```

## Benefits

The NTFS Activity Generator provides several key benefits for Indaleko:

1. **Dynamic Storage Updates**: Keeps storage metadata fresh without full rescans
2. **Email Attachment Tracking**: Links saved attachments to their source emails
3. **Process Attribution**: Associates file operations with the processes that performed them
4. **Temporal Context**: Captures when file operations occurred for activity timelines
5. **User Activity Insights**: Provides visibility into user interactions with files

## Implementation Details

This implementation uses several Windows APIs:

- **USN Journal API**: For tracking file system changes
- **Windows File Information**: For resolving file references to paths
- **COM Automation**: For Outlook integration
- **Process Management**: For correlating file activities with processes

The component is designed for minimal performance impact, with configurable filters to reduce noise and focus on relevant activity.

## Limitations

- Windows-only: The USN Journal is specific to NTFS
- Requires administrative privileges to access the USN Journal
- Outlook integration requires Outlook to be installed
- Not all processes can be reliably associated with file activities
- USN Journal has a finite size; very high activity volumes may cause events to be missed

## Future Enhancements

- Integration with ETW (Event Tracing for Windows) for better process correlation
- Support for non-NTFS filesystems through alternative tracking mechanisms
- Additional heuristics for attachment and file activity classification
- Machine learning-based confidence scoring for attachment detection