# Location Metadata Generator Tool

## Overview

The LocationGeneratorTool is a comprehensive tool for generating realistic location metadata for the Indaleko data generator. It creates rich, contextual location data with proper semantic attributes that can be used to test and evaluate Indaleko's query capabilities.

## Features

- **User Location Profiles**: Generates realistic location patterns based on user profiles
- **Temporal Consistency**: Locations follow realistic patterns based on time of day, day of week
- **Place Categorization**: Categorizes locations as home, work, coffee shop, etc.
- **Rich Metadata**: Includes weather, POI (Point of Interest), and activity context
- **Multiple Location Types**: Supports GPS, WiFi, cell tower, IP, and Bluetooth location data
- **Realistic Movement**: Generates plausible movement patterns including commutes and trips
- **Semantic Attributes**: All location data is properly attached as semantic attributes

## Usage

### Basic Usage

```python
from tools.data_generator_enhanced.agents.data_gen.tools.location_generator import LocationGeneratorTool

# Create the generator
location_generator = LocationGeneratorTool()

# Generate location records
result = location_generator.execute({
    "count": 10,  # Number of records to generate
    "criteria": {
        "user_id": "user123",  # User ID for consistent locations
        "start_time": datetime.datetime.now() - datetime.timedelta(days=7),  # Start time
        "end_time": datetime.datetime.now(),  # End time
        "location_types": ["gps", "wifi"],  # Location types to include
        "include_weather": True,  # Include weather data
        "include_poi": True  # Include POI data
    }
})

# Access the records
location_records = result["records"]
```

### Integration with ActivityGeneratorTool

The LocationGeneratorTool is designed to integrate seamlessly with the ActivityGeneratorTool. You can use it to generate location context for activity records:

```python
# Generate location data
location_result = location_generator.execute({
    "count": 1,
    "criteria": {
        "user_id": user_id,
        "start_time": timestamp,
        "end_time": timestamp,
        "location_types": ["gps"]
    }
})
location = location_result["records"][0]

# Use location data with activity generator
activity_result = activity_generator.execute({
    "count": 1,
    "criteria": {
        "activity_type": "FILE_EDIT",
        "storage_object": file_object,
        "location": location
    }
})
```

## Data Model

Each location record includes:

```json
{
  "Id": "uuid-string",
  "UserId": "user-id",
  "Timestamp": "2023-05-04T14:30:00.000Z",
  "LocationType": "gps",
  "Latitude": 37.7749,
  "Longitude": -122.4194,
  "Accuracy": 5.2,
  "PlaceType": "coffee_shop",
  "Activity": "working",
  "Altitude": 12.5,
  "Speed": 0.5,
  "Weather": {
    "temperature": 18.5,
    "condition": "partly_cloudy",
    "humidity": 65,
    "wind_speed": 8.2,
    "season": "spring"
  },
  "POI": {
    "name": "JavaCup",
    "category": "coffee_shop",
    "distance": 3.5,
    "address": "123 Main St, Springfield, CA"
  },
  "SemanticAttributes": [
    {
      "Identifier": "uuid-for-location-type",
      "Value": "gps"
    },
    {
      "Identifier": "uuid-for-latitude",
      "Value": 37.7749
    },
    ...
  ]
}
```

## Semantic Attributes

The following semantic attributes are generated for each location record:

| Attribute Name | Description | Example Value |
|----------------|-------------|---------------|
| LOCATION_TYPE | Type of location detection | "gps", "wifi", "cell" |
| LOCATION_LATITUDE | Latitude coordinate | 37.7749 |
| LOCATION_LONGITUDE | Longitude coordinate | -122.4194 |
| LOCATION_ACCURACY | Accuracy in meters | 5.2 |
| LOCATION_PLACE_TYPE | Type of place | "home", "work", "coffee_shop" |
| LOCATION_ACTIVITY | Activity at location | "working", "dining", "traveling" |
| LOCATION_WEATHER_CONDITION | Weather condition | "sunny", "rainy", "cloudy" |
| LOCATION_WEATHER_TEMPERATURE | Temperature (Celsius) | 18.5 |
| LOCATION_POI_NAME | Name of nearby POI | "JavaCup", "Tech Campus" |
| LOCATION_POI_CATEGORY | Category of POI | "coffee_shop", "office" |

## Location Profiles

The tool uses LocationProfile objects to maintain consistent locations for users:

- **Home Location**: Base location where user lives
- **Work Location**: Office or workplace location
- **Frequent Places**: Regularly visited locations (coffee shops, gym, grocery store, etc.)
- **Daily Schedules**: Weekday and weekend activity patterns
- **Travel History**: Business trips, vacations, and other travel events

## Location Types

The tool supports multiple location detection methods with varying accuracy:

| Type | Accuracy Range (m) | Altitude | Speed |
|------|-------------------|----------|-------|
| GPS | 3-10 | Yes | Yes |
| WiFi | 15-50 | No | No |
| Cell | 100-1000 | No | Yes |
| IP | 1000-10000 | No | No |
| Bluetooth | 1-5 | No | No |

## Testing

Unit tests are available to verify the functionality of the LocationGeneratorTool:

```bash
# Linux/macOS
./tools/data_generator_enhanced/run_location_tests.sh

# Windows
tools\data_generator_enhanced\run_location_tests.bat
```

## Examples

### Generating a Week of Location Data

```python
from tools.data_generator_enhanced.agents.data_gen.tools.location_generator import LocationGeneratorTool
import datetime

# Create generator
location_generator = LocationGeneratorTool()

# Generate a week of hourly location data
start_time = datetime.datetime.now() - datetime.timedelta(days=7)
end_time = datetime.datetime.now()
hourly_records = []

for day in range(7):
    for hour in range(24):
        timestamp = start_time + datetime.timedelta(days=day, hours=hour)
        result = location_generator.execute({
            "count": 1,
            "criteria": {
                "user_id": "test_user",
                "start_time": timestamp,
                "end_time": timestamp + datetime.timedelta(minutes=1)
            }
        })
        hourly_records.extend(result["records"])

# Now hourly_records contains a week of hourly location data
```

### Generating Travel Data

```python
# Generate location data for a business trip
trip_start = datetime.datetime.now() - datetime.timedelta(days=14)
trip_end = trip_start + datetime.timedelta(days=3)

# Morning at hotel
hotel_location = location_generator.execute({
    "count": 1,
    "criteria": {
        "user_id": "business_traveler",
        "start_time": trip_start.replace(hour=8),
        "end_time": trip_start.replace(hour=8, minute=1),
        "location_types": ["wifi"]
    }
})["records"][0]

# Conference center during day
conference_location = location_generator.execute({
    "count": 1,
    "criteria": {
        "user_id": "business_traveler",
        "start_time": trip_start.replace(hour=10),
        "end_time": trip_start.replace(hour=10, minute=1),
        "location_types": ["gps"]
    }
})["records"][0]

# Restaurant in evening
restaurant_location = location_generator.execute({
    "count": 1,
    "criteria": {
        "user_id": "business_traveler",
        "start_time": trip_start.replace(hour=19),
        "end_time": trip_start.replace(hour=19, minute=1),
        "location_types": ["gps"]
    }
})["records"][0]
```

## Extending the Tool

The LocationGeneratorTool can be extended to support additional features:

- Add more location types (NFC, RFID, etc.)
- Implement additional POI categories
- Add specialized location contexts (hiking trails, beaches, etc.)
- Include time zone and international location support
- Add social context (presence of other users)