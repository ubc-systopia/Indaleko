# Cloud Storage Activity Generator

The CloudStorageActivityGeneratorTool is a component of the Indaleko data generator toolkit that creates realistic cloud storage activities with rich metadata for testing and development purposes.

## Overview

This tool generates synthetic cloud storage activities that can be used to populate test databases and evaluate query capabilities. It simulates realistic patterns including:

- File creation, modification, and sharing activities
- Hierarchical folder structures
- File metadata with MIME types and sizes
- Temporal patterns of user interactions
- Integration with calendar events and named entities
- Support for multiple providers (Google Drive, Dropbox)

## Features

- **Rich Activity Types**: Create, modify, rename, share, download, upload, etc.
- **Realistic File Structures**: Hierarchical folders with parent-child relationships
- **Temporal Consistency**: Activities follow realistic workflows and temporal patterns
- **Entity Integration**: Can reference named entities as file owners or collaborators
- **Calendar Alignment**: Activities can be aligned with calendar events for context
- **Semantic Attributes**: Activities include semantic attributes for querying
- **Provider Support**: Google Drive and Dropbox with provider-specific fields
- **Real-World Workflows**: Simulates common file usage patterns

## Usage

```python
from tools.data_generator_enhanced.agents.data_gen.tools.cloud_storage_generator import CloudStorageActivityGeneratorTool
from datetime import datetime, timezone, timedelta

# Initialize the generator
generator = CloudStorageActivityGeneratorTool()

# Generate Google Drive activities
now = datetime.now(timezone.utc)
start_time = now - timedelta(days=90)
end_time = now

gdrive_result = generator.execute({
    "count": 20,
    "criteria": {
        "user_email": "john.doe@example.com",
        "provider_type": "google_drive",
        "start_time": start_time,
        "end_time": end_time
    }
})

# Generate Dropbox activities
dropbox_result = generator.execute({
    "count": 20,
    "criteria": {
        "user_email": "john.doe@example.com",
        "provider_type": "dropbox",
        "start_time": start_time,
        "end_time": end_time
    }
})

# Get the activities and files
gdrive_activities = gdrive_result["activities"]
gdrive_files = gdrive_result["files"]
```

### Integration with Calendar Events

```python
from tools.data_generator_enhanced.agents.data_gen.tools.calendar_event_generator import CalendarEventGeneratorTool

# Generate calendar events
calendar_generator = CalendarEventGeneratorTool()
calendar_result = calendar_generator.execute({
    "count": 10,
    "criteria": {
        "user_email": "john.doe@example.com",
        "user_name": "John Doe",
        "start_time": start_time,
        "end_time": end_time
    }
})

# Generate cloud storage activities aligned with calendar events
result = generator.execute({
    "count": 30,
    "criteria": {
        "user_email": "john.doe@example.com",
        "provider_type": "google_drive",
        "start_time": start_time,
        "end_time": end_time,
        "calendar_events": calendar_result["events"]
    }
})
```

## Data Structure

### Activity Data

Each generated activity includes:

```json
{
  "activity_id": "unique-identifier",
  "timestamp": "2023-06-01T14:00:00Z",
  "activity_type": "create",
  "item_type": "file",
  "file_name": "Project Report.docx",
  "file_path": "Projects/Atlas/Documentation/Project Report.docx",
  "file_id": "file-id-123456789",
  "provider_type": "gdrive",
  "provider_id": "provider-id-123456789",
  "user_id": "john.doe@example.com",
  "user_name": "John Doe",
  "cloud_item_id": "cloud-item-id-123456789",
  "cloud_parent_id": "parent-folder-id-123456789",
  "shared": false,
  "web_url": "https://drive.google.com/file/d/file-id-123456789/view",
  "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "size": 12345,
  "is_directory": false,
  "created_time": "2023-05-15T10:30:00Z",
  "modified_time": "2023-06-01T14:00:00Z",
  "SemanticAttributes": [
    {
      "Identifier": {
        "Identifier": "f1a0c5d0-8e59-4c00-8c80-f80c1a3b4567",
        "Label": "STORAGE_ACTIVITY"
      },
      "Value": "true"
    },
    {
      "Identifier": {
        "Identifier": "f1a0c5d0-8e59-4c00-8c80-f80c1a3b4568",
        "Label": "FILE_CREATE"
      },
      "Value": "true"
    }
  ]
}
```

