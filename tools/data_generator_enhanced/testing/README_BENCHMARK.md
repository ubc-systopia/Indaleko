# Model-Based Data Generator Benchmark Suite

This directory contains a comprehensive benchmark suite for evaluating the performance and effectiveness of the model-based data generator across different scenarios, dataset sizes, and query patterns.

## Overview

The benchmark suite provides the following capabilities:

- **Multiple Scenarios**: Test data generation across varying dataset sizes and with different metadata focuses (storage, semantic, activity, relationships, etc.)
- **Different Generator Configurations**: Compare legacy generation approaches with model-based generation and specialized domain optimizations
- **Performance Metrics**: Measure generation time, query time, precision, recall, and F1 score across all test cases
- **Visualization**: Generate charts comparing performance across different configurations
- **Rich Reporting**: Produce detailed reports in multiple formats (Markdown, JSON, HTML, PDF)

## Running the Benchmarks

### Quick Start

To run the benchmarks with default settings:

```bash
# On Linux/macOS
./run_benchmark.sh

# On Windows
run_benchmark.bat
```

### Configuration Options

The benchmark suite supports the following command-line options:

| Option | Description |
|--------|-------------|
| `--config FILE` | Path to a JSON configuration file |
| `--output-dir DIR` | Directory to save benchmark results (default: ./benchmark_results) |
| `--repeat N` | Number of times to repeat each benchmark (default: 1) |
| `--scenarios S1 S2...` | Specific scenarios to run (default: all) |
| `--generators G1 G2...` | Specific generators to use (default: all) |
| `--small-only` | Only run small dataset scenarios |
| `--skip-large` | Skip large dataset scenarios |
| `--report-formats FMT1 FMT2...` | Report formats to generate (md, json, csv, html, pdf) |
| `--no-charts` | Skip chart generation |
| `--domain-specific` | Run only domain-specific scenarios |
| `--compare-legacy` | Run only legacy and model-based generators for comparison |
| `--verbose, -v` | Enable verbose logging |

### Example Usage

Run a small benchmark comparing legacy and model-based approaches:

```bash
./run_benchmark.sh --small-only --compare-legacy
```

Run domain-specific benchmarks with detailed reporting:

```bash
./run_benchmark.sh --domain-specific --report-formats md json html
```

Use a custom configuration file:

```bash
./run_benchmark.sh --config config/cross_domain_benchmark.json
```

## Custom Configurations

You can create custom benchmark configurations by defining a JSON configuration file with the following structure:

```json
{
  "description": "Custom Benchmark Configuration",
  "scenarios": [
    {
      "name": "custom_scenario",
      "description": "Custom test scenario",
      "scale_factor": 0.5,
      "storage_count": 500,
      "semantic_count": 400,
      "activity_count": 300,
      "relationship_count": 800,
      "queries": [
        "Find all PDF files",
        "Show me files modified last week"
      ]
    }
  ],
  "generators": [
    {
      "name": "legacy",
      "description": "Legacy generation approach",
      "model_based": false,
      "use_model_templates": false
    },
    {
      "name": "model_based_templates",
      "description": "Model-based generation with templates",
      "model_based": true,
      "use_model_templates": true
    }
  ],
  "repeat": 1,
  "chart_format": ["png", "svg"],
  "report_formats": ["md", "json", "html"]
}
```

See the `config/cross_domain_benchmark.json` file for a more comprehensive example.

## Benchmark Results

Benchmark results are saved to the specified output directory with the following structure:

```
benchmark_results/
  ├── benchmark_TIMESTAMP/
  │   ├── benchmark_results.json    # Raw benchmark data
  │   ├── benchmark_results.csv     # CSV summary of results
  │   ├── benchmark_summary.json    # Analyzed summary data
  │   ├── benchmark_report.md       # Markdown report
  │   ├── benchmark_report.html     # HTML report (if requested)
  │   ├── benchmark_report.pdf      # PDF report (if requested)
  │   └── charts/                   # Generated charts
  │       ├── generation_time.png
  │       ├── precision_recall.png
  │       ├── f1_scores.png
  │       └── query_time.png
```

## Benchmark Components

The benchmark suite consists of the following key components:

- **BenchmarkSuite**: Main class that orchestrates the benchmark process
- **GenerationController**: Generates datasets based on configuration parameters
- **ModelBasedTestRunner**: Executes test queries and calculates metrics
- **SearchMetrics**: Calculates precision, recall, and F1 score for search results
- **ModelBasedQueryGenerator**: Generates AQL queries from natural language

## Extending the Benchmark Suite

To add new scenarios or generator configurations:

1. Create a custom configuration file with your additions
2. Use the `--config` option to specify your configuration file

Alternatively, you can modify the `DEFAULT_SCENARIOS` and `DEFAULT_GENERATORS` lists in `benchmark.py`.

## Dependencies

- **Required**: Python 3.9+, numpy, matplotlib
- **Optional**: markdown (for HTML reports), weasyprint (for PDF reports)

To install optional dependencies:

```bash
pip install markdown weasyprint
```

## Troubleshooting

If you encounter any issues with the benchmark suite:

1. Use the `--verbose` option to enable detailed logging
2. Check the `benchmark.log` file for error messages
3. Try running with `--small-only` to test with minimal data
4. Ensure your database connection is properly configured for query execution

## Report Interpretation

The benchmark reports provide the following key metrics:

- **Generation Time**: How long it takes to generate the dataset
- **Records**: Number of records generated (storage, semantic, activity, relationship)
- **Precision**: Percentage of returned results that are relevant
- **Recall**: Percentage of relevant records that are returned
- **F1 Score**: Harmonic mean of precision and recall
- **Query Time**: Time required to execute the test queries
