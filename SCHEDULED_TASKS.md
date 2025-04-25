# Indaleko Windows Scheduled Tasks

This document provides a comprehensive list of scripts that can be scheduled for periodic data collection on a Windows laptop, organized by category.

## Activity Data Collection

### File System Activity

1. **NTFS File System Activity**
   - **Script**: `run_ntfs_activity.bat`
   - **Category**: Activity (File System)
   - **Recommended Frequency**: Every 15-30 minutes
   - **Requirements**: Administrative privileges
   - **Command**:
     ```
     run_ntfs_activity.bat --volumes C: --interval 30 --verbose
     ```
   - **Notes**: Captures file creation, modification, deletion, and renaming events

### Location Providers (Multiple sources for comparison)

1. **Windows GPS Location**
   - **Script**: `activity/recorders/location/windows_gps_location.py`
   - **Category**: Activity (Location)
   - **Recommended Frequency**: Every 5-10 minutes
   - **Command**:
     ```
     python activity/recorders/location/windows_gps_location.py
     ```
   - **Notes**: Provides latitude, longitude, and accuracy data from Windows Location Service

2. **WiFi Location**
   - **Script**: `activity/collectors/location/wifi_location.py`
   - **Category**: Activity (Location)
   - **Recommended Frequency**: Every 15 minutes
   - **Command**:
     ```
     python activity/collectors/location/wifi_location.py
     ```
   - **Notes**: Determines location based on nearby WiFi networks

3. **IP Location**
   - **Script**: `activity/collectors/location/ip_location.py`
   - **Category**: Activity (Location)
   - **Recommended Frequency**: Hourly
   - **Command**:
     ```
     python activity/collectors/location/ip_location.py
     ```
   - **Notes**: Provides geolocation based on IP address; useful when comparing with other location sources

### Media & Environment Activity

1. **Spotify Music Activity**
   - **Script**: `activity/collectors/ambient/music/spotify_collector.py`
   - **Category**: Activity (Media)
   - **Recommended Frequency**: Hourly
   - **Dependencies**: Spotify API credentials
   - **Command**:
     ```
     python activity/recorders/ambient/spotify_recorder.py
     ```
   - **Notes**: Captures music listening history and preferences

2. **YouTube Media Activity**
   - **Script**: `activity/recorders/ambient/youtube_recorder.py`
   - **Category**: Activity (Media)
   - **Recommended Frequency**: Hourly
   - **Dependencies**: YouTube API credentials
   - **Command**:
     ```
     python activity/recorders/ambient/youtube_recorder.py
     ```
   - **Notes**: Records video watching activity and interaction patterns

3. **Ecobee Thermostat**
   - **Script**: `activity/collectors/ambient/smart_thermostat/ecobee.py`
   - **Category**: Activity (Environment)
   - **Recommended Frequency**: Every 30 minutes
   - **Dependencies**: Ecobee API credentials
   - **Command**:
     ```
     python activity/collectors/ambient/smart_thermostat/ecobee.py
     ```
   - **Notes**: Collects temperature preferences and environmental context

### Collaboration Activity

1. **Discord File Sharing**
   - **Script**: `activity/collectors/collaboration/discord/discord_file_collector.py`
   - **Category**: Activity (Collaboration)
   - **Recommended Frequency**: Hourly
   - **Dependencies**: Discord API token
   - **Command**:
     ```
     python activity/recorders/collaboration/discord_file_recorder.py
     ```
   - **Notes**: Tracks file sharing activities through Discord

2. **Outlook File Sharing**
   - **Script**: `activity/collectors/collaboration/outlook/outlook_file_collector.py`
   - **Category**: Activity (Collaboration)
   - **Recommended Frequency**: Hourly
   - **Dependencies**: Microsoft Graph API credentials
   - **Command**:
     ```
     python activity/recorders/collaboration/outlook_file_recorder.py
     ```
   - **Notes**: Monitors email attachments and file sharing

3. **Calendar Events**
   - **Script**: `activity/collectors/collaboration/calendar/calendar_cli.py`
   - **Category**: Activity (Scheduling)
   - **Recommended Frequency**: Hourly
   - **Command**:
     ```
     python activity/recorders/collaboration/calendar_recorder.py
     ```
   - **Notes**: Captures calendar events and scheduled activities

## Semantic Data Collection

1. **Semantic Background Processor**
   - **Script**: `semantic/run_bg_processor.py`
   - **Category**: Semantic
   - **Recommended Frequency**: Daily (typically during off-hours)
   - **Command**:
     ```
     python semantic/run_bg_processor.py --install-task
     ```
   - **Notes**: Runs all extractors; installs itself as a Windows scheduled task

2. **MIME Type Extractor**
   - **Script**: `semantic/run_scheduled.py`
   - **Category**: Semantic
   - **Recommended Frequency**: Daily
   - **Command**:
     ```
     python semantic/run_scheduled.py --extractors mime --max-cpu 30 --max-memory 1024
     ```
   - **Notes**: Identifies actual file types through content analysis

3. **Checksum Generator**
   - **Script**: `semantic/run_scheduled.py`
   - **Category**: Semantic
   - **Recommended Frequency**: Daily
   - **Command**:
     ```
     python semantic/run_scheduled.py --extractors checksum --max-cpu 30 --max-memory 1024
     ```
   - **Notes**: Computes various hash types for file verification and deduplication

