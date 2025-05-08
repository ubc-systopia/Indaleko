# Task Activity Implementation for Ablation Framework

This document describes the implementation of the Task Activity components for the Indaleko ablation study framework. These components generate synthetic task/application usage data, record it to the database, and provide testing capabilities for ablation studies.

## Components Implemented

1. **TaskActivity Model** (`ablation/models/task_activity.py`):
   - Data model for task activity with application name, window title, and duration
   - Active state tracking and user association
   - Semantic attribute integration following Indaleko patterns
   - Timezone-aware timestamps

2. **TaskActivityCollector** (`ablation/collectors/task_collector.py`):
   - Generates realistic task activity data with application-specific properties
   - Includes realistic window titles based on application type
   - Supports deterministic data generation with seed control
   - Implements match/non-match generation based on query analysis
   - Follows collector pattern with no direct database interaction

3. **TaskActivityRecorder** (`ablation/recorders/task_recorder.py`):
   - Handles database integration following Indaleko patterns
   - Records task activities to ArangoDB
   - Supports batch operations for efficiency
   - Manages truth data for evaluation

4. **Unit Tests** (`ablation/tests/unit/test_task_activity.py`):
   - Tests for the TaskActivity model and collector
   - Validates data generation and model behavior

5. **Integration Tests** (`ablation/tests/integration/test_task_integration.py`):
   - End-to-end tests for collector and recorder integration
   - Tests database operations and query functionality

6. **Demo Script** (`ablation/demo_task_activity.py`):
   - Complete workflow demonstration
   - Generates and records synthetic task activities
   - Shows query execution against recorded data

## Key Features

### Data Model

The `TaskActivity` model includes:

- Task name (e.g., "Document editing", "Data analysis", "Presentation design")
- Application name (e.g., "Microsoft Word", "Excel", "Visual Studio Code")
- Window title for realism (e.g., "Annual Report 2024 - Word")
- Activity duration in seconds
- Active status (whether the task was in foreground)
- User identification
- Source of task data (e.g., "windows_task_manager")
- Semantic attributes following Indaleko patterns

### Collector Capabilities

The collector supports:

- Application-aware task generation with realistic window titles
- Random data generation with realistic properties
- Deterministic generation using seeds for reproducibility
- Named entity integration for consistent identifiers
- Query-aware match generation
- Non-matching data generation for testing
- Targeted matching based on query keywords

### Recorder Integration

The recorder provides:

- ArangoDB integration following Indaleko patterns
- Truth data tracking for precision/recall calculation
- Batch operations for efficiency
- Query capabilities for validation

## Usage Examples

### Basic Usage

```python
from ablation.collectors.task_collector import TaskActivityCollector
from ablation.recorders.task_recorder import TaskActivityRecorder

# Create collector and recorder
collector = TaskActivityCollector()
recorder = TaskActivityRecorder()

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
query = "Find documents I edited in Microsoft Word"
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
query = "Find code I wrote in Visual Studio Code"
entity_ids = collector.generate_truth_data(query)

# Record the truth data
recorder.record_truth_data(query_id, entity_ids)
```

## Demo Script

The demo script (`demo_task_activity.py`) shows a complete workflow:

1. Generates 100 random task activities
2. Creates activities matching specific test queries
3. Records truth data for evaluation
4. Executes sample queries against the database
5. Displays matching results

Run the demo script:

```bash
python -m research.ablation.demo_task_activity
```

## Testing

Run the unit tests:

```bash
python -m unittest research.ablation.tests.unit.test_task_activity
```

Run the integration tests:

```bash
python -m unittest research.ablation.tests.integration.test_task_integration
```

## Architectural Considerations

This implementation follows Indaleko's architectural principles:

1. **Collector/Recorder Pattern**: Strict separation between data collection and database operations
2. **Data Model Integrity**: Extends IndalekoBaseModel with proper schema validation
3. **Timezone-Aware Dates**: All timestamps use UTC timezone
4. **Database Access**: Follows proper collection management practices
5. **Error Handling**: Uses fail-fast approach for database errors

## Next Steps

1. Implement the Collaboration Activity collector and recorder (next activity type)
2. Enhance the ablation testing framework to use our components
3. Develop the result visualization and reporting tools
4. Continue implementing remaining activity types following this pattern
