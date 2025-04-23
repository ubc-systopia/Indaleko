# Personal Digital Archivist

## Vision

The Personal Digital Archivist is an advanced evolution of Indaleko that proactively supports users by understanding their work context and history.

Rather than merely responding to explicit queries, the archivist:

- Recognizes the current project or task context
- Identifies relevant historical work and resources
- Proactively suggests helpful information at appropriate times
- Explains the relevance and connections between current and past work
- Learns from user interactions to improve future suggestions

The ideal experience is exemplified by interactions like:

> **Archivist**: "Tony, I see you're working on a new machine learning project. This is similar to work you did four years ago on customer churn prediction. Would you like me to pull up some relevant files?"

## Architecture

### 1. Project Context Understanding

This component recognizes and understands project-level contexts from user activities:

- **Activity Clustering**: Groups related activities into coherent projects
- **Document Similarity**: Computes semantic similarity between documents
- **Temporal Analysis**: Identifies natural project boundaries and transitions
- **Cross-Project Comparison**: Measures similarity between current work and historical projects

```python
def compare_current_project(current_activities, historical_projects):
    """Compare current work to historical projects."""
    # Generate embeddings for current activities
    current_embedding = embed_project(current_activities)

    # Compare to historical projects
    similarities = []
    for project in historical_projects:
        project_embedding = embed_project(project.activities)
        similarity = cosine_similarity(current_embedding, project_embedding)

        # Enhance with topic and temporal factors
        topical_overlap = calculate_topic_overlap(current_activities, project)
        temporal_recency = calculate_recency_factor(project.end_date)

        # Weighted final score
        adjusted_similarity = similarity * 0.6 + topical_overlap * 0.3 + temporal_recency * 0.1

        similarities.append((project, adjusted_similarity))

    return sorted(similarities, key=lambda x: x[1], reverse=True)
```

### 2. User Model & Personalization

This component builds a comprehensive model of the user's work patterns:

- **Project History**: Database of past projects and their key resources
- **Activity Patterns**: Model of typical work rhythms and preferences
- **Resource Importance**: Learns which resources are most valuable in different contexts
- **Interaction Preferences**: Adapts to how and when the user prefers suggestions

```python
class UserModel:
    """Models user preferences, work patterns, and information needs."""

    def __init__(self, user_id):
        self.user_id = user_id
        self.projects = []
        self.activity_patterns = ActivityPatternLearner()
        self.suggestion_preferences = SuggestionPreferenceModel()
        self.resource_importance = ResourceImportanceModel()

    def predict_information_needs(self, context):
        """Predict what information the user might need in a given context."""
        # Find similar historical contexts
        similar_contexts = self.find_similar_contexts(context)

        # Extract resources accessed in similar contexts
        candidate_resources = []
        for similar_context, similarity in similar_contexts:
            resources = similar_context.get_accessed_resources()
            for resource in resources:
                predicted_importance = self.resource_importance.predict(
                    resource, context
                )
                candidate_resources.append((resource, predicted_importance * similarity))

        return sorted(candidate_resources, key=lambda x: x[1], reverse=True)
```

### 3. Proactive Suggestion Engine

This component decides what to suggest and when:

- **Relevance Scoring**: Ranks potential suggestions by relevance to current context
- **Timing Model**: Determines optimal timing for suggestions
- **Explanation Generation**: Creates natural language explanations for suggestions
- **Suggestion Delivery**: Manages how suggestions are presented to the user

```python
class ProactiveSuggestionEngine:
    """Generates timely, contextual suggestions based on user activities."""

    def generate_suggestions(self, current_context):
        # Get relevant historical projects
        similar_projects = find_similar_projects(current_context)

        # Extract candidate resources
        candidates = []
        for project, similarity in similar_projects:
            if similarity > 0.7:  # Threshold for relevance
                resources = project.get_key_resources()

                for resource in resources:
                    importance = predict_resource_importance(
                        resource, current_context, similarity
                    )

                    candidates.append({
                        "resource": resource,
                        "relevance": similarity,
                        "importance": importance,
                        "source_project": project
                    })

        # Determine if this is a good time to suggest
        timing_score = evaluate_suggestion_timing(current_context)

        if timing_score > 0.8:  # Good time to suggest
            top_candidates = sort_and_filter_candidates(candidates)

            suggestions = []
            for candidate in top_candidates:
                explanation = generate_explanation(
                    candidate["resource"],
                    candidate["source_project"],
                    current_context
                )

                suggestions.append({
                    "resource": candidate["resource"],
                    "explanation": explanation,
                    "confidence": candidate["relevance"] * candidate["importance"]
                })

            return suggestions

        return []  # Not a good time for suggestions
```

