# CLAUDE.md - Indaleko Development Guidelines

## Current Work: Collection Ablation Framework

We've completed implementing and testing a collection ablation framework for measuring how different metadata types affect query precision and recall. The framework provides controlled testing of how the absence of specific collections impacts search effectiveness without requiring architectural changes.

### Collection Ablation Framework

The ablation mechanism allows us to:

1. **Hide specific collections** from queries to measure their impact
2. **Quantify the contribution** of each metadata type to search effectiveness
3. **Identify critical collections** for different query types
4. **Generate metrics** showing relative importance of metadata sources

The framework has been successfully tested with both mock data and real database integration:

```
python -m tools.data_generator_enhanced.testing.test_db_integration --dataset-size 100
python -m tools.data_generator_enhanced.testing.test_ablation --generate-data
```

### Implementation Components:

- **`IndalekoDBCollectionsMetadata`**: Enhanced with ablation tracking and filtering
- **`AblationTester`**: Test harness for measuring ablation impact on query results
- **`AQLAnalyzer`**: Component that examines how AQL queries change when collections are ablated
- **`test_ablation.py`**: Automated tests for the ablation mechanism
- **Database Integration Scripts**: `run_db_integration_test.sh/bat` for running comprehensive tests

### Critical Database Access Patterns

- **SECURITY ISSUE**: Always use `db.aql.execute()` instead of `db.execute()` for non-admin database access
- **Correct Pattern**:
  ```python
  db_config = IndalekoDBConfig()
  db = db_config.get_arangodb()
  cursor = db.aql.execute(query, bind_vars=params)
  ```
- **Dictionary Access**: Always use dictionary syntax for database objects: `obj["field"]` instead of `obj.field`
- **Registration Service Access**: Use `aql.execute()` in custom registration service implementations

### Database Integration Test Results

Our comprehensive database integration tests verified that:

1. **Generated Data Successfully Uploads**: All 10 generator types successfully upload to ArangoDB
2. **Schema Compatibility**: Generated data conforms to ArangoDB schema requirements
3. **Query Effectiveness**: Queries for generated data return correct results
4. **Collection Consistency**: Database operations maintain collection integrity

The integration test includes three levels of query complexity:
1. **Basic Attribute Query**: Single attribute, single collection
2. **Cross-Collection Query**: Single attribute, multiple collections
3. **Complex Query**: Multiple attributes with conditional filtering

To run the database integration tests:
```bash
./run_db_integration_test.sh --dataset-size 100
# Or on Windows:
run_db_integration_test.bat --dataset-size 100
```

### Query-Driven Framework Future Directions

We're extending the ablation framework into a query-driven generation system that:

1. **Analyzes Natural Language Queries**:
   - Extracts entities, actions, relationships, and context from NL queries
   - Determines which data generators are needed for each query
   - Identifies required data patterns and distributions for realistic testing

2. **Calculates Metadata Impact Scores**:
   - Measures precision/recall changes when collections are ablated
   - Generates impact scores for each metadata type
   - Identifies which combinations of metadata types provide optimal results
   - Creates visualizations of metadata contribution to search quality

### Implementation Principles

1. **Real Database Integration**:
   - Use actual database connections, not mocks
   - Test against real ArangoDB schema constraints
   - Handle database errors and constraints gracefully
   - Always use `aql.execute()` instead of `execute()` for queries

2. **Rich Semantic Attributes**:
   - Generate complete set of attributes for each entity type
   - Use proper UUIDs from semantic attribute registries
   - Ensure all attributes are queryable

3. **Consistent Data Access**:
   - Use dictionary access (obj["field"]) over attribute access (obj.field)
   - Never assume database objects expose attributes directly
   - Properly handle None/null values in query results

4. **Cross-Entity Relationships**:
   - Create proper links between related entities
   - Use consistent identifiers across entity types
   - Support complex relationship queries

## Architectural Principles

### Collector/Recorder Pattern

The Collector/Recorder pattern is a key architectural model in Indaleko that separates data collection from processing and storage:

1. **Collectors**:
   - **Only collect raw data** from sources (NTFS, Google Drive, Discord, etc.)
   - **Never normalize or translate** the collected data
   - **Never write directly to the database**
   - May write raw data to intermediate files for later processing
   - Focus exclusively on efficient, reliable data gathering

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
- Scripts invoke a single Collector OR a single Recorder, never both

##### ❌ Prohibited Patterns
- Never instantiate a Recorder from within a Collector
- Never instantiate a Collector from within a Recorder
- Never implement "shortcut" pipelines that bypass separation of concerns

#### Implementation Checkpoints

When implementing new functionality, verify your code against these questions:
1. Does my Collector interact with any database components?
2. Does my script handle both collection and recording responsibilities?
3. Am I bypassing architectural boundaries for convenience?

If the answer to any of these is "yes," you're likely violating the architectural pattern.

### Database Architecture

Indaleko uses a centralized approach for database collection management:

**Important: Never directly create collections!** Use the centralized mechanisms:
1. **Standard Collections**: Define in `db/db_collections.py` (`IndalekoDBCollections` class)
2. **Dynamic Collections**: Use `utils/registration_service.py`

**Collection Naming**:
- Always use constants from `IndalekoDBCollections`:
  ```python
  # GOOD
  db.get_collection(IndalekoDBCollections.Indaleko_Object_Collection)
  # BAD
  db.get_collection("Objects")
  ```

**Security and Enforcement**:
- Pre-commit hooks enforce these patterns (in `check_create_collection_usage.py` and `check_collection_constants.py`)
- Production uses UUID-based collection names for security
- Never call `db.create_collection()` directly

### Cognitive Memory Architecture

Indaleko uses a multi-tier memory architecture:

