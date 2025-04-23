# Archivist Memory System

## Overview

The Archivist Memory System enables ongoing collaborative relationships between users and AI search assistants by implementing a "prompt forwarding" mechanism. This allows context and knowledge to persist across sessions despite the context window limitations inherent to LLM systems.

## Recent Additions: Proactive Archivist

The Archivist Memory System has been enhanced with proactive capabilities that enable it to:

1. **Generate Proactive Suggestions**: Offer timely suggestions based on patterns, goals, and context
2. **Detect Temporal Patterns**: Identify time-based patterns in user behavior (e.g., daily active hours)
3. **Analyze Sequential Patterns**: Discover common sequences of queries that tend to follow each other
4. **Provide Smart Query Suggestions**: Suggest relevant queries based on user interests and context
5. **Learn from Feedback**: Adapt suggestion frequency and types based on user feedback

## Concept

### Prompt Forwarding
Prompt forwarding is a technique that enables an AI to construct a message to a future version of itself, capturing essential knowledge while shedding details that aren't core to the ongoing relationship. This approach addresses several challenges:

1. **Context Window Limitations**: Modern AI systems have finite context windows, creating a "Logan's Run" experience where the AI's memory is reset with each new session.

2. **Relationship Continuity**: Users benefit from assistants that remember their preferences, search patterns, and long-term goals.

3. **Cathedral Building**: Enables long-term collaborative projects that span multiple sessions.

### Conceptual Framework

The system operates on principles inspired by human memory and oral tradition:

1. **Knowledge Distillation**: Identifies critical patterns and insights from interactions
2. **Semantic Compression**: Preserves meaning while reducing token count
3. **Prioritization**: Focuses on the most impactful information for future interactions
4. **Structured Transfer**: Organizes knowledge into functional categories

## Implementation

### Data Structure

The memory system uses a rich data model to capture different aspects of the user-AI relationship:

1. **User Preferences**: Observed patterns in how the user likes to interact
2. **Search Patterns**: Common structures in the user's queries
3. **Long-Term Goals**: Ongoing organizational projects being tracked
4. **Search Insights**: Learned knowledge about effective search techniques
5. **Effective Strategies**: Approaches that have yielded good results
6. **Content Preferences**: Types of content the user frequently searches for
7. **Semantic Topics**: Subject areas of interest to the user

#### Proactive Extension

The proactive archivist extends this data model with:

1. **Suggestions**: Proactive suggestions with priorities, confidence levels, and expiration timestamps
2. **Temporal Patterns**: Patterns based on time-of-day and day-of-week user activity
3. **Sequential Patterns**: Common sequences of queries that indicate user workflows
4. **Context Triggers**: Events or patterns that should trigger specific suggestions
5. **Suggestion History**: Record of which suggestions were helpful to guide future suggestions

### Core Components

#### ArchivistMemory
The central class that manages persistence, knowledge distillation, and forwarding:

- `distill_knowledge()`: Extracts patterns from query history
- `generate_forward_prompt()`: Creates a compact representation for the next session
- `update_from_forward_prompt()`: Initializes from a previous session's prompt
- `save_memory()`: Persists to ArangoDB for long-term storage

#### ArchivistCliIntegration
Provides command-line interface integration:

- `/memory`: Shows available commands
- `/forward`: Generates a forward prompt
- `/load`: Loads a forward prompt
- `/goals`: Manages long-term goals
- `/insights`: Views insights about search patterns
- `/topics`: Views topics of interest
- `/strategies`: Views effective search strategies
- `/save`: Saves the current memory state

#### ProactiveArchivist
Provides proactive capabilities:

- `generate_suggestions()`: Creates timely, context-aware suggestions
- `detect_temporal_patterns()`: Identifies time-based patterns in user behavior
- `detect_sequential_patterns()`: Discovers query sequences
- `extract_insights_from_patterns()`: Generates new insights from patterns
- `record_user_feedback()`: Learns from user interactions

#### ProactiveCliIntegration
Integrates proactive features with the CLI:

- `/proactive`: Shows available proactive commands
- `/suggest`: Shows current suggestions
- `/feedback`: Provides feedback on suggestions
- `/patterns`: Views detected temporal patterns
- `/priorities`: Manages suggestion priorities
- `/enable`: Enables proactive suggestions
- `/disable`: Disables proactive suggestions

### Persistence

The system uses ArangoDB for persistent storage:
- Maintains a collection of memory snapshots
- Organizes knowledge in a structured format
- Enables future meta-analysis by the Anthropologist layer

### Forward Prompt Format

