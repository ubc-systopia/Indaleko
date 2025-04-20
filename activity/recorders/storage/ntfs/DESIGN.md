# NTFS Activity Recorder Design

This document outlines the design for the NTFS activity recorder system in Indaleko, focusing on a tiered approach to activity data storage that mirrors human memory systems while optimizing for efficiency and long-term sustainability.

## Tiered Recorder Architecture

Indaleko's NTFS activity recorder uses a multi-tiered approach inspired by human memory and efficient data lifecycle management:

### 1. Hot Recorder (Hours to Days)

The hot recorder maintains high-fidelity, detailed records of recent file system activities.

**Key Characteristics:**
- Complete NTFS USN journal events with full attribute preservation
- File Reference Number (FRN) to UUID mapping for entity relationship tracking
- Comprehensive indexing for rapid query performance
- Retention period: 24-96 hours depending on system activity volume

**Implementation Approach:**
- Direct ArangoDB collection with full indexing
- Real-time ingestion from the collector JSONL output
- Optimized for write performance with secondary read indices

**Use Cases:**
- Detailed activity timeline reconstruction
- Short-term diagnostics and troubleshooting
- Real-time activity monitoring
- Context-aware search enhancement

### 2. Warm Recorder (Weeks to Months)

The warm recorder applies intelligent compression to maintain useful information while reducing storage requirements.

**Key Characteristics:**
- Selectively compressed activity records
- Grouped related operations (e.g., multiple edits to same file within minutes)
- Preservation of essential attributes and relationships
- Retention period: 1-3 months

**Implementation Approach:**
- Scheduled compression jobs to process aging hot data
- Context-aware compression algorithms
- Optimized collection with selective indexing

**Use Cases:**
- Recent activity lookups
- Pattern detection across weeks of usage
- File history reconstruction without second-by-second detail

### 3. Cool Recorder (Months to Years)

The cool recorder maintains longer-term records with higher compression and aggregation.

**Key Characteristics:**
- Daily/weekly summaries rather than individual events
- Activity patterns and statistics preserved
- Core relationships maintained
- Retention period: 1-5 years

**Implementation Approach:**
- Aggregation processes that run on aging warm data
- Statistical representations of activity patterns
- Specialized time-based indices

**Use Cases:**
- Long-term usage pattern analysis
- Historical file lifecycle tracking
- System health monitoring over time

### 4. Glacial Recorder (5+ Years)

The glacial recorder provides highly compressed, statistical representations of very old activity data.

**Key Characteristics:**
- Extreme compression with only landmark events preserved
- Statistical representation of baseline activity
- Minimal storage footprint
- Retention period: 5+ years

**Implementation Approach:**
- Time-series optimization techniques
- Machine learning to identify significant patterns worth preserving
- Periodic revalidation of importance

**Use Cases:**
- Long-term trend analysis
- Compliance and audit requirements
- Establishing normal behavior baselines

## Context-Aware Compression Strategies

The recorder system employs sophisticated context-aware strategies to determine what information to preserve:

### Activity Pattern Analysis

- **Access Frequency**: Preserve more detail for frequently accessed files
- **Modification Intensity**: Retain more information for files with periods of intense editing
- **Lifecycle Stage**: Different compression for new, active, and stable files
- **User Interaction**: Preserve more for files with direct user interaction vs. system activity

### Semantic Importance Indicators

- **File Type Awareness**: Different preservation strategies based on file types
- **Content Significance**: Integration with semantic extractors to identify important content
- **Path and Name Analysis**: Higher importance for files in project directories or with significant naming patterns
- **Size and Complexity**: Scaled approach based on file characteristics

### Cross-Source Activity Correlation

- **Referenced in Communication**: Higher preservation for files mentioned in emails/messages
- **Meeting Context**: Enhanced preservation for files accessed during calendar events
- **Sharing Status**: More detail for files that have been shared with others
- **Multi-Device Access**: Higher importance for files accessed across devices

### Usage Feedback Loop

- **Search Relevance Reinforcement**: Files returned in search results get importance boost
- **View Counts**: Files viewed by users receive enhanced preservation
- **Query Context Storage**: Preserve the context in which files were important
- **Resurrection Capability**: Ability to enhance previously compressed records when importance increases

