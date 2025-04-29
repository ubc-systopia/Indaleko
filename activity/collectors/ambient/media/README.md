# Media Activity Collectors

This directory contains collectors for various media activity sources, providing rich metadata about content consumption patterns.

## Included Collectors

- **YouTube Collector**: Tracks video viewing history and metadata
- **Other Media Collectors**: (Planned for future implementation)

## YouTube Activity Collector

The YouTube activity collector extracts viewing history and rich metadata from YouTube to provide insights into media consumption patterns.

### Features

- Extracts complete YouTube viewing history
- Captures rich metadata (video titles, channels, categories, etc.)
- Uses existing Google OAuth tokens (shared with Google Drive)
- Classifies content using multi-dimensional activity classification
- Supports scheduled execution for continuous collection
- Maintains state between runs for efficient incremental updates

### Setup

#### Prerequisites

- Python 3.12 or newer
- Google account with YouTube activity
- Google API credentials (OAuth client ID)
- Indaleko environment properly configured

#### OAuth Credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project or select an existing one
3. Enable the YouTube Data API v3
4. Configure OAuth consent screen
5. Create OAuth client ID credentials (Desktop application)
6. Download the credentials JSON file

#### Configuration

Create a configuration file `youtube_collector_config.json` in your Indaleko config directory:

```json
{
  "credentials_file": "/path/to/oauth_credentials.json",
  "token_file": "/path/to/indaleko/data/youtube_token.json",
  "state_file": "/path/to/indaleko/data/youtube_collector_state.json",
  "output_file": "/path/to/indaleko/data/youtube_activities.jsonl",
  "direct_to_db": true,
  "db_config": {
    "use_default": true
  },
  "log_file": "/path/to/indaleko/logs/youtube_collector.log",
  "log_level": "INFO",
  "max_history_days": 90,
  "include_liked_videos": true,
  "include_playlists": true,
  "batch_size": 50
}
```

### Scheduling Collection

#### Linux/macOS (cron)

1. Edit your crontab:
   ```
   crontab -e
   ```

2. Add an entry to run daily:
   ```
   0 3 * * * cd /path/to/indaleko && /path/to/indaleko/.venv-linux-python3.12/bin/python activity/collectors/ambient/media/youtube_collector.py --config /path/to/indaleko/config/youtube_collector_config.json >> /path/to/indaleko/logs/youtube_cron.log 2>&1
   ```

#### Windows (Task Scheduler)

1. Create a batch script `run_youtube_collector.bat`:
   ```batch
   @echo off
   cd /d C:\path\to\indaleko
   call .venv-win32-python3.12\Scripts\activate.bat
   python activity\collectors\ambient\media\youtube_collector.py --config C:\path\to\indaleko\config\youtube_collector_config.json
   ```

2. Open Task Scheduler (taskschd.msc)
3. Create a new Basic Task:
   - Name: "Indaleko YouTube Activity Collector"
   - Trigger: Daily, run once per day
   - Action: Start a program, browse to your batch script
   - Finish and adjust settings as needed

### Usage

#### Manual Execution

You can run the collector manually for testing or one-time collection:

```bash
python activity/collectors/ambient/media/youtube_collector.py --config /path/to/config.json
```

#### Command-Line Options

- `--config PATH`: Path to the configuration file
- `--verbose`: Enable verbose logging
- `--dry-run`: Run without saving data to database
- `--days N`: Override max history days from config
- `--output FILE`: Override output file from config
- `--state FILE`: Override state file from config

### Monitoring Collection

The collector writes detailed logs to the configured log file:

```bash
tail -f /path/to/indaleko/logs/youtube_collector.log
```

### Data Model

The collector captures the following data for each viewed video:

```json
{
  "video_id": "YOUTUBE_VIDEO_ID",
  "title": "Video Title",
  "channel": {
    "id": "CHANNEL_ID",
    "name": "Channel Name"
  },
  "watched_at": "2024-04-20T12:34:56Z",
  "duration": "PT15M30S",
  "watch_percentage": 0.85,
  "url": "https://www.youtube.com/watch?v=YOUTUBE_VIDEO_ID",
  "thumbnail_url": "https://i.ytimg.com/vi/YOUTUBE_VIDEO_ID/hqdefault.jpg",
  "categories": ["Education", "Science & Technology"],
  "tags": ["python", "programming", "tutorial"],
  "description": "Video description text...",
  "published_at": "2023-10-15T08:00:00Z",
  "statistics": {
    "view_count": 123456,
    "like_count": 7890,
    "comment_count": 345
  },
  "activity_classification": {
    "ambient": 0.3,
    "consumption": 0.9,
    "productivity": 0.6,
    "research": 0.8,
    "social": 0.2,
    "creation": 0.1
  }
}
```

### Activity Classification

The YouTube collector implements Indaleko's multi-dimensional activity classification, recognizing that content consumption spans multiple categories:

- **Ambient**: Background/passive viewing (0.0-1.0)
- **Consumption**: Entertainment-focused viewing (0.0-1.0)
- **Productivity**: Work-related content (0.0-1.0)
- **Research**: Educational/informational content (0.0-1.0)
- **Social**: Community/interaction-focused content (0.0-1.0)
- **Creation**: Content creation tutorials/guides (0.0-1.0)

Classification is determined by analyzing video metadata including:
- Video category
- Channel focus
- Content keywords
- Watch patterns (time of day, completion rate)
- User engagement (likes, comments)

### Implementation Details

#### Authentication Flow

The collector implements Google's OAuth 2.0 flow:

1. First run: Opens a browser for user authentication
2. User grants permission to access YouTube data
3. Google provides an access token and refresh token
4. Tokens are stored securely for future use
5. Subsequent runs use the refresh token automatically

#### Incremental Collection

The collector maintains state between runs:

```json
{
  "last_run": "2024-04-20T12:34:56Z",
  "last_history_timestamp": "2024-04-20T12:34:56Z",
  "history_page_token": "ABC123...",
  "stats": {
    "total_videos_found": 123,
    "total_runs": 5,
    "last_run_videos": 10
  }
}
```

This allows it to efficiently retrieve only new activity since the last run.

#### API Quotas

The YouTube Data API has quota limits. The collector implements:

- Batch processing to minimize API calls
- Caching to avoid redundant requests
- Selective fetching of only necessary fields
- Prioritization of history retrieval over metadata enrichment

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
   - Ensure YouTube watch history is enabled in Google account
   - Check for sufficient API quota
   - Verify sufficient lookback period

4. **Database connection issues**:
   - Verify ArangoDB is running
   - Check database credentials
   - Ensure network connectivity if using a remote database

#### Getting Help

If you encounter persistent issues:

1. Check the full log file for detailed error messages
2. Run with the `--verbose` flag for enhanced logging
3. Verify the OAuth flow is completing correctly
4. Consult the Indaleko documentation or seek assistance from the development team

## Contact

For assistance with media collectors, contact the Indaleko development team.
