# Environmental Metadata Generator

The Environmental Metadata Generator creates realistic environmental data for the Indaleko system, including weather conditions and indoor climate data. This synthetic data enables testing of queries that involve environmental context, such as "photos taken on rainy days" or "documents edited when it was hot outside."

## Features

- **Weather Data Generation**
  - Realistic weather patterns with proper seasonal variation
  - Temperature, precipitation, humidity, and wind parameters
  - Temporal consistency with gradual weather transitions
  - Location-based conditions (Northern/Southern hemisphere seasonal differences)
  - Proper semantic attributes for querying

- **Indoor Climate Data Generation**
  - Room-specific temperature and humidity values
  - HVAC system states (heating, cooling, idle)
  - Occupancy detection patterns based on time of day
  - Target temperature adjustments based on schedule
  - Correlations with outdoor conditions

- **Database Integration**
  - Direct insertion into ArangoDB with proper schemas
  - Semantic attributes for effective querying
  - Adheres to Indaleko's data model requirements
  - Proper timezone-aware timestamps

## Core Components

### `WeatherCondition` Class
Provides weather condition types, ranges, and probability distributions:
- Clear, partly cloudy, cloudy, rain, thunderstorm, snow, fog, etc.
- Seasonal probability distributions (winter, spring, summer, fall)
- Parameter ranges for each condition (temperature, humidity, etc.)
- Helper methods for selecting conditions based on location/season

### `WeatherData` Class
Represents a single weather observation:
- Location (latitude, longitude, label)
- Condition type (clear, rain, etc.)
- Temperature, humidity, precipitation, wind speed
- ISO-formatted timestamp

### `IndoorClimateData` Class
Represents indoor climate conditions:
- Room information (name, device ID)
- Temperature and humidity readings
- HVAC mode and state (heat/cool, heating/cooling/idle)
- Target temperature setting
- Occupancy detection and air quality info

### `EnvironmentalMetadataGenerator` Class
Main generator implementation:
- `generate_weather_data()`: Creates weather dataset
- `generate_indoor_climate_data()`: Creates indoor climate dataset
- Database insertion methods with proper error handling
- Activity data model creation with semantic attributes

### `EnvironmentalMetadataGeneratorTool` Class
High-level interface for generating combined datasets:
- Generates both weather and indoor climate data
- Provides summary statistics on generated data
- Handles database interaction
- Supports limiting result sets and date ranges

## Usage Examples

### Basic Usage

```python
from datetime import datetime, timedelta, timezone
from tools.data_generator_enhanced.agents.data_gen.tools.environmental_metadata_generator import EnvironmentalMetadataGeneratorTool

# Initialize the generator tool
generator = EnvironmentalMetadataGeneratorTool()

# Generate data for the past week
start_date = datetime.now(timezone.utc) - timedelta(days=7)
end_date = datetime.now(timezone.utc)

result = generator.generate_environmental_data(
    start_date=start_date,
    end_date=end_date,
    locations=[{
        "latitude": 40.7128,
        "longitude": -74.0060,
        "label": "Home"
    }],
    count_weather=24,  # One reading per hour for a day
    count_climate=24,  # One reading per hour for a day
    insert_to_db=True  # Insert into database
)

print(f"Generated {result['total_weather_records']} weather records")
print(f"Generated {result['total_climate_records']} climate records")
print(f"Inserted {result['weather_db_inserts']} weather records into database")
print(f"Inserted {result['climate_db_inserts']} climate records into database")
```

### Query Examples

The generated data enables complex queries in ArangoDB:

```aql
// Find photos taken on rainy days
FOR doc IN Objects
  FILTER doc.MIMEType LIKE "image/%"
  LET photo_timestamp = doc.Timestamp
  
  LET weather = (
    FOR w IN TempActivityData
      FILTER w.Timestamp >= photo_timestamp - 3600
      FILTER w.Timestamp <= photo_timestamp + 3600
      LET data = JSON_PARSE(w.Record.Data)
      FILTER data.condition == "rain"
      SORT ABS(DATE_DIFF(w.Timestamp, photo_timestamp, "s"))
      LIMIT 1
      RETURN data
  )
  
  FILTER LENGTH(weather) > 0
  RETURN {
    photo: doc,
    weather_condition: weather[0].condition,
    temperature: weather[0].temperature
  }
```

```aql
// Find documents edited when indoor temperature was above 23°C
FOR activity IN ActivityData
  FILTER activity.Type == "FileEdit"
  
  LET climate = (
    FOR c IN TempActivityData
      FILTER c.Timestamp >= activity.Timestamp - 1800
      FILTER c.Timestamp <= activity.Timestamp + 1800
      
      FOR attr IN c.SemanticAttributes
        FILTER attr.Identifier.Identifier == "c5e2c8d0-6b7e-4d8f-a1c2-f0d2a5e7b9c3" // TEMPERATURE_INDOOR_UUID
        FILTER attr.Data > 23.0
        SORT ABS(DATE_DIFF(c.Timestamp, activity.Timestamp, "s"))
        LIMIT 1
        RETURN c
  )
  
  FILTER LENGTH(climate) > 0
  RETURN {
    activity: activity,
    file: activity.ObjectID,
    indoor_temperature: climate[0].SemanticAttributes[0].Data
  }
```

