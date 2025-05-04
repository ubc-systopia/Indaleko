# Semantic Attributes for Data Generation

This document describes the semantic attribute system used in the enhanced data generator.

## Overview

Semantic attributes are a key component of the Indaleko data model, providing consistent and structured metadata for various entities in the system. They consist of:

- An **Identifier** (UUID): A unique identifier that represents the semantic meaning of the attribute
- A **Value**: The actual data associated with the attribute

The system is designed to ensure that semantically equivalent attributes share the same UUID, enabling consistent querying and relationship building across the database.

## SemanticAttributeRegistry

The `SemanticAttributeRegistry` class (in `semantic_attributes.py`) provides a centralized system for managing semantic attributes with the following features:

- **Static UUIDs**: Ensures consistent UUIDs for semantic attributes across runs
- **Domain Organization**: Attributes are organized by domain (storage, activity, semantic, etc.)
- **Attribute Registry**: Maintains a mapping between attribute names and UUIDs
- **Helper Methods**: Provides methods for creating properly formatted attributes

### Key Domains

- `DOMAIN_STORAGE`: Storage-related attributes (file paths, sizes, etc.)
- `DOMAIN_ACTIVITY`: Activity-related attributes (user actions, timestamps, etc.)
- `DOMAIN_SEMANTIC`: Content-related attributes (MIME types, extracted text, etc.)
- `DOMAIN_RELATIONSHIP`: Relationship attributes (relationship types, roles, etc.)
- `DOMAIN_MACHINE`: Machine/device attributes (OS, hostname, etc.)

### Example Usage

```python
from core.semantic_attributes import SemanticAttributeRegistry

# Create a semantic attribute
attribute = SemanticAttributeRegistry.create_attribute(
    SemanticAttributeRegistry.DOMAIN_ACTIVITY,
    "DATA_PATH",
    "/some/file/path"
)

# This will create an IndalekoSemanticAttributeDataModel with:
# - Identifier: "cf3c9dd4-64cc-471e-b15a-174387096c1a" (static UUID for DATA_PATH)
# - Value: "/some/file/path"
```

## Static UUIDs

Using static UUIDs for semantic attributes is crucial for:

1. **Consistent Querying**: Enables reliable queries across different data generation runs
2. **Realistic Benchmarking**: Ensures evaluation results aren't artificially inflated
3. **Compatibility**: Maintains compatibility with the Indaleko data model

We use a predefined set of UUIDs (from `v4-uuid.txt`) to ensure consistency across runs and match the expected format in the Indaleko system.

## Implementation Notes

- All semantic attributes should be created through the `SemanticAttributeRegistry` class
- Direct creation of `IndalekoSemanticAttributeDataModel` instances should be avoided
- New attributes should be registered in the `register_common_attributes()` function
- The field names must be `Identifier` and `Value` (not `AttributeIdentifier`/`AttributeValue`)

## Testing

The `test_semantic_attributes.py` script tests the semantic attribute system to ensure:

1. Correct field names (Identifier/Value)
2. Static UUIDs with consistent mapping
3. Proper integration with the ActivityGeneratorTool

## Relationship to Benchmark Suite

The semantic attribute system is an essential component of the benchmark suite, as it:

1. Provides realistic data for testing precision and recall
2. Ensures consistency across different runs
3. Allows for meaningful cross-domain queries
4. Enables measurement of query performance against real-world attribute patterns

---

Updated on: May 4, 2025