### 4. Natural Language Interaction

This component manages the conversation with the user:

- **Dialogue Management**: Handles multi-turn conversations about suggestions
- **Natural Language Generation**: Creates fluent, contextual messages
- **Intent Understanding**: Interprets user responses to suggestions
- **Adaptive Communication**: Learns the user's preferred communication style

```python
def generate_suggestion_message(suggestion, confidence):
    """Generate a natural language message for a suggestion."""
    if confidence > 0.9:
        # High confidence template
        template = "Tony, I see you're working on {current_project}. This is similar to {past_project} from {time_ago}. Would you like me to pull up {resource_type} that might be relevant?"
    elif confidence > 0.7:
        # Medium confidence template
        template = "This reminds me of some work you did on {past_project}. There might be some {resource_type} from that project that could be helpful. Interested?"
    else:
        # Lower confidence template
        template = "You might want to check out some {resource_type} from {past_project} that seem somewhat related to what you're doing now."

    # Fill in template
    message = fill_template(
        template,
        current_project=current_context.project_name,
        past_project=suggestion["resource"].source_project.name,
        time_ago=format_relative_time(suggestion["resource"].source_project.end_date),
        resource_type=suggestion["resource"].type_description
    )

    return message
```

### 5. Learning from Interactions

This component improves the system based on user feedback:

- **Explicit Feedback**: Learns from direct user responses to suggestions
- **Implicit Feedback**: Observes how users interact with suggested resources
- **Model Updates**: Continuously refines suggestion quality and timing
- **Cold Start Handling**: Strategies for new users or projects

```python
class FeedbackLearningSystem:
    """Learns from explicit and implicit user feedback."""

    def record_explicit_feedback(self, suggestion, feedback):
        """Record explicit user feedback on a suggestion."""
        self.explicit_feedback.append({
            "suggestion": suggestion,
            "feedback": feedback,
            "timestamp": datetime.now(),
            "context": current_context
        })

        # Update models immediately
        update_models_from_explicit(suggestion, feedback)

    def record_implicit_feedback(self, suggestion, user_actions):
        """Record implicit feedback based on user actions."""
        engagement_level = calculate_engagement(user_actions)

        self.implicit_feedback.append({
            "suggestion": suggestion,
            "actions": user_actions,
            "engagement": engagement_level,
            "timestamp": datetime.now(),
            "context": current_context
        })

        # Update models from implicit feedback
        update_models_from_implicit(suggestion, engagement_level)
```

## Entity Equivalence Classes

Indaleko now includes a robust implementation of entity equivalence classes. This system allows different references to the same entity to be recognized and linked, enhancing natural language understanding and query capabilities.

### 1. Entity Equivalence Models

The implementation consists of several key data models:

- **EntityEquivalenceNode**: Represents a specific reference to an entity
  ```python
  class EntityEquivalenceNode(IndalekoBaseModel):
      entity_id: UUID
      name: str
      entity_type: IndalekoNamedEntityType
      canonical: bool = False  # Is this the primary name for the entity?
      source: Optional[str] = None  # Where this reference was found
      context: Optional[str] = None  # Additional context about this reference
  ```

- **EntityEquivalenceRelation**: Represents a relationship between entity references
  ```python
  class EntityEquivalenceRelation(IndalekoBaseModel):
      source_id: UUID  # ID of the source entity
      target_id: UUID  # ID of the target entity
      relation_type: str  # The type of relation (alias, nickname, etc.)
      confidence: float = 1.0  # Confidence score (0-1)
      evidence: Optional[str] = None  # Evidence supporting this relation
  ```

