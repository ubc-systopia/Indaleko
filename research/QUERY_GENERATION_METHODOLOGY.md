# Query Generation Methodology for Ablation Studies

## Overview

This document describes the methodology used for generating test queries in the Indaleko ablation study framework. The approach aims to create scientifically valid experiments that can measure the real impact of ablating different activity data collections on search precision and recall.

## Core Methodology

The ablation framework uses a specialized approach to query generation and evaluation that separates experimental control (ability to measure impact) from what we're actually measuring (how activity data affects search quality).

### Key Design Principles

1. **Experimental Control vs. Measurement**:
   - **Control**: We ensure 100% recall for non-ablated collections using "hidden attributes"
   - **Measurement**: We measure how precision drops when related collections are ablated

2. **Scientific Validity**:
   - Ablation studies must isolate the variable being tested (presence/absence of a collection)
   - Results must be reproducible and comparable across different ablation configurations
   - Metrics must accurately reflect the impact of removing specific data types

3. **Fail-Stop Approach**:
   - No fallbacks or template substitutions when query generation fails
   - Critical failures terminate the experiment rather than compromising scientific integrity
   - Comprehensive logging of all experimental parameters and results

## Query Generation Implementation

The query generation system has two primary components:

1. **EnhancedQueryGenerator**: LLM-driven query generation for realistic, diverse queries
2. **Truth Data Management**: Tracking expected matches for each query to ensure experimental control

### EnhancedQueryGenerator

The `EnhancedQueryGenerator` creates realistic natural language queries that reflect how users might search for activity data:

```python
# Generate queries for EACH activity type in the pair
generator = EnhancedQueryGenerator()
diverse_queries = []

for activity_type in activity_types:
    logging.info(f"Generating enhanced queries for activity type: {activity_type}")

    # Generate queries with proper fail-stop approach - NO fallbacks
    try:
        activity_queries = generator.generate_enhanced_queries(activity_type, count=count//len(activity_types) + 1)
        logging.info(f"Successfully generated {len(activity_queries)} diverse queries for {activity_type} using LLM")
        diverse_queries.extend(activity_queries)
    except Exception as query_gen_error:
        logging.error(f"CRITICAL: Failed to generate diverse queries using EnhancedQueryGenerator: {query_gen_error}")
        logging.error("This is required for proper ablation testing - fix the query generator")
        sys.exit(1)  # Fail-stop immediately - no fallbacks
```

The generator uses different techniques to ensure query diversity:
- Varied query formulations (questions, commands, natural language descriptions)
- Different entity references and attributes within query templates
- Activity-specific terminology and concepts
- Query diversity scoring using Jaro-Winkler similarity to avoid duplicates

### Truth Data Management

For each generated query, we create "truth data" that links the query to specific documents in each collection. This is essential for measuring the impact of ablation:

```python
# Generate matching entities for each collection
matching_entities = {}

for collection in collection_pair:
    # Query the database for real document keys
    try:
        # Get 5 actual document keys from the collection
        entity_ids = []
        cursor = ablation_tester.db.aql.execute(
            f"""
            FOR doc IN {collection}
            LIMIT 5
            RETURN doc._key
            """,
        )

        # Extract the document keys
        for doc_key in cursor:
            entity_ids.append(doc_key)

        # Store truth data with composite key
        store_success = ablation_tester.store_truth_data(query_id, collection, entity_ids)
    except Exception as e:
        logging.exception(f"Error querying collection {collection}: {e}")
        store_success = False
```

## Query Execution and Evaluation

The critical innovation in our approach is the combined query execution method that ensures experimental control while still testing semantic search capabilities:

```python
def _build_combined_query(
    self,
    collection_name: str,
    search_terms: dict,
    truth_data: set[str]
) -> tuple[str, dict]:
    """Build a combined query that uses both truth data lookup and semantic search.

    This ensures 100% recall of truth data when the collection is not ablated,
    while still demonstrating semantic search capabilities.
    """
    bind_vars = search_terms.copy()

    # Add truth keys to bind variables if available
    if truth_data:
        bind_vars["truth_keys"] = list(truth_data)

    # Start building the query
    aql_query = f"""
    FOR doc IN {collection_name}
    FILTER """

    # First part: Direct truth data lookup (ensures 100% recall)
    if truth_data:
        truth_filter = "doc._key IN @truth_keys"
    else:
        # If no truth data, use a filter that's always false
        truth_filter = "false"

    # Second part: Semantic filters based on collection type
    semantic_filters = []

    if "MusicActivity" in collection_name:
        if "artist" in bind_vars:
            semantic_filters.append("doc.artist == @artist")

    # [Additional semantic filters for different collection types...]

    # Combine truth lookup with semantic filters using OR
    # This ensures we get 100% recall of truth data + any additional matches from semantic search
    if semantic_filters:
        semantic_part = " OR ".join(semantic_filters)
        aql_query += f"{truth_filter} OR ({semantic_part})"
    else:
        # If no semantic filters, just use truth filter
        aql_query += truth_filter

    # Complete the query
    aql_query += """
    RETURN doc
    """

    return aql_query, bind_vars
```

