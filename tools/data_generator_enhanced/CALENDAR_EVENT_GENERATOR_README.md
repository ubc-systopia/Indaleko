# Calendar Event Generator Tool

The Calendar Event Generator Tool creates realistic calendar events for testing and evaluation in Indaleko. It generates events with comprehensive metadata including attendees, locations, recurrence patterns, and semantic attributes.

## Features

- **Complete Event Data**: Generates calendar events with subjects, bodies, start/end times, locations, and attendees
- **Recurrence Patterns**: Creates recurring events with proper recurrence metadata (daily, weekly, monthly, etc.)
- **Online Meeting Support**: Includes online meeting details with provider-specific URLs (Teams, Zoom, Google Meet)
- **Rich Semantic Attributes**: Generates all required semantic attributes for effective querying
- **Temporal Consistency**: Events follow realistic scheduling patterns with proper time distributions
- **Cross-Domain Integration**: Events reference location data and named entities when available
- **Database Integration**: Fully compatible with ArangoDB schema for persistent storage

## Usage

### Basic Usage

```python
from tools.data_generator_enhanced.agents.data_gen.tools.calendar_event_generator import CalendarEventGeneratorTool

# Initialize the generator
generator = CalendarEventGeneratorTool()

# Generate 10 calendar events
result = generator.execute({
    "count": 10,
    "criteria": {
        "user_email": "user@example.com",
        "user_name": "Test User",
        "provider": "outlook"  # or "google", "ical", "generic"
    }
})

# Access the generated events
events = result["events"]
```

### Advanced Usage

```python
from datetime import datetime, timezone, timedelta

# Set up time range for events
now = datetime.now(timezone.utc)
start_time = now - timedelta(days=30)  # Last 30 days
end_time = now + timedelta(days=30)    # Next 30 days

# Set up location data to incorporate
locations = [
    {
        "latitude": 37.7749,
        "longitude": -122.4194,
        "name": "San Francisco"
    },
    {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "name": "New York"
    }
]

# Set up named entities to reference
entities = {
    "person": [
        {"Id": "1234", "name": "John Smith", "category": "person"},
        {"Id": "5678", "name": "Jane Doe", "category": "person"}
    ],
    "organization": [
        {"Id": "abcd", "name": "Acme Corp", "category": "organization"}
    ]
}

# Generate events with comprehensive parameters
result = generator.execute({
    "count": 20,
    "criteria": {
        "user_email": "user@example.com",
        "user_name": "Test User",
        "provider": "outlook",
        "start_time": start_time,
        "end_time": end_time,
        "entities": entities,
        "location_data": locations
    }
})
```

## Data Model

Each generated calendar event includes:

- **Basic Event Properties**:
  - `event_id`: Unique identifier for the event
  - `subject`: Event title/subject
  - `body`: Event description
  - `start_time`: Event start time (ISO 8601 format)
  - `end_time`: Event end time (ISO 8601 format)
  - `is_all_day`: Whether it's an all-day event
  - `status`: Event status (confirmed, tentative, cancelled)
  - `importance`: Event importance level

- **Recurrence Information**:
  - `is_recurring`: Whether the event is recurring
  - `recurrence`: Recurrence pattern details (for master events)
    - `type`: Type of recurrence (daily, weekly, monthly, etc.)
    - `interval`: Frequency interval
    - `first_date`: First occurrence date
    - `until_date`: Recurrence end date
  - `series_master_id`: ID of the master event (for instances)
  - `instance_index`: Index in the series (for instances)

- **People Information**:
  - `organizer`: Event organizer details
  - `attendees`: List of event attendees with response status
  - `is_organizer`: Whether the user is the organizer
  - `response_status`: User's response to the event

- **Location Information**:
  - `location`: Physical or virtual location details
    - `display_name`: Location name
    - `address`: Optional physical address
    - `coordinates`: Optional latitude/longitude
    - `is_virtual`: Whether it's a virtual meeting
    - `join_url`: Meeting URL for virtual meetings
  - `is_online_meeting`: Whether it's an online meeting
  - `online_meeting_provider`: Provider name (Teams, Zoom, etc.)
  - `join_url`: Meeting join URL

- **Additional Information**:
  - `categories`: Event categories/tags
  - `attachments`: File attachments with metadata
  - `related_files`: Related document references

## Semantic Attributes

Each event is enriched with semantic attributes for querying:

- `EVENT_ID`: Unique event identifier
- `EVENT_SUBJECT`: Event subject/title
- `EVENT_START_TIME`: Event start time
- `EVENT_END_TIME`: Event end time
- `EVENT_LOCATION`: Event location name
- `EVENT_ORGANIZER`: Event organizer
- `EVENT_STATUS`: Event status
- `EVENT_RECURRENCE`: Recurrence pattern type
- `MEETING_TYPE`: Online meeting provider
- `MEETING_URL`: Online meeting URL
- `EVENT_ATTENDEE`: Event attendees
- `EVENT_RESPONSE`: User's response to the event

## Query Examples

The generated calendar events support rich querying capabilities:

```aql
// Find meetings with a specific person
FOR doc IN CalendarEvents
    FOR attr IN doc.SemanticAttributes
        FILTER attr.Identifier.Label == "EVENT_ATTENDEE"
        AND attr.Value == "John Smith"
        RETURN doc

// Find recurring events
FOR doc IN CalendarEvents
    FILTER doc.is_recurring == true
    RETURN doc

// Find events at a specific location
FOR doc IN CalendarEvents
    FOR attr IN doc.SemanticAttributes
        FILTER attr.Identifier.Label == "EVENT_LOCATION"
        AND attr.Value == "San Francisco"
        RETURN doc

// Find online meetings with a specific provider
FOR doc IN CalendarEvents
    FILTER doc.is_online_meeting == true
    AND doc.online_meeting_provider == "teams"
    RETURN doc
```

## Integration with Other Tools

The Calendar Event Generator integrates well with other Indaleko data generators:

- **LocationGeneratorTool**: Events can reference location data for physical meetings
- **NamedEntityGeneratorTool**: Events can include references to people and organizations
- **CloudStorageActivityGeneratorTool**: File activities can be correlated with calendar events

## Running Tests

To test the Calendar Event Generator:

### Linux/macOS
```bash
./run_calendar_tests.sh
```

### Windows
```batch
run_calendar_tests.bat
```

The tests verify:
1. Basic event generation with all required fields
2. Recurrence pattern generation and instance relationships
3. Database integration with ArangoDB
4. Query capability for various event attributes