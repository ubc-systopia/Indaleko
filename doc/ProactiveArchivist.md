# Proactive Archivist

## Introduction

The Proactive Archivist extends Indaleko's Archivist memory system with intelligent, proactive capabilities. It analyzes patterns in user behavior and anticipates information needs, generating timely suggestions before they're explicitly requested.

The system has been enhanced with cross-source pattern detection, which identifies patterns and correlations across different data sources for a more holistic understanding of user context and behavior. See [CrossSourcePatterns.md](CrossSourcePatterns.md) for detailed information about this feature.

## Key Features

### 1. Proactive Suggestions

The Proactive Archivist can generate several types of suggestions:

- **Query Suggestions**: Recommended queries based on user interests and patterns
- **Content Suggestions**: Recommendations for relevant content
- **Organization Suggestions**: Tips for better information organization
- **Reminders**: Time-based reminders for ongoing goals or projects
- **Search Strategy Suggestions**: Recommendations for more effective search techniques
- **Related Content Suggestions**: Connections between different types of content

### 2. Temporal Pattern Recognition

The system identifies time-based patterns in user behavior:

- **Daily Patterns**: Active hours during the day
- **Weekly Patterns**: Most active days of the week
- **Monthly Patterns**: Monthly usage patterns
- **Session Patterns**: Common behaviors within a session

### 3. Sequential Pattern Analysis

The system detects common sequences in user queries:

- **Query Chains**: Sequences of queries that frequently follow each other
- **Workflow Patterns**: Common pathways through information
- **Refinement Patterns**: How users refine their searches

### 4. Cross-Source Pattern Detection

The system identifies patterns that span different data sources:

- **Activity Correlations**: Relationships between different types of activities
- **Location-Based Patterns**: Activities associated with specific locations
- **Contextual Connections**: Understanding of how different contexts relate
- **Holistic User Modeling**: A more complete picture of user behavior

### 4. Feedback-Based Learning

The system learns from user feedback:

- **Explicit Feedback**: Direct feedback on suggestions (positive/negative)
- **Implicit Feedback**: Tracking which suggestions are acted upon
- **Adaptive Thresholds**: Adjusting suggestion frequency based on feedback
- **Personalized Priorities**: Learning which suggestion types are most valuable

## Implementation

### Core Components

1. **ProactiveArchivist**: Main class that provides proactive capabilities
2. **ProactiveSuggestion**: Data model for individual suggestions
3. **SuggestionType**: Enum defining the types of suggestions
4. **SuggestionPriority**: Enum defining priority levels
5. **TemporalPattern**: Data model representing time-based patterns
6. **ProactiveArchivistData**: Container for all proactive state
7. **ProactiveCliIntegration**: CLI integration for proactive features

### Integration with Archivist

The Proactive Archivist builds on the foundation of the Archivist memory system:

- Uses insights and patterns from the core Archivist
- Adds new dimensions of pattern recognition
- Generates suggestions based on combined knowledge
- Contributes new insights back to the Archivist memory

## Usage

### Command Line Integration

Enable proactive features:

```bash
python -m query.cli --archivist --proactive
```

Basic commands:

- `/proactive`: Show available proactive commands
- `/suggest`: Show current suggestions
- `/feedback <number> positive|negative`: Provide feedback on suggestions
- `/patterns`: View detected temporal patterns
- `/priorities`: Manage suggestion priorities
- `/enable`: Enable proactive suggestions
- `/disable`: Disable proactive suggestions

Cross-source pattern commands:

- `/cross-source`: View cross-source pattern status
- `/cross-enable`: Enable cross-source pattern detection
- `/cross-disable`: Disable cross-source pattern detection
- `/cross-analyze`: Force a cross-source pattern analysis

### Programmatic Usage

To use in your own code:

```python
from query.memory.archivist_memory import ArchivistMemory
from query.memory.proactive_archivist import ProactiveArchivist

# Initialize components
archivist_memory = ArchivistMemory()
proactive = ProactiveArchivist(archivist_memory)

# Generate suggestions
context = {"last_queries": ["find pdf documents", "search for budget reports"]}
suggestions = proactive.generate_suggestions(context)

# Update with patterns
proactive.detect_temporal_patterns(query_history)
proactive.detect_sequential_patterns(query_history)
proactive.extract_insights_from_patterns()

# Record feedback
proactive.record_user_feedback(suggestion_id, feedback_value)
```

## Example Suggestions

The proactive archivist can generate suggestions like:

1. **Goal-based Suggestion**:
   ```
   Continue work on Document Organization
   You haven't made progress on 'Document Organization' recently. Current progress is 35%. Would you like to continue work on this goal?
   ```

2. **Topic-based Query Suggestion**:
   ```
   Suggested search: work documents
   Based on your interests, you might want to try: 'recent work documents from last month'
   ```

3. **Temporal Pattern Suggestion**:
   ```
   Scheduled activity: Daily review
   Based on your usual patterns, it's time for: checking recent email attachments
   ```

4. **Strategy Suggestion**:
   ```
   Try search strategy: specific_constraints
   This search approach might improve your results: Using specific constraints (e.g., dates, exact terms) improves search results
   ```

## Architecture Design

### Data Flow

1. **Query Processing**: Each query updates context and pattern analysis
2. **Pattern Detection**: Regular analysis of temporal and sequential patterns
3. **Suggestion Generation**: Creation of suggestions based on patterns and context
4. **Feedback Collection**: Recording and learning from user feedback
5. **Insight Extraction**: Generating insights from patterns
6. **Memory Integration**: Sharing insights with the core Archivist memory

### Confidence and Priority

Suggestions include:

- **Confidence Score**: How confident the system is in the suggestion (0.0-1.0)
- **Priority Level**: Importance of the suggestion (low, medium, high, critical)
- **Expiration**: When the suggestion is no longer relevant

### User Experience Considerations

The system is designed with these principles:

- **Non-Intrusive**: Doesn't overwhelm with too many suggestions
- **Relevant**: Suggestions are tied to current context and goals
- **Timely**: Delivered at appropriate moments
- **Dismissible**: Easy to dismiss or disable suggestions
- **Adaptive**: Learns which suggestions are helpful

## Future Enhancements

Planned enhancements include:

1. **Machine Learning Integration**: More sophisticated pattern recognition using ML models
2. **Predictive Query Generation**: Generating more sophisticated query suggestions using LLMs
3. **Workflow Analysis**: Deeper understanding of user workflows
4. **Semantic Understanding**: Adding semantic meaning to cross-source patterns
5. **Priority-Based Scheduling**: Optimizing when suggestions are shown
6. **A/B Testing**: Automatically testing different suggestion strategies
7. **Real-time Pattern Detection**: Moving from batch analysis to real-time detection