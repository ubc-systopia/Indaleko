# Google Drive Activity Recorder

This module provides a recorder for Google Drive storage activities, storing activity data collected by the Google Drive Activity Collector in the Indaleko database.

## Overview

The Google Drive Activity Recorder extends the base `StorageActivityRecorder` class and adds Google Drive-specific functionality for storing and querying Google Drive file system activities.

## Features

- Stores Google Drive file activities in the database
- Adds Google Drive-specific semantic attributes
- Provides specialized queries for Drive-specific data
- Generates statistics about Drive activities
- Integrates with the existing Indaleko activity system

## Usage

### Basic Usage

```python
from activity.collectors.storage.cloud.gdrive_activity_collector import GoogleDriveActivityCollector
from activity.recorders.storage.cloud.gdrive.recorder import GoogleDriveActivityRecorder

# Create collector
collector = GoogleDriveActivityCollector(debug=True)

# Create recorder
recorder = GoogleDriveActivityRecorder(
    collector=collector,
    debug=True
)

# Collect and store activities in one step
activity_ids = recorder.collect_and_store_activities()
```

### Storing Pre-Collected Activities

```python
# Collect activities
collector.collect_data()

# Convert to storage activities
storage_activities = [activity.to_storage_activity() for activity in collector.activities]

# Store in database
activity_ids = recorder.store_activities(storage_activities)
```

### Database Queries

The recorder provides specialized queries for Google Drive data:

```python
# Get activities for a specific file
activities = recorder.get_activities_by_drive_id("file-id-123")

# Get activities for files in a specific folder
activities = recorder.get_activities_by_folder("folder-id-456")

# Get activities for files with a specific MIME type
activities = recorder.get_activities_by_mime_type("application/vnd.google-apps.document")

# Get activities for shared files only
activities = recorder.get_shared_activities()

# Get general activity statistics
stats = recorder.get_activity_statistics()

# Get Google Drive-specific statistics
drive_stats = recorder.get_google_drive_specific_statistics()
```

## Architecture

The Google Drive Activity Recorder follows the Indaleko recorder pattern:

1. **Initialize**: Create the recorder with a collector instance
2. **Collect**: Use the collector to gather activities from Google Drive
3. **Process**: Convert activities to standardized storage activity models
4. **Store**: Save activities to the ArangoDB database
5. **Query**: Provide methods for retrieving and analyzing stored activities

## Integration with Activity System

When storing activities, the recorder:

1. Adds Google Drive-specific semantic attributes
2. Preserves multi-dimensional activity classification
3. Maintains entity references and relationships
4. Adds storage provider-specific metadata

## Example Script

A complete example script is provided in `activity/collectors/storage/cloud/examples/gdrive_example.py`:

```bash
python -m activity.collectors.storage.cloud.examples.gdrive_example \
    --credentials=/path/to/credentials.json \
    --days=7 \
    --limit=20 \
    --to-db \
    --debug
```

## Testing

Unit tests are available in `activity/collectors/storage/cloud/test_gdrive_collector.py`:

```bash
python -m activity.collectors.storage.cloud.test_gdrive_collector
```
