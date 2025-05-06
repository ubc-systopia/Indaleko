# EXIF Generator Tool for Indaleko Data Generator

## Overview

The EXIF Generator Tool is a powerful component of the Indaleko data generator framework that creates realistic EXIF metadata for image files. This tool enhances the synthetic data capabilities by generating rich, queryable EXIF data with proper semantic attributes.

## Features

- **Comprehensive EXIF Generation**: Creates complete EXIF metadata including camera information, GPS data, capture settings, and image attributes
- **Real Database Integration**: Connects to ArangoDB to find image files and store generated metadata
- **Diverse Camera Profiles**: Supports multiple camera types including DSLRs, mirrorless cameras, smartphones, and drones
- **Semantic Attribute Integration**: Generates properly structured semantic attributes with standard UUIDs
- **Realistic GPS Data**: Options for random GPS coordinates or location-specific data
- **Temporal Consistency**: Ensures timestamps are coherent across related data
- **Configurable Generation**: Parameters for customizing generated data

## Usage

### Basic Usage

```python
from tools.data_generator_enhanced.agents.data_gen.tools.exif_generator import EXIFGeneratorTool

# Initialize the tool
exif_generator = EXIFGeneratorTool()

# Generate EXIF metadata
result = exif_generator.execute({
    "count": 5,  # Number of records to generate
    "criteria": {
        "user_id": "test_user",
        "camera_types": ["canon", "nikon", "iphone"],
        "time_range": {
            "start": (datetime.datetime.now() - datetime.timedelta(days=30)).timestamp(),
            "end": datetime.datetime.now().timestamp()
        }
    }
})

# Access generated records
records = result["records"]
```

### Advanced Options

```python
# Generate EXIF metadata with specific storage IDs and GPS location
result = exif_generator.execute({
    "count": 10,
    "criteria": {
        "user_id": "test_user",
        "storage_ids": ["id1", "id2", "id3"],  # Specific storage IDs
        "camera_types": ["sony", "fujifilm"],  # Specific camera types
        "time_range": {
            "start": specific_start_time,
            "end": specific_end_time
        },
        "location_coordinates": {
            "latitude": 37.7749,
            "longitude": -122.4194
        }
    }
})
```

## EXIF Record Structure

Generated EXIF records include the following components:

```
{
  "_key": "uuid",
  "Object": "storage_id",
  "UserId": "user_id",
  "Timestamp": timestamp,
  "CameraData": {
    "make": "Canon",
    "model": "EOS 5D Mark IV",
    "serial_number": "CANON-12345678",
    "lens_make": "Canon",
    "lens_model": "EF 24-70mm f/2.8L II USM",
    "software": "Digital Photo Professional"
  },
  "CaptureSettings": {
    "date_time": timestamp,
    "exposure_time": "1/250",
    "aperture": "f/2.8",
    "iso": 800,
    "focal_length": "50mm",
    "flash": false,
    "scene_type": "landscape",
    "exposure_program": "aperture_priority",
    "metering_mode": "pattern",
    "white_balance": "auto"
  },
  "ImageInfo": {
    "width": 6000,
    "height": 4000,
    "bit_depth": 24,
    "color_space": "sRGB",
    "orientation": "horizontal",
    "software": "Digital Photo Professional",
    "artist": "user_id"
  },
  "GpsData": {
    "latitude": 37.7749,
    "longitude": -122.4194,
    "altitude": 15.5,
    "date": "2024:05:01",
    "time": "14:30:22"
  },
  "SemanticAttributes": [
    {...semantic attributes...}
  ],
  "MIMEType": "image/jpeg"
}
```

## Semantic Attributes

The EXIF generator creates semantic attributes with standardized UUIDs for the following EXIF properties:

- **EXIF_DATA**: Main EXIF indicator
- **EXIF_CAMERA_MAKE**: Camera manufacturer
- **EXIF_CAMERA_MODEL**: Camera model name
- **EXIF_CAMERA_SERIAL**: Camera serial number
- **EXIF_LENS_MAKE**: Lens manufacturer
- **EXIF_LENS_MODEL**: Lens model name
- **EXIF_DATETIME**: Image capture date/time
- **EXIF_EXPOSURE**: Exposure time (e.g., "1/250")
- **EXIF_APERTURE**: Aperture value (e.g., "f/2.8")
- **EXIF_ISO**: ISO sensitivity
- **EXIF_FOCAL_LENGTH**: Focal length (e.g., "50mm")
- **EXIF_WIDTH**: Image width in pixels
- **EXIF_HEIGHT**: Image height in pixels
- **EXIF_ORIENTATION**: Image orientation
- **EXIF_GPS_LATITUDE**: GPS latitude
- **EXIF_GPS_LONGITUDE**: GPS longitude
- **EXIF_GPS_ALTITUDE**: GPS altitude

## Supported Camera Types

The EXIF generator supports the following camera types:

- **Smartphones**: iPhone, Samsung, Google Pixel
- **DSLR Cameras**: Canon, Nikon, Sony
- **Mirrorless Cameras**: Fujifilm, Sony
- **Compact Cameras**: Panasonic
- **Drones**: DJI

## Integration with Other Components

The EXIF Generator Tool is designed to work with:

1. **Storage Metadata**: Finds and attaches to existing storage records in the database
2. **Location Data**: Can use coordinates from the LocationGeneratorTool
3. **Semantic Registry**: Uses the standardized SemanticAttributeRegistry
4. **Database Configuration**: Integrates with IndalekoDBConfig for database access

## Testing

Run the tests using the provided scripts:

```
# Linux/macOS
./tools/data_generator_enhanced/run_exif_tests.sh

# Windows
tools\data_generator_enhanced\run_exif_tests.bat
```

## Implementation Details

- Uses real data models from the Indaleko codebase
- Connects to the database to find image files and store metadata
- Creates proper semantic attributes with standardized UUIDs
- Generates realistic camera profiles based on actual camera models
- Follows the Indaleko Tool interface pattern