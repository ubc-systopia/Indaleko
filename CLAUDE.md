# CLAUDE.md - Indaleko Development Guidelines

## CRITICAL: FAIL-STOP IS THE PRIMARY DESIGN PRINCIPLE

Indaleko follows a strict FAIL-STOP model as its primary design principle:

1. NEVER implement fallbacks or paper over errors
2. ALWAYS fail immediately and visibly when issues occur
3. NEVER substitute mock/fake data when real data is unavailable
4. ALWAYS exit with a clear error message (sys.exit(1)) rather than continuing with degraded functionality

This is ESPECIALLY important for scientific experiments like the ablation framework, where data integrity is critical. Silently substituting template-based data when LLM generation fails would invalidate experimental results and is strictly prohibited.

Remember: It is better to fail loudly and immediately than to continue with compromised functionality.

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

We are implementing and refining our comprehensive ablation study framework for scientifically measuring how different activity data types affect query precision and recall. This framework provides controlled testing across all six activity data categories to produce publication-quality research results.

### Ablation Framework Implementation Status

- ✅ Completed BaseActivityRecorder for standardized database interactions
- ✅ Implemented all three activity type collectors and recorders with proper inheritance
- ✅ Enhanced AblationTester with proper truth data validation
- ✅ Added semantic search queries instead of direct key lookups
- ✅ Integrated LLM-driven query generator for realistic user queries
- ✅ Fixed validation timing issues in test workflow
- ✅ Implemented proper fail-stop behavior with immediate feedback
- ✅ Added diverse query templates as fallback
- ✅ Fixed Pydantic V2 compatibility issues
- 🔄 Adding integration with experimental LLM query generator from scratch/
- 🔄 Implementing more activity types (Collaboration, Storage, Media)

### Activity Data Types Being Studied

The ablation study focuses on these six activity data types:

1. **Music Activity** - Music listening patterns from streaming services
2. **Location Activity** - Geographic position data from various sources
3. **Task Activity** - User task management and completion
4. **Collaboration Activity** - Calendar events and file sharing
5. **Storage Activity** - File system operations and access patterns
6. **Media Activity** - Video/content consumption activities

### Improved Error Handling Model

Indaleko uses a strict fail-stop model for error handling:

```python
# CORRECT: Use sys.exit(1) for immediate termination
def validate_critical_data(data):
    """Validate critical data integrity."""
    if not data:
        logging.error("CRITICAL: Missing required data")
        sys.exit(1)  # Immediate termination

    if not all(required_fields.issubset(item.keys()) for item in data):
        logging.error("CRITICAL: Data missing required fields")
        sys.exit(1)  # Immediate termination

    return True

# INCORRECT: Never continue after validation failure
def bad_validation(data):
    """BAD validation function that continues after critical error."""
    valid = True
    if not data:
        logging.error("Data is empty")  # Logs but continues!
        valid = False

    return valid  # Will allow potentially corrupted execution to continue
```

### LLM Query Generation

We've implemented two approaches for query generation:

1. **Direct Integration** - Using LLMQueryGenerator from the research framework
2. **Experimental Integration** - Using EnhancedQueryGenerator from scratch/ experiments

Both implementations ensure:
- High query diversity (different structures, lengths, entities)
- Realistic user patterns (questions, commands, keywords)
- Activity-specific semantics (location, task, music terminology)
- Improved search evaluation through realistic scenarios

### Semantic Search Implementation

Recent improvements to our search implementation:

```python
# OLD: Direct ID lookup - doesn't test search capabilities
def bad_search(query_id, collection):
    """Direct key lookup doesn't test search."""
    truth_data = get_truth_data(query_id, collection)
    aql = f"""
    FOR doc IN {collection}
    FILTER doc._key IN @entity_ids
    RETURN doc
    """
    return db.aql.execute(aql, bind_vars={"entity_ids": truth_data})

# NEW: Semantic attribute search - properly tests search
def better_search(query_text, collection):
    """Attribute-based search tests real capabilities."""
    if "MusicActivity" in collection:
        aql = f"""
        FOR doc IN {collection}
        FILTER doc.artist == @artist OR doc.track == @track
        LIMIT 10
        RETURN doc
        """
        return db.aql.execute(aql, {"artist": "Taylor Swift", "track": "Blank Space"})
    elif "LocationActivity" in collection:
        # Location-specific search...
```

### AblationTester Architecture

The AblationTester now follows this improved workflow:

