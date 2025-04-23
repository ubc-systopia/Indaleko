# Incremental Update Service

## Overview

The Incremental Update Service provides a queue-based system for resolving entities that are detected in activity streams but don't yet exist in the database. This addresses the common scenario where a file system change event (like USN Journal entries) refers to files that haven't yet been indexed.

## Architecture

This service adheres to Indaleko's collector/recorder pattern while providing coordination between them:

1. **Producer Side** (Enqueue):
   - When a recorder (e.g., NTFS Hot Tier Recorder) encounters an unknown entity, it enqueues a resolution request
   - The recorder continues processing other activities without blocking

2. **Consumer Side** (Dequeue):
   - A dedicated service processes the queue
   - Uses existing collectors to gather entity information
   - Uses existing recorders to normalize and store the data
   - Maintains proper processing order (directories before files)

3. **Queue Implementation**:
   - Uses ArangoDB collection for storage
   - Machine-partitioned for independent processing
   - Supports priority levels for critical entities

## Implementation Details

### Queue Structure

```json
{
  "_key": "unique_id",
  "status": "pending",
  "machine_id": "windows-laptop-1",
  "entity_info": {
    "volume_guid": "C:",
    "frn": "40532396646425331",
    "file_path": "/path/if/available"
  },
  "entity_type": "file",
  "path_depth": 3,
  "priority": 1,
  "timestamp": "2025-04-23T11:07:21Z",
  "attempts": 0,
  "last_error": null
}
```

### Processing Model

- Single agent per machine to prevent race conditions
- Process in path depth order (directories first)
- Automatic retry with backoff for failed resolutions
- Status tracking for monitoring and diagnostics

### Integration Points

- `ProducerMixin`: Used by recorders to enqueue missing entities
- `ResolutionService`: Processes the queue and invokes collectors/recorders
- Configurable processing rates and batch sizes

## Design Rationale

The service follows a decoupled design to maintain architectural integrity while adding dynamic update capabilities:

- **Separation of Concerns**: Uses existing collectors and recorders without modifying their core responsibilities
- **Platform Focus**: Initially targets Windows NTFS for simplicity
- **Research Priority**: Focuses on proving the UPI concept rather than maximizing efficiency
- **Simplicity**: Favors a straightforward, maintainable design over complex optimizations

The single-agent-per-machine model was chosen over more complex dependency tracking to:
1. Simplify implementation
2. Reduce race condition risks
3. Match expected workload characteristics
4. Provide a clear path to future enhancements

## Usage Example

```python
# In a recorder that detects missing entities
from storage.incremental_update.producer_mixin import EntityResolutionProducer

class MyRecorder(BaseRecorder, EntityResolutionProducer):
    def process_activity(self, activity):
        entity = self.find_entity(activity.entity_id)
        if entity is None:
            # Entity doesn't exist, queue it for resolution
            self.enqueue_entity_resolution(
                volume_guid=activity.volume,
                frn=activity.frn,
                file_path=activity.path,
                entity_type="file"
            )
            
        # Continue with other processing
```

## Future Enhancements

- Cross-platform support (Linux, macOS)
- Performance optimizations for high-volume scenarios
- Integration with importance scoring for prioritization
- Advanced metrics and monitoring