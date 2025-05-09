# Ablation Query Design

## Overview

This document outlines the design for implementing an authentic ablation testing framework that integrates with Indaleko's existing query pipeline. The framework will measure the real impact of removing specific activity data collections on search precision and recall without relying on arbitrary simulation factors.

## Current Challenges

The current ablation testing implementation has several limitations:

1. **Truth-based Querying**: The current implementation directly queries using document keys from truth data, which doesn't accurately simulate how ablation affects real searches.
2. **Artificial Impact Factors**: Using arbitrary factors to simulate the impact of ablation undermines scientific validity.
3. **Disconnection from Query Pipeline**: The implementation doesn't leverage Indaleko's sophisticated query translation and execution pipeline.

## Proposed Solution: Query Pipeline Integration

We will adapt Indaleko's existing query pipeline to support ablation testing with the following approach:

### 1. Query Pipeline Adaptation

Create a simplified `AblationQueryPipeline` class that adapts key components from the CLI query pipeline:

```python
class AblationQueryPipeline:
    """Pipeline for executing queries with selective collection ablation."""
    
    def __init__(self, db_config):
        """Initialize the ablation query pipeline."""
        self.db_config = db_config
        self.nl_parser = EnhancedNLParser()
        self.query_translator = AQLTranslator()
        self.query_executor = AQLQueryExecutor()
        
    def execute_query(self, query_text, ablated_collections=None):
        """Execute a query with specified collections ablated."""
        if ablated_collections is None:
            ablated_collections = []
            
        # 1. Parse the natural language query
        parsed_query = self.nl_parser.parse(query=query_text)
        
        # 2. Filter out ablated collections from available categories
        collection_categories = [
            entity.collection for entity in parsed_query.Categories.category_map
            if entity.collection not in ablated_collections
        ]
        
        # 3. Map entities and get collection metadata (excluding ablated collections)
        entity_mappings = self.map_entities(parsed_query.Entities)
        collection_metadata = self.get_collection_metadata(collection_categories)
        
        # 4. Get indices for available collections
        indices = self._get_indices(collection_categories)
        
        # 5. Create structured query for available collections
        structured_query = StructuredQuery(
            original_query=query_text,
            intent=parsed_query.Intent.intent,
            entities=entity_mappings,
            db_info=collection_metadata,
            db_indices=indices,
        )
        
        # 6. Translate to AQL
        query_data = TranslatorInput(
            Query=structured_query,
            Connector=self.llm_connector,
        )
        translated_query = self.query_translator.translate(query_data)
        
        # 7. Execute the query
        results = self.query_executor.execute(
            translated_query.aql_query,
            self.db_config,
            bind_vars=translated_query.bind_vars,
        )
        
        return {
            "results": results,
            "parsed_query": parsed_query,
            "translated_query": translated_query,
            "collection_categories": collection_categories
        }
```

### 2. Ablation Testing Process

Update the `AblationTester` class to utilize this pipeline:

```python
def test_ablation(self, query_id: uuid.UUID, query_text: str, target_collection: str):
    """Test the impact of ablating collections on a specific query.
    
    Args:
        query_id: The UUID of the query
        query_text: The natural language query text
        target_collection: The collection to evaluate results against
        
    Returns:
        AblationResult object with metrics
    """
    # 1. Get truth data for evaluation
    truth_data = self.get_truth_data(query_id, target_collection)
    
    # 2. Run baseline query with all collections available
    baseline_results = self.query_pipeline.execute_query(query_text)
    baseline_metrics = self._calculate_metrics(
        baseline_results["results"], 
        truth_data,
        target_collection
    )
    
    # 3. Run queries with each collection ablated
    ablation_results = {}
    for collection in self.collections_to_test:
        if collection != target_collection:
            # Run query with this collection ablated
            results = self.query_pipeline.execute_query(
                query_text, 
                ablated_collections=[collection]
            )
            
            # Calculate metrics
            metrics = self._calculate_metrics(
                results["results"],
                truth_data,
                target_collection
            )
            
            # Store results
            impact_key = f"{collection}_impact_on_{target_collection}"
            ablation_results[impact_key] = {
                "metrics": metrics,
                "query_info": {
                    "aql_query": results["translated_query"].aql_query,
                    "bind_vars": results["translated_query"].bind_vars,
                    "collections_used": results["collection_categories"]
                }
            }
    
    return {
        "baseline": baseline_metrics,
        "ablation_results": ablation_results
    }
```

### 3. Metric Calculation

Calculate precision, recall, and F1 score based on actual query results compared to truth data:

```python
def _calculate_metrics(self, results, truth_data, collection_name):
    """Calculate precision, recall and F1 score for search results.
    
    Args:
        results: The search results from query execution
        truth_data: Set of document keys that should match
        collection_name: The collection being evaluated
        
    Returns:
        Dictionary with precision, recall and F1 score
    """
    # Extract document keys from results
    result_keys = set()
    for doc in results:
        if "_key" in doc:
            result_keys.add(doc["_key"])
    
    # Calculate true positives, false positives, and false negatives
    true_positives = len(result_keys.intersection(truth_data))
    false_positives = len(result_keys - truth_data)
    false_negatives = len(truth_data - result_keys)
    
    # Calculate precision, recall, and F1 score
    precision = true_positives / (true_positives + false_positives) if true_positives + false_positives > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if true_positives + false_negatives > 0 else 0
    f1_score = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0
    
    return {
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "impact": 1.0 - f1_score  # Impact is reduction in F1 score
    }
```

## Benefits of This Approach

1. **Authentic Impact Measurement**: The impact of ablation is measured based on real changes to query results, not arbitrary simulation factors.

2. **Integration with Existing Pipeline**: Leverages Indaleko's sophisticated query translation and execution pipeline.

3. **Preserves Collection Relationships**: Naturally captures the relationships between collections through the LLM-driven query translation process.

4. **Scientific Validity**: Impact scores reflect actual degradation in precision and recall when collections are ablated.

5. **Maintainability**: Follows Indaleko's architectural patterns and reuses existing code.

## Implementation Plan

1. **Create AblationQueryPipeline Class**: Adapt the query pipeline components from `query/cli.py` for ablation testing.

2. **Update AblationTester**: Integrate the pipeline into the ablation tester, replacing the current mechanism.

3. **Enhance Metric Calculation**: Ensure metrics are calculated based on actual query results compared to truth data.

4. **Visualization Enhancements**: Update visualization components to display collection relationships based on actual impact measurements.

5. **Implement Cross-Collection Tests**: Add support for measuring higher-order impacts when multiple collections are ablated simultaneously.

## Conclusion

This design ensures that our ablation testing framework will provide scientifically valid measurements of how different activity data types impact search precision and recall. By integrating with Indaleko's existing query pipeline, we'll capture authentic behaviors and relationships without relying on arbitrary simulation factors.