# Knowledge Base Updating System

This module implements a knowledge base updating system for the Indaleko Archivist, allowing it to learn from interactions, track patterns, and improve recommendations over time.

## Core Components

### 1. Learning Events
The system captures learning events from various sources and uses them to update the knowledge base:

- **Query success events**: Successful queries that return useful results
- **User feedback events**: Explicit or implicit feedback from users
- **Entity discovery events**: New entity information
- **Schema update events**: Changes in data structure
- **Pattern discovery events**: Newly identified patterns

### 2. Knowledge Patterns
The system maintains a database of knowledge patterns that can be applied to enhance queries:

- **Query patterns**: Templates and parameters for common query types
- **Entity relationships**: Connections between different entities
- **Schema updates**: Evolution of data structure over time
- **User preferences**: Learned user preferences

### 3. Feedback System
Users can provide feedback that influences the system's learning:

- **Explicit positive**: Direct positive feedback from users
- **Explicit negative**: Direct negative feedback from users
- **Implicit positive**: Inferred from user actions (e.g., using results)
- **Implicit negative**: Inferred from user actions (e.g., ignoring results)

## Implementation

The key classes that implement the knowledge base updating functionality are:

- **KnowledgeBaseManager**: Core implementation that manages learning events, patterns, and feedback
- **ArchivistKnowledgeIntegration**: Integrates with Archivist memory and Entity Equivalence
- **KnowledgeBaseCliIntegration**: Provides CLI commands for knowledge base features

## Database Collections

The system uses the following ArangoDB collections:

- **LearningEvents**: Records of all learning events
- **KnowledgePatterns**: Database of learned patterns
- **FeedbackRecords**: Records of user feedback

## CLI Commands

The knowledge base system adds the following commands to the CLI:

- `/kb`: Show knowledge base commands
- `/patterns`: Show learned query patterns
- `/patterns [id]`: Show details for a specific pattern
- `/entities`: Show entity equivalence groups
- `/entities [name]`: Show details for entities matching name
- `/feedback positive`: Give positive feedback on last query
- `/feedback negative`: Give negative feedback on last query
- `/insights`: Show knowledge base insights

## Usage Examples

### Recording a Learning Event

```python
from knowledge_base import KnowledgeBaseManager, LearningEventType

kb_manager = KnowledgeBaseManager()

# Record a query success event
event = kb_manager.record_learning_event(
    event_type=LearningEventType.query_success,
    source="query_execution",
    content={
        "query": "Find documents about Indaleko",
        "intent": "document_search",
        "result_count": 5,
        "entities": ["Indaleko"],
        "collections": ["Objects"]
    },
    confidence=0.9
)
```

### Applying Knowledge to Enhance a Query

```python
# Enhance a query with learned patterns
enhanced_query = kb_manager.apply_knowledge_to_query(
    query_text="Show me files related to Indaleko",
    intent="document_search"
)

print(f"Enhanced Query: {enhanced_query}")
```

### Recording User Feedback

```python
from knowledge_base import KnowledgeBaseManager, FeedbackType

kb_manager = KnowledgeBaseManager()

# Record positive feedback
feedback = kb_manager.record_feedback(
    feedback_type=FeedbackType.explicit_positive,
    feedback_strength=0.9,
    feedback_data={
        "comment": "Great results for this query!",
        "result_relevance": 0.95,
        "result_completeness": 0.85,
        "interaction": "clicked_result"
    },
    query_id="query123"
)
```

### Using the Integration Layer

```python
from archivist.kb_integration import ArchivistKnowledgeIntegration

# Initialize the integration
kb_integration = ArchivistKnowledgeIntegration()

# Process a query
query_response = kb_integration.process_query(
    query_text="Find documents about knowledge base systems",
    query_intent="document_search",
    entities=[
        {
            "name": "knowledge base systems",
            "type": "topic",
            "original_text": "knowledge base systems"
        }
    ]
)
```

## Testing

To test the knowledge base functionality, use the test script:

```bash
# Run all tests
python archivist/test_knowledge_base.py --all

# Test specific features
python archivist/test_knowledge_base.py --events
python archivist/test_knowledge_base.py --patterns
python archivist/test_knowledge_base.py --feedback
python archivist/test_knowledge_base.py --queries
python archivist/test_knowledge_base.py --entities
python archivist/test_knowledge_base.py --stats
```

To test the CLI integration:

```bash
python archivist/kb_cli_integration.py --command "/patterns"
```

## Future Enhancements

- Predictive knowledge generation
- Cross-user knowledge sharing
- Adaptive query optimization
- Multi-modal learning
- Integration with large language models for more sophisticated pattern discovery
