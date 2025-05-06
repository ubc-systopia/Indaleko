# Schema Validation in Indaleko's ArangoDB Collections

When working with the Indaleko database, particularly when inserting relationship records, careful attention must be paid to schema requirements. This document outlines the key schema validation issues discovered during implementation of the relationship generator.

## Common Schema Validation Issues

### 1. Edge Collection Requirements

When working with ArangoDB edge collections (like the Relationships collection):

- Records must have `_from` and `_to` fields pointing to valid vertices in the format `collection/key`
- The edge collection must be created with `edge=True` parameter
- Both vertices referenced by `_from` and `_to` must exist in the database

### 2. Relationship Data Model Requirements

The `IndalekoRelationshipDataModel` has specific field requirements:

- `Objects` must be a **tuple** of two strings (not a list), representing UUIDs
- `Record` must be an `IndalekoRecordDataModel` with proper timestamps
- `Relationships` must be a list of `IndalekoSemanticAttributeDataModel` records
- All timestamp fields must include timezone information

### 3. Timestamp Format Issues

ArangoDB is strict about date/time formats:

- All timestamps must include timezone information (prefer UTC)
- Use `datetime.now(timezone.utc).timestamp()` for consistent timestamp format

### 4. UUID Handling

When working with UUIDs:

- Always convert UUIDs to strings before inserting into the database
- UUIDs should be in canonical format (e.g., `"12345678-1234-5678-1234-567812345678"`)
- Ensure all required UUID fields have valid values

## Correct Relationship Record Structure

Here's an example of a correctly structured relationship record:

```python
{
    "_key": "uniquekey123456",  # Generated with hashlib.md5 for uniqueness
    "_from": "Objects/object1key",  # Collection/key format
    "_to": "Objects/object2key",  # Collection/key format
    "Record": {
        "RecordUUID": "12345678-1234-5678-1234-567812345678",
        "SourceIdentifier": {
            "SourceIdentifierUUID": "12345678-1234-5678-1234-567812345678",
            "Source": "IndalekoDG",
            "Timestamp": 1712345678.123  # UTC timestamp with seconds
        },
        "Timestamp": 1712345678.123  # UTC timestamp with seconds
    },
    "Objects": (
        "12345678-1234-5678-1234-567812345678",  # Object1 UUID as string
        "87654321-4321-8765-4321-876543210987"   # Object2 UUID as string
    ),
    "Relationships": [
        {
            "SemanticAttributeUUID": "12345678-1234-5678-1234-567812345678",
            "Name": "contains",
            "AttributeType": "relationship",
            "Value": True,
            "Timestamp": 1712345678.123  # UTC timestamp with seconds
        }
    ]
}
```

## Helper Method Approach

The most reliable way to create relationship records is to use the `IndalekoRelationship` class and associated helper methods:

```python
from storage.i_relationship import IndalekoRelationship

# Create using the helper method approach
relationship = IndalekoRelationship(
    objects=(object1_uuid, object2_uuid),
    relationships=[semantic_attribute.dict()],
    source_id=source_identifier.dict()
)

# Convert to dictionary and add edge collection fields
relationship_dict = relationship.dict()
relationship_dict["_key"] = relationship_key
relationship_dict["_from"] = from_id
relationship_dict["_to"] = to_id
```

## References

- For relationship structure, see `data_models/relationship.py`
- For helper methods, see `storage/recorders/base.py`
- For edge collection creation, see `db/db_collections.py`
