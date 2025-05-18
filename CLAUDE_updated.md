# CLAUDE.md - Indaleko Development Guidelines

## Current Work: Collection Ablation Framework

We've implemented a robust collection ablation framework for measuring how different metadata types affect query precision and recall. The framework provides controlled testing of how the absence of specific collections impacts search effectiveness without requiring architectural changes.

### Collection Ablation Framework

The ablation mechanism allows us to:

1. **Hide specific collections** from queries to measure their impact
2. **Quantify the contribution** of each metadata type to search effectiveness
3. **Identify critical collections** for different query types
4. **Generate metrics** showing relative importance of metadata sources

Progress on the ablation framework:
- ✅ Fixed LIMIT statement issue in AQL queries that was artificially restricting results
- ✅ Implemented proper collection ablation with `IndalekoDBCollectionsMetadata`
- ✅ Created metrics calculation for precision, recall, F1, and impact
- ✅ Verified end-to-end functionality with test datasets
- ✅ Implemented comprehensive ablation testing framework
- ✅ Created SQLite-based truth data tracking system
- ✅ Developed cluster-based approach with 4/2 source split
- ✅ Added enhanced query generation targeting specific activity types
- 🔄 Next steps in ABLATION_INTEGRATION_TODO.md

### Core Commands:

**Run simplified ablation test:**
```bash
python test_ablation_comprehensive.py
```

**Run mock demonstration of the framework:**
```bash
python tools/data_generator_enhanced/testing/mock_generator_demo.py
```

**Run full ablation integration test:**
```bash
python run_ablation_integration_test.py --dataset-size 100 --num-queries 10
```

**Cross-platform runners:**
```bash
# Linux/macOS
./run_ablation_test.sh

# Windows
run_ablation_test.bat
```

**Reset database for clean testing:**
```bash
python -m db/db_config reset
```

### Main Framework Components:

- **`truth_data_tracker.py`**: SQLite-based system for tracking test data and results
- **`cluster_generator.py`**: Manages 4/2 split of activity sources for testing
- **`query_generator_enhanced.py`**: Generates queries targeting specific metadata types
- **`ablation_integration_test.py`**: End-to-end integration test for ablation framework
- **`IndalekoDBCollectionsMetadata`**: Manages collection ablation and restoration
- **`ablation_execute_query.py`**: Fixed query execution that handles LIMIT statements properly
- **`test_ablation_comprehensive.py`**: Simplified ablation test that runs end-to-end
- **`test_ablation.py`**: Automated tests for the ablation mechanism
- **`ABLATION_INTEGRATION_TODO.md`**: Roadmap for integrating with real data generators
- **`ablation_implementation_status.md`**: Current status of the implementation

### Activity Sources for Ablation Testing

The framework is designed to work with six activity sources:

1. **Activity**: General activity records (`ActivityContext` collection)
2. **Music**: Music listening activity (`MusicActivityContext` collection)
3. **Location**: Geolocation and spatial activity (`GeoActivityContext` collection)
4. **Environmental**: Temperature and environmental data (`TempActivityContext` collection)
5. **Semantic**: Content-based metadata (`SemanticData` collection)
6. **Query History**: Previous search activities (`QueryHistory` collection)

These are organized into experimental (4) and control (2) groups for each test cluster.

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
- **Database Reset**: Use `python -m db/db_config reset` to completely reset the database
- **Large Result Sets**: Either paginate results or use sampling for very large collections

### Ablation Testing Framework Design

The framework follows this design:

1. **Cluster-Based Testing**:
   - Create balanced clusters with 4 experimental and 2 control sources
   - Each cluster provides a different mix of sources for robust testing
   - Uses randomization with fixed seed for reproducibility

2. **Query Generation**:
   - Creates natural language queries targeting specific activity types
   - Balances queries between experimental and control metadata categories
   - Supports both template-based and LLM-based generation

3. **Truth Data Management**:
   - SQLite database tracks all studies, clusters, queries, and results
   - Records detailed metrics for all ablation scenarios
   - Generates comprehensive reports with statistical analysis

4. **Metrics Calculation**:
   - **Precision**: Measure of result accuracy (true positives / all returned)
   - **Recall**: Measure of result completeness (true positives / all relevant)
   - **F1 Score**: Harmonic mean of precision and recall
   - **Impact**: Measure of performance degradation when collection is ablated (1.0 - F1)

5. **Test Execution**:
   - Reset database between test runs
   - Generate synthetic test data targeting specific queries
   - Run baseline query with no ablation
   - Run tests with individual sources ablated
   - Run tests with all experimental/control sources ablated
   - Compare results and calculate metrics

### Integration with Data Generators

The framework is designed to work with the existing data generator classes:

- `StorageMetadataGeneratorImpl` in `tools/data_generator_enhanced/generators/storage.py`
- `ActivityMetadataGeneratorImpl` in `tools/data_generator_enhanced/generators/activity.py`
- `SemanticMetadataGeneratorImpl` in `tools/data_generator_enhanced/generators/semantic.py`

