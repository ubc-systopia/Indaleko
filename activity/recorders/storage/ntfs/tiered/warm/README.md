# NTFS Warm Tier Activity Data Generator

The Warm Tier in Indaleko's tiered memory architecture serves as an intermediate storage layer between high-fidelity "hot" tier data and long-term archival storage. This component implements storage-efficient, aggregated representations of file system activities.

## Overview

The warm tier provides:
- Extended retention (default 30 days vs. 4 days in hot tier)
- Storage efficiency through intelligent aggregation
- Importance-based retention of significant activities
- Compression of repetitive or low-importance activities

## Architecture

The warm tier architecture follows Indaleko's collector/recorder pattern:

1. **Tier Transition Manager**
   - Orchestrates movement of data from hot tier to warm tier
   - Makes retention decisions based on age and importance
   - Batches transition operations for efficiency

2. **Warm Tier Recorder**
   - Stores processed activities in the warm tier
   - Implements aggregation and compression logic
   - Manages TTL-based expiration

3. **Importance Scorer**
   - Evaluates significance of activities for retention decisions
   - Uses multiple factors (recency, type, frequency, etc.)
   - Provides configurable importance thresholds

## Implementation Status

Current implementation:
- ✅ Basic warm tier recorder with ArangoDB integration
- ✅ Age-based transition from hot tier
- ✅ Multi-factor importance scoring
- ✅ Time-window based activity aggregation
- ✅ TTL-based storage management
- ✅ Core functionality unit tests

Needed improvements:
- Enhanced aggregation rules (entity and context-based)
- Transaction support for reliable transitions
- More comprehensive integration test suite
- Content-based aggregation (beyond time windows)
- Entity metadata enrichment
- Query spanning across hot and warm tiers
- Performance optimization for batch transitions

## Usage

### Running Tier Transitions

```bash
# Basic transition from hot to warm tier
python -m activity.recorders.storage.ntfs.tiered.tier_transition --run

# Custom age threshold for transition (default: 12 hours)
python -m activity.recorders.storage.ntfs.tiered.tier_transition --run --age-hours 24

# View transition statistics without running
python -m activity.recorders.storage.ntfs.tiered.tier_transition --stats
```

### Manual Warm Tier Management

```bash
# View warm tier statistics
python -m activity.recorders.storage.ntfs.tiered.warm.recorder --stats

# Check hot tier for transition-ready activities
python -m activity.recorders.storage.ntfs.tiered.warm.recorder --hot-tier

# Run transition from hot tier to warm tier
python -m activity.recorders.storage.ntfs.tiered.warm.recorder --transition
```

## Storage Efficiency

The warm tier achieves storage efficiency through:

1. **Activity Aggregation**: Similar activities within a time window are combined
   - Create/modify/close sequences merged into single activities
   - Repetitive modifications to same file aggregated
   - Related operations grouped by entity

2. **Importance-Based Retention**:
   - High importance activities (0.7-1.0): retained with minimal compression
   - Medium importance activities (0.4-0.7): moderate aggregation
   - Low importance activities (0.0-0.4): aggressive aggregation

3. **TTL-Based Management**:
   - Configurable retention period (default 30 days)
   - Automatic expiration without manual cleanup

4. **Selective Attribute Preservation**:
   - Retention of critical metadata while dropping verbose details
   - Preservation of relationship context for semantic understanding

## Design Principles

The warm tier implementation follows these principles:

1. **Storage Efficiency**: Reduce storage requirements while preserving key insights
2. **Contextual Preservation**: Maintain relationships and context for meaningful analysis
3. **Query Compatibility**: Ensure queries work seamlessly across tiers
4. **Adaptive Compression**: Apply different compression levels based on importance
5. **Graceful Degradation**: Preserve most important data elements for longest periods

## Integration Points

The warm tier integrates with:
- Hot tier recorder for data acquisition
- Entity mapping system for consistent references
- Query system for multi-tier search
- Activity context for enhanced aggregation decisions
- Importance scorer for retention decisions

## Technical Specifications

- **Database Collections**: ArangoDB collection with standard IndalekoRecordDataModel schema
- **TTL Management**: TTL index on `Record.Data.ttl_timestamp` field
- **Query Support**: Compatible with standard activity queries
- **Activity Data Model**: Extended NtfsStorageActivityData with aggregation metadata

## Aggregation Algorithm

The current aggregation algorithm:
1. Groups activities by (entity_id, activity_type, time_window)
2. For each group with 3+ activities:
   - Creates a single aggregated activity preserving critical metadata
   - Records count and time range of original activities
   - Assigns maximum importance of any constituent activity

Future enhancements:
- Session-based aggregation (user activity patterns)
- Content-similarity based grouping
- Context-aware aggregation (related entities)
- Adaptive time windows based on activity volumes
