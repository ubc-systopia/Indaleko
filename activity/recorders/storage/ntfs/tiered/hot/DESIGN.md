# NTFS Hot Tier Recorder Design

This document outlines the design for the "Hot" tier of the NTFS activity recorder system in Indaleko, focusing on high-fidelity recent data retention and efficient database storage.

## Hot Tier Overview

The hot tier recorder is the first level in Indaleko's multi-tiered activity storage architecture. It is responsible for:

1. Receiving raw activity data from the NTFS USN journal collector
2. Processing, enhancing, and storing this data in the database
3. Providing efficient query capabilities for recent activities
4. Supporting eventual transition of data to the Warm tier

## Key Design Goals

1. **High Performance**: Optimized for write-heavy workloads as new activities are continuously collected
2. **Complete Fidelity**: Preserve all details from the original USN records
3. **File Entity Mapping**: Map file reference numbers (FRNs) to entity UUIDs for relationship tracking
4. **Cross-OS Compatibility**: Support both processing of JSONL files and direct collector integration
5. **Data Accessibility**: Provide efficient query mechanisms for recent activity retrieval

## Implementation Components

### 1. NtfsHotTierRecorder Class

The main recorder class that implements the recorder interface and manages activity storage:

```python
class NtfsHotTierRecorder(StorageActivityRecorder):
    """
    Hot tier recorder for NTFS storage activities.
    
    Handles high-volume, recent NTFS file system activities collected from the USN Journal,
    preserving full fidelity before eventual transition to warm tier.
    """
    
    def __init__(self, **kwargs):
        """Initialize the hot tier recorder."""
        # Core configuration
        self._collection_name = "ntfs_activities_hot"
        self._ttl_days = kwargs.get("ttl_days", 4)  # Default 4-day retention
        
        # Initialize recorder base
        super().__init__(**kwargs)
        
        # Set up TTL index for automatic expiration
        self._setup_ttl_index()
        
        # Initialize FRN to UUID mapping cache
        self._frn_entity_cache = {}
        
    def process_jsonl_file(self, file_path: str) -> List[uuid.UUID]:
        """Process a JSONL file containing NTFS activities."""
        # Implementation for file-based processing
        
    def process_collector_activities(self, collector) -> List[uuid.UUID]:
        """Process activities directly from a collector instance."""
        # Implementation for direct collector integration
        
    def _setup_ttl_index(self):
        """Set up TTL index for automatic expiration of hot tier data."""
        # Implementation for TTL index creation
        
    def _map_frn_to_entity(self, frn: str, volume: str) -> uuid.UUID:
        """Map a file reference number to an entity UUID."""
        # Implementation for entity mapping
```

### 2. Data Flow

```
+------------------+        +----------------------+        +-------------------+
| USN Journal      |        | NtfsHotTierRecorder  |        | ArangoDB          |
| Collector        |  --->  | - Process activities |  --->  | - ntfs_activities_hot
| - JSONL output   |        | - Map FRNs           |        | - TTL index       |
+------------------+        | - Enhance metadata   |        +-------------------+
                            +----------------------+
```

### 3. Database Schema

#### Collection: ntfs_activities_hot

```json
{
  "_key": "unique_activity_id",
  "timestamp": "2025-04-19T12:34:56.789Z",
  "activity_type": "create",
  "entity_id": "file_entity_uuid",
  "file_reference_number": "1234567890",
  "parent_file_reference_number": "9876543210",
  "file_name": "document.docx",
  "file_path": "C:\\Users\\Documents\\document.docx",
  "volume_name": "C:",
  "is_directory": false,
  "attributes": {
    "usn_reason_flags": ["FILE_CREATE"],
    "usn_record_number": 12345,
    "rename_type": null
  },
  "machine_id": "hostname_or_machine_id",
  "ttl_timestamp": "2025-04-23T12:34:56.789Z",
  "importance_score": 0.65,
  "search_hits": 0,
  "entity_relationships": [
    {"type": "parent", "entity_id": "parent_folder_uuid"},
    {"type": "user", "entity_id": "user_uuid"}
  ]
}
```

### 4. Entity Mapping Strategy

The hot tier recorder employs a critical function: mapping file reference numbers (FRNs) to permanent entity UUIDs. This mapping is essential because:

1. FRNs are Windows-specific and can be reused after file deletion
2. Entity UUIDs are consistent across the entire Indaleko system
3. Relationships between files, folders, and other entities require stable identifiers

The mapping strategy involves:

