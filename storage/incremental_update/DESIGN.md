# Incremental Update Service Design

## Problem Statement

The Indaleko NTFS activity recorder encounters entities (files/directories) from the USN Journal that don't yet exist in the database. Currently, the system simply logs these instances and skips updating them, resulting in incomplete activity records.

## Solution Overview

Create a queue-based service that:
1. Captures references to missing entities
2. Invokes appropriate collectors to gather entity data
3. Uses existing recorders to normalize and store the entity
4. Ensures proper ordering (directories before contained files)

## Design Decisions

### Queue Implementation

**Decision**: Use ArangoDB for the queue storage.

**Rationale**:
- Already a dependency in our system
- Built-in persistence
- Transactional safety
- No additional infrastructure required

### Processing Model 

**Decision**: Single agent per machine with path-depth ordering.

**Rationale**:
- Eliminates race conditions without complex locking
- Simplifies implementation
- Matches our expected volume requirements
- Allows future scaling across machines if needed

**Alternatives Considered**:
1. **Complex dependency tracking** - Rejected due to complexity and race condition risks
2. **Distributed workers with locking** - Unnecessary complexity for current scale
3. **File-based queue** - Less reliable, harder to monitor

### Platform Support

**Decision**: Initially target Windows NTFS only.

**Rationale**:
- Aligns with current file monitoring capabilities
- Focuses effort on proving the concept
- Establishes pattern that can be extended to other platforms

## Component Design

### EntityResolutionQueue Collection

```
{
  "_key": "<uuid>",
  "status": "pending|processing|completed|failed",
  "machine_id": "<machine_identifier>",
  "entity_info": {
    "volume_guid": "<volume>",
    "frn": "<file_reference_number>",
    "file_path": "<path_if_available>"
  },
  "entity_type": "file|directory",
  "path_depth": <integer>,
  "priority": <1-5>,
  "timestamp": "<iso-datetime>",
  "attempts": <integer>,
  "last_error": "<error_message>",
  "last_attempt_time": "<iso-datetime>"
}
```

### ProducerMixin

Interface for recorders to enqueue missing entities:

```python
class EntityResolutionProducer:
    def enqueue_entity_resolution(
        self, 
        volume_guid: str, 
        frn: str, 
        file_path: Optional[str] = None,
        entity_type: str = "file",
        priority: int = 3
    ) -> str:
        """
        Enqueue an entity for resolution.
        
        Returns:
            The queue entry ID
        """
        # Implementation
```

### ResolutionService

Processes the queue by:
1. Finding pending entries for the machine
2. Sorting by path depth (directories first)
3. Marking entries as "processing"
4. Invoking appropriate collectors
5. Passing data to recorders
6. Updating status to "completed" or "failed"

### Integration Flow

```
                           ┌─────────────────┐
                           │  NTFS Journal   │
                           │    Recorder     │
                           └────────┬────────┘
                                    │ Missing Entity
                                    ▼
┌───────────────────────────────────────────────────────┐
│                  ProducerMixin                        │
└────────────────────────────┬──────────────────────────┘
                             │
                             ▼
┌───────────────────────────────────────────────────────┐
│              EntityResolutionQueue                    │
└────────────────────────────┬──────────────────────────┘
                             │
                             ▼
┌───────────────────────────────────────────────────────┐
│              ResolutionService                        │
└────────┬─────────────────────────────────┬────────────┘
         │                                 │
         ▼                                 ▼
┌─────────────────┐               ┌─────────────────┐
│ Windows Storage │               │ Windows Storage │
│   Collector     │               │   Recorder      │
└─────────────────┘               └─────────────────┘
```

## Implementation Plan

### Phase 1: Core Infrastructure
1. Create queue collection schema
2. Implement ProducerMixin
3. Basic queue operations (enqueue, dequeue, update)

### Phase 2: Resolution Service
1. Service implementation
2. Integration with Windows Storage Collector
3. Integration with Windows Storage Recorder
4. Path-based ordering

### Phase 3: Integration
1. Add ProducerMixin to NTFS Hot Tier Recorder
2. Standalone service runner
3. Monitoring and logging

### Phase 4: Testing & Validation
1. Unit tests
2. Integration tests
3. Performance measurement

## Metrics and Monitoring

- Queue length over time
- Processing rate (entities/minute)
- Success/failure ratios
- Retry statistics
- Entity type distribution

## Future Considerations

- Scale to multiple agents with volume partitioning
- Cross-platform support
- Pre-emptive entity resolution based on directory patterns
- Integration with importance scoring system
- Batch processing optimizations