# Location Activity Implementation for Ablation Framework

This document describes the implementation of the Location Activity components for the Indaleko ablation study framework. These components generate synthetic location data, record it to the database, and provide testing capabilities for ablation studies.

## Components Implemented

1. **LocationActivity Model** (`ablation/models/location_activity.py`):
   - Data model for location activity with coordinates, location type, device information
   - Semantic attribute integration following Indaleko patterns
   - Timezone-aware timestamps

2. **LocationActivityCollector** (`ablation/collectors/location_collector.py`):
   - Generates synthetic location data with realistic properties
   - Supports deterministic data generation with seed control
   - Implements match/non-match generation based on query analysis
   - Follows collector pattern with no direct database interaction

3. **LocationActivityRecorder** (`ablation/recorders/location_recorder.py`):
   - Handles database integration following Indaleko patterns
   - Records location activities to ArangoDB
   - Supports batch operations for efficiency
   - Manages truth data for evaluation

4. **Unit Tests** (`ablation/tests/unit/test_location_activity.py`):
   - Tests for the LocationActivity model and collector
   - Validates data generation and model behavior

5. **Integration Tests** (`ablation/tests/integration/test_location_integration.py`):
   - End-to-end tests for collector and recorder integration
   - Tests database operations and query functionality

6. **Demo Script** (`ablation/demo_location_activity.py`):
   - Complete workflow demonstration
   - Generates and records synthetic location activities
   - Shows query execution against recorded data

## Key Features

### Data Model

The `LocationActivity` model includes:

- Location name (e.g., "Home", "Work", "Coffee Shop")
- Geographic coordinates with accuracy information
- Location type categorization (residential, commercial, educational, etc.)
- Device information
- WiFi network information when applicable
- Source of location data (GPS, WiFi, cell, etc.)
- Semantic attributes following Indaleko patterns

### Collector Capabilities

The collector supports:

- Random data generation with realistic properties
- Deterministic generation using seeds for reproducibility
- Named entity integration for consistent identifiers
- Query-aware match generation
- Non-matching data generation for testing

### Recorder Integration

The recorder provides:

- ArangoDB integration following Indaleko patterns
- Truth data tracking for precision/recall calculation
- Batch operations for efficiency
- Query capabilities for validation

## Usage Examples

### Basic Usage

```python
from ablation.collectors.location_collector import LocationActivityCollector
from ablation.recorders.location_recorder import LocationActivityRecorder

# Create collector and recorder
collector = LocationActivityCollector()
recorder = LocationActivityRecorder()

# Generate and record a single activity
activity = collector.collect()
recorder.record(activity)

# Generate and record a batch of activities
activities = collector.generate_batch(count=10)
recorder.record_batch(activities)
```

### Query-Based Data Generation

```python
# Generate data matching a specific query
query = "Find files I accessed while at the Coffee Shop"
matching_data = collector.generate_matching_data(query, count=5)
recorder.record_batch(matching_data)

# Generate data that should NOT match the query
non_matching_data = collector.generate_non_matching_data(query, count=5)
recorder.record_batch(non_matching_data)
```

### Truth Data Recording

```python
import uuid

# Generate a query ID
query_id = uuid.uuid4()

# Generate truth data for a query
query = "Find files I accessed while at Home"
entity_ids = collector.generate_truth_data(query)

# Record the truth data
recorder.record_truth_data(query_id, entity_ids)
```

## Demo Script

The demo script (`demo_location_activity.py`) shows a complete workflow:

1. Generates 100 random location activities
2. Creates activities matching specific test queries
3. Records truth data for evaluation
4. Executes sample queries against the database
5. Displays matching results

Run the demo script:

```bash
python -m research.ablation.demo_location_activity
```

## Testing

Run the unit tests:

```bash
python -m unittest research.ablation.tests.unit.test_location_activity
```

Run the integration tests:

```bash
python -m unittest research.ablation.tests.integration.test_location_integration
```

## Architectural Considerations

This implementation follows Indaleko's architectural principles:

1. **Collector/Recorder Pattern**: Strict separation between data collection and database operations
2. **Data Model Integrity**: Extends IndalekoBaseModel with proper schema validation
3. **Timezone-Aware Dates**: All timestamps use UTC timezone
4. **Database Access**: Follows proper collection management practices
5. **Error Handling**: Uses fail-fast approach for database errors

## Next Steps

1. Integrate with the AblationTester for systematic testing
2. Extend with more sophisticated truth data tracking
3. Enhance query generation based on location characteristics
4. Add performance metrics collection
5. Implement the remaining activity types following this pattern
