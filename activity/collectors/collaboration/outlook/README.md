# Outlook Email File Sharing Activity Generator for Indaleko

## Overview

The Outlook Email File Sharing Activity Generator is a component for the Indaleko system that collects, processes, and stores information about files shared through Microsoft Outlook emails. It follows Indaleko's collector/recorder architecture pattern, where:

- **Collector**: Sets up a web service with ngrok tunneling to receive data from a custom Outlook add-in when emails with file attachments or links are sent
- **Recorder**: Processes file sharing data and stores it in the Indaleko database with appropriate semantic attributes

This component tracks files shared via email attachments, as well as OneDrive and SharePoint links embedded in emails, providing a comprehensive view of file sharing activity through Microsoft's tools.

## Architecture

The Outlook Email File Sharing Activity Generator consists of:

1. **Data Models**:
   - `SharedFileData`: Represents a shared file with properties like filename, URL, size, and content type
   - `EmailFileShareData`: Represents an email file sharing event with email metadata and file data

2. **Collector**:
   - `OutlookFileShareCollector`: Sets up a local web service with ngrok tunneling
   - Generates and serves an Outlook add-in manifest for installation
   - Provides a web API for the add-in to send data when emails are sent
   - Extracts metadata about shared files including filename, type, and context

3. **Recorder**:
   - `OutlookFileShareRecorder`: Processes file sharing data and stores it in the Indaleko database
   - Creates semantic attributes for efficient querying
   - Provides utilities for retrieving and querying file sharing information
   - Supports both collector-based and file-based data import

4. **Outlook Add-in**:
   - JavaScript client that runs within Outlook
   - Extracts file attachment details
   - Identifies OneDrive and SharePoint links in email content
   - Sends data to the collector's web API

## Features

- Secure data collection via ngrok tunneling
- Add-in automatic manifest generation
- Support for regular attachments, OneDrive links, and SharePoint links
- Comprehensive metadata capture (sender, recipients, subject, timestamp)
- Advanced querying capabilities (by filename, sender, content type)
- Integration with Microsoft's Office add-in ecosystem
- Support for both web and desktop Outlook clients

## Requirements

- Python 3.7+
- Flask
- pyngrok
- Microsoft Outlook (desktop or web)
- Internet connection for ngrok tunneling

## Usage

### Setting Up the Collector

```python
from activity.collectors.collaboration.outlook.outlook_file_collector import OutlookFileShareCollector
from activity.recorders.collaboration.outlook_file_recorder import OutlookFileShareRecorder

# Initialize the collector
collector = OutlookFileShareCollector(
    config_dir="./config",
    data_dir="./outlook_data",
    port=5000
)

# Initialize the recorder with the collector
recorder = OutlookFileShareRecorder(collector=collector)

# Start the collector to begin receiving data
collector.collect_data()

# The collector will output setup instructions including:
# - Public ngrok URL
# - Path to the generated manifest file
# - Instructions for installing the add-in in Outlook
```

### Installing the Add-in in Outlook

1. Open Outlook
2. Go to "Get Add-ins" / "Manage Add-ins"
3. Select "My Add-ins" > "Add a custom add-in" > "Add from file"
4. Browse to the generated manifest file (typically in the `./manifest` directory)
5. Complete the installation

### Processing Collected Data

```python
# Sync data from collector to database
count = recorder.sync_from_collector()
print(f"Synced {count} file shares from collector")

# Scan data directory for JSON files from add-in
count = recorder.scan_data_directory()
print(f"Imported {count} file shares from JSON files")

# Look up files by filename
files = recorder.lookup_file_by_filename("report.docx")

# Look up files by sender
files = recorder.lookup_files_by_sender("sender@example.com")

# Get all file shares
all_shares = recorder.get_all_file_shares(limit=100)
```

## How It Works

### Data Flow

1. **Installation**: The user installs the Outlook add-in using the generated manifest.

2. **Email Sending**:
   - When the user sends an email with attachments or links, the add-in captures details.
   - The add-in extracts metadata from both regular attachments and links.
   - The data is sent to the collector's web API.

3. **Data Collection**:
   - The collector receives data via its web API endpoint.
   - Data is stored in JSON files in the data directory.
   - The collector also maintains an in-memory list of file shares.

4. **Data Recording**:
   - The recorder processes data from the collector and/or JSON files.
   - Each file share is converted to the appropriate data model.
   - Semantic attributes are created for database indexing.
   - Data is stored in the Indaleko database.

5. **Data Retrieval**:
   - The recorder provides methods to query the stored data.
   - Users can search by filename, sender, content type, etc.

### Security Considerations

- **ngrok Tunneling**: Uses secure HTTPS endpoint without storing sensitive data.
- **Local Processing**: All data is processed locally, with the web service only receiving metadata.
- **Limited Scope**: The add-in only collects metadata about shared files, not the file contents.

## Customization

### Custom Add-in Styling

You can customize the add-in's appearance by modifying the HTML returned in the `taskpane` route:

```python
@app.route("/taskpane")
def taskpane():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Custom Indaleko File Tracker</title>
        <style>
            /* Your custom styles here */
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f0f0f0;
            }
        </style>
    </head>
    <body>
        <!-- Your custom UI here -->
    </body>
    </html>
    """
```

### Additional File Type Support

To support additional file types or link formats, extend the JavaScript functions in the add-in:

```javascript
// Extract additional link types (like Google Drive)
function extractGoogleDriveLinks(htmlContent) {
    var links = [];
    var parser = new DOMParser();
    var doc = parser.parseFromString(htmlContent, "text/html");
    var anchors = doc.querySelectorAll("a");
    
    anchors.forEach(function(anchor) {
        var href = anchor.getAttribute("href");
        if (href && href.includes("drive.google.com")) {
            links.push(href);
        }
    });
    
    return links;
}
```

## Troubleshooting

### Add-in Not Appearing in Outlook

1. Verify that the manifest XML is valid
2. Check that the ngrok tunnel is running and accessible
3. Ensure that Outlook has the necessary permissions to install add-ins

### Data Not Being Received

1. Check the collector's logs for any API errors
2. Verify that the add-in is correctly sending data
3. Ensure that the ngrok tunnel is still active

### Database Storage Issues

1. Verify database connection settings
2. Check that the collection is properly registered
3. Look for any schema validation errors

## Future Enhancements

- Real-time notification of new file shares
- Content extraction and analysis from shared files
- Integration with Microsoft Graph API for enhanced data
- Support for more complex email sharing patterns
- Analytics on file sharing trends and patterns