1. **Setup** - Connect to database and prepare collections
2. **Generate Data** - Create synthetic activity data across multiple types
3. **Generate Queries** - Use LLM/templates to create diverse test queries
4. **Create Truth Data** - Record which entities should match which queries
5. **Validate** - Verify truth data integrity AFTER creation
6. **Execute Tests** - For each collection, measure baseline then ablate
7. **Calculate Metrics** - Measure precision, recall, F1 for each condition
8. **Generate Reports** - Create visualizations and markdown summaries
9. **Cleanup** - Restore all collections to their original state

### Key Improvements

- **Proper Collection Order** - Validation now runs after truth data creation
- **Real Search Tests** - Uses semantic search not ID lookups
- **Query Diversity** - Each query uses different template, parameters, or LLM generation
- **Improved Error Detection** - Fail-stop with clear error messages
- **Truth Data Integrity** - Uses actual database keys for expected matches

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

### Data Models and Pydantic Handling

Always extend IndalekoBaseModel for database models:
```python
from data_models.base import IndalekoBaseModel

class MyArangoModel(IndalekoBaseModel):
    name: str
    value: int
```

#### Pydantic V2 Best Practices

Indaleko uses Pydantic V2 for data validation and serialization. Follow these practices:

1. **Never use the deprecated .dict() method**
```python
# INCORRECT - Deprecated in Pydantic V2, will be removed in V3
serialized_data = pydantic_object.dict()  # Will generate warnings

# CORRECT - Use model_dump() for dict conversion
serialized_data = pydantic_object.model_dump()

# CORRECT - For JSON serialization in one step
json_string = pydantic_object.model_dump_json()

# CORRECT - If you need a dictionary from JSON string
doc = json.loads(pydantic_object.model_dump_json())
```

2. **Use model_config instead of Config class**
```python
# INCORRECT - Old style Config class
class OldModel(BaseModel):
    name: str

    class Config:
        arbitrary_types_allowed = True

# CORRECT - New style model_config
class NewModel(BaseModel):
    name: str

    model_config = {"arbitrary_types_allowed": True}
```

3. **Prefer Field over field for defaults**
```python
from pydantic import BaseModel, Field

class UserModel(BaseModel):
    # Use Field with proper type annotation
    name: str = Field(default="Anonymous")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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

### Error Handling and Fail-Stop Approach

Indaleko uses a strict fail-stop approach for critical errors:

```python
import sys

# CRITICAL ERRORS: Use sys.exit(1) for immediate termination
def critical_operation():
    """Operation that must succeed or the program cannot continue."""
    try:
        result = risky_but_essential_operation()
        if not result:
            logger.error("CRITICAL: Essential operation failed")
            sys.exit(1)  # Exit immediately with error status
        return result
    except Exception as e:
        logger.error(f"CRITICAL: Fatal error in essential operation: {e}")
        sys.exit(1)  # Exit immediately with error status

# NON-CRITICAL ERRORS: Use exceptions for recoverable issues
try:
    result = risky_operation()
except (ValueError, KeyError) as e:
    logger.error(f"Failed to process data: {e}")
    raise IndalekoProcessingError(f"Data processing failed: {str(e)}") from e
```

#### When to Use Fail-Stop
- For validation errors that would lead to corrupted data
- For essential infrastructure components (database connection, file system)
- When continuing would produce meaningless or incorrect results
- When the same error will occur repeatedly in a loop

#### When Not to Use Fail-Stop
- For recoverable errors where alternate flows exist
- For expected error conditions that can be handled
- In library code called by other components
- During data import where partial success is acceptable

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

## Experimental Code

Indaleko uses the `scratch/` directory for experimental code and prototypes. This provides a safe space to try new approaches without affecting the main codebase.

### Using the Scratch Directory

1. **Purpose**: Use `scratch/` for rapid prototyping and experimentation
2. **Integration**: Move stable code from `scratch/` to main codebase when ready
3. **Independence**: Design experiments to run standalone first

```python
# Good pattern for experimental code
if __name__ == "__main__":
    # Setup standalone test environment
    setup_test_data()

    # Run the experiment
    result = experimental_function()

    # Report results
    print(f"Experiment results: {result}")
```

### Current Experimental Projects

1. **LLM Query Generation** (`scratch/llm_query_generation/`)
   - Enhanced query diversity experiments
   - Direct LLM connectors without full infrastructure
   - Jaro-Winkler analysis for query diversity
   - Semantic matching algorithms

2. **Query Matching Results** (`scratch/query_matching_results/`)
   - Experimental matching algorithms
   - Performance testing for different query strategies
   - Analysis of query precision/recall with minimal infrastructure

3. **Adapting Experimental Code**
   - Get experimental code working in isolation first
   - Use imports/try-except to integrate with main code
   - Clearly comment experimental status
