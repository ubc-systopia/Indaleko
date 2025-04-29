# ArangoSearch Views in Indaleko

This document describes the implementation and usage of ArangoSearch views in Indaleko for efficient text search capabilities.

## Overview

ArangoSearch is a full-text search engine built into ArangoDB. It provides better search capabilities than regular AQL filtering, including:

- Tokenization and stemming of text
- Language-specific analyzers
- Relevance ranking
- Primary sort ordering
- Stored values for performance
- Advanced text search capabilities (phrase, proximity, fuzzy)

The Indaleko integration of ArangoSearch maintains this functionality alongside our existing collection and index system, allowing for seamless upgrades to search performance.

## Implementation

### Architecture

The implementation follows the same pattern as our index system:

1. **Collection Definition**: Views are defined in `db/db_collections.py` alongside the collections they index
2. **View Models**: We created `data_models/db_view.py` with `IndalekoViewDefinition` model
3. **View Management**: A dedicated `IndalekoCollectionView` class in `db/collection_view.py` handles view operations
4. **Automatic Creation**: The `IndalekoCollections` class now creates views automatically during database setup

This approach maintains the clarity of our collection and index relationship while handling views separately where needed.

### View Definition Format

In `db/db_collections.py`, views are defined as part of collection definitions:

```python
Indaleko_Object_Collection: {
    "internal": False,
    "schema": IndalekoObjectDataModel.get_arangodb_schema(),
    "edge": False,
    "indices": {
        "URI": {"fields": ["URI"], "unique": True, "type": "persistent"},
        # ... other indices ...
    },
    "views": [
        {
            "name": Indaleko_Objects_Text_View,
            "fields": ["Label", "Record.Attributes.URI", "Record.Attributes.Description"],
            "analyzers": ["text_en"],
            "stored_values": ["_key", "Label"]
        }
    ]
}
```

Each view definition specifies:
- `name`: Name of the view
- `fields`: List of fields to index for text search
- `analyzers`: List of analyzers to use (default: `"text_en"`)
- `stored_values`: Fields to store in the view for faster retrieval

### View Creation Process

1. When `IndalekoCollections` initializes:
   - Collections are created as before
   - `_create_views()` is called to process view definitions
   - For each collection with views, `IndalekoViewDefinition` objects are created
   - Views are created or updated via `IndalekoCollectionView`

2. The `IndalekoCollectionView` class:
   - Handles view creation, update, and deletion operations
   - Maintains a cache of existing views
   - Includes methods to query view metadata
   - Follows the same API patterns as our other database interfaces

## View Usage

### In AQL Queries

ArangoSearch views are referenced in AQL using the `SEARCH` operation:

```aql
FOR doc IN ObjectsTextView
SEARCH ANALYZER(
    LIKE(doc.Label, @query) OR
    LIKE(doc.Record.Attributes.URI, @query),
    "text_en"
)
SORT BM25(doc) DESC
LIMIT 50
RETURN doc
```

This is more efficient and flexible than the traditional filter approach:

```aql
FOR obj IN Objects
FILTER obj.Label != null AND LIKE(obj.Label, CONCAT('%', @query, '%'), true)
LIMIT 50
RETURN obj
```

### In the Streamlit GUI

The search functionality in the Streamlit GUI has been updated to use ArangoSearch views when available, with automatic fallback to regular queries if views don't exist.

This approach provides:
- Better search accuracy through proper text analysis
- Improved performance with stored values
- Ranked results based on relevance
- No modification to query tools needed (transparent upgrade)

## Testing Views

A test script `db/test_views.py` provides functionality to:
- List existing views
- Create test views
- Delete test views
- Ensure defined views exist
- Execute test queries using views

Usage examples:

```bash
# List all views
python -m db.test_views --list

# Create all defined views
python -m db.test_views --ensure

# Test search query
python -m db.test_views --query "indaleko project"
```

## Performance Considerations

ArangoSearch views provide substantial performance benefits, particularly for:

1. **Text-heavy search queries** - Fields like descriptions, labels, and notes
2. **Partial matching** - Finding parts of words using stemming
3. **Relevance ranking** - Sorting by similarity to the query
4. **Multi-field searches** - Searching across multiple text fields at once

The trade-offs to consider:
- **Storage space** - Views consume additional disk space
- **Index maintenance** - Modest overhead during write operations
- **Memory usage** - Views consume RAM for efficient operation

## Future Extensions

Potential enhancements to the view implementation:

1. **Multiple analyzers** - Using language-specific and specialized analyzers
2. **Faceted search** - Leveraging views for faceted navigation
3. **Synonyms and thesaurus** - Adding synonyms to improve search quality
4. **Cross-collection search** - Creating views that span multiple collections
5. **Performance tuning** - Optimizing stored values and primary sort

## Conclusion

ArangoSearch views provide a significant upgrade to Indaleko's search capabilities with minimal changes to the existing architecture. The integration respects the existing collection/index pattern while adding powerful text search capabilities.

These views are particularly valuable for natural language search of file metadata, activity descriptions, and named entities, enhancing the core Indaleko value proposition of unified personal indexing.
