# Collection Ablation Implementation Plan

## Overview

This document outlines the plan for implementing a collection ablation mechanism for Indaleko's testing framework. The goal is to enable systematic testing of how the absence of specific data types affects query precision and recall without requiring architectural changes to the current codebase.

## Approach

Instead of modifying each generator to use a registration service, we'll implement an "ablation list" approach that:

1. Hides collections from query processing
2. Allows for controlled testing of how each data type affects results
3. Preserves the current collection naming scheme

## Implementation Steps

### 1. Collection Metadata Manager Enhancement

Update `db/db_collection_metadata.py` to:
- Add an ablation list mechanism
- Filter collections based on this list
- Provide methods to ablate/restore collections

```python
class CollectionMetadataManager:
    def __init__(self):
        self._ablated_collections = set()  # Collections to exclude

    def ablate_collection(self, collection_name):
        """Add a collection to the ablation list."""
        self._ablated_collections.add(collection_name)
        return collection_name

    def restore_collection(self, collection_name):
        """Remove a collection from the ablation list."""
        if collection_name in self._ablated_collections:
            self._ablated_collections.remove(collection_name)
            return True
        return False

    def get_collections(self):
        """Get all non-ablated collections."""
        all_collections = self._get_all_collections()
        return [c for c in all_collections if c["name"] not in self._ablated_collections]

    def is_ablated(self, collection_name):
        """Check if a collection is currently ablated."""
        return collection_name in self._ablated_collections
```

### 2. Ablation Testing Framework

Create a new module for testing how ablation affects query results:

```python
class AblationTester:
    def __init__(self, db_config):
        self.db_config = db_config
        self.collection_manager = CollectionMetadataManager()
        self.query_executor = QueryExecutor()

    def test_ablation(self, query, collections_to_ablate):
        """
        Test how ablating specific collections affects results.

        Args:
            query: The natural language query to test
            collections_to_ablate: List of collections to ablate

        Returns:
            Dictionary with baseline and ablation results
        """
        # 1. Run baseline query
        baseline_results = self.query_executor.execute_query(query)

        # 2. Capture baseline AQL
        baseline_aql = self.query_executor.get_last_aql()

        # 3. Ablate collections
        for collection in collections_to_ablate:
            self.collection_manager.ablate_collection(collection)

        # 4. Run query with ablations
        ablated_results = self.query_executor.execute_query(query)

        # 5. Capture ablated AQL
        ablated_aql = self.query_executor.get_last_aql()

        # 6. Restore collections
        for collection in collections_to_ablate:
            self.collection_manager.restore_collection(collection)

        # 7. Calculate metrics
        precision, recall = self._calculate_metrics(
            baseline_results, ablated_results)

        return {
            "baseline": {
                "results": baseline_results,
                "aql": baseline_aql
            },
            "ablated": {
                "results": ablated_results,
                "aql": ablated_aql
            },
            "metrics": {
                "precision": precision,
                "recall": recall
            },
            "ablated_collections": collections_to_ablate
        }
```

### 3. AQL Analysis Component

Create a utility to analyze how AQL changes when collections are ablated:

```python
class AQLAnalyzer:
    def __init__(self):
        self.collection_pattern = re.compile(r'FOR\s+\w+\s+IN\s+(\w+)')

    def extract_collections(self, aql):
        """Extract collection names from AQL."""
        return self.collection_pattern.findall(aql)

    def compare_queries(self, baseline_aql, ablated_aql):
        """Compare baseline and ablated AQL."""
        baseline_collections = self.extract_collections(baseline_aql)
        ablated_collections = self.extract_collections(ablated_aql)

        missing_collections = set(baseline_collections) - set(ablated_collections)

        return {
            "baseline_collections": baseline_collections,
            "ablated_collections": ablated_collections,
            "missing_collections": list(missing_collections)
        }
```

### 4. Integration with Query CLI

Modify the query CLI to support ablation testing:

```python
@click.option('--ablate', '-a', multiple=True,
              help='Collection to ablate for testing')
def main(query, ablate=None):
    # Initialize components
    db_config = IndalekoDBConfig()
    ablation_tester = AblationTester(db_config)

    # If ablation testing requested
    if ablate:
        results = ablation_tester.test_ablation(query, ablate)
        display_ablation_results(results)
    else:
        # Normal query execution
        query_executor = QueryExecutor()
        results = query_executor.execute_query(query)
        display_results(results)
```

### 5. Collection Truncation Alternative

As an alternative to hiding collections, implement a truncation approach:

```python
def truncate_collection(collection_name):
    """Empty a collection without removing it."""
    db_config = IndalekoDBConfig()
    db = db_config.get_arangodb()

    try:
        collection = db.collection(collection_name)
        collection.truncate()
        return True
    except Exception as e:
        logging.error(f"Error truncating collection {collection_name}: {e}")
        return False
```

## Testing Procedure

1. Generate synthetic data with all metadata types
2. Run a set of test queries to establish baseline precision/recall
3. Ablate each collection type and re-run the queries
4. Analyze how results change when specific data types are excluded
5. Verify AQL changes appropriately reflect the ablated collections
6. Document the impact of each metadata type on query results

## Implementation Timeline

1. Collection Metadata Manager Enhancement (2 hours)
2. Ablation Testing Framework (3 hours)
3. AQL Analysis Component (2 hours)
4. Integration with Query CLI (2 hours)
5. Testing & Validation (4 hours)

## Success Criteria

1. Can successfully hide collections from query engine
2. AQL changes appropriately when collections are ablated
3. Precision/recall metrics change as expected
4. Can quantify the importance of each metadata type

## Next Steps

After implementing and testing the ablation mechanism:

1. Create a comprehensive test suite covering all metadata types
2. Document the impact of each type on query effectiveness
3. If issues arise, revisit the registration model approach