## Sample Record Structure

### Weather Data Record
```json
{
  "Timestamp": "2025-05-01T14:00:00.000Z",
  "Record": {
    "SourceIdentifier": {
      "Identifier": "51e7c8d2-4a3f-45b9-8d1e-9c2a5b3f7e6d",
      "Version": "1.0.0",
      "Description": "Weather Data Generator"
    },
    "Timestamp": "2025-05-01T14:00:00.000Z",
    "Data": "{\"timestamp\": \"2025-05-01T14:00:00.000Z\", \"location\": {\"latitude\": 40.7128, \"longitude\": -74.0060, \"label\": \"Home\"}, \"condition\": \"partly_cloudy\", \"temperature\": 22.5, \"humidity\": 65.0, \"precipitation\": 0.0, \"wind_speed\": 10.5}"
  },
  "SemanticAttributes": [
    {
      "Identifier": {
        "Identifier": "69f7a1b0-5c4c-4a7f-8d3e-cd6cb0e6a129",
        "Version": "1",
        "Description": "condition"
      },
      "Data": "partly_cloudy"
    },
    {
      "Identifier": {
        "Identifier": "53c3e8d7-aa21-4b5f-9f3c-5b8a6f91e0a2",
        "Version": "1",
        "Description": "temperature"
      },
      "Data": 22.5
    }
  ]
}
```

### Indoor Climate Data Record
```json
{
  "Timestamp": "2025-05-01T14:00:00.000Z",
  "Record": {
    "SourceIdentifier": {
      "Identifier": "6ea66ced-5a54-4cba-a421-50d5671021cb",
      "Version": "1.0.0",
      "Description": "Smart Thermostat Data Generator"
    },
    "Timestamp": "2025-05-01T14:00:00.000Z",
    "Data": "{\"timestamp\": \"2025-05-01T14:00:00.000Z\", \"location\": {\"room\": \"Living Room\"}, \"temperature\": 21.5, \"humidity\": 45.0, \"hvac_mode\": \"auto\", \"hvac_state\": \"idle\", \"fan_mode\": \"auto\", \"target_temperature\": 22.0, \"device_id\": \"ecobee123abc\", \"device_name\": \"Living Room\", \"occupancy_detected\": true, \"air_quality\": 85}"
  },
  "SemanticAttributes": [
    {
      "Identifier": {
        "Identifier": "c5e2c8d0-6b7e-4d8f-a1c2-f0d2a5e7b9c3",
        "Version": "1",
        "Description": "temperature"
      },
      "Data": 21.5
    },
    {
      "Identifier": {
        "Identifier": "7d8e9f0a-1b2c-3d4e-5f6g-7h8i9j0k1l2m",
        "Version": "1",
        "Description": "humidity"
      },
      "Data": 45.0
    }
  ]
}
```

## Integration with Other Generators

The Environmental Metadata Generator works particularly well with:

1. **Location Generator** - Correlate weather with GPS positions
2. **EXIF Generator** - Add weather conditions to photo metadata
3. **Activity Generator** - Create realistic indoor activities based on weather

## Running Tests

To run the tests for the Environmental Metadata Generator:

### Linux/macOS:
```sh
./run_environmental_tests.sh
```

### Windows:
```cmd
run_environmental_tests.bat
```

## Database Collections

The generator uses the following database collections:
- `Indaleko_TempActivityData_Collection` - For both weather and indoor climate data

## Semantic Attributes

The following semantic attribute UUIDs are used:

| Attribute | UUID | Description |
|-----------|------|-------------|
| Weather Condition | 69f7a1b0-5c4c-4a7f-8d3e-cd6cb0e6a129 | Type of weather (clear, rain, etc.) |
| Outdoor Temperature | 53c3e8d7-aa21-4b5f-9f3c-5b8a6f91e0a2 | Outdoor temperature in Celsius |
| Indoor Temperature | c5e2c8d0-6b7e-4d8f-a1c2-f0d2a5e7b9c3 | Indoor temperature in Celsius |
| Outdoor Humidity | 2a7c1e95-6d3f-4b0a-9c1d-8e6f4a2b5c3d | Outdoor humidity percentage |
| Indoor Humidity | 7d8e9f0a-1b2c-3d4e-5f6g-7h8i9j0k1l2m | Indoor humidity percentage |
| Wind Speed | 4b5c6d7e-8f9g-0h1i-2j3k-4l5m6n7o8p9 | Wind speed in km/h |
| Precipitation | 9a8b7c6d-5e4f-3g2h-1i0j-9k8l7m6n5o | Precipitation amount in mm |
| Air Quality | 0p9o8n7m-6l5k-4j3h-2g1f-0e9d8c7b6a | Indoor air quality index |