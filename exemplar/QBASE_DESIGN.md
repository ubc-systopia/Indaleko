# ExemplarQueryBase Design - Embodying Ayni Principles

## Overview

The `ExemplarQueryBase` class in `db/qbase.py` provides a consistent pattern for exemplar queries while respecting their unique aspects. It embodies the Ayni principle by offering real value without forcing artificial constraints.

## Key Design Principles

### 1. **Meaningful Abstraction**
The base class abstracts only what is truly common:
- Path initialization pattern
- Query structure (base, limit, no_limit, count)
- Bind variable management
- Execution and display patterns

### 2. **Flexibility Through Hooks**
Subclasses have control through:
- **Required methods**: `_initialize_query_components()` and `_build_base_bind_variables()`
- **Optional overrides**: `_get_collection()` and `_get_default_limit()`

### 3. **Respect for Variations**
- Q1 uses text search with analyzers
- Q2 uses timestamp filtering with document formats
- Q3 uses entity relationships and complex joins
- The base class accommodates all these patterns naturally

## Common Patterns Identified

### From Analysis of q1.py and q2.py:

1. **Initialization Pattern**
   - Setting up INDALEKO_ROOT
   - Converting limit to int
   - Creating query variants

2. **Query Structure**
   - Base AQL query
   - Version with LIMIT
   - Version without LIMIT
   - COUNT query

3. **Bind Variables**
   - Base variables
   - Variables with limit
   - Variables without limit

4. **Execution Pattern**
   - Creating ExemplarQuery object
   - Using TimedAQLExecute
   - Displaying results consistently

## Implementation Benefits

### 1. **Reduced Duplication**
- 250+ lines of base class eliminates ~50-70 lines per query class
- Standard execution pattern shared across all queries

### 2. **Consistency**
- All queries follow the same structural pattern
- Results displayed uniformly
- Easy to understand new queries

### 3. **Maintainability**
- Changes to execution pattern need only one update
- New features (like caching) can be added centrally
- Bug fixes apply to all queries

### 4. **Extensibility**
- Easy to add new query types
- Can override specific behaviors as needed
- Supports both simple and complex queries

## Usage Examples

### Simple Query (Q1 Refactored)
```python
class ExemplarQuery1(ExemplarQueryBase):
    def _initialize_query_components(self):
        self._query = 'Show me documents with "report" in their titles.'
        self._base_aql = """..."""
        self._named_entities = []
    
    def _build_base_bind_variables(self):
        return {"name": "%report%"}
```

### Complex Query (Q2 Refactored)
```python
class ExemplarQuery2(ExemplarQueryBase):
    def _initialize_query_components(self):
        # Set up document formats, complex AQL, named entities
        
    def _build_base_bind_variables(self):
        # Return multiple bind variables
        
    def _get_collection(self):
        # Override to use different view
        return IndalekoDBCollections.Indaleko_Objects_Timestamp_View
```

## Migration Path

1. Keep existing q*.py files unchanged
2. Create refactored versions as examples
3. Gradually migrate as queries are updated
4. No forced changes - use base class only where it adds value

## Ayni Principle in Action

The base class embodies reciprocity by:
- **Giving**: Common functionality, reduced duplication, consistency
- **Taking**: Only what's necessary (two abstract methods)
- **Respecting**: Each query's unique requirements
- **Adding Value**: Without forcing conformity

This design provides real benefits while maintaining the flexibility needed for diverse query patterns.