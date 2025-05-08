# Indaleko Ablation Study Framework

This directory contains the implementation of the Ablation Study Framework for Indaleko. The framework allows for systematic measurement of how different activity data types affect search precision and recall.

## Overview

The ablation study measures how the removal of specific activity collections impacts search effectiveness. By systematically removing (ablating) different activity data collections from the database and measuring the change in search performance, we can quantify the value each activity type contributes to search results.

## Key Components

### Models

- `activity.py` - Defines the basic activity data types and models
- `ablation_results.py` - Models for storing ablation test results and metrics
- `location_activity.py`, `music_activity.py`, etc. - Specific activity type models

### Database Management

- `database.py` - Provides database interface for the ablation framework
- `collections.py` - Manages collection naming and creation

### Query Generation

- `generator.py` - Creates test queries targeting different activity types
- `truth_tracker.py` - Tracks which documents should match each query

### Testing Framework

- `test_runner.py` - Central class that orchestrates the ablation testing process
- Integration tests for each component

## Workflow

The ablation testing framework follows this workflow:

1. Generate synthetic test data for each activity type
2. Create test queries targeting specific activity types
3. Track truth data (which documents should match each query)
4. Run baseline tests with all collections active
5. Run ablation tests with each collection removed one by one
6. Calculate precision, recall, and F1 score impact
7. Generate reports showing the contribution of each activity type

## Usage

### Running a Basic Ablation Test

```python
from research.ablation.testing.test_runner import AblationTestRunner

# Initialize the test runner
runner = AblationTestRunner(
    test_name="Activity Ablation Test",
    description="Testing impact of different activity types"
)

# Run a test with 25 queries across all activity types
test_metadata = runner.run_test(num_queries=25)

# Results are stored in the database for analysis
print(f"Test ID: {test_metadata.test_id}")
print(f"Time taken: {test_metadata.total_execution_time_ms} ms")
print("Impact Ranking:")
for impact in test_metadata.impact_ranking:
    print(f"- {impact['collection']}: {impact['impact']:.3f}")
```

### Working with Truth Data

The `TruthTracker` component manages ground truth data for queries:

```python
from research.ablation.query.truth_tracker import TruthTracker

# Initialize the truth tracker
tracker = TruthTracker()

# Record truth data for a query
tracker.record_query_truth(
    query_id="12345",
    matching_ids=["doc1", "doc2", "doc3"],
    query_text="What songs did I listen to last week?",
    activity_types=["MUSIC"],
    difficulty="medium",
    metadata={"entities": [], "temporal": "last week"}
)

# Get matching IDs for a query
matching_ids = tracker.get_matching_ids("What songs did I listen to last week?")

# Save truth data to a file for backup/sharing
tracker.save_to_file(Path("./truth_data.json"))
```

## Activity Type Taxonomy

The ablation study focuses on these six primary activity data types:

1. **Music Activity** - Music listening patterns from streaming services
2. **Location Activity** - Geographic position data from various sources
3. **Task Activity** - User task management and completion
4. **Collaboration Activity** - Calendar events and file sharing
5. **Storage Activity** - File system operations and access patterns
6. **Media Activity** - Video/content consumption activities

## Metrics and Analysis

The framework calculates these key metrics for each ablation test:

- **Precision** - Percentage of returned results that are relevant
- **Recall** - Percentage of relevant items that are found
- **F1 Score** - Harmonic mean of precision and recall
- **Impact** - Performance degradation when a collection is ablated
- **Relative Contribution** - Comparative importance of each activity type

## Implementation Status

- ✅ Created core database models and collection management
- ✅ Implemented test runner for ablation management
- ✅ Built TruthTracker for managing ground truth data
- ✅ Created unit and integration tests
- 🔄 Developing query generation mechanism
- 🔄 Implementing activity type models and collectors
- 🔄 Finalizing validation strategies and metrics calculation