This combined approach provides several benefits:
1. **Control**: Guaranteed 100% recall of truth data for non-ablated collections
2. **Realism**: Semantic search filters that reflect real user queries
3. **Measurement**: Precision drops measurably when related collections are ablated
4. **Validity**: Clear distinction between experimental control and what we're measuring

## Ablation Impact Measurement

After generating queries and truth data, we measure the impact of ablation by:

1. Establishing baseline metrics with all collections available
2. Ablating each collection one at a time
3. Running the same queries and measuring changes in precision, recall, and F1 score
4. Calculating impact as the reduction in F1 score (1.0 - ablated_f1_score)

This provides a scientifically rigorous measurement of how each activity data type affects search performance.

## Scientific Rationale for the "Hidden Attribute" Approach

The use of "hidden attributes" (direct document key lookups) is scientifically valid because:

1. The experiment is measuring precision impact, not recall capability
2. All collections start with the same baseline (100% recall), making precision changes comparable
3. The approach isolates the variable being tested (presence/absence of a collection)
4. The method is transparent and fully reproducible

As noted in our design documentation: "Recall = 1.0 (because our queries are crafted to do that, and doing it via a 'hidden attribute' does not devalue the experiment). Precision is what we expect to see drop, precisely because episodic human memory can be quite precise for temporal, geospatial, environmental, and social clues."

## Current Limitations and Potential Improvements

While the current methodology provides a robust foundation for ablation studies, several limitations and potential improvements should be noted:

### Limitations

1. **Artificial Baseline**: The "hidden attribute" approach creates an artificially perfect baseline (100% recall), which may not reflect real-world query behavior where users rarely achieve perfect recall.

2. **Query Diversity Limitations**: Even with LLM generation, the queries might not fully represent the complete diversity of real user behavior, especially for niche or complex queries.

3. **Collection Bias**: The current implementation may have bias toward certain collection types based on the templates and examples provided to the LLM.

4. **Limited Cross-Collection Queries**: While we do generate queries that span multiple collections, they might not fully capture the complex inter-relationships between all collection types.

5. **Fixed Entity References**: The named entities used in queries may be limited and not evolve over time, unlike real user queries that change with current events.

6. **Lack of Query Evolution**: Real users' queries evolve over time as they learn from previous results, but our approach generates queries independently.

7. **Query Complexity**: Most generated queries remain relatively simple compared to the complex, context-dependent queries real users might formulate.

8. **LLM Limitations**: The LLM-based query generator has some inherent limitations in understanding the full spectrum of activity data relationships.

### Potential Improvements

1. **User Simulation**: Implement a more sophisticated user simulation that learns from query results and evolves queries over time.

2. **Multi-step Queries**: Generate multi-step query sequences that represent a user's search journey rather than independent queries.

3. **Personalized Query Generation**: Generate queries based on specific user profiles to reflect different search patterns.

4. **Real-world Query Corpus**: Incorporate a corpus of real user queries (anonymized) to better represent actual search behavior.

5. **Advanced Semantic Relationships**: Enhance query generation to better capture complex relationships between different activity types.

6. **Improved Entity Management**: Develop more sophisticated entity management to ensure queries reference consistent entities across collections.

7. **Contextual Query Generation**: Generate queries that consider temporal, spatial, and social context more effectively.

8. **Query Difficulty Calibration**: Generate queries with calibrated levels of difficulty to measure performance across simple and complex queries.

## Conclusion

The query generation methodology implemented in the Indaleko ablation framework represents a scientifically rigorous approach to measuring the impact of different activity data types on search performance. By separating experimental control (using "hidden attributes" for 100% recall) from what we're measuring (precision impact), we can obtain meaningful, reproducible results about the value of different activity data collections for cognitive search systems.

This methodology provides a solid foundation for ongoing research into the role of different activity data types in supporting contextual and cognitive search capabilities.