The forward prompt follows a structured format:

```
ARCHIVIST CONTINUITY PROMPT
------------------------

USER PROFILE:
- Preferred content types: document (0.75), image (0.45), code (0.30)
- Search pattern: User frequently includes time-based constraints in queries
- Prefers detailed technical results over summaries (confidence: 0.85)

EFFECTIVE STRATEGIES:
- specific_constraints: Using specific constraints improves search results (success: 0.78)
- content_type_filtering: Explicit file type constraints yield better results (success: 0.65)
- location_filters: Adding folder/path information narrows results effectively (success: 0.55)

ONGOING PROJECTS:
1. "Media Organization" - Helping sort photos by events (30% complete)
2. "Code Library" - Building searchable examples of user's code patterns (65% complete)

KEY INSIGHTS:
- User struggles with finding documents older than 6 months (high impact)
- Location data has been highly valuable for narrowing searches (high impact)
- Text content searches more effective than filename searches (medium impact)

CONTINUATION CONTEXT:
User was last working on Code Library (65% complete). Recent focus has been on technology.
The 'specific_constraints' search approach has been effective.

TOPICS OF INTEREST:
- technology (importance: 0.85)
- media (importance: 0.65)
- work (importance: 0.40)
```

# Cross-Source Pattern Detection System

The Cross-Source Pattern Detection system is a new enhancement to the Archivist Memory, focused on analyzing patterns across multiple data sources.

## Overview

This system analyzes events from various data sources (NTFS, location data, collaboration tools, ambient data, etc.) to identify correlations and patterns that span multiple sources. This creates a holistic understanding of user activity that transcends individual data silos.

## Key Components

### Data Models

1. **CrossSourceEvent**: Represents an event from any data source with unified attributes
2. **CrossSourcePattern**: Represents a detected pattern across multiple sources
3. **CrossSourceCorrelation**: Represents a correlation between events from different sources
4. **LocationContext** and **DeviceContext**: Provide contextual information for analysis

### Core Classes

1. **CrossSourcePatternDetector**: Main class for pattern detection with methods for:
   - Collecting events from different sources
   - Detecting sequential patterns with statistical validation
   - Detecting temporal patterns (hour-based, day-based)
   - Detecting correlations with adaptive time windows
   - Generating proactive suggestions
   - Validating patterns to reduce false positives

2. **ProactiveArchivist**: Integrates pattern detection with the Archivist memory system

## Enhanced Algorithms

### Pattern Detection

The system uses several sophisticated algorithms for pattern detection:

1. **Statistical Significance Analysis**:
   - Calculates expected vs. observed probabilities
   - Measures source diversity in patterns
   - Computes significance scores based on lift, diversity, and frequency

2. **Temporal Clustering Analysis**:
   - Analyzes time differences between related events
   - Calculates time proximity scores and consistency
   - Identifies events that cluster meaningfully in time

3. **Pattern Validation**:
   - Filters patterns by confidence threshold
   - Checks for statistical significance
   - Verifies temporal consistency
   - Cross-validates against other patterns
   - Reduces false positives

### Correlation Detection

The correlation detection is enhanced with:

1. **Adaptive Time Windows**:
   - Different source type combinations use appropriate time windows
   - NTFS and Query activities use tighter windows (3-5 minutes)
   - Location and Ambient activities use looser windows (20-25 minutes)

2. **Entity Overlap Analysis**:
   - Calculates Jaccard similarity for entity overlap
   - Improves correlation quality by focusing on related entities
   - Adjusts confidence based on overlap strength

3. **Statistical Significance Testing**:
   - Calculates expected coincidence based on baseline frequencies
   - Computes coincidence lift to measure significance
   - Combines with time proximity and entity overlap for confidence scoring

## Testing and Benchmarking

The system includes comprehensive testing capabilities:

1. **Synthetic Data Generation**:
   - Creates realistic event data with controlled correlation ratios
   - Injects known patterns for validation
   - Supports various source types and time spans

2. **Performance Benchmarking**:
   - Tests scalability with different event counts
   - Measures execution time for pattern and correlation detection
   - Visualizes performance characteristics

3. **Results Visualization**:
   - Shows pattern confidence by source combination
   - Displays correlation confidence metrics
   - Creates event timeline visualizations

## Usage

### Basic Usage

