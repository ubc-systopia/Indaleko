# Calendar Activity Collector for Indaleko

This module provides functionality to collect calendar events from various providers (Google Calendar, Microsoft Outlook Calendar) for inclusion in Indaleko's activity database.

## Features

* Collects events from Google Calendar and Microsoft Outlook Calendar
* Extracts rich metadata including:
  * Event details (subject, body, times)
  * Attendees and responses
  * Meeting locations (physical and virtual)
  * Online meeting information (Teams, Zoom, etc.)
  * Recurrence patterns
  * Attachments
* Stores events with semantic attributes for searchability
* Supports incremental collection with change tracking

## Requirements

### Google Calendar

For Google Calendar integration, you'll need:

1. Google API client libraries:
   ```bash
   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
   ```

2. A Google Cloud project with the Google Calendar API enabled
3. OAuth 2.0 Client ID credentials downloaded as JSON

### Microsoft Outlook Calendar

For Outlook Calendar integration, you'll need:

1. Microsoft Authentication Library (MSAL):
   ```bash
   pip install msal requests
   ```

2. A registered application in the Microsoft identity platform (Azure AD)
3. Client ID and Client Secret for your application

## Usage

### Command-line Interface

The calendar collector includes a command-line interface for testing and using the collector:

```bash
# Google Calendar
python activity/collectors/collaboration/calendar/calendar_cli.py --provider google --config /path/to/config.json

# Outlook Calendar
python activity/collectors/collaboration/calendar/calendar_cli.py --provider outlook --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET

# Store events in the database
python activity/collectors/collaboration/calendar/calendar_cli.py --provider google --store

# Customize time range
python activity/collectors/collaboration/calendar/calendar_cli.py --start-days 7 --end-days 30

# Register with activity service manager (to make events appear in query results)
python activity/collectors/collaboration/calendar/calendar_cli.py --register
```

### Programmatic Usage

#### Google Calendar

```python
from activity.collectors.collaboration.calendar.google_calendar import GoogleCalendarCollector
from activity.recorders.collaboration.calendar_recorder import CalendarRecorder

# Create collector
collector = GoogleCalendarCollector(
    config_path="/path/to/gcalendar_config.json",
    token_path="/path/to/gcalendar_token.json"
)

# Authenticate
collector.authenticate()

# Collect events
collector.collect_data(
    start_time=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30),
    end_time=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=90)
)

# Process events
events = collector.process_data()

# Create recorder and store events
recorder = CalendarRecorder(collection_name="CalendarEvents")
recorder.store_calendar_events(events)
```

#### Outlook Calendar

```python
from activity.collectors.collaboration.calendar.outlook_calendar import OutlookCalendarCollector
from activity.recorders.collaboration.calendar_recorder import CalendarRecorder

# Create collector
collector = OutlookCalendarCollector(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET"
)

# Authenticate
collector.authenticate()

# Collect events
collector.collect_data(
    start_time=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30),
    end_time=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=90)
)

# Process events
events = collector.process_data()

# Create recorder and store events
recorder = CalendarRecorder(collection_name="CalendarEvents")
recorder.store_calendar_events(events)
```

### Simplified Collection and Storage

The recorder provides a convenience method for collecting and storing events:

```python
from activity.recorders.collaboration.calendar_recorder import CalendarRecorder

# Create recorder
recorder = CalendarRecorder()

# Collect and store events from Google Calendar
recorder.collect_and_store(
    collector_type="google",
    config_path="/path/to/gcalendar_config.json",
    token_path="/path/to/gcalendar_token.json",
    start_days=30,
    end_days=90
)

# Collect and store events from Outlook Calendar
recorder.collect_and_store(
    collector_type="outlook",
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    start_days=30,
    end_days=90
)
```

## Configuration

### Google Calendar

Create a file named `gcalendar_config.json` in the `config` directory with your OAuth client ID credentials:

```json
{
  "installed": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "your-project-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
  }
}
```

### Outlook Calendar

Create a file named `outlook_calendar_config.json` in the `config` directory:

```json
{
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET",
  "tenant_id": "common",
  "redirect_uri": "http://localhost:8000"
}
```

## Semantic Attributes

The calendar events are stored with the following semantic attributes:

* `CALENDAR_EVENT_ID`: Unique identifier for the event
* `CALENDAR_EVENT_SUBJECT`: Event subject/title
* `CALENDAR_EVENT_START_TIME`: Start time of the event
* `CALENDAR_EVENT_END_TIME`: End time of the event
* `CALENDAR_EVENT_LOCATION`: Location of the event
* `CALENDAR_EVENT_ORGANIZER`: Event organizer
* `CALENDAR_EVENT_STATUS`: Event status (confirmed, tentative, cancelled)
* `CALENDAR_EVENT_RECURRENCE`: Recurrence pattern for recurring events
* `CALENDAR_MEETING_TYPE`: Online meeting provider (Teams, Zoom, etc.)
* `CALENDAR_MEETING_URL`: URL to join the online meeting
* `CALENDAR_EVENT_ATTENDEES`: List of event attendees
* `CALENDAR_EVENT_RESPONSE`: User's response to the event
* `ADP_COLLABORATION_GOOGLE_CALENDAR`: Indicates Google Calendar events
* `ADP_COLLABORATION_OUTLOOK_CALENDAR`: Indicates Outlook Calendar events

## Integration with Indaleko Query

The calendar collector/recorder registers with Indaleko's activity service manager, making calendar events available through the query interface. This allows you to search for calendar events using natural language queries like:

* "Show meetings from last week"
* "Find calendar events with [person]"
* "Show me online meetings scheduled for tomorrow"
* "What meetings did I attend last month?"

The registration happens automatically when you use the recorder, but you can also explicitly register using:

```bash
python activity/collectors/collaboration/calendar/calendar_cli.py --register
```

## Data Models

The collector uses the following data models to represent calendar events:

* `CalendarEvent`: Main event model
* `EventAttendee`: Represents an attendee and their response
* `EventLocation`: Represents a physical or virtual location
* `RecurrencePattern`: Represents a recurrence pattern for recurring events
* `EventAttachment`: Represents a file attached to an event

These models extend Indaleko's base activity and collaboration data models.