- **EntityEquivalenceGroup**: Represents a collection of equivalent entity references
  ```python
  class EntityEquivalenceGroup(IndalekoBaseModel):
      group_id: UUID = uuid4()
      canonical_id: UUID  # The ID of the canonical entity reference
      entity_type: IndalekoNamedEntityType
      members: List[UUID] = []  # List of entity reference IDs in this group
  ```

### 2. Entity Equivalence Manager

The `EntityEquivalenceManager` class provides comprehensive functionality for managing entity equivalences:

```python
class EntityEquivalenceManager:
    """
    Manages entity equivalence classes in Indaleko.

    This class is responsible for:
    1. Maintaining equivalence relationships between entity references
    2. Identifying potential equivalences using string similarity and context
    3. Resolving entity references to their canonical forms
    4. Managing the persistence of equivalence data
    """

    def add_entity_reference(self, name, entity_type, canonical=False, source=None, context=None):
        """Add a new entity reference to the system."""
        # Implementation...

    def add_relation(self, source_id, target_id, relation_type, confidence=1.0, evidence=None):
        """Add a relation between two entity references."""
        # Implementation...

    def merge_entities(self, source_id, target_id, relation_type="same_entity", confidence=1.0):
        """Merge two entities into the same equivalence class."""
        # Implementation...

    def get_canonical_reference(self, entity_id):
        """Get the canonical reference for an entity."""
        # Implementation...

    def get_all_references(self, entity_id):
        """Get all equivalent references for an entity."""
        # Implementation...
```

### 3. String Similarity Integration

The system leverages the Jaro-Winkler string similarity algorithm from `utils/misc/string_similarity.py` to automatically suggest potential equivalences:

```python
def _find_potential_matches(self, node, similarity_threshold=0.85):
    """Find potential matching entities for a given node."""
    matches = []

    # Check against all existing nodes of the same type
    for existing_id, existing_node in self._nodes_cache.items():
        # Skip if not the same entity type
        if existing_node.entity_type != node.entity_type:
            continue

        # Skip self-comparison
        if existing_id == node.entity_id:
            continue

        # Compute similarity
        similarity = jaro_winkler_similarity(
            node.name.lower(),
            existing_node.name.lower()
        )

        # If similarity is above threshold, add to matches
        if similarity >= similarity_threshold:
            matches.append((existing_id, similarity))

            # Suggest relation if high confidence
            if similarity >= 0.9:
                self._suggest_relation(node.entity_id, existing_id, similarity)

    return matches
```

### 4. Entity Graph Visualization

The system can generate graph representations of entity equivalence networks:

```python
def get_entity_graph(self, entity_id):
    """Get a representation of the entity's equivalence graph."""
    nodes = []
    edges = []

    # Find the group containing this entity
    target_group = None
    for group in self._groups_cache.values():
        if entity_id in group.members:
            target_group = group
            break

    # Add all members from the group
    for member_id in target_group.members:
        node = self._nodes_cache.get(member_id)
        if node:
            nodes.append({
                "id": str(node.entity_id),
                "name": node.name,
                "type": node.entity_type,
                "canonical": node.canonical
            })

    # Add all relations between group members
    for source_id in target_group.members:
        for target_id in target_group.members:
            if source_id != target_id:
                relation_key = f"{source_id}_{target_id}"
                relation = self._relations_cache.get(relation_key)
                if relation:
                    edges.append({
                        "source": str(relation.source_id),
                        "target": str(relation.target_id),
                        "type": relation.relation_type,
                        "confidence": relation.confidence
                    })

    return {"nodes": nodes, "edges": edges}
```

### 5. Database Integration

The implementation uses ArangoDB to store entity equivalence data:

- **EntityEquivalenceNodes**: A collection of all entity references
- **EntityEquivalenceRelations**: An edge collection of relationships between entities
- **EntityEquivalenceGroups**: A collection of entity equivalence groups

```python
def _setup_collections(self):
    """Set up the necessary collections in the database."""
    db = self.db_config.db

    # Entity equivalence nodes collection
    if not db.has_collection("EntityEquivalenceNodes"):
        db.create_collection("EntityEquivalenceNodes")

    # Entity equivalence relations collection
    if not db.has_collection("EntityEquivalenceRelations"):
        db.create_collection("EntityEquivalenceRelations", edge=True)

    # Entity equivalence groups collection
    if not db.has_collection("EntityEquivalenceGroups"):
        db.create_collection("EntityEquivalenceGroups")
```