1. **Hot Tier (Sensory Memory)**:
   - Recent high-fidelity activity data (4 days TTL)
   - Entity mapping for stable identifiers
   - Primary input: `run_ntfs_activity.bat`

2. **Warm Tier (Short-Term Memory)**:
   - Aggregated activity with importance scoring (30 days TTL)
   - Transition: `run_tier_transition.bat`

3. **Cold Tier (Long-Term Memory)**:
   - Archival storage for important historical data
   - Compressed representation for efficient storage

Tier management commands:
```
run_memory_consolidation.bat --consolidate-all
run_tier_transition.bat --run --age-hours 12 --batch-size 1000
```

## Development Environment

### Package Management
Indaleko uses `uv` for dependency management (defined in `pyproject.toml`):

```bash
# Install uv
pip install uv

# Install dependencies
uv pip install -e .
```

### Virtual Environments
Platform-specific environments:
- Windows: `.venv-win32-python3.12`
- Linux: `.venv-linux-python3.13`
- macOS: `.venv-macos-python3.12`

Always activate before running code:
```bash
# Linux
source .venv-linux-python3.13/bin/activate

# Windows (PowerShell)
.venv-win32-python3.12\Scripts\Activate.ps1

# Windows (CMD)
.venv-win32-python3.12\Scripts\activate.bat

# macOS
source .venv-macos-python3.12/bin/activate
```

### Cross-Platform Development
- All scripts must work with `-help` flag on all platforms
- For Windows-specific code, use conditional imports after CLI parsing
- Don't mask import errors for non-platform-specific packages

## Style Guidelines
- **Imports**: standard library → third-party → local
- **Types**: Use type hints for all functions and variables
- **Formatting**: 4 spaces, ~100 char line length
- **Naming**: CamelCase (classes), snake_case (functions/vars), UPPER_CASE (constants)
- **Interfaces**: Prefix with 'I' (IObject, IRelationship)
- **Documentation**: Docstrings with Args/Returns sections

### Timezone-Aware Datetime
Always use timezone-aware datetimes for ArangoDB:
```python
from datetime import datetime, timezone
from pydantic import Field

class MyModel(IndalekoBaseModel):
    # Timezone-aware dates
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @validator('created_at')
    def ensure_timezone(cls, v):
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
```

### Data Models
Always extend IndalekoBaseModel for database models:
```python
from data_models.base import IndalekoBaseModel

class MyArangoModel(IndalekoBaseModel):
    name: str
    value: int
```

## Common Commands

### Testing & Development
- Run tests: `pytest tests/`
- Format code: `black .`
- Lint code: `flake8`

### Data Collection
- NTFS activity: `run_ntfs_activity_v2.py --volumes C: --interval 30`
- Semantic extraction: `python semantic/run_scheduled.py --all`
- File system indexing: `python run_incremental_indexer.py --volumes [PATH]`

### Memory Management
- Hot tier verification: `verify_hot_tier.bat` (or `.sh`)
- Tier transitions: `run_tier_transition.bat --run --age-hours 12`
- Memory consolidation: `run_memory_consolidation.bat --consolidate-all`

### Query & GUI
- Run CLI: `python -m query.cli --enhanced-nl --context-aware`
- Run GUI: `run_gui.bat` (or `./run_gui.sh`)

### Data Generator
- Run all data generator tests: `./tools/data_generator_enhanced/run_all_tests.sh`
- Run individual generator tests: `./tools/data_generator_enhanced/run_*_tests.sh`
- Run specific generator: `python -m tools.data_generator_enhanced.generate_data`
- Run database integration tests: `python -m tools.data_generator_enhanced.testing.test_*_db_integration`
- Check test status: `tools/data_generator_enhanced/TEST_STATUS.md`
- Check implementation status: `tools/data_generator_enhanced/IMPLEMENTATION_STATUS.md`

## Best Practices

### Database Integration
```python
# Always test with real database connections
def setup_db_connection(self):
    try:
        self.db_config = IndalekoDBConfig()
        self.db = self.db_config.get_arangodb()
        return True
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return False

# Use dictionary-style access for ArangoDB compatibility
# CORRECT
checksum_value = document["MD5"]
# INCORRECT - will fail with dictionaries
checksum_value = document.MD5

# Create proper semantic attributes as dictionaries
attribute = {
    "Identifier": {
        "Identifier": SEMANTIC_ATTRIBUTE_ID,
        "Label": "Attribute Label"
    },
    "Value": attribute_value
}
```

### Error Handling
```python
try:
    result = risky_operation()
except (ValueError, KeyError) as e:
    logger.error(f"Failed to process data: {e}")
    raise IndalekoProcessingError(f"Data processing failed: {str(e)}") from e
```

### Entity Lookups
Always lookup file system entities by natural identifiers first:
```python
# CORRECT: Use natural identifiers (FRN, Volume GUID)
cursor = db.aql.execute(
    """
    FOR doc IN Objects
    FILTER doc.LocalIdentifier == @frn AND doc.Volume == @volume
    LIMIT 1
    RETURN doc
    """,
    bind_vars={"frn": file_reference_number, "volume": volume_guid}
)
```

### Logging
```python
from utils.logging_setup import setup_logging

# Start of main function
setup_logging()
logger = logging.getLogger(__name__)
```

### CLI Template
Use the standard CLI template for all command-line tools:
```python
def main() -> None:
    setup_logging()
    runner = IndalekoCLIRunner(
        cli_data=cli_data,
        handler_mixin=YourHandlerMixin(),
        features=IndalekoBaseCLI.cli_features(),
        Run=your_run_function,
    )
    runner.run()
```

See `NTFS_ACTIVITY_CLI_README.md` for details.
