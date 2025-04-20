# NTFS Hot Tier Recorder

## Overview

The NTFS Hot Tier Recorder is a component of Indaleko's tiered activity storage system. It's responsible for storing high-fidelity, recent NTFS file system activities for a short period before they transition to longer-term storage tiers.

## Key Features

- High-volume storage of recent NTFS file system activities
- File Reference Number (FRN) to Entity UUID mapping
- TTL-based automatic expiration
- Importance scoring algorithm for future tier transitions
- Comprehensive query capabilities for recent activities
- JSON/JSONL file processing for cross-platform support
- Multi-platform support (Windows, MacOS, Linux)

## Architecture

The Hot Tier Recorder follows Indaleko's collector/recorder pattern:

1. **NTFS Collector**: Collects raw file system activities
2. **Hot Tier Recorder**: Processes and stores activities in the hot tier
3. **Future Work**: Warm/cool/glacial tiers for longer-term storage

## Usage

### Command Line Tool

The easiest way to use the Hot Tier Recorder is through the command-line interface:

```bash
# View available activity files
./load_hot_tier_data.sh --list

# Process activities in simulation mode (no database connection)
./load_hot_tier_data.sh --simulate --report

# Process all activity files
./load_hot_tier_data.sh --all --report

# Process a specific file with custom TTL
./load_hot_tier_data.sh --file data/ntfs_activity.jsonl --ttl-days 7
```

### Windows Batch File

For Windows users, a batch file is provided:

```cmd
# View available activity files
load_hot_tier_data.bat --list

# Process activities in simulation mode
load_hot_tier_data.bat --simulate --report
```

### Python API

The Hot Tier Recorder can also be used programmatically:

```python
from activity.recorders.storage.ntfs.tiered.hot.recorder import NtfsHotTierRecorder
from db.db_config import IndalekoDBConfig

# Setup database connection
db_config = IndalekoDBConfig()
db_config.start()

# Create recorder
recorder = NtfsHotTierRecorder(
    ttl_days=4,  # Duration before automatic expiration
    db_config=db_config
)

# Process activities from JSONL file
activity_ids = recorder.process_jsonl_file("data/ntfs_activities.jsonl")

# Or process activities directly from a collector
from activity.collectors.storage.ntfs.ntfs_collector_v2 import NtfsStorageActivityCollectorV2
collector = NtfsStorageActivityCollectorV2(volumes=["C:"])
collector.collect_data()
recorder.process_collector_activities(collector)

# Query recent activities
recent_activities = recorder.get_recent_activities(hours=24, limit=10)
```

## Database Structure

The Hot Tier Recorder uses two main collections:

1. **Hot Tier Activities Collection**: Stores the actual file system activities
   - TTL index for automatic expiration
   - Indices for efficient querying
   - Importance scoring for future tier transitions

2. **Entity Collection**: Maps file system entities to stable UUIDs
   - Tracks file reference numbers (FRNs) to entity mappings
   - Remembers file paths across renames
   - Maintains deletion status
   - Tracks access patterns

## Key Capabilities

1. **TTL-Based Expiration**: Activities automatically expire after a configurable period (default: 4 days)
2. **Entity Mapping**: Multiple FRNs map to the same logical entity UUID
3. **Importance Scoring**: Activities are scored for importance based on:
   - Activity type (create, delete, rename are more important)
   - File type (documents, code, etc. are more important than temporary files)
   - Path significance (user folders, projects are more important than cache, temp)
   - Search feedback loop (items that are searched for often gain importance)
4. **Detailed Queries**:
   - Time-based (`get_recent_activities`)
   - Entity-based (`get_activities_by_entity`)
   - Type-based (`get_activities_by_type`)
   - Rename tracking (`get_rename_activities`)
   - Statistics (`get_hot_tier_statistics`)

## Future Enhancements

- Warm tier transition for important activities
- Enhanced importance scoring with ML-based predictions
- Integration with other activity contexts (Spotify, YouTube, etc.)
- Timeline visualization of activities
- Clustering of related activities

## Requirements

- Python 3.9+ (3.12+ recommended)
- ArangoDB 3.10+ (for TTL indices)
- Windows (for direct collection) or any platform (for JSONL file processing)

## Related Components

- NTFS Collector v2: Collects real-time file system activities
- Entity Equivalence Manager: Unified entity tracking across sources
- Query system: Integrates hot tier data into search results
- Archivist: Proactive suggestions based on hot tier data