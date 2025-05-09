# AQL Cross-Collection Query Enhancement

This document describes how to enhance the AQL translator to support queries that span multiple collections using the cross-collection references implemented with the `SharedEntityRegistry` and `EnhancedActivityRecorder`.

## Current Implementation

The current AQL translator is designed to work with single-collection queries:

```python
def translate_to_aql(self, query_text, collection, activity_type=None):
    """Translate a natural language query to AQL.
    
    Args:
        query_text: The natural language query text
        collection: The collection to search in
        activity_type: Optional activity type for specialized translation
        
    Returns:
        Tuple[str, Dict]: The AQL query string and bind variables
    """
    # Single collection query implementation...
    aql = f"""
    FOR doc IN {collection}
    FILTER doc.attribute LIKE @search_term
    RETURN doc
    """
    return aql, {"search_term": search_term}
```

## Cross-Collection Enhancement

The enhanced AQL translator should support queries that span multiple collections with explicit relationships. Here's how to implement it:

```python
def translate_to_aql(self, query_text, collection, activity_types=None, relationship_type=None):
    """Translate a natural language query to AQL.
    
    Args:
        query_text: The natural language query text
        collection: The primary collection to search in
        activity_types: Optional list of activity types for cross-collection queries
        relationship_type: Optional relationship type between collections
        
    Returns:
        Tuple[str, Dict]: The AQL query string and bind variables
    """
    # Check if we need a cross-collection query
    if activity_types and len(activity_types) > 1 and relationship_type:
        return self._translate_cross_collection_query(
            query_text, collection, activity_types, relationship_type
        )
    else:
        # Existing single-collection logic...
        pass
```

### Cross-Collection Translation Logic

The actual cross-collection translation method needs to:

1. Determine the primary and secondary collections
2. Build an AQL query that JOINs across collections using the references field
3. Add filters based on the query entities and relationship type

```python
def _translate_cross_collection_query(self, query_text, primary_collection, activity_types, relationship_type):
    """Translate a cross-collection query to AQL.
    
    Args:
        query_text: The natural language query text
        primary_collection: The primary collection to search in
        activity_types: List of activity types for cross-collection query
        relationship_type: Relationship type between collections
        
    Returns:
        Tuple[str, Dict]: The AQL query string and bind variables
    """
    # Determine collections
    collections = [f"ablation_{a_type.name.lower()}" for a_type in activity_types]
    primary_collection = collections[0]
    secondary_collection = collections[1]
    
    # Extract entities from query text
    # (Using simplified entity extraction for illustration)
    entities = self._extract_entities(query_text)
    
    # Build the cross-collection AQL query
    aql = f"""
    FOR doc IN {primary_collection}
    FILTER doc.references != null AND doc.references.{relationship_type} != null
    FOR related IN {secondary_collection}
    FILTER related._id IN doc.references.{relationship_type}
    """
    
    # Add filters based on extracted entities
    if entities:
        entity_conditions = []
        for entity in entities:
            entity_conditions.append(f"doc.name LIKE @entity_{len(entity_conditions)}")
            entity_conditions.append(f"related.name LIKE @entity_{len(entity_conditions)}")
        
        if entity_conditions:
            aql += f"\nFILTER " + " OR ".join(entity_conditions)
    
    # Add return statement
    aql += "\nRETURN doc"
    
    # Create bind variables
    bind_vars = {}
    for i, entity in enumerate(entities):
        bind_vars[f"entity_{i}"] = f"%{entity}%"
    
    return aql, bind_vars
```

## Multi-Hop Relationship Queries

For more complex queries that traverse multiple collections (e.g., "tasks discussed in meetings at specific locations"), we need to support multi-hop relationship traversal:

```python
def translate_multi_hop_query(self, query_text, primary_collection, relationship_paths):
    """Translate a query with multi-hop relationships.
    
    Args:
        query_text: The natural language query text
        primary_collection: The primary collection to start from
        relationship_paths: List of (source, relationship, target) tuples
            defining the relationship path to traverse
        
    Returns:
        Tuple[str, Dict]: The AQL query string and bind variables
    """
    # Start with the primary collection
    aql = f"FOR doc IN {primary_collection}\n"
    
    # Add relationship traversals
    for i, (source, relationship, target) in enumerate(relationship_paths):
        join_var = f"related{i+1}"
        aql += f"  FOR {join_var} IN {target}\n"
        
        # Determine the direction of the relationship
        if source == primary_collection:
            # Direct relationship from doc to related
            aql += f"    FILTER {join_var}._id IN doc.references.{relationship}\n"
        else:
            # Relationship from previous related to next related
            prev_var = f"related{i}"
            aql += f"    FILTER {join_var}._id IN {prev_var}.references.{relationship}\n"
    
    # Extract entities from query text
    entities = self._extract_entities(query_text)
    
    # Add filters based on extracted entities
    if entities:
        entity_conditions = []
        # Add conditions for each extracted entity
        # ...
        
        if entity_conditions:
            aql += f"  FILTER " + " OR ".join(entity_conditions) + "\n"
    
    # Return the documents
    aql += "  RETURN doc"
    
    # Create bind variables
    bind_vars = {}
    # ...
    
    return aql, bind_vars
```

## Implementation Plan

1. Extend the `AQLQueryTranslator` class with the new methods
2. Add support for cross-collection query detection
3. Implement the `_translate_cross_collection_query` method
4. Implement entity extraction and relevance scoring
5. Add support for multi-hop relationship queries
6. Test with different cross-collection scenarios

## AQL Query Examples

### Task + Meeting Relationship

```aql
FOR task IN ablation_task
  FILTER task.references != null AND task.references.created_in != null
  FOR meeting IN ablation_collaboration
    FILTER meeting._id IN task.references.created_in
    FILTER task.name LIKE "%project report%" OR meeting.title LIKE "%quarterly planning%"
    RETURN task
```

### Meeting + Location Relationship

```aql
FOR meeting IN ablation_collaboration
  FILTER meeting.references != null AND meeting.references.located_at != null
  FOR location IN ablation_location
    FILTER location._id IN meeting.references.located_at
    FILTER location.name LIKE "%downtown office%"
    RETURN meeting
```

### Task + Meeting + Location (Multi-hop)

```aql
FOR task IN ablation_task
  FILTER task.references != null AND task.references.discussed_in != null
  FOR meeting IN ablation_collaboration
    FILTER meeting._id IN task.references.discussed_in
    FILTER meeting.references != null AND meeting.references.located_at != null
    FOR location IN ablation_location
      FILTER location._id IN meeting.references.located_at
      FILTER location.name LIKE "%coffee shop%"
      RETURN task
```

## Testing Strategy

1. Unit tests for each method in the enhanced translator
2. Integration tests with real cross-collection queries
3. Performance testing with large datasets
4. Validation against expected results
5. Integration with the ablation testing framework

## Future Enhancements

1. Support for more complex relationship patterns
2. Optimization for query performance
3. Dynamic relationship discovery based on query content
4. Support for query explanation and visualization