# Cross-Source Pattern Detection

## Introduction

Cross-Source Pattern Detection is an advanced feature of the Indaleko Proactive Archivist that identifies patterns and correlations across different data sources. This capability enables a more holistic understanding of user behavior and context, leading to more relevant and insightful proactive suggestions.

## Key Concepts

### Data Sources

The system analyzes events from multiple data sources:

1. **NTFS Activity**: File system events (creation, modification, deletion, etc.)
2. **Collaboration**: Events from Discord, Outlook, and other collaboration tools
3. **Location**: GPS, WiFi, and other location-based events
4. **Ambient**: Events from environmental sources like Spotify and smart thermostats
5. **Task Activity**: Task creation, completion, and management events
6. **Query**: Search activity from the Indaleko query interface

### Event Timeline

Events from all sources are collected and arranged in chronological order, creating a comprehensive event timeline for analysis. This unified timeline allows the system to identify relationships between events that occur close together in time.

### Pattern Types

The system identifies several types of patterns:

1. **Sequential Patterns**: Common sequences of events across different sources
2. **Temporal Patterns**: Events that regularly occur at specific times or days
3. **Location Patterns**: Activities associated with specific locations
4. **Correlated Events**: Events from different sources that frequently co-occur

### Contextual Understanding

In addition to patterns, the system builds contextual models:

1. **Location Context**: Understanding of different locations and associated activities
2. **Device Context**: Profiles of different devices and their typical usage
3. **Time Context**: Understanding of time-based behavior patterns
4. **Entity Relationships**: Connections between entities across different sources

## Architecture

### Components

1. **CrossSourceEvent**: Unified representation of events from any data source
2. **CrossSourcePattern**: Representation of patterns detected across sources
3. **CrossSourceCorrelation**: Representation of correlations between events
4. **CrossSourcePatternDetector**: Core engine for pattern and correlation detection
5. **ContextualData**: Models for contextual information (locations, devices, etc.)

### Data Flow

1. **Collection**: Events are collected from various data sources
2. **Timeline Construction**: Events are arranged chronologically
3. **Pattern Detection**: Sequential, temporal, and location patterns are identified
4. **Correlation Analysis**: Events are analyzed for meaningful correlations
5. **Suggestion Generation**: Patterns and correlations inform proactive suggestions
6. **Insight Extraction**: High-confidence patterns are converted to insights

### Integration with Proactive Archivist

The Cross-Source Pattern Detector enhances the Proactive Archivist in several ways:

1. **Unified Context**: Provides a more complete picture of user context
2. **Richer Suggestions**: Generates suggestions based on holistic understanding
3. **Enhanced Insights**: Produces insights that span multiple data sources
4. **Context-Aware Recommendations**: Leverages contextual models for better recommendations

## Implementation

### Event Collection

The system collects events from various sources through database queries:

```python
# Example: Collecting NTFS events
collection = db_config.db.collection("NTFSActivity")
cursor = collection.find(
    {"Record.Timestamp": {"$gt": last_update.isoformat()}},
    sort=[("Record.Timestamp", 1)],
    limit=max_events
)
```

### Pattern Detection

The system uses a sliding window approach to detect sequential patterns:

```python
# Scan through timeline with sliding window
for i in range(len(timeline) - window_size + 1):
    window = timeline[i:i+window_size]
    
    # Create sequence signature from event types
    event_signatures = []
    for event_id in window:
        event = self.data.events.get(event_id)
        if event:
            event_signatures.append(event.get_event_signature())
    
    # Create a sequence signature
    sequence_sig = "|".join(event_signatures)
    
    # Update counter
    sequence_counter[sequence_sig] += 1
```

### Correlation Analysis

The system groups events by time windows to detect correlations:

```python
# Analyze each time window for correlations
for window in time_windows:
    # Group events by source type
    events_by_source = defaultdict(list)
    for event_id in window:
        event = self.data.events.get(event_id)
        if event:
            events_by_source[event.source_type].append(event_id)
    
    # Check pairs of source types
    for i, source_type1 in enumerate(source_types):
        for j in range(i+1, len(source_types)):
            source_type2 = source_types[j]
            
            # Calculate correlation strength
            correlation = CrossSourceCorrelation(
                source_events=events1 + events2,
                source_types=[source_type1, source_type2],
                confidence=confidence,
                relationship_type=relationship_type,
                description=description
            )
```

### Suggestion Generation

The system generates suggestions based on detected patterns and correlations:

```python
# Create a suggestion based on a pattern
suggestion = ProactiveSuggestion(
    suggestion_type=suggestion_type,
    title=title,
    content=content,
    expires_at=now + timedelta(hours=1),
    priority=priority,
    confidence=pattern.confidence,
    context={"pattern_id": pattern.pattern_id}
)
```

## CLI Commands

The following commands are available for managing cross-source pattern detection:

- `/cross-source`: View cross-source pattern status
- `/cross-enable`: Enable cross-source pattern detection
- `/cross-disable`: Disable cross-source pattern detection
- `/cross-analyze`: Force a cross-source pattern analysis

## Example Patterns

### Sequential Pattern

```
Pattern: Cross-source pattern: ntfs + query
Description: Sequential pattern involving Ntfs and Query
Confidence: 0.75
Source Types: [NTFS, QUERY]
```

This pattern indicates that users frequently perform certain searches after specific file activities.

### Location Pattern

```
Pattern: Location pattern: Home + ntfs
Description: Activities at Home frequently involve ntfs events
Confidence: 0.70
Source Types: [LOCATION, NTFS]
```

This pattern indicates that the user frequently interacts with specific files when at home.

### Temporal Pattern

```
Pattern: Hour pattern: collaboration at 9:00
Description: Collaboration activity frequently occurs around 9:00-10:00
Confidence: 0.80
Source Types: [COLLABORATION]
```

This pattern indicates that the user frequently engages in collaboration activities during the 9:00 hour.

## Example Suggestions

Cross-source patterns lead to more contextually relevant suggestions:

1. **Location-based Content Suggestion**
   ```
   Files relevant to your location
   Based on your patterns, we've noticed you typically access certain files when at this location. Would you like to see them?
   ```

2. **Activity Correlation Suggestion**
   ```
   Connection between Music and Work
   We've noticed a correlation between your Spotify and work file activities. Would you like to explore this connection?
   ```

3. **Workflow Optimization Suggestion**
   ```
   Consider connecting Query and File activities
   You often use search and file operations together. Consider creating a workflow that connects them more efficiently.
   ```

## Future Enhancements

Planned enhancements for cross-source pattern detection include:

1. **Machine Learning Models**: More sophisticated pattern detection using ML techniques
2. **Semantic Understanding**: Incorporating semantic understanding of event content
3. **User Intent Modeling**: Inferring user intent from cross-source patterns
4. **Pattern Visualization**: Interactive visualizations of detected patterns
5. **Personalized Weighting**: Learning which patterns are most valuable to each user
6. **Real-time Detection**: Moving from batch analysis to real-time pattern detection