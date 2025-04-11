# Discord File Sharing Activity Generator for Indaleko

## Overview

The Discord File Sharing Activity Generator is a component for the Indaleko system that collects, processes, and stores information about files shared through Discord. It follows Indaleko's collector/recorder architecture pattern, where:

- **Collector**: Connects to the Discord API and gathers information about shared files from DMs and servers
- **Recorder**: Processes file sharing data and stores it in the Indaleko database with appropriate semantic attributes

This component tracks shared files across Discord channels, maintaining the relationship between Discord CDN URLs (which have no obvious connection to the original file) and their original filenames.

## Architecture

The Discord File Sharing Activity Generator consists of:

1. **Data Models**:
   - `SharedFileData`: Represents a shared file with properties like filename, URL, size, and content type
   - `DiscordDataModel`: Represents a Discord file sharing event with message context, channel/guild information, and file data

2. **Collector**:
   - `DiscordFileShareCollector`: Connects to Discord's API using a user token to scan messages for attachments
   - Extracts metadata about shared files including original filename, CDN URL, and sharing context
   - Supports scanning both direct messages and server channels

3. **Recorder**:
   - `DiscordFileShareRecorder`: Processes file attachment data and stores it in the Indaleko database
   - Creates semantic attributes for efficient querying
   - Maintains mappings between original filenames and Discord CDN URLs
   - Provides utilities for retrieving file sharing information

4. **Semantic Attributes**:
   - Custom UUIDs for file properties (filename, URL, content type, etc.)
   - Contextual attributes (channel, server, message details)
   - Sharing details (sender, timestamp)

## Features

- Cross-platform file sharing tracking
- Association of CDN URLs with original filenames
- Metadata extraction (file size, MIME type)
- Context capture (message content, channel information)
- Advanced querying capabilities (by filename, URL, server, etc.)
- Incremental syncing to avoid duplicates
- Support for both DMs and server channels

## Usage

### Basic Usage

```python
from activity.collectors.collaboration.discord.discord_file_collector import DiscordFileShareCollector
from activity.recorders.collaboration.discord_file_recorder import DiscordFileShareRecorder

# Initialize components with a Discord user token
collector = DiscordFileShareCollector(token="YOUR_DISCORD_TOKEN")
recorder = DiscordFileShareRecorder(collector=collector)

# Collect and store Discord file attachments
count = recorder.sync_attachments()
print(f"Synced {count} new attachments to database")

# Retrieve attachments by filename
attachments = recorder.retrieve_attachments_by_filename("example.pdf")
for attachment in attachments:
    print(f"Found: {attachment['filename']} at URL: {attachment['url']}")

# Generate a mapping from filenames to CDN URLs
mapping = recorder.generate_filename_to_url_mapping()
for filename, urls in mapping.items():
    print(f"{filename}: {len(urls)} URLs")
```

### Security and Token Management

For security, store your Discord token in a JSON configuration file rather than hardcoding it:

```python
# Store token in config/discord-token.json
{
    "token": "YOUR_DISCORD_TOKEN"
}

# Load token from file
collector = DiscordFileShareCollector(token_file="./config/discord-token.json")
```

### Scanning Specific Discord Servers

```python
# Collect data from Discord
attachments = collector.collect_data()

# Get guild-specific attachments
guild_id = "123456789012345678"
guild_attachments = [a for a in attachments if a.get("guild_id") == guild_id]
print(f"Found {len(guild_attachments)} attachments in guild {guild_id}")
```

## Implementation Details

### Authentication

The collector uses a Discord user token (not a bot token) to access the API. This approach has some benefits:

1. Access to the user's DMs, which bot tokens cannot access
2. Access to all servers the user is a member of
3. No need to add a bot to servers or set up OAuth flows

However, this approach requires the user to provide their token, which should be handled securely.

### CDN URL Structure

Discord CDN URLs have a structure like:
```
https://cdn.discordapp.com/attachments/CHANNEL_ID/MESSAGE_ID/FILENAME
```

However, the filename in the URL may not match the original filename. The collector captures the original filename from the message metadata and stores it along with the CDN URL.

### Rate Limiting

Discord's API has rate limits, so the collector implements sensible defaults to avoid hitting these limits:
- Limits message history retrieval to 100 messages per channel
- Adds delays between API calls
- Implements exponential backoff for retries

### Incremental Syncing

The recorder implements incremental syncing to avoid storing duplicate attachments:
1. When syncing, it compares new attachments against existing ones
2. Only stores attachments that don't already exist in the database
3. Uses the attachment URL as a unique identifier

## Extending the Component

### Adding Support for More Discord Data

To extend this component to capture more Discord data:

1. Update the data models to include new fields
2. Add collection logic in the collector
3. Add semantic attributes and processing in the recorder

For example, to add support for reactions:

```python
# Add to the data model
class DiscordDataModel(BaseCollaborationDataModel):
    # ...existing fields...
    Reactions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of reactions to the message"
    )

# Update collector to capture reactions
def extract_file_attachments(self, messages, channel_data):
    # ...existing code...
    for message in messages:
        # ...existing code...
        
        # Add reactions
        if "reactions" in message:
            file_data["reactions"] = message["reactions"]
```

### Adding File Content Extraction

To extract and process the actual file content:

1. Add file downloading capability to the collector
2. Implement content processing based on file type
3. Store content metadata in the database

For example:

```python
def download_attachment(self, url, filename):
    """Download a file from a Discord CDN URL"""
    headers = self._get_discord_api_headers()
    response = requests.get(url, headers=headers, stream=True)
    
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        return True
    return False
```

## Future Enhancements

- Real-time monitoring using Discord's WebSocket API
- Content extraction and analysis
- User activity correlation
- Integration with other collaboration providers
- Advanced search capabilities
- Automatic file categorization based on content and context