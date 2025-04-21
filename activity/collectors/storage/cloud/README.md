# Cloud Storage Activity Collectors

This directory contains collectors for various cloud storage services, providing rich metadata about file activities and sharing patterns.

## Included Collectors

- **Google Drive Collector**: Tracks file activities and metadata
- **Dropbox Collector**: Monitors file changes and sharing
- **OneDrive Collector**: Captures file activities and permissions
- **Other Cloud Storage Collectors**: (Planned for future implementation)

## Common Features

All cloud storage collectors share these features:

- Cross-platform compatibility (Windows, macOS, Linux)
- Designed for scheduled execution via cron, Task Scheduler, or similar
- OAuth-based authentication with secure token storage
- Incremental collection with state persistence
- Rich metadata extraction (file properties, sharing info, etc.)
- Direct database integration or JSONL output
- Configurable logging and error handling

## Google Drive Collector

The Google Drive collector extracts file metadata, activity history, and sharing information from Google Drive.

### Features

- Monitors file creation, modification, and deletion
- Captures sharing permissions and activities
- Tracks file version history
- Extracts rich metadata (MIME types, custom properties, etc.)
- Uses Google's Drive API for efficient change tracking
- Supports scheduled execution for continuous collection

### Setup

#### Prerequisites

- Python 3.12 or newer
- Google account with Drive access
- Google API credentials (OAuth client ID)
- Indaleko environment properly configured

#### OAuth Credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project or select an existing one
3. Enable the Google Drive API and Drive Activity API
4. Configure OAuth consent screen
5. Create OAuth client ID credentials (Desktop application)
6. Download the credentials JSON file

#### Configuration

Create a configuration file `gdrive_collector_config.json` in your Indaleko config directory:

```json
{
  "credentials_file": "/path/to/oauth_credentials.json",
  "token_file": "/path/to/indaleko/data/gdrive_token.json",
  "state_file": "/path/to/indaleko/data/gdrive_collector_state.json",
  "output_file": "/path/to/indaleko/data/gdrive_activities.jsonl",
  "direct_to_db": true,
  "db_config": {
    "use_default": true
  },
  "log_file": "/path/to/indaleko/logs/gdrive_collector.log",
  "log_level": "INFO",
  "include_trashed": false,
  "include_shared_with_me": true,
  "include_team_drives": true,
  "max_change_history_days": 30,
  "metadata_fields": [
    "id", "name", "mimeType", "parents", "createdTime", 
    "modifiedTime", "owners", "sharingUser", "permissions", 
    "shared", "properties"
  ],
  "batch_size": 100
}
```

### Scheduling Collection

#### Linux/macOS (cron)

1. Edit your crontab:
   ```
   crontab -e
   ```

2. Add an entry to run every hour:
   ```
   0 * * * * cd /path/to/indaleko && /path/to/indaleko/.venv-linux-python3.12/bin/python activity/collectors/storage/cloud/google_drive_collector.py --config /path/to/indaleko/config/gdrive_collector_config.json >> /path/to/indaleko/logs/gdrive_cron.log 2>&1
   ```

#### Windows (Task Scheduler)

1. Create a batch script `run_gdrive_collector.bat`:
   ```batch
   @echo off
   cd /d C:\path\to\indaleko
   call .venv-win32-python3.12\Scripts\activate.bat
   python activity\collectors\storage\cloud\google_drive_collector.py --config C:\path\to\indaleko\config\gdrive_collector_config.json
   ```

2. Open Task Scheduler (taskschd.msc)
3. Create a new Basic Task:
   - Name: "Indaleko Google Drive Collector"
   - Trigger: Daily, repeat every 1 hour
   - Action: Start a program, browse to your batch script
   - Finish and adjust settings as needed

### Usage

#### Manual Execution

You can run the collector manually for testing or one-time collection:

```bash
python activity/collectors/storage/cloud/google_drive_collector.py --config /path/to/config.json
```

#### Command-Line Options

- `--config PATH`: Path to the configuration file
- `--verbose`: Enable verbose logging
- `--dry-run`: Run without saving data to database
- `--full-sync`: Force a full synchronization instead of incremental
- `--output FILE`: Override output file from config
- `--state FILE`: Override state file from config

### Data Model

The collector captures the following data for each Drive file activity:

```json
{
  "file_id": "GOOGLE_DRIVE_FILE_ID",
  "file_name": "Document.pdf",
  "mime_type": "application/pdf",
  "activity_type": "MODIFIED",
  "timestamp": "2024-04-20T12:34:56Z",
  "user": {
    "id": "user@example.com",
    "name": "User Name",
    "email": "user@example.com"
  },
  "file_metadata": {
    "created_time": "2024-03-15T09:30:00Z",
    "modified_time": "2024-04-20T12:34:56Z",
    "size": 2048576,
    "md5_checksum": "d41d8cd98f00b204e9800998ecf8427e",
    "parents": ["FOLDER_ID"],
    "trashed": false,
    "web_view_link": "https://drive.google.com/file/d/FILE_ID/view",
    "icon_link": "https://drive-thirdparty.googleusercontent.com/16/type/application/pdf"
  },
  "sharing": {
    "shared": true,
    "permissions": [
      {
        "id": "PERMISSION_ID",
        "type": "user",
        "email_address": "collaborator@example.com",
        "role": "reader",
        "display_name": "Collaborator Name"
      }
    ],
    "shared_drive_id": null
  },
  "version_info": {
    "version_number": 3,
    "size_bytes": 2048576,
    "last_modifying_user": "user@example.com"
  }
}
```

### Implementation Details

#### Authentication Flow

The collector implements Google's OAuth 2.0 flow:

1. First run: Opens a browser for user authentication
2. User grants permission to access Google Drive
3. Google provides an access token and refresh token
4. Tokens are stored securely for future use
5. Subsequent runs use the refresh token automatically

#### Change Tracking

For efficient change tracking, the collector uses:

1. Google Drive Changes API with page tokens
2. Stores the last sync token in the state file
3. Only retrieves changes since the last sync
4. Falls back to full sync if token expires

#### State Management

The collector maintains state in a JSON file:

```json
{
  "last_run": "2024-04-20T12:34:56Z",
  "last_sync_token": "ABC123...",
  "last_start_page_token": "XYZ456...",
  "change_stats": {
    "created": 10,
    "modified": 25,
    "deleted": 5
  },
  "total_files": 1275,
  "total_runs": 48
}
```

### Troubleshooting

#### Common Issues

1. **Authentication failures**:
   - Check that OAuth credentials are correct
   - Verify token file is accessible and valid
   - Re-authenticate if tokens have expired

2. **API quota exceeded**:
   - Reduce batch size in configuration
   - Increase collection interval
   - Consider creating a new Google Cloud project

3. **Missing data**:
   - Check for changes API limitations (some changes may be omitted)
   - Verify sufficient API quota
   - Run with `--full-sync` to ensure complete data

4. **Database issues**:
   - Verify ArangoDB is running
   - Check database credentials
   - Ensure network connectivity if using remote database

#### Getting Help

If you encounter persistent issues:

1. Check the full log file for detailed error messages
2. Run with the `--verbose` flag for enhanced logging
3. Verify that the OAuth flow is completing correctly
4. Consult the Indaleko documentation or seek assistance from the development team

## Dropbox Collector

(See separate document for Dropbox collector details)

## OneDrive Collector

(See separate document for OneDrive collector details)

## Contact

For assistance with cloud storage collectors, contact the Indaleko development team.