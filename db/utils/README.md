# Database Utilities for Indaleko

This directory contains utility functions to enhance database operations in the Indaleko project.

## Query Performance Monitoring

The `query_performance.py` module provides tools for monitoring ArangoDB query performance. It includes:

### `timed_aql_execute` Function

A wrapper function for ArangoDB's AQL execute method that:

- Times query execution
- Logs slow queries (exceeding a configurable threshold)
- Captures EXPLAIN data for slow queries
- Redacts sensitive data in bind variables
- Provides warnings for queries not using indexes

#### Usage

```python
from db import timed_aql_execute

# Basic usage (logs queries taking more than 5 seconds)
cursor = timed_aql_execute(
    db,
    "FOR doc IN @@collection FILTER doc.LocalIdentifier == @frn RETURN doc",
    bind_vars={"@collection": "Objects", "frn": "12345"}
)

# Custom threshold and other options
cursor = timed_aql_execute(
    db,
    "FOR doc IN @@collection FILTER doc.LocalIdentifier == @frn RETURN doc",
    bind_vars={"@collection": "Objects", "frn": "12345"},
    threshold=0.5,           # 500ms threshold
    capture_explain=True,    # Capture EXPLAIN data (default)
    log_level=logging.INFO   # Use INFO level instead of WARNING
)
```

### Retrofitting Existing Code

To retrofit existing code that uses direct AQL execute calls:

1. Import the function:
   ```python
   from db import timed_aql_execute
   ```

2. Replace direct execute calls:
   ```python
   # Before:
   cursor = db._arangodb.aql.execute(
       query,
       bind_vars=bind_vars
   )

   # After:
   cursor = timed_aql_execute(
       db,
       query,
       bind_vars=bind_vars,
       threshold=0.5  # Optional custom threshold
   )
   ```

3. Optional: Add custom threshold or log level for specific queries:
   ```python
   # For potentially slow operations, use a higher threshold
   cursor = timed_aql_execute(
       db,
       complex_query,
       bind_vars=complex_bind_vars,
       threshold=10.0  # 10 second threshold for complex operations
   )

   # For critical paths, use INFO level to always log
   cursor = timed_aql_execute(
       db,
       critical_query,
       bind_vars=critical_bind_vars,
       log_level=logging.INFO  # Always log this query
   )
   ```

## Example Implementation

See `db/test_query_performance.py` for a full test implementation.

For a concrete example of retrofitting existing entity lookup code, see:
`activity/recorders/storage/ntfs/tiered/hot/entity_query_example.py`
