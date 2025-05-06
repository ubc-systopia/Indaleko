# Database Integration Test for Semantic Attributes

This document explains the database integration test for semantic attributes in the Indaleko data generator.

## Overview

The integration test validates the complete flow:

1. Generate test data with semantic attributes
2. Upload the data to ArangoDB
3. Execute AQL queries against the uploaded data
4. Verify query results match expected outputs

## Problem

The original data generator code had several issues:

1. The `FileMetadataGeneratorTool` created storage objects with empty semantic attributes
2. The activity generator had similar issues with semantic attributes
3. JSON serialization failed for UUID and datetime types
4. The complex AQL query was failing due to array access

## Solution

We implemented a database integration test that:

1. Adds semantic attributes to storage objects and activities
2. Handles UUID and datetime serialization
3. Uses a more reliable AQL query format
4. Tests three different query scenarios

### Key Components

- **JSON Serialization**: We implemented a recursive function `convert_to_json_serializable` to properly handle UUIDs and datetime objects.
- **Semantic Attributes**: We added two methods to add semantic attributes to objects and activities.
- **Query Testing**: We test three different levels of complexity:
  1. Basic attribute query (single attribute, single collection)
  2. Cross-collection query (single attribute, specific collection)
  3. Complex query (multiple attributes, single collection)

## Running the Test

```bash
python -m tools.data_generator_enhanced.testing.test_db_integration --dataset-size 100 --debug
```

Command line arguments:
- `--dataset-size`: Number of records to generate (default: 100)
- `--output`: Path to save results (default: db_integration_test_results.json)
- `--skip-cleanup`: Skip database cleanup after test
- `--debug`: Enable debug logging

## Results

The test outputs detailed metrics:
- Generation time
- Upload time
- Query time
- Query success rate
- Attribute usage statistics
- Detailed query results

Example output:
```json
{
  "metrics": {
    "generation_time": 0.008,
    "upload_time": 0.009,
    "query_time": 0.009,
    "query_success_rate": 1.0
  },
  "attribute_stats": {
    "unique_attributes": 16,
    "total_attributes": 120
  }
}
```

## Fixing the Root Issue

To permanently fix the root issue:

1. Update `FileMetadataGeneratorTool._generate_file_model` to add semantic attributes
2. Add a new method `_generate_semantic_attributes` to handle different attribute types
3. Ensure all generated objects have proper semantic attributes

A patch file with these changes is provided in `tools/data_generator_enhanced/agents/data_gen/patches/fix_semantic_attributes.py`.

## Remaining Work

1. Apply the patch to the `FileMetadataGeneratorTool` class
2. Create unit tests for the `SemanticAttributeRegistry` class
3. Add integration tests for other aspects of the data generator

## Architecture Notes

This integration test follows Indaleko's architecture principles:
- Uses `IndalekoDBCollections` constants for collection names
- Uses `IndalekoDBConfig` for database connectivity
- Maintains proper separation of concerns

The semantic attribute registry follows the UUID-based approach used in the main codebase, ensuring consistency between generated test data and real application data.