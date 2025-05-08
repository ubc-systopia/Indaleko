# CLAUDE.md - Indaleko Development Guidelines

## Available Tools

### MCP ArangoDB Access
Direct database access is available through MCP tools:
- `mcp__arango-mcp__arango_query` - Execute AQL queries directly against the database
- `mcp__arango-mcp__arango_insert` - Insert documents into collections
- `mcp__arango-mcp__arango_update` - Update existing documents
- `mcp__arango-mcp__arango_remove` - Remove documents from collections
- `mcp__arango-mcp__arango_backup` - Create backups of collections
- `mcp__arango-mcp__arango_list_collections` - List all collections in the database
- `mcp__arango-mcp__arango_create_collection` - Create new collections

Use these tools to verify database state, diagnose issues, and confirm that code problems aren't actually database connectivity issues. Following the fail-stop model for database operations, any genuine database connectivity issue requires immediate attention.

## Current Work: Comprehensive Ablation Study Framework

We are designing and implementing a complete ablation study framework for scientifically measuring how different activity data types affect query precision and recall. This framework provides controlled testing across all six activity data categories to produce publication-quality research results.

### Ablation Study Design Progress

Our detailed design document (`research/DESIGN 2025-05-07.md`) outlines a comprehensive approach that:

1. **Systematically measures** the impact of each activity data type on search effectiveness
2. **Generates synthetic data** for controlled experiments across all six activity types
3. **Uses LLM-driven query generation** to create realistic search scenarios
4. **Produces accurate metrics** for statistical analysis of search effectiveness
5. **Follows Indaleko's architectural patterns** for proper database integration

### Activity Data Types Being Studied

The ablation study focuses on these six activity data types:

1. **Music Activity** - Music listening patterns from streaming services
2. **Location Activity** - Geographic position data from various sources
3. **Task Activity** - User task management and completion
4. **Collaboration Activity** - Calendar events and file sharing
5. **Storage Activity** - File system operations and access patterns
6. **Media Activity** - Video/content consumption activities

### Current Implementation Status

- ✅ Created comprehensive synthetic data collector designs for all activity types
- ✅ Developed recorder interfaces following proper database integration patterns
- ✅ Designed Named Entity Recognition component for consistent entity representation
- ✅ Implemented query generation mechanism using existing LLM infrastructure
- ✅ Created truth data tracking system for accuracy measurements
- ✅ Designed collection integration with proper collection naming in `IndalekoDBCollections`
- ✅ Implemented query-truth integration with expected match generation
- ✅ Integrated PromptManager for cognitive protection in query generation
- ✅ Designed depth-first implementation approach starting with Location activity
- ✅ Implemented LocationActivityCollector with data generation capabilities
- ✅ Implemented LocationActivityRecorder with database integration
- ✅ Created unit and integration tests for Location activity components
- ✅ Developed demo script showing end-to-end Location activity workflow
- ✅ Implemented TaskActivityCollector with application-aware data generation
- ✅ Implemented TaskActivityRecorder with database integration
- ✅ Created comprehensive tests for Task activity components
- ✅ Developed end-to-end demo for Task activity workflow
- ✅ Implemented AblationTester with collection ablation mechanism
- ✅ Created metrics calculation for precision, recall, and F1 score
- ✅ Developed AblationTestRunner for experiment coordination
- ✅ Added reporting and visualization capabilities
- ✅ Created an end-to-end ablation demo script
- 🔄 Working on Collaboration Activity implementation (next activity type)
- 🔄 Preparing to implement the remaining activity types

### Key Framework Components

- **Synthetic Data Generators** - Each activity type has a dedicated collector and recorder
- **Query Generation System** - Uses LLM to create realistic search queries
- **NER Component** - Manages named entities like "home" and "work" for consistency
- **Truth Data Tracker** - Records which files should match each query
- **Ablation Testing Framework** - Measures precision, recall and F1 score impacts
- **ArangoDB Integration** - Proper collection management and database access patterns

### Database Access Patterns for Ablation

All database operations follow Indaleko's established patterns:

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

### Synthetic Data Generation Flow

The synthetic data generation follows these steps:

1. Generate natural language queries targeting specific activity types
2. Extract file references, named entities, and activity references
3. Create matching metadata based on query components
4. Create non-matching metadata (temporally distant or semantically different)
5. Record both matching and non-matching data in the database
6. Track "ground truth" about which files should match which queries

### Collector/Recorder Pattern Implementation

Following Indaleko's architectural principles, our design separates:

- **Collectors** - Generate raw synthetic data but never interact with the database
- **Recorders** - Process collector data and handle database interactions
- **Controller** - Coordinates the collector-recorder workflow maintaining separation of concerns

Our implementation uses a direct integration approach for synthetic data where:
- Collectors generate data in-memory
- Controller passes data directly to recorders
- Recorders handle database insertion
- Errors are handled with a fail-fast approach for immediate debugging

### Metrics Collection and Analysis

For each activity type, the framework will measure:

- **Precision** - How many returned results are relevant
- **Recall** - How many relevant items are found
- **F1 Score** - Harmonic mean of precision and recall
- **Impact** - Performance degradation when the activity collection is ablated
- **Relative Contribution** - Comparative importance of each activity type

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

## Best Practices

### Code Verification and Testing

**CRITICAL: Always test your code before committing**

1. **Verify All Implementations**: Never claim that code works until you have tested it yourself
   - Run every script you create at least once
   - Test all code paths, not just the happy path
   - Handle potential errors gracefully

2. **Test Complex Systems End-to-End**:
   - For multi-component systems like the ablation framework, test the entire flow
   - Verify data is correctly generated, stored, and retrieved
   - Confirm metrics are calculated correctly
   - Check visualization and reporting functionality

3. **Handle Large Codebase Challenges**:
   - Run focused tests on components you're modifying
   - Use small-scale test cases first before full-scale tests
   - Create dedicated test scripts for complex functionality

```python
# Example test harness pattern
def test_component():
    # Setup test data
    test_data = generate_test_data()
    
    # Run the component under test
    result = component_function(test_data)
    
    # Verify results
    assert result.status == "success"
    assert len(result.items) == len(test_data)
    
    # Log verification
    logger.info(f"Verified component with {len(test_data)} items")
    
    return result

# Always run your tests!
if __name__ == "__main__":
    test_result = test_component()
    print(f"Test {'passed' if test_result else 'failed'}")
```

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
