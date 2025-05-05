# Query-Driven Metadata Generation Framework

## Overview

This document outlines the architecture and implementation strategy for a query-driven metadata generation framework that builds on the enhanced synthetic data generators developed for Indaleko. The framework is designed to support comprehensive testing of precision and recall for natural language queries, with special emphasis on maintaining realistic database conditions through consistent collection usage.

## Experimental Methodology

The framework implements the following experimental flow:

1. **Query-Based Data Generation**:
   - Input: `<query, positive_match_count, negative_match_count>`
   - The system generates data where the specified number of files will match the query (positive matches) and others will not (negative matches)
   - All data is inserted into the database using a consistent collection structure

2. **Precision/Recall Measurement**:
   - Run the query through the query engine (query/cli.py or query/assistants/cli.py)
   - Measure how many expected matches were found (true positives) vs. unexpected matches (false positives)
   - Calculate precision and recall based on the known ground truth

3. **Metadata Value Demonstration**:
   - Capture AQL generated for all test queries that demonstrate perfect precision/recall
   - Perform ablation studies by disabling classes of metadata (through de-registration or truncation)
   - Observe how precision/recall degrades when specific metadata types are removed
   - Quantify the value added by activity context metadata

## Key Challenge: Collection Consistency

A critical requirement is maintaining collection consistency across queries. Instead of creating a separate collection for each query (which makes precision/recall trivial but unrealistic), the system must:

- Use a single shared collection for each metadata type (e.g., one collection for all Spotify data)
- Ensure proper isolation between data generated for different queries within the same collection
- Handle potential overlap cases where the same data might match multiple queries

This approach better reflects real-world conditions where all data of a particular type is stored together, and queries must differentiate relevant from irrelevant items within that shared space.

## Implementation Architecture

### 1. Query-Driven Generator Framework

```python
class QueryDrivenGenerator:
    def __init__(self, db_config):
        self.db_config = db_config
        self.registration_service = ActivityDataRegistrationService()
        self.generators = self._load_generators()
        self.query_analyzer = QueryAnalyzer()
        
    def generate_data(self, query, positive_count, negative_count):
        # Analyze query to determine required metadata types
        metadata_types = self.query_analyzer.analyze_query(query)
        
        # Generate positive examples that match query
        positive_examples = self._generate_examples(
            metadata_types, positive_count, match_query=True, query=query)
        
        # Generate negative examples that won't match query
        negative_examples = self._generate_examples(
            metadata_types, negative_count, match_query=False, query=query)
        
        # Insert into database using consistent collection names from registration service
        self._insert_data(positive_examples + negative_examples)
        
        return {
            "query": query,
            "positive_ids": [ex.id for ex in positive_examples],
            "negative_ids": [ex.id for ex in negative_examples],
            "metadata_types": metadata_types
        }
        
    def _insert_data(self, examples):
        db = self.db_config.get_arangodb()
        
        for example in examples:
            # Get consistent collection name from registration service
            # This ensures all data of same type goes to the same collection
            collection_name = self.registration_service.get_collection_name(
                example.data_type
            )
            
            # Insert into that collection
            collection = db.collection(collection_name)
            collection.insert(example.to_dict())
```

### 2. Ensuring Collection Consistency

```python
class ActivityDataRegistrationService:
    """
    Service to ensure consistent collection naming across all queries
    for the same data type.
    """
    def __init__(self):
        self._load_registered_services()
        
    def get_collection_name(self, service_type):
        """
        Returns the UUID-based collection name for a given service type.
        If the service is not yet registered, registers it first.
        """
        if service_type not in self.services:
            self._register_service(service_type)
            
        return self.services[service_type].collection_name
        
    def _register_service(self, service_type):
        """
        Register a new service with a UUID-based collection name.
        This ensures all instances of this metadata type use the same collection.
        """
        # Create a service entry with a UUID
        service_uuid = str(uuid.uuid4())
        
        # Register in the ActivityDataProviders collection
        self._register_in_database(service_type, service_uuid)
        
        # Update local cache
        self.services[service_type] = ServiceInfo(
            type=service_type,
            uuid=service_uuid,
            collection_name=f"ActivityProviderData_{service_uuid}"
        )
```

### 3. Query Analysis and Metadata Generation