### Provider-specific Fields

#### Google Drive

```json
{
  "drive_id": "0ADxkfjd83jfkJDkslf",
  "parents": ["parent-folder-id-123456789"],
  "spaces": ["drive"],
  "version": "1"
}
```

#### Dropbox

```json
{
  "dropbox_file_id": "dropbox-file-id-123456789",
  "revision": "5e6f7g8h",
  "shared_folder_id": "shared-folder-id-123456789"
}
```

## File and Folder Structure

The generator creates a hierarchical file structure with folders and files:

```json
{
  "file_id": "folder-id-123456789",
  "cloud_item_id": "folder-id-123456789",
  "file_name": "Projects",
  "path": "Projects",
  "item_type": "directory",
  "is_directory": true,
  "provider_type": "gdrive",
  "cloud_parent_id": null,
  "children": ["subfolder-id-123456789", "file-id-123456789"],
  "created_time": "2023-01-15T10:30:00Z",
  "modified_time": "2023-06-01T14:00:00Z",
  "shared": false,
  "user_email": "john.doe@example.com",
  "mime_type": "application/vnd.google-apps.folder"
}
```

## Activity Types

The generator supports multiple activity types:

- **CREATE**: File or folder creation
- **MODIFY**: Content modification
- **DELETE**: File or folder deletion
- **RENAME**: Rename operation with preserved content
- **MOVE**: Move file or folder to a different location
- **COPY**: Copy operation with new file ID
- **SECURITY_CHANGE**: Permission or security setting changes
- **ATTRIBUTE_CHANGE**: Metadata changes without content changes
- **SHARE**: File sharing operation
- **UNSHARE**: Removing sharing permissions
- **READ**: File read/view operation
- **DOWNLOAD**: File download to local device
- **UPLOAD**: File upload to cloud storage
- **SYNC**: Synchronization operation between devices
- **VERSION**: New version created for versioned files
- **RESTORE**: Restore from previous version/trash
- **TRASH**: Moved to trash/recycle bin

## Running Tests

To run the test suite for the cloud storage activity generator:

**Linux/macOS:**
```bash
./run_cloud_storage_tests.sh
```

**Linux/macOS with database integration:**
```bash
./run_cloud_storage_tests.sh -db
```

**Windows:**
```cmd
run_cloud_storage_tests.bat
```

**Windows with database integration:**
```cmd
run_cloud_storage_tests.bat -db
```

## Integration with Other Generators

The cloud storage activity generator works best when integrated with:

1. **NamedEntityGeneratorTool**: For realistic user and collaborator entities
2. **CalendarEventGeneratorTool**: For context-aware file activities
3. **ChecksumGeneratorTool**: For enriching files with integrity data (future)

## Query Examples

This generator enables several types of queries:

1. **Provider-specific queries**:
   - "Show all my Google Drive files"
   - "Find files I've shared on Dropbox"
   - "List all files I've created in the Cloud"

2. **Activity-based queries**:
   - "When was the last time I modified this document?"
   - "Which files did I share last week?"
   - "What files have I downloaded recently?"

3. **Cross-domain queries**:
   - "Find documents I edited during my meeting with Jane"
   - "Show files related to the Atlas project I worked on yesterday"
   - "What presentations did I share during the conference last month?"

4. **Metadata queries**:
   - "Find all spreadsheets over 5MB"
   - "Show me documents with 'Budget' in the filename"
   - "List all PDFs in my Project folders"

## Implementation Notes

- All activities include proper, timezone-aware timestamps
- File paths maintain hierarchical consistency and proper parent-child relationships
- Activities follow realistic temporal workflows (create → modify → share)
- Semantic attributes are structured according to the Indaleko schema
- Folder structures follow common organizational patterns
- MIME types and file extensions are properly matched
- File naming follows realistic patterns based on file type and purpose