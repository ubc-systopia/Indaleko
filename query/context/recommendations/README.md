# Contextual Query Recommendation Engine

This module implements a sophisticated recommendation engine for suggesting queries to users based on multiple sources of context including query history, activity context, entity relationships, and temporal patterns.

## Architecture

The recommendation engine uses a provider-based architecture where specialized providers generate recommendations from different sources. The main components are:

### Core Components

1. **RecommendationEngine**: Central coordinator that collects, ranks, and filters recommendations from all providers.
2. **RecommendationProvider**: Base class for all recommendation providers.
3. **QueryHistoryRecommender**: Generates recommendations based on query history.
4. **ActivityContextRecommender**: Generates recommendations based on user activities.
5. **EntityRelationshipRecommender**: Generates recommendations based on entity relationships.
6. **TemporalPatternRecommender**: Generates recommendations based on temporal patterns.
7. **RecommendationArchivistIntegration**: Integrates the recommendation engine with the Archivist memory system.

### Data Models

1. **QuerySuggestion**: Represents a recommended query with confidence, description, and source.
2. **RecommendationSource**: Enumeration of recommendation sources (QUERY_HISTORY, ACTIVITY_CONTEXT, etc.).
3. **RecommendationSettings**: Configuration settings for the recommendation engine.
4. **RecommendationFeedback**: Feedback on recommendations for learning.

## Integration with Archivist

The recommendation engine has been integrated with the Archivist memory system to:

1. Leverage Archivist's knowledge for more relevant recommendations
2. Enhance Archivist with recommendation capabilities
3. Convert recommendations to proactive suggestions
4. Share insights between the systems
5. Provide a unified CLI interface

## Key Features

1. **Multi-Source Recommendations**: Combines recommendations from multiple sources.
2. **Confidence-Based Ranking**: Ranks recommendations by confidence.
3. **Diversity Enforcement**: Ensures diversity in recommendations.
4. **Feedback Learning**: Learns from user feedback.
5. **Context Awareness**: Uses rich context for recommendations.
6. **Proactive Integration**: Works with Proactive Archivist for suggestions.
7. **CLI Integration**: Provides command-line interface for recommendations.

## Usage Examples

### Basic Usage

```python
from query.context.recommendations.engine import RecommendationEngine

# Create recommendation engine
engine = RecommendationEngine(debug=True)

# Get recommendations
recommendations = engine.get_recommendations(
    current_query="important documents",
    context_data={"recent_queries": ["project files", "documents to review"]}
)

# Display recommendations
for rec in recommendations:
    print(f"{rec.query} (confidence: {rec.confidence:.2f})")
    print(f"  {rec.description}")
```

### Archivist Integration

```python
from query.context.recommendations.archivist_integration import RecommendationArchivistIntegration
from query.memory.archivist_memory import ArchivistMemory
from query.memory.proactive_archivist import ProactiveArchivist

# Initialize components
memory = ArchivistMemory()
proactive = ProactiveArchivist(memory)

# Create integration
integration = RecommendationArchivistIntegration(
    cli_instance,
    archivist_memory=memory,
    proactive_archivist=proactive
)

# Register commands with CLI
integration.register_commands()

# Show recommendations
integration.show_recommendations("")
```

## CLI Commands

The integration provides the following CLI commands:

1. `/recommend`: Show query recommendations
2. `/rconfig`: Configure recommendation settings
3. `/rstats`: Show recommendation statistics
4. `/rfeedback`: Provide feedback on recommendations
5. `/rtest`: Test recommendation generation
6. `/rhelp`: Show recommendation help

## Testing

Use the `test_recommendation_integration.py` script to test the integration:

```bash
python query/context/test_recommendation_integration.py --debug
```

## Extending the Engine

To create a new recommendation provider:

1. Extend the `RecommendationProvider` base class
2. Implement the `generate_suggestions()` method
3. Register the provider with the engine

Example:

```python
from query.context.recommendations.base import RecommendationProvider
from query.context.data_models.recommendation import RecommendationSource

class MyCustomRecommender(RecommendationProvider):
    def __init__(self, **kwargs):
        super().__init__(RecommendationSource.CUSTOM, **kwargs)

    def generate_suggestions(self, current_query=None, context_data=None, max_suggestions=10):
        # Implementation here
        return suggestions
```

## Feedback Learning

The recommendation engine includes a feedback learning system:

1. Users provide feedback (accept/reject) on recommendations
2. The engine records feedback and shares it with providers
3. Providers update their models based on feedback
4. The engine adjusts confidence thresholds based on acceptance rates

This allows the system to continuously improve its recommendations based on user interactions.
