# Contextual Query Recommendation Engine

This document outlines the design and implementation plan for the Contextual Query Recommendation Engine, a component that suggests relevant queries based on the user's current context, past queries, and activity patterns.

## Overview

The recommendation engine analyzes multiple data sources to generate query suggestions that are likely to be useful to the user in their current context:

1. **Query History**: Past queries, their relationships, and effectiveness
2. **Activity Context**: Current and recent user activities across collectors
3. **Entity Relationships**: Connections between entities identified in queries
4. **Temporal Patterns**: Time-based patterns in user behavior

## Architecture

### Core Components

1. **RecommendationEngine**: Central coordinator for generating recommendations
2. **RecommendationSources**: Interface for components that provide recommendations
   - QueryHistoryRecommender: Based on query patterns and history
   - ActivityContextRecommender: Based on current activities
   - EntityRelationshipRecommender: Based on entity connections
   - TemporalPatternRecommender: Based on time-of-day patterns

3. **RecommendationRanker**: Scores and prioritizes recommendations
4. **RecommendationStorage**: Persists recommendations and feedback

### Data Flow

1. The engine collects input from multiple sources:
   - Current query (if any)
   - Recent queries and their results
   - Current activity context
   - Time and date information

2. Each recommender component generates candidate suggestions

3. The ranker evaluates and prioritizes suggestions based on:
   - Relevance to current context
   - Past effectiveness (if applicable)
   - User feedback on similar suggestions
   - Diversity considerations

4. Top recommendations are presented to the user

5. User interaction (accept/ignore/explicit feedback) is recorded

## Implementation Plan

### Phase 1: Core Infrastructure ✅

1. Create base interfaces and data models: ✅
   - `RecommendationSource` interface ✅
   - `QuerySuggestion` data model ✅
   - `RecommendationEngine` coordinator class ✅
   - `RecommendationRanker` with basic scoring ✅

2. Implement QueryHistoryRecommender: ✅
   - Analyze query patterns (refinement, broadening, pivot) ✅
   - Extract effective queries from history ✅
   - Generate variations of successful queries ✅

### Phase 2: Context-Aware Recommendations ✅

1. Implement ActivityContextRecommender: ✅
   - Connect to activity context system ✅
   - Generate recommendations based on current activities ✅
   - Create mappings between activity types and query templates ✅

2. Implement EntityRelationshipRecommender: ✅
   - Identify entities in current context ✅
   - Suggest queries based on related entities ✅
   - Incorporate entity importance scoring ✅

### Phase 3: Advanced Features ✅

1. Implement TemporalPatternRecommender: ✅
   - Analyze time-of-day patterns in queries ✅
   - Detect recurring information needs ✅
   - Generate suggestions based on schedule ✅

2. Enhance RecommendationRanker: ✅
   - Implement ML-based ranking algorithm ✅
   - Add personalization based on user preferences ✅
   - Incorporate diversity considerations ✅

### Phase 4: Integration and UI

1. Integrate with CLI:
   - Add commands to display recommendations
   - Implement feedback collection

2. Integrate with Assistant interface:
   - Add suggestion capabilities to conversations
   - Implement contextual prompts

3. Add visualization tools:
   - Display recommendation sources
   - Show relationships between suggestions

## API Design

### RecommendationEngine

```python
class RecommendationEngine:
    """Central coordinator for generating contextual query recommendations."""

    def get_recommendations(
        self,
        current_query: Optional[str] = None,
        context_data: Dict[str, Any] = None,
        max_results: int = 5
    ) -> List[QuerySuggestion]:
        """Generate recommendations based on current context."""
        pass

    def record_feedback(
        self,
        suggestion_id: UUID,
        feedback: FeedbackType,
        result_count: Optional[int] = None
    ) -> None:
        """Record user feedback about a suggestion."""
        pass
```

### RecommendationSource

```python
class RecommendationSource(ABC):
    """Interface for components that generate query suggestions."""

    @abstractmethod
    def generate_suggestions(
        self,
        current_query: Optional[str],
        context_data: Dict[str, Any],
        max_suggestions: int = 10
    ) -> List[QuerySuggestion]:
        """Generate query suggestions based on the given context."""
        pass

    @abstractmethod
    def update_from_feedback(
        self,
        suggestion: QuerySuggestion,
        feedback: FeedbackType,
        result_count: Optional[int] = None
    ) -> None:
        """Update internal models based on feedback."""
        pass
```

### QuerySuggestion

```python
class QuerySuggestion(IndalekoBaseModel):
    """Model representing a suggested query."""

    suggestion_id: UUID = Field(default_factory=uuid.uuid4)
    query_text: str
    rationale: str
    confidence: float
    source: str
    source_context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    relevance_factors: Dict[str, float] = Field(default_factory=dict)
```

## Evaluation Metrics

The recommendation engine will be evaluated based on:

1. **Acceptance Rate**: Percentage of suggestions that users select
2. **Success Rate**: Percentage of accepted suggestions that yield useful results
3. **Discovery Value**: How often suggestions lead to new insights
4. **Response Time**: Latency in generating recommendations
5. **Relevance**: How well suggestions match the current context

## Testing Strategy

1. **Unit Testing**:
   - Test each recommender component in isolation
   - Verify ranking algorithm with predefined scenarios

2. **Integration Testing**:
   - Test interaction with activity context system
   - Verify recommendation storage and retrieval

3. **End-to-End Testing**:
   - Test recommendation generation in CLI
   - Verify feedback collection and processing

4. **Synthetic Workload Testing**:
   - Generate synthetic query and activity data
   - Evaluate recommendation quality with different scenarios

## Timeline

1. Phase 1: Core Infrastructure - 1-2 days
2. Phase 2: Context-Aware Recommendations - 1-2 days
3. Phase 3: Advanced Features - 1-2 days
4. Phase 4: Integration and UI - 1 day

Total estimated time: 4-7 days
