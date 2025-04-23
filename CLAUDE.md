# CLAUDE.md - Indaleko Development Guidelines

## Architectural Principles

### Collector/Recorder Pattern

The Collector/Recorder pattern is a foundational architectural model in Indaleko that strictly separates data collection from processing and storage:

1. **Collectors**:
   - **Only collect raw data** from sources (NTFS, Google Drive, Discord, etc.)
   - **Never normalize or translate** the collected data
   - **Never write directly to the database**
   - May write raw data to intermediate files for later processing
   - Should focus exclusively on efficient, reliable data gathering

2. **Recorders**:
   - **Process and normalize** data from collectors
   - **Translate** raw data into standardized formats
   - **Write processed data to the database**
   - Implement database queries and statistics generation
   - Handle entity mapping and relationship management

Common integration patterns:
- **Loose Coupling**: Collectors write to files, recorders read independently
- **Tight Coupling**: Recorders wrap collectors but maintain separation of concerns

### Architectural Integrity Guidelines

#### Component Interaction Rules

##### ✅ Correct Patterns
- Collectors write data to files or streams that Recorders can consume
- Recorders read from files/streams produced by Collectors
- Scripts may invoke a single Collector OR a single Recorder, never both

##### ❌ Prohibited Patterns
- Never instantiate a Recorder from within a Collector or collection script
- Never instantiate a Collector from within a Recorder
- Never implement "shortcut" pipelines that bypass the separation of concerns

#### Implementation Checkpoints

When implementing new functionality, verify your code against these questions:
1. Does my Collector directly or indirectly interact with any database components?
2. Does my script try to handle both collection and recording responsibilities?
3. Am I tempted to "simplify" by bypassing architectural boundaries?

If the answer to any of these is "yes," you're likely violating the architectural pattern.

#### Cross-Component Operations

For operations that span collection and recording:
- Create separate scripts that invoke each component in sequence
- Use clear file-based interfaces between components
- Implement proper error handling that respects component boundaries
- Document the expected data flow between components

#### Common Anti-Patterns to Avoid

1. **The Shortcut Anti-Pattern**: Bypassing architectural layers for convenience or performance
2. **The Monolith Anti-Pattern**: Creating scripts that handle multiple architectural responsibilities
3. **The Hidden Dependency Anti-Pattern**: Embedding database logic inside collection components

### Database Architecture

Indaleko uses a centralized approach for database collection management:

**Important: Never directly create collections!** Always use the centralized mechanisms:
1. **For Standard Collections**: Define them in `db/db_collections.py` in the `IndalekoDBCollections` class
2. **For Dynamic Collections**: Use the registration service in `utils/registration_service.py`

**Collection Naming**:
- Always use the constants from `IndalekoDBCollections` instead of string literals:
  ```python
  # BAD
  db.get_collection("Objects")

  # GOOD
  db.get_collection(IndalekoDBCollections.Indaleko_Object_Collection)
  ```
- This ensures consistency and makes it easier to update collection names

**Security Considerations**:
- Production uses UUID-based collection names for security
- Controlled collection access through centralized points
- Never call `db.create_collection()` directly
- Always use `IndalekoCollections.get_collection(collection_name)`

**Enforcement**:
- Pre-commit hooks enforce these patterns:
  - `check_create_collection_usage.py`: Ensures `create_collection()` is only called from authorized locations
  - `check_collection_constants.py`: Ensures collection names are referenced via constants, not strings
- Violating these patterns will prevent commits

### Cognitive Memory Architecture

Indaleko implements a biomimetic cognitive memory architecture with multiple tiers:

1. **Sensory Memory**:
   - High-fidelity recent activity data (TTL: 4 days)
   - Entity mapping system for stable identifiers
   - Importance scoring for retention decisions

2. **Short-Term Memory**:
   - Aggregated activity data with importance scoring
   - Longer retention period (30 days default)
   - Automatic consolidation from sensory memory

3. **Long-Term Memory** (In Development):
   - Archival tier for important historical data
   - Heavily compressed representation
   - Searchable via stable entity identifiers

