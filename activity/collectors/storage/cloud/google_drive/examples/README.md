# Google Drive Activity Collection Examples

This directory contains examples for using the Google Drive Activity Collector and Recorder in Indaleko.

## Examples

### google_drive_example.py

A comprehensive example demonstrating:
- OAuth authentication with Google API
- Collecting activities from Google Drive
- Processing and displaying activity data
- Storing activities in the database (optional)
- Exporting activities to JSONL files

Usage:
```bash
# Test OAuth authentication
python google_drive_example.py --test-oauth

# Collect activities from the last 7 days
python google_drive_example.py

# Collect activities with more options
python google_drive_example.py --days 30 --limit 50 --detailed --output activities.jsonl

# Store activities in the database
python google_drive_example.py --to-db
```

Options:
- `--days DAYS`: Number of days of history to collect (default: 7)
- `--limit LIMIT`: Maximum number of activities to display (default: 100)
- `--credentials PATH`: Path to custom OAuth credentials file
- `--token PATH`: Path to custom token file
- `--output PATH`: Path to save activities in JSONL format
- `--detailed`: Show detailed activity information
- `--debug`: Enable debug logging
- `--test-oauth`: Test only the OAuth flow
- `--reauth`: Force re-authentication by removing token file
- `--to-db`: Store activities in the Indaleko database

### test_organization.py

A simple script for testing the organization of Google Drive integration packages.

Usage:
```bash
python test_organization.py
```

## Configuration

These examples use the following configuration files:

1. **Credentials File**: `config/gdrive_client_secrets.json`
   - OAuth client credentials from Google Cloud Console
   - Required for authentication

2. **Token File**: `config/gdrive_token.json`
   - Created automatically after authentication
   - Stores refresh token for subsequent runs

## Importing from Examples

You can import and use functions from these examples in your own code:

```python
from activity.collectors.storage.cloud.google_drive.examples.google_drive_example import (
    test_oauth,
    collect_activities,
    store_in_database
)

# Test authentication
test_oauth(credentials_file="path/to/credentials.json", token_file="path/to/token.json")

# Collect activities
activities = collect_activities(days=14, limit=100)

# Store in database
store_in_database(activities)
```
