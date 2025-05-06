# Activity Metadata Generator

The Activity Metadata Generator is responsible for creating realistic activity metadata records that represent user activities associated with files in Indaleko. These activities include location data (where files were created or accessed), music playback information, and temperature/environmental data.

## Supported Activity Types

The generator currently supports three main types of activity metadata:

### 1. Location Activity

Represents geographical location data associated with files:
- Latitude and longitude coordinates
- Accuracy and altitude information
- City, country, and region data
- Timezone information

These records simulate location data captured when users interact with files, such as creating documents while traveling or accessing files from different locations.

### 2. Music Activity

Represents music playback data associated with files:
- Artist, track, and album information
- Genre classification
- Duration of playback
- Music service (Spotify, Apple Music, etc.)

These records simulate scenarios where users might be listening to music while working on documents or media files.

### 3. Temperature Activity

Represents environmental data associated with files:
- Temperature readings (in Celsius)
- Humidity levels
- Smart device information (thermostats, sensors)
- Room location data

These records simulate smart home/office integration where environmental conditions are captured during file operations.

## Implementation Details

### Database Integration

The Activity Metadata Generator directly interacts with the following ArangoDB collections:
- `GeoActivityData_Collection` - For location activity records
- `MusicActivityData_Collection` - For music playback records
- `TempActivityData_Collection` - For temperature/environmental records

Each record includes:
- Reference to a storage object (_key)
- Standardized Record structure (Version, Source, Type, etc.)
- Timestamp information
- Semantic attributes specific to the activity type
- Activity-specific metadata fields

### Truth Record Generation

The generator supports creating "truth records" with specific characteristics for testing search capabilities:
- Location records for specific cities (e.g., New York)
- Music records for specific artists or genres
- Temperature records for specific environments

These truth records can be used to validate search queries that target specific activity contexts.

## Usage Examples

### General Activity Generation

```python
# Initialize the generator with database connection
activity_generator = ActivityMetadataGeneratorImpl({}, db_config)

# Generate 100 random activity records
activity_records = activity_generator.generate(100)
```

### Generating Specific Activity Types

```python
# Generate location activity in New York
location_records = activity_generator.generate_truth(5, {
    "storage_keys": ["key1", "key2", "key3", "key4", "key5"],
    "activity_criteria": {
        "type": "location",
        "city": "New York",
        "latitude": 40.7128,
        "longitude": -74.0060
    }
})

# Generate classical music activity
music_records = activity_generator.generate_truth(3, {
    "storage_keys": ["key6", "key7", "key8"],
    "activity_criteria": {
        "type": "music",
        "artist": "Mozart",
        "genre": "Classical"
    }
})
```

## Extending the Generator

To add new activity types or enhance existing ones:

1. Add new model classes in the activity.py file
2. Implement the generation logic in the ActivityMetadataGeneratorImpl class
3. Update the `_generate_activity_metadata` method to include the new activity type
4. Add collection initialization in the `_ensure_collections_exist` method
5. Implement methods for truth record generation for the new activity type
