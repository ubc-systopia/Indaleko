# Indaleko Ablation Study Framework

## Table of Contents
1. [Overview](#overview)
2. [Terminology](#terminology)
3. [Design Principles](#design-principles)
4. [Activity Data Types](#activity-data-types)
5. [Directory Structure](#directory-structure)
6. [Collection Management](#collection-management)
7. [Named Entity Recognition](#named-entity-recognition)
8. [Synthetic Data Generation](#synthetic-data-generation)
9. [Implementation Plan](#implementation-plan)
10. [Testing Strategy](#testing-strategy)
11. [Query Integration](#query-integration)
12. [Metrics and Analysis](#metrics-and-analysis)
13. [Integration with Existing Infrastructure](#integration-with-existing-infrastructure)

## Overview

The Indaleko Ablation Study Framework enables systematic research into how different activity data types affect query precision and recall. This framework provides a scientific methodology for measuring the impact of specific data collections on search effectiveness.

### Goals and Objectives

1. **Systematically measure** the impact of each activity data type on search effectiveness
2. **Generate synthetic data** for controlled experiments across all six activity types
3. **Use LLM-driven query generation** to create realistic search scenarios
4. **Produce accurate metrics** for statistical analysis of search effectiveness
5. **Follow Indaleko's architectural patterns** for proper database integration

### Core Components

The framework consists of these primary components:

- **Synthetic Data Generators** - Each activity type has a dedicated collector
- **Database Recorders** - Process and store generated data
- **NER Component** - Manages named entities like "home" and "work" for consistency
- **Query Generation System** - Uses LLM to create realistic search queries
- **Truth Data Tracker** - Records which files should match each query
- **Ablation Testing Framework** - Measures precision, recall and F1 score impacts
- **ArangoDB Integration** - Proper collection management and database access patterns

## Terminology

- **Activity Context**: A cursor mechanism for capturing activity state. **Not applicable to this project**.
- **Activity Data**: Information about specific events relatable to human episodic memory.
- **Activity Data Provider**: Code mechanism that converts Activity Data into normalized form.
- **ArangoDB**: Multi-modal database used by Indaleko.
- **Collection**: Logical storage unit in ArangoDB corresponding to specific schema.
- **Collector**: Component that "gathers" information without writing to the database.
- **Recorder**: Component that "records" information from collectors to the database.

## Design Principles

The ablation study framework adheres to Indaleko's established architectural principles:

### Collector/Recorder Pattern

- **Collectors** generate data but never interact with the database
- **Recorders** process collected data and handle database interactions
- **Controller** coordinates the workflow maintaining separation of concerns

### Integration Approach

- Collectors generate data in-memory
- Controller passes data directly to recorders
- Recorders handle database insertion
- Errors are handled with a fail-fast approach

### Database Access

- Use `IndalekoDBConfig()` for database connections
- Follow Indaleko's collection management patterns
- Use collection constants from `IndalekoDBCollections`
- Follow schema and data consistency guidelines

## Activity Data Types

The ablation study focuses on these six activity data types:

1. **Music Activity** - Music listening patterns from streaming services
2. **Location Activity** - Geographic position data from various sources
3. **Task Activity** - User task management and completion
4. **Collaboration Activity** - Calendar events and file sharing
5. **Storage Activity** - File system operations and access patterns
6. **Media Activity** - Video/content consumption activities

### Activity Type to Data Model Mapping

| Activity Data Type | Pydantic Data Model | File Location |
|--------------------|---------------------|---------------|
| Music Activity | AmbientMusicData | activity/collectors/ambient/music/music_data_model.py |
| Location (Geo) Activity | BaseLocationDataModel | activity/collectors/location/data_models/base_location_data_model.py |
| Task Activity | TaskActivityData | activity/collectors/task_activity/data_models/task_data_model.py |
| Collaboration Activity | BaseCollaborationDataModel | activity/collectors/collaboration/data_models/collaboration_data_model.py |
| Storage Activity | BaseStorageActivityData | activity/collectors/storage/data_models/storage_activity_data_model.py |
| Media Activity | YouTubeVideoActivity | activity/collectors/ambient/media/youtube_data_model.py |

### Storage Types

For simplicity, the ablation study uses two representative storage types:
- **Cloud**: OneDrive (chosen for its integration with collaboration activities)
- **Local**: ext4 (chosen for accessibility and simplicity)

## Directory Structure

To maintain separation from the main codebase, all work products are kept within the `/research` directory:

```
/research/
  ├── docs/                              # Documentation files
  ├── ablation/                          # Core ablation framework code
  │   ├── __init__.py
  │   ├── base.py                        # Base interfaces and classes
  │   ├── collectors/                    # Data generator implementations
  │   ├── recorders/                     # Database writer implementations
  │   ├── models/                        # Data models
  │   ├── query/                         # Query generation and tracking
  │   ├── ner/                           # Named Entity Recognition
  │   └── utils/                         # Utility functions
  ├── tests/                             # Test files
  │   ├── unit/                          # Unit tests
  │   ├── integration/                   # Integration tests
  │   └── system/                        # System tests
  ├── scripts/                           # Utility scripts
  └── results/                           # Results from ablation studies
      ├── raw/                           # Raw result data
      ├── reports/                       # Generated reports
      └── visualizations/                # Generated visualizations
```

### Integration with Main Codebase

For access from the main codebase without moving files, a lightweight entry point is provided:

```python
# /tools/ablation_study.py
"""Entry point for the ablation study framework."""

import sys
from pathlib import Path

# Add research directory to path
research_dir = Path(__file__).parent.parent / "research"
sys.path.append(str(research_dir))

# Re-export components from research project
from research.ablation import runner
from research.ablation.cli import main

if __name__ == "__main__":
    main()
```

### File Naming Conventions

- Python modules: Use snake_case (e.g., `entity_manager.py`)
- Class names: Use PascalCase (e.g., `EntityManager`)
- Function names: Use snake_case (e.g., `generate_data`)
- Constants: Use UPPER_SNAKE_CASE (e.g., `DEFAULT_SEED`)
- Documentation files: Use UPPER_SNAKE_CASE with `.md` extension
- Generated files: Include date/time stamp (e.g., `results_20250510_143000.json`)

## Collection Management

All database collections are defined as static collections. The collections for the ablation study are:

| Variable Name | Text | Purpose |
|---------------|------|---------|
| Indaleko_Ablation_Music_Activity_Collection | AblationMusicActivity | Synthetic music activity data |
| Indaleko_Ablation_Location_Activity_Collection | AblationLocationActivity | Synthetic location/geo activity data |
| Indaleko_Ablation_Task_Activity_Collection | AblationTaskActivity | Synthetic task management activity data |
| Indaleko_Ablation_Collaboration_Activity_Collection | AblationCollaborationActivity | Synthetic collaboration activity data |
| Indaleko_Ablation_Storage_Activity_Collection | AblationStorageActivity | Synthetic storage operation activity data |
| Indaleko_Ablation_Media_Activity_Collection | AblationMediaActivity | Synthetic media consumption activity data |
| Indaleko_Ablation_Query_Truth_Collection | AblationQueryTruth | Truth data for query evaluation |

Note that NER should use the existing collection (Indaleko_Named_Entity_Collection) because this is directly used as part of query resolution.  This eliminates the need to change that code flow.

## Named Entity Recognition

The Named Entity Recognition (NER) component manages named entities that represent common search terms and personalized references. It provides consistent entity definitions across the ablation study.

### NER Data Model

```python
class IndalekoNamedEntityDataModel(IndalekoBaseModel):
    """
    Data model for named entities in Indaleko.
    """
    entity_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        title="EntityID",
        description="Unique identifier for this named entity"
    )
    name: str = Field(
        ...,
        title="Name",
        description="The name of the entity (e.g., 'home', 'work', 'my phone')"
    )
    entity_type: str = Field(
        ...,
        title="EntityType",
        description="The type of entity (e.g., 'location', 'device', 'time period')"
    )
    attributes: List[Dict[str, Any]] = Field(
        ...,
        title="Attributes",
        description="List of attributes defining this entity"
    )
    # Additional fields omitted for brevity
```

### NamedEntityManager

The `NamedEntityManager` class provides the interface for interacting with named entities:

```python
class NamedEntityManager:
    """
    Manager for Indaleko's Named Entity Recognition (NER) system.
    """
    def __init__(self):
        """Initialize the NER manager with a database connection."""
        self.db_config = IndalekoDBConfig()
        self.db = self.db_config.get_arangodb()
        self.collection_name = IndalekoDBCollections.Indaleko_Named_Entity_Collection

    def get_entity_by_name(self, name: str, entity_type: Optional[str] = None):
        """Look up a named entity by its name."""
        # Implementation details omitted

    def add_entity(self, entity):
        """Add a new named entity to the collection."""
        # Implementation details omitted

    # Additional methods omitted for brevity
```

### NER Integration with Ablation Study

The NER system is integrated with query processing and synthetic data generation to ensure consistency between queries and expected results.

## Synthetic Data Generation

### Synthetic Data Construction Process

Constructing synthetic data follows these steps:

1. Create a model instance based on the appropriate Indaleko data model
2. Populate semantic attributes using known UUIDs
3. Pass the data to an appropriate recorder for database insertion

### Semantic Attributes

Semantic attributes are stored in a standardized format:

```python
{
    "Identifier": {
        "Identifier": str(uuid),
        "Label": "attribute_name"
    },
    "Value": attribute_value
}
```

UUIDs for semantic attributes are centrally defined (e.g., `ADP_LOCATION_LATITUDE = "edfdb410-8150-4bf0-8969-8ee4b9ba77c2"`).

### Generator Implementation Pattern

Each synthetic data generator follows this pattern:

```python
def generate_activity(parameters):
    """Generate synthetic activity data."""

    # Generate data based on parameters

    # Create semantic attributes
    semantic_attributes = [
        {"Identifier": ACTIVITY_ATTRIBUTE_ID, "Value": attribute_value},
        # Additional attributes
    ]

    # Create and return the activity record
    return ActivityDataModel(
        Record=create_record(),
        Timestamp=timestamp,
        SemanticAttributes=semantic_attributes,
        # Additional fields
    )
```

## Implementation Plan

The implementation will proceed in phases, focusing on correctness over performance and following the collector/recorder pattern.

### Phase 1: Infrastructure Setup (Week 1)

- Create project structure and base interfaces
- Implement base models
- Set up testing framework
- Integrate with database

### Phase 2: Data Model Implementation (Week 1-2)

- Implement Pydantic models for all six activity types
- Create semantic attribute registries
- Develop the NER component
- Implement validation utilities

### Phase 3: Collector Implementation (Week 2-3)

Implement synthetic data generators for each activity type:
- Music Activity Collector
- Location Activity Collector
- Task Activity Collector
- Collaboration Activity Collector
- Storage Activity Collector
- Media Activity Collector

### Phase 4: Recorder Implementation (Week 3-4)

For each activity type, implement a recorder that:
- Processes output from the collector
- Normalizes and transforms data
- Writes to the appropriate collection
- Implements error handling

### Phase 5: Query Generation and Integration (Week 4-5)

- Implement query generator using LLM
- Create integration with existing query pipeline
- Develop integration with NER
- Implement metrics collection
- Create truth data tracker

### Phase 6: Test Runner and Integration (Week 5-6)

- Implement ablation test runner
- Create CLI interface
- Develop integration tests
- Implement reporting and visualization

### Key Interfaces

#### Base Collector Interface

```python
class ISyntheticCollector(ABC):
    """Interface for all synthetic data collectors."""

    @abstractmethod
    def collect(self) -> dict:
        """Generate synthetic activity data."""
        pass

    @abstractmethod
    def generate_truth_data(self, query: str) -> set[UUID]:
        """Generate truth data for a specific query."""
        pass
```

#### Base Recorder Interface

```python
class ISyntheticRecorder(ABC):
    """Interface for all synthetic data recorders."""

    @abstractmethod
    def record(self, data: dict) -> bool:
        """Record synthetic activity data to the database."""
        pass

    @abstractmethod
    def record_truth_data(self, query_id: UUID, entity_ids: set[UUID]) -> bool:
        """Record truth data for a specific query."""
        pass
```

## Testing Strategy

The testing strategy is guided by these principles:

1. **Correctness Over Performance**: Ensure accurate results even at the expense of performance
2. **Deterministic Behavior**: Use fixed random seeds for reproducibility
3. **Layered Validation**: Test components individually and integrated
4. **Ground Truth Verification**: Always validate against known truth data
5. **Fail-Fast Approach**: Halt on errors rather than continuing with invalid data

### Testing Levels

#### 1. Unit Testing

Each component will have comprehensive unit tests:
- Query Generator
- Metadata Generator
- Named Entity Manager
- Synthetic Data Collectors
- Synthetic Data Recorders

#### 2. Integration Testing

These tests verify the correct interaction between components:
- Collector-Recorder Integration
- Query-Metadata Integration
- NER-Metadata Integration

#### 3. System Testing

These tests verify the entire ablation framework:
- End-to-End Ablation Test
- Database Integration Test
- LLM Integration Test

### Validation Criteria

#### 1. Data Correctness

- **Semantic Attributes**: All entities must have required semantic attributes with correct UUIDs
- **Timestamps**: All datetime fields must be timezone-aware (UTC)
- **Entity References**: Named entities must be consistently referenced
- **Collection Names**: Only use collection variables from IndalekoDBCollections

#### 2. Metadata Matching Validation

- **Temporal Consistency**: Matching data should have appropriate temporal relationships
- **Entity Consistency**: Entity references should match between query and data
- **Semantic Relevance**: Activity data should semantically match query components
- **Non-Matching Criteria**: Non-matches should differ in meaningful ways

#### 3. Metrics Validation

- **Ground Truth Alignment**: Results must match truth data
- **Impact Measurement**: Ablation impact should be measurable and consistent
- **Statistical Significance**: Results should have sufficient samples for validity
- **Reproducibility**: Fixed seeds should produce identical metrics

## Query Integration

The ablation study leverages Indaleko's existing query infrastructure:

1. **Query CLI Integration**
   - Use `query/cli.py` patterns to capture query history
   - Integrate with the query translator for NL → AQL conversion
   - Leverage existing metrics collection

2. **Assistant CLI Integration**
   - Use `query/assistants/cli.py` for enhanced query processing
   - Leverage named entity resolution tools
   - Use the Requests interface for structured query handling

3. **Query Pipeline**
   - Use the full query pipeline with parser → translator → executor
   - Track query execution plans for analysis
   - Capture performance metrics

### Query Diversity Analysis

To ensure the scientific rigor of the ablation study, the framework analyzes query diversity using Indaleko's existing Jaro-Winkler implementation:

```python
from utils.misc.string_similarity import jaro_winkler_similarity

def analyze_query_diversity(queries, similarity_threshold=0.85):
    """Analyze the diversity of a set of queries using Jaro-Winkler similarity."""
    # Extract query texts
    query_texts = [q["text"] for q in queries]

    # Calculate similarity matrix
    similarity_matrix = []
    for q1 in query_texts:
        row = []
        for q2 in query_texts:
            row.append(jaro_winkler_similarity(q1, q2))
        similarity_matrix.append(row)

    # Calculate diversity metrics
    n_queries = len(query_texts)

    # Count similar query pairs (excluding self-comparisons)
    similar_pairs = 0
    total_pairs = 0

    for i in range(n_queries):
        for j in range(i+1, n_queries):
            similarity = similarity_matrix[i][j]
            total_pairs += 1

            if similarity >= similarity_threshold:
                similar_pairs += 1

    # Calculate average similarity (ignoring self-comparisons)
    total_similarity = sum(similarity_matrix[i][j]
                         for i in range(n_queries)
                         for j in range(i+1, n_queries))
    avg_similarity = total_similarity / total_pairs if total_pairs > 0 else 0

    # Calculate diversity score (1 - avg_similarity)
    diversity_score = 1 - avg_similarity

    return {
        "diversity_score": diversity_score,
        "similar_query_pairs": similar_pairs,
        "total_query_pairs": total_pairs,
        "similar_pair_percent": (similar_pairs / total_pairs * 100) if total_pairs > 0 else 0,
        "average_similarity": avg_similarity
    }
```

The query generation system also implements diversity-driven query generation:

```python
def generate_diverse_queries(activity_type, count, similarity_threshold=0.85):
    """Generate a diverse set of queries, ensuring minimal redundancy."""
    diverse_queries = []
    attempts = 0
    max_attempts = count * 3  # Allow multiple attempts to find diverse queries

    while len(diverse_queries) < count and attempts < max_attempts:
        # Generate a candidate query
        candidate = generate_query(activity_type)
        candidate_text = candidate["text"]

        # Check similarity with existing queries
        is_diverse = True
        for existing_query in diverse_queries:
            existing_text = existing_query["text"]
            similarity = jaro_winkler_similarity(candidate_text, existing_text)

            if similarity >= similarity_threshold:
                is_diverse = False
                break

        # Add to diverse set if sufficiently different
        if is_diverse:
            diverse_queries.append(candidate)

        attempts += 1

    return diverse_queries
```

This approach ensures that:
1. The ablation study uses a diverse set of test queries
2. The diversity of the query set can be quantified with meaningful metrics
3. Redundant queries that could skew test results are filtered out

### Query-Truth Integration

The ablation framework includes a sophisticated integration between query generation and ground truth tracking, ensuring accurate performance measurement:

```python
class TestQuery:
    """Data class for a test query."""

    query_id: uuid.UUID
    query_text: str
    activity_types: List[ActivityType]
    difficulty: str  # easy, medium, hard
    expected_matches: List[str]  # List of document IDs that should match this query
    metadata: Dict[str, object]
```

The query generator produces TestQuery objects with expected_matches populated based on query characteristics:

```python
def generate_queries(count, activity_types=None, difficulty_levels=None):
    """Generate test queries with expected matches."""
    queries = []
    for i in range(count):
        # Select an activity type and difficulty level
        act_type = activity_types[i % len(activity_types)]
        difficulty = difficulty_levels[i % len(difficulty_levels)]

        # Generate query text from appropriate template
        query_text = generate_query_text(act_type, i)

        # Generate synthetic matching document IDs
        match_count = get_match_count_for_difficulty(difficulty)
        expected_matches = generate_expected_matches(act_type, match_count)

        # Create query object with expected matches
        query = TestQuery(
            query_text=query_text,
            activity_types=[act_type],
            difficulty=difficulty,
            expected_matches=expected_matches,
        )
        queries.append(query)

    return queries
```

The TruthTracker component records and retrieves truth data for performance measurement:

```python
class TruthTracker:
    """Tracker for query truth data."""

    def record_query_truth(self, query_id, matching_ids, query_text, activity_types):
        """Record truth data for a query."""
        doc = {
            "query_id": str(query_id),
            "query_text": query_text,
            "matching_ids": matching_ids,
            "activity_types": activity_types,
        }
        collection = self.db.collection(
            IndalekoDBCollections.Indaleko_Ablation_Query_Truth_Collection
        )
        return collection.insert(doc)

    def get_matching_ids(self, query_text, activity_types=None):
        """Get the document IDs that should match a query."""
        # Query the database to find matching IDs for this query
        # Implementation details omitted for brevity
        return matching_ids
```

The integration produces the following workflow:

1. Generate test queries with expected matches
2. Record truth data in the Indaleko_Ablation_Query_Truth_Collection
3. Execute queries against the database
4. Compare actual results with expected matches
5. Calculate precision, recall, and F1 score

This approach ensures that:
1. Ground truth is consistently maintained
2. Performance metrics are based on known expected results
3. Truth data can be persisted and reused for reproducibility
4. The impact of ablating collections can be precisely measured

## Metrics and Analysis

### Ablation Result Model

```python
class AblationResult(BaseModel):
    """Model for storing the results of an ablation test."""

    query_id: UUID
    ablated_collection: str
    precision: float
    recall: float
    f1_score: float
    execution_time_ms: int
    result_count: int
    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def impact(self) -> float:
        """Calculate the impact score of ablating this collection."""
        return 1.0 - self.f1_score
```

### Metrics Calculation

For each activity type, the framework will measure:
- **Precision**: How many returned results are relevant
- **Recall**: How many relevant items are found
- **F1 Score**: Harmonic mean of precision and recall
- **Impact**: Performance degradation when the collection is ablated
- **Relative Contribution**: Comparative importance of each activity type

### Results Reporting

Results will be stored in structured formats and presented through:
1. Summary reports
2. Detailed analysis reports
3. Visualizations (charts, graphs)
4. Raw data for further analysis

## Integration with Existing Infrastructure

### Database Access Pattern

```python
# Correct database access pattern
db_config = IndalekoDBConfig()
db = db_config.get_arangodb()
cursor = db.aql.execute(query, bind_vars=params)

# Using collection constants instead of hardcoded strings
collection_name = IndalekoDBCollections.Indaleko_Ablation_Music_Activity_Collection
db.collection(collection_name)

# Collection ablation with proper management
ablation_tester = AblationTester()
ablation_tester.ablate_collection("AblationMusicActivity")
# ... run tests ...
ablation_tester.restore_collection("AblationMusicActivity")
```

### Error Handling

```python
try:
    result = risky_operation()
except (ValueError, KeyError) as e:
    logger.error(f"Failed to process data: {e}")
    raise IndalekoProcessingError(f"Data processing failed: {str(e)}") from e
```

### Collector-Recorder Integration

The framework uses a wrapped interface pattern rather than file-based integration:

```python
# Controller
music_collector = MusicActivityCollector()
music_recorder = MusicActivityRecorder()

# Generate data
music_data = music_collector.collect()

# Record data
success = music_recorder.record(music_data)
```

This approach better aligns with the typical activity data handling patterns and simplifies the implementation.
