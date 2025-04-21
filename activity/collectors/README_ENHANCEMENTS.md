# Indaleko Activity Collection Enhancement Plan

This document outlines the plan for enhancing Indaleko's activity data collection capabilities. The goal is to collect richer metadata from various sources to support sophisticated pattern detection and knowledge management.

## Core Principles

1. **Simplicity First**: Use the least technically complex mechanism that achieves our goals.
2. **Leverage Existing Infrastructure**: Utilize native task schedulers (cron, Task Scheduler) rather than building custom services.
3. **Cross-Platform Compatibility**: Ensure collectors work consistently across platforms where possible.
4. **Shared Database Access**: All collectors will write to the single shared ArangoDB instance.
5. **Robust State Management**: Each collector must maintain state between runs to support incremental collection.
6. **Resource Consciousness**: Minimize impact on system resources and external API quota limits.

## Priority Enhancements

### 1. NTFS Collection Script Enhancement (Windows-specific)

**Goal**: Improve the existing NTFS USN Journal collector for reliable scheduled execution.

**Implementation Details**:
- Enhance the script to process USN journal entries since last run
- Persist state in a simple JSON file with robust error handling
- Implement proper locking to prevent concurrent execution
- Add comprehensive logging with configurable verbosity
- Optimize database interaction for larger data volumes
- Configure retry logic for database connection failures

**Scheduling Strategy**:
- Configure Windows Task Scheduler to run every 5-15 minutes
- Set proper recovery options (restart on failure)
- Configure to run with appropriate credentials

**Location**: `/activity/collectors/storage/ntfs/`

### 2. Discord File Sharing Collector (Cross-Platform)

**Goal**: Enhance the Discord collector to operate as a scheduled task and extract richer metadata.

**Implementation Details**:
- Update for scheduled task compatibility with proper state tracking
- Track last-processed message timestamp to enable incremental collection
- Implement robust error handling for connection issues
- Extract rich metadata from shared files including:
  - File context (surrounding conversation)
  - User relationship data
  - Topic classification
  - Link to original messages
- Add configurable filters for channels/servers to monitor

**Scheduling Strategy**:
- Run as a cron job/scheduled task every 15-30 minutes
- Include backoff mechanisms if API rate limits are reached

**Location**: `/activity/collectors/collaboration/discord/`

### 3. Cloud Storage Integration (Cross-Platform)

**Goal**: Implement robust collectors for Dropbox, Google Drive, and OneDrive.

**Implementation Details**:

#### 3.1 Dropbox
- Enhance the existing collector to track last sync timestamp
- Implement webhook support for real-time notifications where possible
- Fallback to efficient polling for changes
- Extract rich sharing metadata and version history
- Properly handle Dropbox API rate limits

#### 3.2 Google Drive
- Update the Google Drive collector to use incremental sync API
- Share OAuth tokens with other Google services (YouTube)
- Extract file metadata including sharing information and activity
- Implement efficient change tracking

#### 3.3 OneDrive
- Enhance OneDrive collector to use Microsoft Graph API change tracking
- Implement proper OAuth flow compatible with other Microsoft services
- Extract rich metadata about files and sharing patterns

**Scheduling Strategy**:
- Configure as cron jobs/scheduled tasks to run every 30-60 minutes
- Implement intelligent backoff for API limits

**Location**: `/activity/collectors/storage/cloud/`

### 4. Media Activity Collection (Cross-Platform)

**Goal**: Enhance and complete collectors for media consumption tracking.

**Implementation Details**:

#### 4.1 YouTube History
- Complete implementation using Google OAuth (shared with Google Drive)
- Extract rich contextual metadata:
  - Video categories
  - Creator information
  - Watch duration and engagement
  - Related videos
- Implement catch-up logic for missed intervals

#### 4.2 Spotify Activity
- Implement Spotify collector with robust OAuth flow
- Extract rich metadata:
  - Artist and album information
  - Genre classifications
  - Listening duration
  - Playlist context
- Track listening patterns and preferences

**Scheduling Strategy**:
- Configure scheduled tasks to run 2-3 times daily
- Implement efficient lookback to catch missed activities

**Location**: `/activity/collectors/ambient/media/` and `/activity/collectors/ambient/music/`

### 5. Location Data Collection (Platform-specific)

**Goal**: Enhance location data collectors for richer context information.

**Implementation Details**:

#### 5.1 Windows GPS Location
- Enhance the Windows location collector to extract GPS data
- Integrate with mapping services for reverse geocoding
- Implement state tracking for efficient updates

#### 5.2 IP/WiFi Location (Cross-Platform)
- Update IP and WiFi collectors for scheduled execution
- Implement more sophisticated location change detection
- Add batch processing for efficiency

**Scheduling Strategy**:
- Run location collectors at appropriate intervals (15-60 minutes)
- Update only when significant changes detected

**Location**: `/activity/collectors/location/`

## Implementation Schedule

### Phase 1: Foundation and Framework
1. Update state management framework for all collectors
2. Implement robust error handling and logging
3. Create documentation for scheduled task configuration

### Phase 2: Storage Activity Collectors
1. Enhance NTFS collector for scheduled execution
2. Update cloud storage collectors for incremental sync
3. Implement cross-platform configuration sharing

### Phase 3: Collaboration and Media Collectors
1. Enhance Discord file sharing collector
2. Complete YouTube history collector
3. Implement Spotify activity collector

### Phase 4: Integration and Testing
1. Comprehensive testing across platforms
2. Create monitoring and statistics dashboard
3. Optimize database interaction patterns

## Documentation Standards

Each collector should include:

1. **README.md**: Detailed documentation including:
   - Purpose and capabilities
   - Configuration requirements
   - Authentication setup
   - Scheduling recommendations
   - Troubleshooting guide

2. **example_config.json**: Template configuration file

3. **setup_scripts/**: Platform-specific scripts for setting up scheduled tasks