## Development Environment

### Package Management
Indaleko uses `uv` for package management across multiple platforms. The dependencies are defined in `pyproject.toml`.

- **Setup Environment**:
  ```bash
  # Install uv if not already installed
  pip install uv

  # Install dependencies in the platform-specific virtual environment
  uv pip install -e .
  ```

### Virtual Environments
The project maintains separate virtual environments for each platform:
- `.venv-win32-python3.12` - Windows environment
- `.venv-linux-python3.13` - Linux environment
- `.venv-macos-python3.12` - macOS environment

Always activate the appropriate environment before running any Indaleko code:
```bash
# Linux
source .venv-linux-python3.13/bin/activate

# Windows (PowerShell)
.venv-win32-python3.12\Scripts\Activate.ps1

# Windows (Command Prompt)
.venv-win32-python3.12\Scripts\activate.bat

# macOS
source .venv-macos-python3.12/bin/activate
```

> **IMPORTANT**: Never run Indaleko code without activating the correct virtual environment first. Most errors and dependency issues occur when running outside the virtual environment.

### Cross-Platform Development
- All scripts must work with `-help` flag on all platforms, even if platform-specific imports fail
- For Windows-specific code, do conditional imports after CLI parsing, not at module level
- Never mask import errors for non-platform-specific packages
- Do not disable Ruff warnings without explicit approval

## Style Guidelines
- **Imports**: standard library → third-party → local (with blank lines between)
- **Types**: Use type hints for all functions and variable declarations
- **Formatting**: 4 spaces, ~100 char line length, docstrings with triple quotes
- **Naming**: CamelCase for classes, snake_case for functions/vars, UPPER_CASE for constants
- **Interfaces**: Prefix with 'I' (IObject, IRelationship)
- **Error handling**: Specific exceptions with descriptive messages
- **Documentation**: All modules, classes and methods need docstrings (Args/Returns sections)
- **Module organization**: Copyright header, imports, constants, classes, functions, main

### Timezone-Aware Datetime
Always use timezone-aware datetimes for ArangoDB compatibility:
```python
from datetime import datetime, timezone
from pydantic import BaseModel, Field, validator

class MyModel(BaseModel):
    # Use Field with default_factory for timezone-aware dates
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Add validators to ensure datetimes have timezones
    @validator('created_at')
    def ensure_timezone(cls, v):
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
```

