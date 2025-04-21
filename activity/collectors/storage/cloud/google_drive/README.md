# Google Drive Activity Collector for Indaleko

This module provides functionality for collecting and recording file activity data from Google Drive. It interfaces with the Google Drive Activity API to gather information about file creation, modification, sharing, and other activities.

## Features

- Collects file activities from Google Drive
- Monitors file creation, modification, deletion, and sharing
- Supports activity classification for context-aware understanding
- Provides detailed file metadata including sharing status
- Records complete activity timelines

## Components

1. **Google Drive Activity Collector**
   - Authenticates with Google's OAuth 2.0
   - Queries the Drive Activity API
   - Processes activity data into standard models

2. **Google Drive Activity Recorder**
   - Stores activities in Indaleko's database
   - Provides query capabilities for stored activities
   - Generates statistics and reports

3. **Data Models**
   - Activity data models that represent Google Drive activities
   - File information models for Google Drive files
   - User information models for activity participants

## Usage

```bash
# Basic usage
python -m activity.collectors.storage.cloud.google_drive.google_drive_collector

# Specify days to collect and output format
python -m activity.collectors.storage.cloud.google_drive.examples.google_drive_example --days 30 --output drive_activities.jsonl

# Test OAuth authentication
python -m activity.collectors.storage.cloud.google_drive.examples.google_drive_example --test-oauth

# Store directly to database
python -m activity.collectors.storage.cloud.google_drive.examples.google_drive_example --to-db
```

## OAuth Authentication

The collector uses OAuth 2.0 to authenticate with Google Drive. It requires:

1. Google API credentials from the Google Cloud Console
2. Required scopes for Drive and Drive Activity APIs
3. Browser-based authentication flow for user consent

On first run, it will prompt for authentication in a browser. Subsequent runs use the stored token.

## Architecture

The collector follows the standard Indaleko collector/recorder pattern:

1. Collector retrieves raw activity data from Google Drive
2. Activities are processed into standard activity models
3. Recorder stores the processed activities in the database
4. Queries can be performed against the stored activities

## Dependencies

- google-api-python-client
- google-auth-httplib2
- google-auth-oauthlib
- requests

## See Also

- [Google Drive Activity API Reference](https://developers.google.com/drive/activity/v2/reference)
- [Indaleko Activity Collectors Overview](link-to-collectors-docs)