```python
class QueryAnalyzer:
    def analyze_query(self, query):
        """
        Analyze a natural language query to determine which types of metadata
        are needed and with what parameters.
        """
        # Extract entities, relationships, and contexts from the query
        # This could use the existing NL parser from query/query_processing/
        
        # Map extracted concepts to required generators
        required_metadata = []
        
        # Example analysis for "Find documents I worked on while listening to Spotify in Seattle"
        if "listening" in query.lower() and "spotify" in query.lower():
            required_metadata.append({
                "type": "music_activity",
                "params": {"service": "spotify"}
            })
            
        if any(loc in query.lower() for loc in ["seattle", "location", "where"]):
            required_metadata.append({
                "type": "location",
                "params": {"location": "Seattle, WA"}
            })
            
        # Always include basic file metadata
        required_metadata.append({
            "type": "storage",
            "params": {"activity": "edit"}
        })
        
        return required_metadata
        
class MetadataGenerator:
    """Base class for specific metadata generators"""
    def __init__(self, registration_service):
        self.registration_service = registration_service
        
    def generate(self, params, match_query=True):
        """
        Generate metadata entries that either match or don't match
        the specified parameters.
        """
        raise NotImplementedError()
        
    def get_collection_name(self):
        """
        Get the consistent collection name for this metadata type
        """
        return self.registration_service.get_collection_name(self.metadata_type)
```

### 4. Precision/Recall Evaluation and Ablation

```python
class QueryEvaluator:
    def evaluate_query(self, query, ground_truth):
        # Run query through query/cli.py system
        results = self._run_query(query)
        
        # Capture generated AQL
        aql = self._capture_aql(query)
        
        # Calculate precision and recall
        true_positives = len([r for r in results if r in ground_truth["positive_ids"]])
        false_positives = len([r for r in results if r not in ground_truth["positive_ids"]])
        false_negatives = len([id for id in ground_truth["positive_ids"] if id not in results])
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        
        return {
            "precision": precision,
            "recall": recall,
            "aql": aql
        }

class AblationStudy:
    def run_ablation(self, queries, ground_truth_map, metadata_types):
        results = {}
        
        # First run baseline with all metadata
        baseline = self._run_baseline(queries, ground_truth_map)
        results["baseline"] = baseline
        
        # Then ablate each metadata type
        for metadata_type in metadata_types:
            # Option 1: De-register collection
            service = self.registration_service.get_service_by_type(metadata_type)
            self.registration_service.deregister_service(service.uuid)
            
            # Option 2: Truncate collection but keep it registered
            # collection_name = service.collection_name
            # self._truncate_collection(collection_name)
            
            # Run all queries again
            ablated_results = self._run_queries(queries, ground_truth_map)
            results[metadata_type] = ablated_results
            
            # Restore for next iteration if needed
            self.registration_service.register_service(service)
            
        return results
```

## Implementation Considerations

### 1. Collection Naming Consistency

To ensure proper collection naming consistency:

- Use the `ActivityDataRegistrationService` to map semantic types to UUID-based collection names
- Always look up collection names through this service rather than hardcoding them
- Maintain a single collection for each metadata type across all queries
- Tag generated data with query identifiers to track which query it was generated for

### 2. Data Isolation Within Shared Collections

While using shared collections, the system must maintain proper isolation:

- Include query identifiers in generated metadata to track provenance
- Use query-specific attributes in data that won't affect other queries
- Handle edge cases where the same metadata might match multiple queries

### 3. Integration with Existing Components

The framework should integrate with:

- Existing enhanced data generators (location, EXIF, music, etc.)
- Query processing system (query/cli.py)
- Database schema and collection structure
- UUID-based naming system and registration services

### 4. Realistic Query Coverage

To ensure comprehensive testing:

- Generate a diverse set of queries covering different metadata types
- Include complex queries that span multiple metadata types
- Test boundary conditions and edge cases
- Create queries with varying levels of specificity

## Ablation Study Methodology

The ablation study will systematically remove each type of metadata to measure its impact:

1. **Full System Baseline**: Measure precision/recall with all metadata types
2. **Sequential Removal**: Remove one metadata type at a time:
   - Deregister or truncate collections
   - Run all test queries
   - Measure change in precision/recall
3. **Cumulative Removal**: Remove metadata types progressively
4. **Minimal System**: Measure precision/recall with only storage and basic semantic metadata

## Implementation Plan

1. Enhance existing data generators to use consistent collection naming
2. Implement the query analyzer to identify required metadata from NL queries
3. Build orchestration layer to coordinate multiple generators
4. Develop precision/recall measurement and AQL capture mechanism
5. Implement ablation study framework
6. Create reporting and visualization components

## Conclusion

This framework provides a comprehensive approach for generating query-specific metadata while maintaining realistic database conditions with shared collections. By ensuring all metadata of the same type is stored in consistent collections (through the activity data registration service), the system will better reflect real-world conditions and provide more meaningful precision/recall measurements.