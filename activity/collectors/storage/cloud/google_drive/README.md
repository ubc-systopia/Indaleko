# Google Drive Activity Collector for Indaleko

This module provides functionality for collecting and recording file activity data from Google Drive. It interfaces with the Google Drive Activity API to gather information about file creation, modification, sharing, and other activities.

## Features

- Collects file activities from Google Drive
- Monitors file creation, modification, deletion, and sharing
- Supports activity classification for context-aware understanding
- Provides detailed file metadata including sharing status
- Records complete activity timelines
- Integrates with Indaleko database for storage and analysis

## Components

1. **Google Drive Activity Collector**
   - Authenticates with Google's OAuth 2.0
   - Queries the Drive Activity API
   - Processes activity data into standard models
   - Located at `activity/collectors/storage/cloud/google_drive/google_drive_collector.py`

2. **Google Drive Activity Recorder**
   - Stores activities in Indaleko's database
   - Provides query capabilities for stored activities
   - Generates statistics and reports
   - Located at `activity/recorders/storage/cloud/gdrive/recorder.py`

3. **OAuth Utilities**
   - Handles OAuth 2.0 authentication with Google APIs
   - Manages token storage and refresh
   - Located at `activity/collectors/storage/cloud/google_drive/oauth_utils.py`

4. **Data Models**
   - Activity data models that represent Google Drive activities
   - File information models for Google Drive files
   - User information models for activity participants
   - Located in `activity/collectors/storage/cloud/google_drive/data_models/`

## Usage

### Basic Collection

```python
from activity.collectors.storage.cloud.google_drive.google_drive_collector import GoogleDriveActivityCollector

# Create collector
collector = GoogleDriveActivityCollector(
    debug=True  # Enable debug logging
)

# Collect data
collector.collect_data()

# Access collected activities
for activity in collector.activities:
    print(f"Activity: {activity.activity_type}, File: {activity.file.name}")

# Save to JSONL file (default is data/gdrive_activities.jsonl)
collector.store_data()
```

### End-to-End Collection and Recording

```python
from activity.collectors.storage.cloud.google_drive.google_drive_collector import GoogleDriveActivityCollector
from activity.recorders.storage.cloud.gdrive.recorder import GoogleDriveActivityRecorder

# Create collector
collector = GoogleDriveActivityCollector(
    debug=True
)

# Create recorder that uses the collector
recorder = GoogleDriveActivityRecorder(
    collector=collector,
    debug=True
)

# Collect and store activities in one operation
activity_ids = recorder.collect_and_store_activities()
print(f"Collected and stored {len(activity_ids)} activities")

# Get statistics
stats = recorder.get_google_drive_specific_statistics()
print(f"Total activities: {stats.get('total_activities', 0)}")
print(f"Sharing percentage: {stats.get('sharing_percentage', 0):.1f}%")
```

### Command-Line Usage

```bash
# Basic usage
python -m activity.collectors.storage.cloud.google_drive.google_drive_collector

# Specify days to collect and output format
python -m activity.collectors.storage.cloud.google_drive.google_drive_collector --days 30 --output drive_activities.jsonl

# Enable debug logging
python -m activity.collectors.storage.cloud.google_drive.google_drive_collector --debug

# Store directly to database
python -m activity.collectors.storage.cloud.google_drive.google_drive_collector --direct-to-db
```

## OAuth Authentication

The collector uses OAuth 2.0 to authenticate with Google Drive. It requires:

1. Google API credentials from the Google Cloud Console
   - Create a project
   - Enable Drive API and Drive Activity API
   - Create OAuth credentials for a desktop application
   - Download credentials JSON file

2. Set up authentication:
   ```python
   from activity.collectors.storage.cloud.google_drive.oauth_utils import GoogleOAuthManager

   # Create manager with credentials file
   oauth_manager = GoogleOAuthManager(
       credentials_file="path/to/client_secrets.json",
       token_file="path/to/token.json",
       scopes=["https://www.googleapis.com/auth/drive.activity.readonly",
               "https://www.googleapis.com/auth/drive.metadata.readonly"]
   )

   # Load or request credentials
   credentials = oauth_manager.load_credentials()

   # Get user info
   user_info = oauth_manager.get_user_info()
   print(f"Authenticated as {user_info.get('name')} ({user_info.get('email')})")
   ```

On first run, it will prompt for authentication in a browser. Subsequent runs use the stored token.

## Architecture

The collector follows the standard Indaleko collector/recorder pattern:

1. **Collector**: Retrieves raw activity data from Google Drive
   - Handles authentication
   - Makes API requests
   - Processes raw responses into structured data
   - Maintains state between runs

2. **Recorder**: Stores processed activities in the database
   - Builds database documents
   - Adds semantic attributes
   - Provides query methods
   - Generates statistics

3. **Data Flow**:
   - Collector retrieves activities from Google API
   - Activities are processed into standard activity models
   - Recorder stores the processed activities in the database
   - Queries can be performed against the stored activities

## Integration with Activity Context

Google Drive activities integrate with Indaleko's Activity Context system:

```python
from activity.context.service import ActivityContext

# Initialize context manager
context = ActivityContext()

# Get activities related to Google Drive from context
activities = context.get_activities_with_filter(
    filter_query={
        "sources": ["google_drive"],
        "time_range": {
            "start": "2023-04-10T00:00:00Z",
            "end": "2023-04-17T23:59:59Z"
        }
    }
)

# Get activities with high research classification
research_activities = context.get_activities_by_primary_classification(
    classification="research",
    limit=10
)
```

## Dependencies

- google-api-python-client
- google-auth-httplib2
- google-auth-oauthlib
- requests
- pydantic

## See Also

- [Google Drive Activity API Reference](https://developers.google.com/drive/activity/v2/reference)
- [Indaleko Activity Collectors Overview](../README.md)