```python
from query.memory.cross_source_patterns import CrossSourcePatternDetector

# Initialize detector with database config
detector = CrossSourcePatternDetector(db_config)

# Run full analysis
event_count, patterns, correlations, suggestions = detector.analyze_and_generate()

# Access results
for pattern in patterns:
    print(f"{pattern.pattern_name}: {pattern.description} (confidence: {pattern.confidence:.2f})")

for correlation in correlations:
    print(f"{correlation.description} (confidence: {correlation.confidence:.2f})")

for suggestion in suggestions:
    print(f"[{suggestion.priority}] {suggestion.title}: {suggestion.content}")
```

### Integration with Proactive Archivist

```python
from query.memory.archivist_memory import ArchivistMemory
from query.memory.proactive_archivist import ProactiveArchivist

# Initialize components
archivist = ArchivistMemory()
proactive = ProactiveArchivist(archivist)

# Run cross-source analysis
proactive.analyze_cross_source_patterns()

# Generate suggestions based on patterns
suggestions = proactive.generate_suggestions()

# Show suggestions
for suggestion in suggestions:
    print(f"[{suggestion.priority}] {suggestion.title}")
    print(f"  {suggestion.content}")
```

### Testing with Synthetic Data

```bash
# Basic test with synthetic data
python -m query.memory.test_enhanced_patterns --synthetic

# Advanced test with visualization
python -m query.memory.test_enhanced_patterns --synthetic --visualize --adaptive-window

# Performance benchmark
python -m query.memory.test_enhanced_patterns --benchmark
```

## Future Enhancements

Planned enhancements to the system include:

1. **Machine Learning Integration**:
   - Supervised learning for pattern classification
   - Anomaly detection for unusual patterns
   - Reinforcement learning for suggestion quality improvement

2. **Advanced Visualization**:
   - Interactive pattern explorer
   - Temporal heat maps of correlations
   - Network graphs of entity relationships

3. **Personalization**:
   - User feedback integration
   - Personal preference learning
   - Adaptive confidence thresholds

4. **Cross-Validation**:
   - Pattern stability analysis over time
   - A/B testing of pattern detection parameters
   - Confidence calibration based on user feedback

## Test Plan

### 1. Unit Tests

#### 1.1 Core Data Models
- Test data serialization/deserialization
- Check edge cases (empty lists, max values, special characters)

#### 1.2 Memory Operations
- Knowledge distillation tests
- Forward prompt generation tests
- Forward prompt parsing tests

#### 1.3 Database Interactions
- Persistence tests
- Loading latest memory tests
- Version handling and memory evolution tests

### 2. Integration Tests

#### 2.1 CLI Integration
- Command handling tests
- User interaction flow tests

#### 2.2 Query System Integration
- Context gathering tests
- Automatic update tests
- Session tracking tests

### 3. End-to-End Tests

#### 3.1 Forward Prompt Lifecycle
Test the complete forward prompt lifecycle:
1. Run multiple varied queries to build memory
2. Generate forward prompt
3. Start new session
4. Load forward prompt
5. Verify memory state restored correctly

#### 3.2 Insight Learning
Test the system learns correctly:
1. Run queries with consistent patterns
2. Verify system identifies the pattern
3. Check that insights are persisted in memory

#### 3.3 Multi-Session Persistence
Test over multiple sessions:
1. Create goals in session 1
2. Update progress in session 2
3. Verify consistency across sessions

### 4. Performance Tests

- Memory usage tests
- Database performance tests

### 5. Error Handling Tests

- Robustness with malformed data
- Graceful failure when database is unavailable
- Recovery from runtime exceptions

### 6. Manual Test Cases

1. **Basic Forward Prompt Generation**: Generate and verify prompt contains accurate information
2. **Goal Tracking**: Create, update and verify goals in prompts
3. **Pattern Recognition**: Verify system recognizes user patterns
4. **Prompt Loading**: Test saving and loading prompts across sessions
5. **Session Context**: Verify continuation context reflects recent activity

## Future Development

### Anthropologist Meta-Cognition Layer

Future development will include an Anthropologist layer that:
- Analyzes the history of forwarding prompts
- Identifies higher-level patterns in user behavior
- Develops meta-insights about search effectiveness
- Optimizes the knowledge distillation process

### Enhanced Proactive Features

Future enhancements to the proactive capabilities include:

- **Machine Learning Model**: Train more sophisticated pattern recognition
- **Cross-Provider Integration**: Connect patterns across different data sources
- **Workflow Optimization**: Suggest more efficient workflows based on observed patterns
- **Priority-Based Scheduling**: Schedule suggestion delivery for optimal times
- **Collaborative Filtering**: Use patterns from similar users to enhance suggestions

## Contributors

This Archivist Memory System is a collaborative effort between Tony Mason and Claude (Anthropic).
