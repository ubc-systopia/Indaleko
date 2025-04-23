# Cloud Storage Activity Collectors

This directory contains collectors for various cloud storage services, capturing file activities such as creation, modification, deletion, and sharing. These collectors are designed to run on a schedule and integrate with Indaleko's activity system.

## Available Collectors

- **Google Drive Activity Collector**: Captures file activities from Google Drive
- **Dropbox Activity Collector**: Captures file activities from Dropbox (planned)
- **OneDrive Activity Collector**: Captures file activities from OneDrive (planned)

## Architecture

The cloud storage collectors follow Indaleko's collector/recorder pattern:

1. **Collectors**: Retrieve activity data from cloud storage APIs
2. **Recorders**: Process and store activity data in the database

All collectors implement scheduled collection with incremental updates, maintaining state between runs to ensure efficient operation.

## Common Features

- OAuth-based authentication
- Incremental collection using change tokens/cursors
- Activity classification and normalization
- Direct database integration
- Configurable scheduling
- Resource usage controls
- Comprehensive error handling

## Google Drive Activity Collector

The Google Drive Activity collector monitors changes to files and folders in a user's Google Drive account, capturing events like:

- File and folder creation
- File modifications and renames
- File deletions and trash actions
- File sharing and permission changes
- File comments and annotations

### Setup

1. **Register application in Google Cloud Console**
   - Create a project in [Google Cloud Console](https://console.cloud.google.com/)
   - Enable Google Drive API
   - Create OAuth 2.0 credentials
   - Add authorized redirect URIs (localhost for testing)

2. **Install dependencies**
   ```bash
   pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
   ```

3. **Configure credentials**
   - Save OAuth client credentials to `config/gdrive_client_secrets.json`
   - Run collector once to authenticate and store tokens

4. **Set up scheduled collection**
   - Use the provided setup script to configure cron job:
     ```bash
     ./setup_gdrive_collector.sh
     ```

### Authentication

The Google Drive collector uses a shared OAuth authentication system that can:

1. Use existing credentials from the legacy Google Drive collector (`storage/collectors/cloud/g_drive.py`)
2. Load OAuth tokens from a token file
3. Authenticate with a client secrets file
4. Request new tokens interactively when needed

This allows multiple collectors to share the same authentication credentials, providing a seamless experience for users.

```python
# The OAuth flow is managed by the GoogleOAuthManager class
from activity.collectors.storage.cloud.oauth_utils import GoogleOAuthManager

# Create OAuth manager
oauth_manager = GoogleOAuthManager(
    credentials_file="path/to/client_secrets.json",
    token_file="path/to/token.json",
    scopes=["https://www.googleapis.com/auth/drive.activity.readonly"],
    debug=True
)

# Get credentials
credentials = oauth_manager.load_credentials()

# Get user information
user_info = oauth_manager.get_user_info()
print(f"Authenticated as {user_info.get('name')} ({user_info.get('email')})")

# Build API services
drive_service = oauth_manager.build_service('drive', 'v3')
activity_service = oauth_manager.build_service('driveactivity', 'v2')
```

### Usage

```bash
# Run manually with default settings
python -m activity.collectors.storage.cloud.gdrive_activity_collector

# Specify configuration file
python -m activity.collectors.storage.cloud.gdrive_activity_collector --config path/to/config.json

# Force full collection (instead of incremental)
python -m activity.collectors.storage.cloud.gdrive_activity_collector --full

# Run with debug logging
python -m activity.collectors.storage.cloud.gdrive_activity_collector --debug
```

### Configuration

Create a configuration file `gdrive_collector_config.json`:

```json
{
  "credentials_file": "config/gdrive_client_secrets.json",
  "token_file": "config/gdrive_token.json",
  "state_file": "data/gdrive_collector_state.json",
  "output_file": "data/gdrive_activities.jsonl",
  "direct_to_db": true,
  "db_config": {
    "use_default": true
  },
  "collection": {
    "max_results_per_page": 100,
    "max_pages_per_run": 10,
    "include_drive_items": true,
    "include_comments": true,
    "include_shared_drives": true,
    "filter_apps": ["docs", "sheets", "slides", "forms"]
  },
  "scheduling": {
    "interval_minutes": 15,
    "retry_delay_seconds": 60,
    "max_retries": 3
  },
  "logging": {
    "log_file": "logs/gdrive_collector.log",
    "log_level": "INFO"
  }
}
```

## Integration with Activity System

The cloud storage collectors integrate with Indaleko's activity system by:

1. Converting cloud storage events to standardized activity data models
2. Classifying activities along multiple dimensions (ambient, consumption, productivity, etc.)
3. Linking activities to user identities and content entities
4. Supporting cross-referencing with other activity sources

## Google Drive Activity Recorder

The Google Drive Activity Recorder stores the activities collected by the Google Drive Activity Collector in the Indaleko database. It provides specialized queries and statistics for Google Drive-specific data.

### Usage

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

# Collect activities
collector.collect_data()

# Convert to storage activities
storage_activities = [activity.to_storage_activity() for activity in collector.activities]

# Store in database
activity_ids = recorder.store_activities(storage_activities)

# Get statistical information
stats = recorder.get_google_drive_specific_statistics()
print(f"Total activities: {stats.get('total_count', 0)}")
```

### Special Queries

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
```

### Example Script

A complete example script is provided in `examples/gdrive_example.py`:

```bash
python -m activity.collectors.storage.cloud.examples.gdrive_example \
    --credentials=/path/to/credentials.json \
    --days=7 \
    --limit=20 \
    --to-db \
    --debug
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify that OAuth credentials are correct
   - Check for expired refresh tokens
   - Ensure redirect URIs match configuration

2. **API Rate Limits**
   - Implement exponential backoff for retries
   - Adjust collection frequency in configuration

3. **Missing Events**
   - Check change token validity (some APIs expire change tokens)
   - Verify correct timestamp ranges for incremental collection

4. **Database Connection Issues**
   - Check ArangoDB connection
   - Verify database credentials and permissions

### Debugging

Enable debug logging for detailed information:

```bash
python -m activity.collectors.storage.cloud.gdrive_activity_collector --debug
```

View logs with:

```bash
tail -f logs/gdrive_collector.log
```
