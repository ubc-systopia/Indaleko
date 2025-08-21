# Gmail Collector for Indaleko

The Gmail Collector retrieves email metadata from Gmail using the Gmail API, following Indaleko's Collector/Recorder pattern.

## Setup

### 1. Enable Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API for your project
4. Create OAuth 2.0 credentials (Desktop application type)
5. Download the credentials JSON file

### 2. Configure the Collector

1. Copy `gmail_config.example.json` to your config directory as `gmail_config.json`
2. Replace the placeholder values with your OAuth credentials

```bash
cp gmail_config.example.json ~/.config/indaleko/gmail_config.json
# Edit the file with your credentials
```

### 3. First Run - OAuth Authorization

On first run, the collector will open a browser for OAuth authorization:

```bash
python gmail_collector.py
```

This will create `gmail_token.json` in your config directory with refresh tokens.

## Usage

### Basic Collection

Collect recent messages:
```bash
python gmail_collector.py
```

### Search-based Collection

Collect specific messages using Gmail search syntax:
```bash
python gmail_collector.py --query "is:unread"
python gmail_collector.py --query "from:important@example.com"
python gmail_collector.py --query "has:attachment larger:10M"
```

### Collection Modes

- **Messages**: Individual email messages (default)
  ```bash
  python gmail_collector.py --mode messages
  ```

- **Threads**: Email conversations
  ```bash
  python gmail_collector.py --mode threads
  ```

- **All**: Both messages and threads
  ```bash
  python gmail_collector.py --mode all
  ```

### Limiting Results

```bash
python gmail_collector.py --max-results 100
```

### Output Control

```bash
python gmail_collector.py --datadir ./gmail_data --outputfile gmail_2024.json
```

## Data Format

The collector outputs raw Gmail API data without normalization, including:

- **Message Metadata**: ID, thread ID, labels, snippet, size, internal date
- **Headers**: From, To, Subject, Date, Message-ID, References
- **Parts Info**: Attachments and MIME structure
- **Labels**: All Gmail labels/folders
- **Statistics**: Collection counts and errors

Example output structure:
```json
{
  "platform": "Gmail",
  "collector": "gmail_collector",
  "email": "user@gmail.com",
  "collected_at": "2024-01-01T12:00:00Z",
  "labels": [...],
  "messages": [
    {
      "id": "msg_id",
      "threadId": "thread_id",
      "labelIds": ["INBOX", "UNREAD"],
      "snippet": "Email preview text...",
      "headers": {
        "From": "sender@example.com",
        "To": "recipient@example.com",
        "Subject": "Email subject"
      },
      "parts": [...]
    }
  ],
  "statistics": {
    "message_count": 100,
    "thread_count": 50,
    "label_count": 20,
    "error_count": 0
  }
}
```

## Collector/Recorder Pattern

This collector follows Indaleko's architectural pattern:

- **Collector** (this module): Retrieves raw Gmail data via API
- **Recorder** (separate module): Processes and stores data in database

The collector never:
- Normalizes data formats
- Writes to the database
- Transforms Gmail's native structure

## Security Notes

- OAuth tokens are stored locally in `gmail_token.json`
- Only read-only scopes are requested
- Message bodies are not downloaded (metadata only)
- Credentials never leave your local system

## Performance Considerations

- Uses batch requests where possible
- Retrieves metadata only (not full message bodies)
- Supports pagination for large mailboxes
- Includes performance measurement hooks

## Troubleshooting

### Token Expiration
If you see 401 errors, delete `gmail_token.json` and re-authenticate:
```bash
rm ~/.config/indaleko/gmail_token.json
python gmail_collector.py
```

### API Quotas
Gmail API has usage quotas. For large mailboxes, use `--max-results` to limit collection.

### Missing Config File
Ensure `gmail_config.json` exists in your config directory with valid OAuth credentials.
