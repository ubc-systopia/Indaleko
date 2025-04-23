# Indaleko Activity Recorder Examples

This directory contains example implementations of activity recorders using the template class.

## SimpleActivityRecorder

The `simple_recorder.py` file demonstrates how to create a minimal activity recorder using the `TemplateRecorder` base class. This example shows:

1. How to create a custom activity data model
2. How to implement a basic collector
3. How to extend the template recorder with minimal code
4. How to define and use semantic attributes
5. How to register with the activity service

### Key Components

1. **SimpleActivity**: A minimal data model for activity data
2. **SimpleCollector**: A basic collector that generates sample activities
3. **SimpleActivityRecorder**: A recorder that extends TemplateRecorder

### Using the Example

To run the example:

```bash
python -m activity.recorders.examples.simple_recorder
```

This will create the recorder, show its configuration, and collect sample activities. For database operations, you'll need to uncomment the relevant lines in the main function.

### Customizing with Your Own Recorder

To create your own recorder based on this example:

1. Start by copying the example
2. Replace SimpleActivity with your data model
3. Replace SimpleCollector with your collection logic
4. Update the UUIDs and semantic attributes to match your use case
5. Update the `collect_and_process_data` method with your specific logic

The template handles:
- Database connections
- Service registration
- Document formatting
- Error handling
- Logging

You only need to implement the specific logic for your data source.

## Advantages of Using TemplateRecorder

The template recorder significantly reduces the amount of code you need to write:

- **Without template**: ~200-300 lines of code
- **With template**: ~150 lines of code, with most being specific to your use case

More importantly, the template handles all the complex parts:

1. Service registration with proper parameters
2. Database connection management
3. Error handling and logging
4. Document formatting and structure

You only need to focus on the specific logic for your data source.

## Example Recorder Implementations

For more complex examples, refer to the actual recorders in the Indaleko codebase:

1. **NTFS Activity**: `/activity/recorders/ntfs_activity/ntfs_activity_recorder.py`
2. **Windows GPS Location**: `/activity/recorders/location/windows_gps_location.py`
3. **Calendar Events**: `/activity/recorders/collaboration/calendar_recorder.py`
