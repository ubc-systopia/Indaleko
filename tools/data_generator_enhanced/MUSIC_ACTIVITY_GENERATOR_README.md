# MusicActivityGenerator

The MusicActivityGenerator creates realistic music listening activity data that simulates Spotify usage patterns. This tool generates temporally consistent listening sessions with proper artist, genre, and device correlations for testing Indaleko's music activity context capabilities.

## Features

- **Temporal Consistency**: Generates listening patterns that follow realistic daily rhythms
- **Location Integration**: Creates correlations between music listening and physical locations
- **Genre Preferences**: Simulates user genre preferences with weighted probabilities
- **Artist Catalog**: Maintains a consistent artist/album/track catalog
- **Audio Features**: Includes Spotify-specific audio characteristics (danceability, energy, etc.)
- **Device Patterns**: Correlates device usage with location contexts
- **Semantic Attributes**: Proper semantic attribute handling for Indaleko's querying system

## Usage

```python
from tools.data_generator_enhanced.agents.data_gen.tools.music_activity_generator import MusicActivityGeneratorTool
from datetime import datetime, timedelta, timezone

# Initialize the generator
generator = MusicActivityGeneratorTool()

# Generate music activity for the past week
result = generator.generate_music_activities(
    start_date=datetime.now(timezone.utc) - timedelta(days=7),
    end_date=datetime.now(timezone.utc),
    count=100,  # Optional: specify exact number of activities
    insert_to_db=True  # Insert directly to database
)

# View summary statistics
print(f"Generated {result['total_records']} music activity records")
print(f"Top artists: {result['top_artists']}")
print(f"Device distribution: {result['device_distribution']}")
```

### Location Integration

```python
# Sample location data (can come from LocationGeneratorTool)
location_data = [
    {
        "timestamp": "2024-05-03T08:30:00+00:00",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "location_type": "home",
        "label": "Home"
    },
    {
        "timestamp": "2024-05-03T14:15:00+00:00", 
        "latitude": 37.7833,
        "longitude": -122.4167,
        "location_type": "work",
        "label": "Office"
    }
]

# Generate music activity that correlates with locations
result = generator.generate_music_activities(
    start_date=datetime.now(timezone.utc) - timedelta(days=1),
    end_date=datetime.now(timezone.utc),
    location_data=location_data,
    insert_to_db=True
)
```

## Data Model

The MusicActivityGenerator uses the same data model as Indaleko's ambient music collectors, ensuring compatibility with the database and querying systems:

- **Base Model**: `AmbientMusicData` from `activity/collectors/ambient/music/music_data_model.py`
- **Spotify Model**: `SpotifyAmbientData` from `activity/collectors/ambient/music/spotify_data_model.py`
- **Database Collection**: Uses `IndalekoDBCollections.Indaleko_MusicActivityData_Collection`

### Key Fields

Each music activity record includes:

- **Track Information**: Name, artist, album, duration 
- **Playback State**: Position, playing status, volume
- **Device Context**: Device type, name
- **Spotify Details**: Track/artist/album IDs, shuffle/repeat state
- **Audio Features**: Danceability, energy, valence, instrumentalness, acousticness
- **Semantic Attributes**: Properly formatted for database querying

## Sample Queries

Generated data supports natural language queries like:

### Time-Based Queries
```aql
// Find music I listened to yesterday
FOR doc IN MusicActivityContext
  FILTER doc.Timestamp >= @yesterday_start AND doc.Timestamp <= @yesterday_end
  RETURN doc
```

### Device-Based Queries
```aql
// Find songs I listen to on my Speaker
FOR doc IN MusicActivityContext
  FOR attr IN doc.SemanticAttributes
    FILTER attr.Identifier.Identifier == @device_id AND attr.Data == "Speaker"
    RETURN doc
```

### Artist-Based Queries
```aql
// Find all songs by a specific artist
FOR doc IN MusicActivityContext
  FOR attr IN doc.SemanticAttributes
    FILTER attr.Identifier.Identifier == @artist_id AND attr.Data == "Queen"
    RETURN doc
```

### Combined Context Queries
```aql
// Find upbeat music I listen to at the gym
FOR doc IN MusicActivityContext
  FILTER doc.Timestamp >= @start_date AND doc.Timestamp <= @end_date
  LET is_at_gym = (
    FOR loc IN LocationContext
      FILTER loc.Timestamp <= doc.Timestamp
      FILTER loc.Timestamp >= DATE_SUBTRACT(doc.Timestamp, 1, "hour")
      FILTER loc.location_type == "gym"
      LIMIT 1
      RETURN 1
  )
  LET is_upbeat = (
    FOR attr IN doc.SemanticAttributes
      FILTER attr.Identifier.Description == "energy" AND TO_NUMBER(attr.Data) >= 0.7
      LIMIT 1
      RETURN 1
  )
  FILTER LENGTH(is_at_gym) > 0 AND LENGTH(is_upbeat) > 0
  RETURN doc
```

## Testing

Run the test suite with the included test scripts:

```bash
# Linux/macOS
./tools/data_generator_enhanced/run_music_tests.sh

# Windows
.\tools\data_generator_enhanced\run_music_tests.bat
```

The tests include:
- Unit tests for all generator components
- Database integration tests that verify proper storage and retrieval
- Complex query tests that validate natural language query capabilities

## Integration with Other Generators

The MusicActivityGenerator is designed to work with other Indaleko generators:

- **LocationGeneratorTool**: Correlate music listening with physical locations
- **SocialMediaActivityGeneratorTool**: Create shared context between social media and music
- **CalendarEventGeneratorTool**: Correlate music with calendar events (e.g., workout sessions)

## Implementation Details

The generator creates a rich internal model of the user's music preferences:

1. **Genre Preferences**: Each simulated user has 2-4 favorite genres with higher weights
2. **Artist Catalog**: Maintains artists, albums, and tracks with consistent durations and attributes
3. **Temporal Patterns**: Models realistic listening times (morning commute, work hours, evening)
4. **Location Correlations**: Maps location types to device preferences

The tool ensures proper ArangoDB integration by:
- Using correct collection names from `IndalekoDBCollections`
- Generating proper semantic attributes with UUIDs from known semantic attribute registries
- Creating timezone-aware timestamps for all records
- Using dictionary access patterns for database compatibility