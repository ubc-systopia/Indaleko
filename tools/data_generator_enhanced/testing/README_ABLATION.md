# Indaleko Ablation Testing Framework

This document provides detailed instructions for running ablation tests to measure the impact of different activity metadata types on query precision and recall.

## Overview

The ablation testing framework allows you to systematically test how removing specific metadata collections affects query results. This helps quantify the contribution of each activity data source to search effectiveness.

## Components

The framework consists of the following components:

1. **ClusterGenerator (cluster_generator.py)**
   - Manages activity source grouping into experimental and control clusters
   - Implements 4/2 split of sources (4 experimental, 2 control)
   - Supports randomized or balanced cluster generation

2. **TruthDataTracker (truth_data_tracker.py)**
   - SQLite-based system for tracking test data and results
   - Records precision, recall, F1, and impact metrics
   - Generates comprehensive reports

3. **QueryGenerator (query_generator_enhanced.py)**
   - Creates natural language queries targeting specific activity types
   - Supports template-based and LLM-based query generation
   - Balances experimental and control metadata categories

4. **AblationIntegrationTest (ablation_integration_test.py)**
   - End-to-end test pipeline for a single cluster
   - Handles database setup, data generation, query execution, and result reporting
   - Provides detailed metrics on metadata impact

5. **Fixed Query Execution (ablation_execute_query.py)**
   - Handles LIMIT statements properly to avoid artificially restricted results
   - Ensures accurate recall metrics for large collections

## Quick Start

To run a simple ablation test with default settings:

```bash
# On Linux/macOS
./run_ablation_test.sh

# On Windows
run_ablation_test.bat
```

This will:
1. Generate a balanced cluster with 4 experimental and 2 control sources
2. Create 10 test queries (5 experimental, 5 control)
3. Generate 100 test data records
4. Run ablation tests for each source
5. Generate a comprehensive report

## Advanced Usage

The test runner supports several command-line options:

```bash
python run_ablation_integration_test.py [options]
```

Options:
- `--seed INT`: Random seed for reproducibility (default: 42)
- `--dataset-size INT`: Number of test data records (default: 100)
- `--num-queries INT`: Number of test queries (default: 10)
- `--output-dir DIR`: Output directory (default: ablation_results)
- `--truncate-collections`: Truncate collections before testing
- `--use-llm`: Use LLM for query generation
- `--llm-provider STR`: LLM provider (openai or anthropic)
- `--debug`: Enable debug logging

Example with custom settings:

```bash
python run_ablation_integration_test.py --seed 123 --dataset-size 200 --num-queries 20 --output-dir my_results --use-llm --llm-provider anthropic
```

## Understanding Results

The test generates several output files:

1. **ablation_results.db**: SQLite database with complete test data
2. **ablation_report_{timestamp}.md**: Comprehensive markdown report
3. **ablation_summary_{timestamp}.txt**: Simple text summary
4. **ablation_test_{timestamp}.log**: Detailed log file

The report includes:
- Source impact metrics (precision, recall, F1, impact)
- Cluster configuration details
- Query details and results
- Overall conclusions about metadata importance

## Impact Metric

The Impact metric is defined as:
```
Impact = 1.0 - F1
```

Where F1 is the harmonic mean of precision and recall:
```
F1 = 2 * (precision * recall) / (precision + recall)
```

A higher Impact value indicates that ablating a collection has a greater negative effect on query results, suggesting that the collection is more important.

## Customizing the Framework

### Adding New Activity Sources

To add a new activity source:

1. Update `ClusterGenerator.__init__()` with a new `ActivitySource` instance
2. Add the collection name to `AblationIntegrationTest.reset_database()`
3. Add query templates to `QueryGenerator._initialize_templates()`

### Modifying Test Protocol

To change the test protocol:

1. Edit `AblationIntegrationTest.run_ablation_tests()` to modify the test sequence
2. Add new metrics to `TruthDataTracker.add_ablation_result()`
3. Update report generation in `TruthDataTracker.generate_report()`

## Extending to Multiple Clusters

The current implementation tests a single cluster. To extend to multiple clusters:

1. Modify `run_ablation_integration_test.py` to generate multiple clusters
2. Update `AblationIntegrationTest` to loop through all clusters
3. Enhance report generation to compare results across clusters

## Troubleshooting

If you encounter issues:

1. **Database connection error**: Ensure ArangoDB is running and accessible
2. **Missing collections**: Run `python -m db/db_config reset` to reset the database
3. **LLM errors**: Check API key configuration in `config/openai-key.ini`
4. **Memory issues**: Reduce `dataset-size` for large collections

## Additional Information

For more details on the ablation study design, see `doc/AblationDesign.md`.

For questions or issues, please file a GitHub issue or contact the project maintainers.