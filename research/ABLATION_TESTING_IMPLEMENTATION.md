# Ablation Testing Framework Implementation

This document describes the implementation of the Ablation Testing Framework for the Indaleko platform. The framework provides a systematic way to measure how different activity data types affect search precision and recall.

## Components Implemented

1. **AblationTester** (`ablation/ablation_tester.py`):
   - Core component for collection ablation and restoration
   - Truth data retrieval and metric calculation
   - Query execution with timing measurements
   - Precision, recall, and F1 score calculation

2. **AblationTestRunner** (`ablation/ablation_test_runner.py`):
   - Coordinates ablation experiments across multiple queries and collections
   - Manages test execution and result collection
   - Generates summary reports and visualizations
   - Provides data export in multiple formats

3. **Demo Script** (`ablation/demo_ablation_test.py`):
   - Complete end-to-end demonstration
   - Generates synthetic test data
   - Creates test queries with truth data
   - Runs ablation tests and generates reports

## Key Features

### Collection Ablation

The framework implements a non-destructive ablation approach:
- Backs up collection data before removing it
- Temporarily removes the collection to simulate its absence
- Restores the original data after testing
- Ensures proper cleanup even in case of errors

### Metrics Calculation

The framework calculates key information retrieval metrics:
- **Precision**: Proportion of retrieved results that are relevant
- **Recall**: Proportion of relevant items that are retrieved
- **F1 Score**: Harmonic mean of precision and recall
- **Impact**: Performance degradation when a collection is ablated

### Test Runner Capabilities

The test runner provides:
- Batch test execution across multiple queries
- Aggregation of metrics across test runs
- Summary report generation in Markdown format
- Visualization of results with matplotlib and seaborn
- Data export in JSON and CSV formats

## Usage Examples

### Basic Usage

```python
from ablation.ablation_tester import AblationConfig, AblationTester

# Create tester
tester = AblationTester()

# Ablate a collection
tester.ablate_collection("AblationLocationActivity")

# Run a query and calculate metrics
result = tester.test_ablation(
    query_id=query_id,
    query_text="Find files I accessed at Home",
    collection_name="AblationTaskActivity",
)

# Restore the collection
tester.restore_collection("AblationLocationActivity")

# Clean up
tester.cleanup()
```

### Running Comprehensive Tests

```python
from ablation.ablation_test_runner import AblationTestRunner
from ablation.ablation_tester import AblationConfig

# Create runner
runner = AblationTestRunner(output_dir="./ablation_results")

# Configure ablation test
config = AblationConfig(
    collections_to_ablate=[
        "AblationLocationActivity",
        "AblationTaskActivity",
    ],
    query_limit=100,
)

# Run tests for multiple queries
results = runner.run_batch_tests(queries, config)

# Generate reports and visualizations
runner.save_results_json()
runner.save_results_csv()
runner.generate_summary_report()
runner.generate_visualizations()
```

## Demo Script

The demo script (`demo_ablation_test.py`) shows a complete workflow:

1. Generates synthetic location and task activities
2. Creates test queries with truth data
3. Runs ablation tests across all collections
4. Generates summary reports and visualizations
5. Exports results in multiple formats

Run the demo script:

```bash
python -m research.ablation.demo_ablation_test
```

## Reports and Visualizations

The framework generates several outputs:

1. **Summary Report**: Markdown file with metrics and interpretations
2. **Impact Chart**: Bar chart showing impact by collection
3. **Impact Heatmap**: Heatmap showing impact relationships between collections
4. **Precision-Recall Plot**: Scatter plot of precision vs. recall
5. **F1 Score Chart**: Bar chart of F1 scores by collection

These visualizations help identify:
- Which activity types have the greatest impact on search quality
- How collections affect each other when ablated
- Relationships between precision and recall across collections

## Architectural Considerations

This implementation follows Indaleko's architectural principles:

1. **Database Integrity**: Non-destructive collection ablation
2. **Error Handling**: Fail-safe approach with proper cleanup
3. **Data Validation**: Metrics based on ground truth data
4. **Separation of Concerns**: Clear boundaries between components

## Next Steps

1. **Comparative Analysis**: Extend the framework to compare ablation between different query types
2. **Statistical Significance**: Add statistical testing to validate impact significance
3. **Interactive Visualization**: Develop interactive visualizations for exploring results
4. **Temporal Analysis**: Add support for measuring impact over time
5. **Query Clustering**: Group queries by characteristics for more nuanced analysis