## Implementation Architecture

### Collection Structure

```
Collections:
- ntfs_activity_hot (TTL index: 4 days)
  - Full activity records
  - Complete indexing for rapid query
  - Real-time ingestion

- ntfs_activity_warm (TTL index: 90 days)
  - Compressed records
  - Selective indexing
  - Batch ingestion from hot tier

- ntfs_activity_cool (No TTL)
  - Aggregated records
  - Minimal indexing
  - Batch ingestion from warm tier

- ntfs_activity_glacial (No TTL)
  - Statistical summaries
  - Ultra-efficient storage
  - Periodic ingestion from cool tier
```

### Processing Pipeline

```
Daily Job:
1. Identify hot records approaching expiration
2. Calculate importance scores using context-aware algorithms
3. Apply compression strategy based on importance:
   - High importance → Less compression, more attributes preserved
   - Low importance → Higher compression, fewer attributes preserved
4. Store in warm collection
5. Delete processed records from hot collection

Monthly Job:
1. Identify warm records approaching expiration
2. Re-evaluate importance based on usage patterns
3. Aggregate related activities into statistical summaries
4. Store in cool collection
5. Delete processed records from warm collection

Yearly Job:
1. Process cool records over 1 year old
2. Create long-term statistical summaries
3. Identify and preserve landmark events
4. Store in glacial collection
5. Delete processed records from cool collection
```

### Key Data Structures

#### Importance Scorer

```python
class ActivityImportanceScorer:
    def calculate_score(self, activity_record, context):
        # Start with base importance
        score = 0.3
        
        # Activity type importance
        if activity_record.activity_type in ["CREATE", "SECURITY_CHANGE"]:
            score += 0.2  # These are typically more significant
        
        # File characteristics
        if context.is_document(activity_record.file_path):
            score += 0.1
            
        # Usage patterns
        search_hits = context.get_search_hit_count(activity_record.file_reference)
        score += min(0.3, search_hits * 0.05)  # Cap at 0.3
        
        # Cross-source references
        references = context.get_entity_references(activity_record.file_reference)
        score += min(0.2, len(references) * 0.04)
        
        return min(1.0, score)  # Cap at 1.0
```

#### Compression Strategies

```python
class CompressionManager:
    def select_strategy(self, importance_score):
        if importance_score > 0.8:
            return FullDetailStrategy()
        elif importance_score > 0.5:
            return CoreAttributeStrategy()
        elif importance_score > 0.3:
            return RelationshipPreservingStrategy()
        else:
            return MinimalStrategy()
            
    def compress_record(self, record, importance_score):
        strategy = self.select_strategy(importance_score)
        return strategy.compress(record)
```

## Query Integration

The tiered recorder system is designed to be transparent to query operations:

1. **Unified View**: Create a database view that spans all tiers
2. **Tier Awareness**: Include tier information in results for context
3. **Detail Level Indicators**: Clearly mark records with their compression level
4. **Cross-Tier Joins**: Enable relationship traversal across compression tiers

## Performance and Efficiency Metrics

The system will track and report:

- **Storage Efficiency**: Compression ratios across tiers
- **Query Performance**: Response times for common queries
- **Relevance Preservation**: Success rate in preserving search-relevant records
- **Importance Prediction**: Accuracy of importance scoring algorithm
- **Resource Utilization**: CPU/memory impact of compression processes

## Next Steps for Implementation

1. Implement basic Hot Recorder that integrates with the NTFS collector
2. Develop importance scoring algorithm with initial heuristics
3. Create compression strategies for Warm tier
4. Implement TTL-based transition between Hot and Warm
5. Develop aggregation strategies for Cool tier
6. Build unified query interface across tiers
7. Implement usage feedback mechanism via search hits
8. Create monitoring and metrics for the tiered system

## Conclusion

This tiered recorder design creates a sophisticated, adaptive system that mirrors human memory, optimizes resource usage, and becomes more intelligent through usage patterns. The approach enables Indaleko to maintain comprehensive activity history while ensuring long-term sustainability and performance.