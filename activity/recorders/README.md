# Indaleko Activity Recorders

**Note: This documentation was updated as part of the implementation of service registration for the NTFS Activity Recorder and verification of the Location Data Recorder registration. It now includes information about the TemplateRecorder base class for simplified implementations.**

This directory contains the recorder implementations for various activity types in the Indaleko system.

## Overview

Recorders are responsible for taking data from collectors and storing it in the Indaleko database. They follow a consistent pattern that includes:

1. Collecting data from various sources
2. Processing and transforming the data
3. Storing the data in the database
4. Registering with the activity service manager

## Service Registration

Activity recorders should register with the `IndalekoActivityDataRegistrationService` to make their data and capabilities visible to the query system. This registration process:

1. Creates a unique collection for the recorder's data
2. Registers the semantic attributes and schemas supported by the recorder
3. Makes the data discoverable by the query interface
4. Enables cross-activity relationships and queries

### Implementing Service Registration

To properly register an activity recorder, follow these steps:

1. Import the registration service:
   ```python
   from data_models.activity_data_registration import IndalekoActivityDataRegistrationDataModel
   from activity.recorders.registration_service import IndalekoActivityDataRegistrationService
   ```

2. Create a source identifier:
   ```python
   source_identifier = IndalekoSourceIdentifierDataModel(
       Identifier=self._recorder_id,
       Version=self._version,
       Description=self._description
   )
   ```

3. Create a record data model:
   ```python
   record = IndalekoRecordDataModel(
       SourceIdentifier=source_identifier,
       Timestamp=datetime.now(timezone.utc),
       Attributes={},
       Data=""
   )
   ```

4. Register with the service manager:
   ```python
   registration_kwargs = {
       "Identifier": str(self._recorder_id),
       "Name": self._name,
       "Description": self._description,
       "Version": self._version,
       "Record": record,
       "DataProvider": "Your Activity Type",
       "DataProviderType": "Activity",
       "DataProviderSubType": "YourSubType",
       "DataProviderCollectionName": self._collection_name,
       "CreateCollection": True,
       "SourceIdentifiers": [
           # Add relevant semantic attribute UUIDs
       ],
       "SchemaIdentifiers": [
           # Add relevant schema UUIDs
       ],
       "Tags": ["your", "relevant", "tags"]
   }
   
   service = IndalekoActivityDataRegistrationService()
   service.register_provider(**registration_kwargs)
   ```

## Available Recorders

### NTFS Activity Recorder

Records file system activities from the NTFS USN Journal on Windows systems.

```python
from activity.recorders.ntfs_activity.ntfs_activity_recorder import NtfsActivityRecorder

recorder = NtfsActivityRecorder(
    auto_connect=True,  # Connect to database automatically
    register_service=True  # Register with service manager
)
```

### Location Data Recorders

Records location data from various sources including Windows GPS, IP geolocation, WiFi positioning, and more.

```python
from activity.recorders.location.windows_gps_location import WindowsGPSLocationRecorder

recorder = WindowsGPSLocationRecorder()
```

### Calendar Event Recorder

Records calendar events from Google Calendar and Microsoft Outlook.

```python
from activity.recorders.collaboration.calendar_recorder import CalendarRecorder

recorder = CalendarRecorder(
    collection_name="CalendarEvents"
)
```

## Testing Registration

Use the included test scripts to verify your service registration implementation:

- For NTFS Activity: `python -m activity.recorders.ntfs_activity.test_registration`
- For Location Data: `python -m activity.recorders.location.test_registration`

## Adding New Recorders

When adding a new recorder, you have two options:

### Option 1: Use the TemplateRecorder (Recommended)

The easiest way to create a new recorder is to extend the `TemplateRecorder` class:

```python
from activity.recorders.template import TemplateRecorder

class YourCustomRecorder(TemplateRecorder):
    """Your custom recorder implementation."""
    
    def __init__(self, **kwargs):
        # Set your defaults
        kwargs.setdefault("name", "Your Custom Recorder")
        kwargs.setdefault("recorder_id", uuid.UUID("your-custom-uuid"))
        # ...other defaults
        
        # Initialize template
        super().__init__(**kwargs)
        
        # Your custom setup
        # ...
    
    def collect_and_process_data(self) -> List[Any]:
        """Implement your data collection logic here."""
        # ...
    
    def get_collector_class_model(self) -> Dict[str, Type]:
        """Return your collector class model."""
        # ...
    
    def get_json_schema(self) -> dict:
        """Return your JSON schema."""
        # ...
```

See the examples in `activity/recorders/examples/` for a complete example.

### Option 2: Extend RecorderBase Directly

For more control, you can extend `RecorderBase` directly:

1. Extend the appropriate base class (`RecorderBase` or a specialized subclass)
2. Implement all abstract methods
3. Register with the activity service manager
4. Provide proper error handling and logging
5. Document your recorder in this README

## Template Class Features

The `TemplateRecorder` class provides several benefits:

1. **Simplified Service Registration**: Automatically handles registration with the activity service manager
2. **Default Implementations**: Provides sensible defaults for common methods
3. **Error Handling**: Built-in error handling and logging
4. **Standardized Document Formatting**: Consistent formatting of documents for the database

You only need to implement three abstract methods:
- `collect_and_process_data()`: Your data collection logic
- `get_collector_class_model()`: Information about your collector
- `get_json_schema()`: The JSON schema for your data

See the template class documentation in `activity/recorders/template.py` for more details.