4. **EXIF Metadata Extractor**
   - **Script**: `semantic/run_scheduled.py`
   - **Category**: Semantic
   - **Recommended Frequency**: Daily
   - **Command**:
     ```
     python semantic/run_scheduled.py --extractors exif --max-cpu 30 --max-memory 1024
     ```
   - **Notes**: Extracts image/media metadata including camera info and geolocation

5. **Unstructured Content Extractor**
   - **Script**: `run_unstructured_extraction.bat`
   - **Category**: Semantic
   - **Recommended Frequency**: Weekly (during off-hours)
   - **Requirements**: Docker, sufficient disk space
   - **Command**:
     ```
     run_unstructured_extraction.bat
     ```
   - **Notes**: Extracts text, tables, and structure from documents; resource-intensive

## Storage Data Collection

1. **Incremental File System Indexer**
   - **Script**: `run_incremental_indexer.py`
   - **Category**: Storage
   - **Recommended Frequency**: Hourly
   - **Command**:
     ```
     python run_incremental_indexer.py --volumes C:\Users\TonyMason --db-records --verbose
     ```
   - **Notes**: Identifies new or modified files since last run

2. **Google Drive Activity**
   - **Script**: `activity/collectors/storage/cloud/gdrive_activity_collector.py`
   - **Category**: Storage (Cloud)
   - **Recommended Frequency**: Hourly
   - **Dependencies**: Google Drive API credentials
   - **Command**:
     ```
     python activity/recorders/storage/cloud/gdrive_recorder.py
     ```
   - **Notes**: Syncs file activity from Google Drive

3. **Dropbox Activity**
   - **Script**: `activity/collectors/storage/dropbox/dropbox_collector.py`
   - **Category**: Storage (Cloud)
   - **Recommended Frequency**: Hourly
   - **Dependencies**: Dropbox API credentials
   - **Command**:
     ```
     python activity/recorders/storage/dropbox/dropbox_recorder.py
     ```
   - **Notes**: Captures file activity from Dropbox

## Memory Tier Management

1. **Memory Consolidation**
   - **Script**: `run_memory_consolidation.bat`
   - **Category**: Storage (Memory Management)
   - **Recommended Frequency**: Daily
   - **Command**:
     ```
     run_memory_consolidation.bat --consolidate-all
     ```
   - **Notes**: Manages transitions between memory tiers

2. **Tier Transition**
   - **Script**: `run_tier_transition.bat`
   - **Category**: Storage (Memory Management)
   - **Recommended Frequency**: Every 12 hours
   - **Command**:
     ```
     run_tier_transition.bat --run --age-hours 12 --batch-size 1000
     ```
   - **Notes**: Transitions data from hot tier to warm tier; essential for queries like "Show me files I created last Monday"

## Setting Up Windows Task Scheduler

1. Open Task Scheduler (type `taskschd.msc` in the Start menu)
2. Click "Create Basic Task" in the right panel
3. Enter Name and Description for the task
4. Select Trigger (Daily, Weekly, or When computer starts)
5. For scripts that need to run multiple times per day:
   - Choose "Daily"
   - After creating the task, open its properties
   - Go to the "Triggers" tab, edit the trigger
   - Check "Repeat task every" and set the desired interval (e.g., 30 minutes)
6. For Action, select "Start a program"
7. In Program/script, browse to either:
   - `C:\Users\TonyMason\source\repos\indaleko\.venv-win32-python3.12\Scripts\python.exe` (for Python scripts)
   - `C:\Users\TonyMason\source\repos\indaleko\[script].bat` (for batch files)
8. For Python scripts, add the full script path in "Add arguments"
9. Set "Start in" to `C:\Users\TonyMason\source\repos\indaleko`
10. In the "Settings" tab, consider these options:
    - "Allow task to be run on demand"
    - "Run task as soon as possible after a scheduled start is missed"
    - For the NTFS collector that requires admin rights, check "Run with highest privileges"

## Recommended Scheduling Plan

This is a suggested schedule that balances data freshness with system performance:

| Time | Task |
|------|------|
| Every 10 minutes | Windows GPS Location |
| Every 15 minutes | WiFi Location |
| Every 30 minutes | NTFS File System Activity, Ecobee Thermostat |
| Hourly | IP Location, Incremental File System Indexer, Spotify, YouTube, Discord, Outlook, Calendar, Google Drive, Dropbox |
| 2:00 AM | Semantic Background Processor (MIME, Checksum, EXIF) |
| 3:00 AM | Memory Consolidation |
| 3:00 AM (Every 12h) | Tier Transition |
| Sunday 3:00 AM | Unstructured Content Extractor |

## Data Analysis Opportunities

Running these diverse collectors creates unique opportunities for query analysis:

1. **Multi-source Location Data**: Compare location determined by GPS, WiFi, and IP
2. **Activity Context**: Correlate file activities with environmental factors (temperature, music)
3. **Temporal Patterns**: Analyze time-based relationships between different activities
4. **Warm Tier Queries**: Enable queries like "Show me files I created last Monday" through tier transitions
5. **Semantic Relationships**: Discover connections between document content that file systems don't capture

## Notes on Performance

- All scripts respect the Indaleko architectural principles with proper separation of collectors and recorders
- Most scripts include resource throttling to avoid impacting system performance
- For laptops, consider setting tasks to not run when on battery power
- All tasks support logging to help diagnose any issues