Integration tasks are outlined in `ABLATION_INTEGRATION_TODO.md`.

### Performance Considerations:

- ActivityContext collection contains over 1 million documents
- Queries without LIMIT statements can take 15+ seconds for full scans
- Use increased LIMIT values rather than removing LIMIT completely
- Consider implementing sampling for large collections
- For large test sets, use batch processing for data generation and upload

The framework targets the full protocol in `doc/AblationDesign.md`:
- 100 natural language queries (50 ablation, 50 control)
- Synthetic metadata generation (5 matching + 45 non-matching per query)
- Comprehensive metrics reports

### Metadata Categories

Metadata in Indaleko is organized into the following categories for ablation testing:

1. **Temporal**: created_at, modified_at, session_duration
2. **Activity**: action, collaborator
3. **Spatial**: geolocation, device_location
4. **Content**: file_type, keywords, tags
5. **Ambient**: music, temperature, environmental
6. **Social**: sharing, collaboration, communication

Each category can be ablated independently to measure its impact on query results.

### Implementation Principles for Ablation Testing

1. **Database Integrity**:
   - Reset database before each test run with `python -m db/db_config reset`
   - Use actual database connections, not mocks
   - Test against real ArangoDB schema constraints
   - Handle large collections appropriately with sampling or pagination

2. **Clean Test Data**:
   - Generate synthetic data that targets specific metadata categories
   - Create controlled matching and non-matching entries
   - Ensure data is attributable to specific categories being tested

3. **Accurate Metrics**:
   - Use fixed query execution that handles LIMIT statements properly
   - Calculate precision, recall, and F1 scores for each ablation scenario
   - Record execution times to identify performance impacts
   - Document AQL transformations for query analysis

4. **Reproducible Results**:
   - Use fixed random seeds for reproducibility
   - Document full test methodology and data generation
   - Include comprehensive reports with ablation metrics
   - Properly restore all collections after testing

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

### Schema and Data Consistency

To maintain schema consistency:

1. **Record.Attributes vs Record.Attribute**: Always use `Record.Attributes` (plural) for ArangoDB access patterns
2. **Collection Names**: Use proper names like `Objects`, `Activities`, and `SemanticData`
3. **Timezone-Aware Dates**: Always use timezone-aware datetime objects for ArangoDB

The prompt management system helps detect and fix these inconsistencies automatically.

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
- **Types**: Use type hints for all functions and variables (Python 3.12+ features encouraged)
- **Formatting**: 4 spaces, ~100 char line length
- **Naming**: CamelCase (classes), snake_case (functions/vars), UPPER_CASE (constants)
- **Interfaces**: Prefix with 'I' (IObject, IRelationship)
- **Documentation**: Docstrings with Args/Returns sections
- **Modern Python**: Use match/case and other Python 3.12+ features where appropriate

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
- Lint code: `flake8` or `ruff`

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

### Ablation Framework
- Run mock demo: `python tools/data_generator_enhanced/testing/mock_generator_demo.py`
- Run integration test: `python run_ablation_integration_test.py --dataset-size 100 --num-queries 10`
- Run with shell script: `./run_ablation_test.sh` (Linux/macOS) or `run_ablation_test.bat` (Windows)
- View implementation status: `ablation_implementation_status.md`
- Integration TODO list: `ABLATION_INTEGRATION_TODO.md`

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

### ArangoDB Cursor Handling
ArangoDB cursors should be handled carefully, especially with large result sets:

```python
# For small result sets, fully consume the cursor
if isinstance(results, Cursor):
    result_list = [doc for doc in results]  # Convert cursor to list
    result_data["results"] = result_list
else:
    result_data["results"] = results
```

For large collections (like ActivityContext with 1M+ documents):
```python
# Process cursor in batches with a batch_size parameter
cursor = db.aql.execute(query, bind_vars=params, batch_size=1000)

# Option 1: Cap maximum results to avoid memory issues
results = []
max_results = 10000
for doc in cursor:
    results.append(doc)
    if len(results) >= max_results:
        logging.info(f"Reached maximum result count of {max_results}")
        break

# Option 2: Process results in batches without storing everything
processed = 0
for doc in cursor:
    process_document(doc)  # Process each document individually
    processed += 1
    if processed % 10000 == 0:
        logging.info(f"Processed {processed} documents...")
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

When performing lookups for ablation testing:
```python
# For ablation tests, remember we're replacing small LIMIT values with larger ones
# This means single entity lookups should still use LIMIT 1
# But aggregation queries should use larger values or sampling

# When testing, log AQL transformations
logging.info(f"Original query: {aql_query}")
transformed_query = re.sub(r'LIMIT\s+\d+', increase_limit_function, aql_query)
logging.info(f"Transformed query: {transformed_query}")
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