### IndalekoBaseModel
Always extend IndalekoBaseModel (not Pydantic's BaseModel) for database models:

```python
from data_models.base import IndalekoBaseModel

class MyArangoModel(IndalekoBaseModel):
    name: str
    value: int

    class Config:
        json_schema_extra = {
            "example": {
                "name": "example_name",
                "value": 42
            }
        }
```

## Common Commands

### Core Commands
- Run all tests: `pytest tests/`
- Run single test: `pytest tests/path/to/test.py::test_function_name -v`
- Lint code: `flake8` or `pylint`
- Format code: `black .`
- Build package: `python -m build`

### Memory Commands
- Sensory memory verification: `./verify_sensory_memory.sh --full-verification`
- Load data to sensory memory: `./load_sensory_memory_data.sh --simulate --report`
- Run memory consolidation: `./run_memory_consolidation.sh --run --verbose`
- Configure consolidation: `./run_memory_consolidation.sh --run --age-hours 24 --batch-size 500`

### Query System Commands
- Test query tools: `python query/tools/test_tools.py --query "Your query here" --debug`
- Test EXPLAIN: `python query/test_explain.py --query "Your query here" --debug`
- Test enhanced NL: `python query/test_enhanced_nl.py --query "Your query here" --debug`
- Run CLI with enhanced NL: `python -m query.cli --enhanced-nl --context-aware --deduplicate`
- Run CLI with Archivist: `python -m query.cli --archivist --optimizer`
- Get help: `python -m query.cli --help`

### GUI Commands
- Run Streamlit GUI: `cd utils/gui/streamlit && streamlit run app.py`
- Run Windows GUI script: `run_gui.bat`
- Run Linux/macOS GUI script: `./run_gui.sh`

## Best Practices

### Error Handling
```python
try:
    # Operation that might fail
    result = risky_operation()
except (ValueError, KeyError) as e:
    # Handle specific errors
    logger.error(f"Failed to process data: {e}")
    raise IndalekoProcessingError(f"Data processing failed: {str(e)}") from e
```

### Logging
```python
from utils.i_logging import get_logger

logger = get_logger(__name__)
logger.info("Processing completed", extra={
    "object_id": obj.id,
    "process_time": elapsed_time,
    "result_count": len(results)
})
```

### Performance Tracking
```python
from perf.perf_mixin import IndalekoPerformanceMixin

class MyProcessor(IndalekoPerformanceMixin):
    def process_data(self, data):
        with self.perf_context("data_processing"):
            # Processing logic
```

### Testing
```python
def test_entity_equivalence_merge():
    # Arrange
    manager = EntityEquivalenceManager()
    entity1 = manager.add_entity_reference(...)
    entity2 = manager.add_entity_reference(...)

    # Act
    result = manager.merge_entities(entity1.entity_id, entity2.entity_id)

    # Assert
    assert result is True
    assert manager.get_canonical_reference(entity2.entity_id).entity_id == entity1.entity_id
```

## Key Components

### Activity Classification Framework
Indaleko uses a multi-dimensional classification framework for activities with weights from 0.0 to 1.0:

```python
from activity.data_model.activity_classification import IndalekoActivityClassification

classification = IndalekoActivityClassification(
    ambient=0.7,       # Background/passive use
    consumption=0.9,   # Media/content consumption
    productivity=0.2,  # Work-related activity
    research=0.5,      # Learning/information gathering
    social=0.1,        # Social interaction
    creation=0.0       # Content creation
)

# Get primary classification dimension
primary_dimension = max(classification.dict().items(), key=lambda x: x[1])[0]
```

### Activity Context Framework
The Activity Context system aggregates activities across sources with rich contextual filtering:

```python
from activity.context.service import ActivityContext

# Initialize context manager
context = ActivityContext(db_config)

# Get recent activities with minimum research classification
activities = context.get_recent_activities(
    time_window=3600,  # seconds
    classification_filter={
        "research": 0.5  # Minimum research dimension weight
    }
)
```

### Query System Integration
Indaleko features a modular query system with natural language understanding:

1. **NLParserTool**: Parses natural language queries to extract intent, entities, and collections
2. **AQLTranslatorTool**: Converts structured queries to AQL with bind variables
3. **QueryExecutorTool**: Executes or explains AQL queries

Data flow: Natural language → Parser → Translator → Executor

### ArangoSearch Views
Views enable efficient full-text search:

```python
# Using a view in a query
cursor = db.aql.execute(
    """
    FOR doc IN ObjectsTextView
    SEARCH ANALYZER(LIKE(doc.Label, @query), "text_en")
    SORT BM25(doc) DESC
    LIMIT 50
    RETURN doc
    """,
    bind_vars={"query": search_term}
)
```

## Troubleshooting

### Common Database Issues
- "No indexes are being used" - Add appropriate indexes for frequently filtered fields
- High `estimatedCost` - Refine your query to use indexes and reduce collection scans
- "collection not found" - Check collection names, ensure using valid collections
- "AQL: timeout" - Increase the `max_runtime` parameter or optimize your query
- "Not authorized" - Verify database credentials in config file

### Environment Issues
- Import errors - Ensure the correct virtual environment is activated
- Missing packages - Run `uv pip install -e .` to update dependencies
- Platform-specific errors - Check if code is running on the correct platform
- Performance issues - Use the performance monitoring tools to identify bottlenecks

### Integration Issues
- Data not being stored - Ensure recorder is properly connected to the database
- Missing relationships - Check that entity mapping is functioning correctly
- Incomplete activities - Verify collector implementation captures all necessary data