#### 4.1 FRN Lookup Algorithm
```python
def get_or_create_entity_uuid(frn: str, volume: str, file_path: str, is_directory: bool) -> uuid.UUID:
    """Get existing entity UUID or create a new one for an FRN."""
    # First check cache
    cache_key = f"{volume}:{frn}"
    if cache_key in self._frn_entity_cache:
        return self._frn_entity_cache[cache_key]
    
    # Query existing mapping
    entity = self._query_entity_by_frn(frn, volume)
    if entity:
        # Store in cache and return
        self._frn_entity_cache[cache_key] = entity["_id"]
        return entity["_id"]
    
    # No existing entity, create new one
    entity_uuid = self._create_entity(frn, volume, file_path, is_directory)
    self._frn_entity_cache[cache_key] = entity_uuid
    return entity_uuid
```

#### 4.2 Entity Creation
When a previously unseen FRN is encountered, a new entity record is created that contains:
- Permanent UUID
- Initial file metadata (path, name, type)
- Creation timestamp
- Reference to the originating activity

### 5. TTL Management

The hot tier uses automatic expiration through ArangoDB's TTL (Time-To-Live) index feature:

```python
def _setup_ttl_index(self):
    """Set up TTL index for automatic expiration of hot tier data."""
    # Calculate TTL in seconds
    ttl_seconds = self._ttl_days * 24 * 60 * 60
    
    # Create TTL index on ttl_timestamp field
    self._collection.add_ttl_index(
        fields=["ttl_timestamp"],
        expireAfter=ttl_seconds
    )
    
    self._logger.info(f"Created TTL index with {self._ttl_days} day expiration")
```

Each document includes a `ttl_timestamp` field that determines when it should expire from the hot tier. The TTL index automatically removes documents once this timestamp is reached.

### 6. Importance Scoring

Even in the hot tier, we begin tracking an importance score that will influence the compression level when transitioning to the warm tier:

```python
def _calculate_initial_importance(self, activity_data: Dict) -> float:
    """Calculate initial importance score for an activity."""
    base_score = 0.3  # Start with modest importance
    
    # Factor 1: Activity type importance
    if activity_data["activity_type"] in ["create", "security_change"]:
        base_score += 0.2  # Creation events matter more
    
    # Factor 2: File type importance (basic version)
    file_path = activity_data.get("file_path", "")
    if any(file_path.lower().endswith(ext) for ext in [".docx", ".xlsx", ".pdf", ".py", ".md"]):
        base_score += 0.1  # Document types matter more
    
    # Factor 3: Path significance
    if "\\Documents\\" in file_path or "\\Projects\\" in file_path:
        base_score += 0.1  # User document areas matter more
    
    return min(1.0, base_score)  # Cap at 1.0
```

### 7. Integration with File Entity System

The hot tier recorder integrates with Indaleko's file entity system to:
1. Create permanent entity records for files
2. Update entity metadata based on activities
3. Establish relationships between file entities
4. Support full entity history reconstruction

```python
def _update_entity_metadata(self, entity_id: uuid.UUID, activity_data: Dict):
    """Update entity metadata based on activity."""
    # Skip if this is a deletion activity
    if activity_data["activity_type"] == "delete":
        self._mark_entity_deleted(entity_id)
        return
    
    # For renames, update the entity's name and path
    if activity_data["activity_type"] == "rename":
        self._update_entity_name_path(entity_id, activity_data)
        return
    
    # For other activities, update last_modified and access timestamps
    self._update_entity_timestamps(entity_id, activity_data)
```

## Query Capabilities

The hot tier recorder provides specialized query methods for recent activity analysis:

1. **Recent Activities**: Retrieve most recent activities by time window
2. **Entity Timeline**: Get complete timeline for a specific entity
3. **Activity Type**: Query activities by specific types (create, modify, etc.)
4. **Path Pattern**: Find activities affecting files matching path patterns
5. **Rename Tracking**: Special handling for rename operations (both old and new names)

## Transition to Warm Tier

While automatic TTL handles basic expiration, the eventual integration with the warm tier will involve:

1. **Pre-expiration Processing**: Before TTL expiration, evaluate activities for warm tier
2. **Importance-Based Compression**: Apply compression based on calculated importance
3. **Batch Processing**: Process activities in batches for efficiency
4. **Relationship Preservation**: Ensure entity relationships are maintained in compressed form

## Next Steps for Implementation

1. Create basic hot tier recorder class skeleton
2. Implement JSONL file processing for cross-platform operation
3. Add direct collector integration for Windows environments
4. Implement entity mapping functions
5. Create TTL index management
6. Add basic importance scoring
7. Build query methods for recent activity access
8. Add test suite with sample data files