### 6. Testing the Implementation

A comprehensive test suite is provided in `test_entity_equivalence.py`:

```bash
# Run all entity equivalence tests
python archivist/test_entity_equivalence.py --all

# Test specific components
python archivist/test_entity_equivalence.py --create  # Test entity creation
python archivist/test_entity_equivalence.py --merge   # Test entity merging
python archivist/test_entity_equivalence.py --graph   # Test entity graph generation
python archivist/test_entity_equivalence.py --multi   # Test multiple equivalence classes
python archivist/test_entity_equivalence.py --stats   # Test statistics

# Reset test data
python archivist/test_entity_equivalence.py --reset
```

### 7. Use Cases

The entity equivalence system enables several advanced capabilities:

1. **Entity Resolution**: Resolving different references to the same entity
   ```python
   # Given "Dr. Jones" in a query, can resolve to "Elizabeth Jones"
   canonical = manager.get_canonical_reference(entity_id)
   ```

2. **Reference Normalization**: Normalizing varied references in queries
   ```python
   # Convert various references to canonical forms before query execution
   query_entities = extract_entities(query)
   normalized_entities = [manager.get_canonical_reference(e.entity_id) for e in query_entities]
   ```

3. **Entity Network Analysis**: Understanding relationships between entities
   ```python
   # Get the full entity equivalence graph for visualization
   graph = manager.get_entity_graph(entity_id)
   ```

4. **Enhanced Query Understanding**: Leveraging entity relationships in queries
   ```python
   # For a query like "documents I shared with Beth last week"
   # Can resolve "Beth" to "Elizabeth Jones" for more accurate results
   ```

The entity equivalence system significantly enhances the Archivist's ability to understand natural language references and maintain contextual awareness across conversations.

## Request-based Assistant Implementation

The Archivist now includes a Request-based Assistant implementation using OpenAI's latest API, providing a more robust conversation management system with enhanced tool integration.

### Core Components

1. **Request Assistant Class**: `RequestAssistant` in `request_assistant.py` provides:
   - Thread-based conversation management via OpenAI's API
   - Tool registration and execution
   - Context management with automatic refresh capabilities
   - Memory integration with the `ArchivistMemory` system
   - Database operation tracking for system optimization

2. **CLI Interface**: `RequestArchivistCLI` in `request_cli.py` provides:
   - Interactive command-line interface
   - Support for conversation management commands
   - Entity management via `/entities` command
   - Memory visualization and management
   - Context refreshing for token limit management

3. **Context Management**: The system intelligently manages context:
   - Automatically summarizes large database schemas
   - Compresses large query results
   - Refreshes context windows when token limits are reached
   - Creates conversation summaries for continuity

4. **Named Entity Recognition**: The system now extracts and manages named entities:
   - Extracts entities from user messages (people, places, organizations, etc.)
   - Stores entities in the `NamedEntities` collection
   - Provides entity search, listing, and management
   - Enriches search capabilities by understanding references

## Usage

### Running the Entity Equivalence Tests

```bash
# Run all entity equivalence tests
python archivist/test_entity_equivalence.py --all

# Test specific components
python archivist/test_entity_equivalence.py --create --merge --graph
```

### Running the Request-based CLI

```bash
# Run the interactive CLI
python archivist/request_cli.py

# Run with a specific model
python archivist/request_cli.py --model gpt-4o-mini

# Run in debug mode
python archivist/request_cli.py --debug
```

### Testing the Implementation

```bash
# Run basic tests
python archivist/test_request_assistant.py --test basic

# Test conversation functionality
python archivist/test_request_assistant.py --test conversation

# Test context management
python archivist/test_request_assistant.py --test context

# Run all tests
python archivist/test_request_assistant.py --test all
```

## Contribution

This project is actively being developed. Contributions welcome in these areas:

- Entity equivalence algorithm improvements
- Context management techniques
- Memory systems and persistence optimizations
- Reflection and metacognition algorithms
- Entity network visualization
- Natural language understanding enhancements
- Database interaction recording optimization
