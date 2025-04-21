# Discord File Sharing Collector

This module collects information about files shared on Discord servers and direct messages. It tracks file sharing activities and stores metadata about the shared files to enable contextualized search and discovery.

## Features

- Monitors Discord servers and direct messages for file sharing activities
- Extracts rich metadata about shared files and their context
- Works on any platform (Windows, macOS, Linux) with Python support
- Designed for scheduled execution via cron, Task Scheduler, or similar
- Maintains state between runs to support incremental collection
- Implements careful rate limiting to respect Discord API constraints

## Setup

### Prerequisites

- Python 3.12 or newer
- Discord account with access to servers/channels you want to monitor
- Discord bot token or user token
- Indaleko environment properly configured

### Configuration

Create a configuration file `discord_collector_config.json` in your Indaleko config directory:

```json
{
  "token": "YOUR_DISCORD_TOKEN",
  "token_type": "bot",  // "bot" or "user"
  "state_file": "/path/to/indaleko/data/discord_collector_state.json",
  "output_file": "/path/to/indaleko/data/discord_file_shares.jsonl",
  "direct_to_db": true,
  "db_config": {
    "use_default": true
  },
  "log_file": "/path/to/indaleko/logs/discord_collector.log",
  "log_level": "INFO",
  "scan_dms": true,
  "scan_servers": true,
  "excluded_servers": ["Server to exclude"],
  "excluded_channels": ["general"],
  "lookback_days": 7,
  "batch_size": 100,
  "rate_limit": {
    "requests_per_second": 1
  }
}
```

### Getting a Discord Token

#### Bot Token (Recommended)

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a New Application
3. Navigate to the "Bot" tab
4. Click "Add Bot" and confirm
5. Under the "Token" section, click "Copy" to copy your bot token
6. Add the bot to your servers with proper permissions

#### User Token (Advanced Users)

Using a user token provides access to your personal Discord account. This approach is not officially supported by Discord and may violate their Terms of Service.

For testing purposes only:
1. Open Discord in your web browser
2. Open Developer Tools (F12)
3. Go to the Network tab
4. Look for requests to Discord's API
5. Find the "Authorization" header, which contains your user token

### Setting Up Scheduled Execution

#### Linux/macOS (cron)

1. Edit your crontab:
   ```
   crontab -e
   ```

2. Add an entry to run every 30 minutes:
   ```
   */30 * * * * cd /path/to/indaleko && /path/to/indaleko/.venv-linux-python3.12/bin/python activity/collectors/collaboration/discord/discord_file_collector.py --config /path/to/indaleko/config/discord_collector_config.json >> /path/to/indaleko/logs/discord_cron.log 2>&1
   ```

#### Windows (Task Scheduler)

1. Create a batch script `run_discord_collector.bat`:
   ```batch
   @echo off
   cd /d C:\path\to\indaleko
   call .venv-win32-python3.12\Scripts\activate.bat
   python activity\collectors\collaboration\discord\discord_file_collector.py --config C:\path\to\indaleko\config\discord_collector_config.json
   ```

2. Open Task Scheduler (taskschd.msc)
3. Create a new Basic Task:
   - Name: "Indaleko Discord File Collector"
   - Trigger: Daily, recur every 1 day, repeat every 30 minutes
   - Action: Start a program, browse to your batch script
   - Finish and adjust settings as needed

## Usage

### Manual Execution

You can run the collector manually to test or for one-time collection:

```bash
python activity/collectors/collaboration/discord/discord_file_collector.py --config /path/to/config.json
```

### Command-Line Options

- `--config PATH`: Path to the configuration file
- `--verbose`: Enable verbose logging
- `--dry-run`: Run without saving data to database
- `--lookback DAYS`: Override lookback days from config
- `--output FILE`: Override output file from config
- `--state FILE`: Override state file from config

### Monitoring Collection

The collector writes detailed logs to the configured log file. You can monitor these logs for any issues:

```bash
tail -f /path/to/indaleko/logs/discord_collector.log
```

## Implementation Details

### State Management

The collector maintains state in a JSON file with the following structure:

```json
{
  "last_run": "2024-04-20T12:34:56Z",
  "servers": {
    "server_id_1": {
      "last_message_id": "123456789012345678",
      "channels": {
        "channel_id_1": "123456789012345678",
        "channel_id_2": "123456789012345678"
      }
    }
  },
  "dms": {
    "dm_channel_id_1": "123456789012345678"
  },
  "stats": {
    "total_files_found": 123,
    "total_runs": 45,
    "last_run_files": 5
  }
}
```

### Data Model

The collector captures the following data for each shared file:

```json
{
  "file_id": "uuid",
  "message_id": "discord_message_id",
  "channel_id": "discord_channel_id",
  "server_id": "discord_server_id",
  "user_id": "discord_user_id",
  "username": "username#1234",
  "filename": "example.pdf",
  "file_url": "https://cdn.discordapp.com/...",
  "file_size": 12345,
  "content_type": "application/pdf",
  "created_at": "2024-04-20T12:34:56Z",
  "message_content": "Check out this file!",
  "context": {
    "channel_name": "general",
    "server_name": "My Server",
    "thread_name": "Discussion Thread",
    "conversation_snippet": ["Previous message", "Current message", "Next message"]
  },
  "metadata": {
    "has_embeds": true,
    "is_reply": false,
    "mentioned_users": ["user1#1234", "user2#5678"],
    "reactions": [{"emoji": "👍", "count": 3}, {"emoji": "❤️", "count": 1}]
  }
}
```

### Rate Limiting

The collector implements careful rate limiting to respect Discord's API constraints:

- Default rate: 1 request per second
- Adaptive backoff when approaching rate limits
- Pause and resume mechanism when hitting rate limits

## Troubleshooting

### Common Issues

1. **Authentication failures**:
   - Verify your token is correct and has not expired
   - Check that the token has appropriate permissions

2. **Permission issues**:
   - Ensure the bot/user has access to the channels being monitored
   - Check that the bot has the "Read Message History" permission

3. **Rate limiting**:
   - Reduce the batch size in configuration
   - Increase the interval between scheduled runs
   - Check logs for rate limit warnings

4. **Missing data**:
   - Verify Discord's CDN (Content Delivery Network) is accessible
   - Check that the state file is being updated correctly
   - Ensure lookback period covers the expected time range

5. **Database issues**:
   - Verify ArangoDB is running
   - Check database credentials
   - Ensure network connectivity if using remote database

### Getting Help

If you encounter persistent issues:

1. Check the full log file for detailed error messages
2. Run with the `--verbose` flag for enhanced logging
3. Verify that the state file is being updated correctly
4. Consult the Indaleko documentation or seek assistance from the development team

## Contact

For assistance with this collector, contact the Indaleko development team.