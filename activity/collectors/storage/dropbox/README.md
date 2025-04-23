# Dropbox Storage Activity Collector/Recorder for Indaleko

This module provides a standardized implementation of storage activity collection and recording for Dropbox, following Indaleko's collector/recorder pattern. It monitors file operations within a Dropbox account and creates standardized storage activity records for them.

## Features

- Real-time monitoring of Dropbox file activities through the Dropbox API
- Detection of file activities with detailed metadata:
  - Creation, modification, deletion operations
  - File metadata (name, path, size, etc.)
  - Revision tracking
  - Shared folder information
- OAuth-based authentication with automatic token refresh
- Configurable polling interval for API requests
- Full integration with Indaleko's activity tracking system
- Rich semantic attributes for effective querying and classification
- Database storage with comprehensive query capabilities
- Special handling for shared files and folders

## Architecture

This implementation follows Indaleko's standardized collector/recorder pattern:

### Collector (`DropboxStorageActivityCollector`)

The collector is responsible for gathering raw Dropbox file system activities:

- Handles Dropbox API authentication with OAuth
- Polls the Dropbox API for file changes at configurable intervals
- Processes file events into standardized activity models
- Preserves Dropbox-specific metadata (file IDs, revisions, sharing info)
- Provides access to collected activities for recording or analysis

### Recorder (`DropboxStorageActivityRecorder`)

The recorder is responsible for storing and querying the collected activities:

- Stores collected activities in the Indaleko database
- Adds semantic attributes for classification and querying
- Provides comprehensive query capabilities by various criteria
- Generates statistics and analytics on the stored activities
- Special queries for Dropbox-specific concepts (shared folders, revisions)

### Data Models

The implementation uses standardized data models for consistent representation:

- `BaseStorageActivityData`: Common base for all storage activities
- `CloudStorageActivityData`: Base for cloud storage providers
- `DropboxStorageActivityData`: Dropbox-specific extension with revision and shared folder info
- `StorageActivityMetadata`: Metadata about activity collection
- `StorageActivityType`: Enumeration of activity types (create, modify, delete, etc.)
- `StorageItemType`: Enumeration of item types (file, directory, etc.)
- `StorageProviderType`: Enumeration of provider types (NTFS, Dropbox, etc.)

## Setup and Configuration

### Dropbox App Registration

Before using this implementation, you need to register an app in the Dropbox developer console:

1. Go to [https://www.dropbox.com/developers/apps](https://www.dropbox.com/developers/apps)
2. Click "Create app"
3. Choose "Scoped access" API
4. Choose "Full Dropbox" access type
5. Name your app (e.g., "Indaleko")
6. Submit the form to create your app
7. On the app settings page, note down your App key and App secret
8. Under "OAuth 2", add "http://localhost:8669" to the list of Redirect URIs
9. Save your changes

### Configuration File

Create a Dropbox configuration file at the default location (or specify a custom location):

```json
{
  "app_key": "your_app_key",
  "app_secret": "your_app_secret"
}
```

Save this file as `dropbox_config.json` in the Indaleko config directory.

## Usage

### Basic Monitoring

```python
from activity.collectors.storage.dropbox.dropbox_collector import DropboxStorageActivityCollector
from activity.recorders.storage.dropbox.dropbox_recorder import DropboxStorageActivityRecorder

# Create a collector
collector = DropboxStorageActivityCollector(
    monitor_interval=60,  # Check for changes every 60 seconds
    auto_start=True       # Start monitoring immediately
)

# Create a recorder that uses the collector
recorder = DropboxStorageActivityRecorder(
    collector=collector,
    collection_name="DropboxActivity"  # Optional custom collection name
)

# Wait for some time to collect activities
import time
time.sleep(300)  # 5 minutes

# Store collected activities
activities = collector.get_activities()
activity_ids = recorder.store_activities(activities)
print(f"Stored {len(activity_ids)} activities")

# Stop monitoring when done
collector.stop_monitoring()
```

### First Run Authentication

On first run, the collector will guide you through the OAuth authentication process:

1. It will display a URL to visit in your browser
2. You'll be asked to authorize the app to access your Dropbox
3. After authorization, you'll receive an authentication code
4. Enter this code when prompted by the collector
5. The collector will store the credentials for future use

### Database Querying

```python
# Get activities by type
create_activities = recorder.get_activities_by_type(
    activity_type=StorageActivityType.CREATE,
    limit=10
)

# Get activities by file path
file_activities = recorder.get_activities_by_path(
    file_path="/Documents/important.docx"
)

# Get activities by Dropbox file ID
file_id_activities = recorder.get_activities_by_dropbox_id(
    dropbox_id="id:a1b2c3d4e5f6g7h8i9j0"
)

# Get activities by file revision
revision_activities = recorder.get_activities_by_revision(
    revision="a1b2c3d4e5"
)

# Get activities for files in a shared folder
shared_folder_activities = recorder.get_activities_by_shared_folder(
    shared_folder_id="1234567890"
)

# Get all activities for shared files
shared_activities = recorder.get_shared_activities()
```

### Statistics and Analytics

```python
# Get Dropbox-specific statistics
stats = recorder.get_dropbox_specific_statistics()

# Display statistics
print(f"Total activities: {stats['total_count']}")
print(f"Shared file percentage: {stats['sharing_percentage']:.1f}%")
print("Activities by type:")
for activity_type, count in stats["by_type"].items():
    print(f"  {activity_type}: {count}")

# Display top shared folders
print("Top shared folders:")
for folder_id, count in stats["top_shared_folders"].items():
    print(f"  {folder_id}: {count} activities")
```

## Example Script

The package includes a complete example script at `/activity/collectors/storage/examples/dropbox_example.py`:

```bash
# Basic usage
python -m activity.collectors.storage.examples.dropbox_example

# Monitor for a specific duration
python -m activity.collectors.storage.examples.dropbox_example --duration 600  # 10 minutes

# Change the polling interval
python -m activity.collectors.storage.examples.dropbox_example --poll-interval 30  # 30 seconds

# Filter by activity types
python -m activity.collectors.storage.examples.dropbox_example --filter-types CREATE,MODIFY,DELETE

# Show only shared file activities
python -m activity.collectors.storage.examples.dropbox_example --shared-only

# Enable debug mode
python -m activity.collectors.storage.examples.dropbox_example --debug
```

## Limitations

- Rate limits: The Dropbox API has rate limits that may affect monitoring of very active accounts
- Real-time events: The implementation uses polling rather than webhooks (webhooks support is planned)
- Conflict resolution: In case of conflicts between versions, only the latest version is tracked
- Auth flow: Currently requires manual entry of OAuth code rather than using a local web server callback

## Future Enhancements

- Webhook support for real-time change notifications
- Local web server for simplified OAuth flow
- Enhanced conflict detection and resolution
- Improved change detection with smarter diffing
- Better handling of large Dropbox accounts with many files
- Support for more Dropbox-specific features (Paper documents, comments, etc.)

## Semantic Attributes

The implementation uses the following semantic attributes to enrich the activities:

- **STORAGE_ACTIVITY**: Basic attribute for all storage activities
- **STORAGE_DROPBOX**: Identifies activities specifically from Dropbox
- **PROVIDER_DROPBOX**: Indicates the storage provider type
- **STORAGE_SHARED**: Identifies activities involving shared folders
- **FILE_CREATE/MODIFY/DELETE**: Indicates the type of file operation
- **ITEM_FILE/DIRECTORY**: Differentiates files vs. directories
