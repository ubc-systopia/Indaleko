# Indaleko Analytics

The Indaleko Analytics package provides specialized tools for performing analytical queries against the Indaleko Unified Personal Index (UPI).

## Features

- Statistical analysis of indexed file data
- Distribution analysis by file type, size, and age
- Visualization of data patterns
- Support for specialized analytical queries
- Optimized AQL queries for ArangoDB performance

## File Statistics Tool

The File Statistics Tool (`file_statistics.py`) provides comprehensive analytics about the files indexed in the Indaleko system:

### Key Metrics

- Total object count (files and directories)
- File vs. directory distribution
- File type distribution
- File size statistics (total, average, median, min, max)
- File age distribution
- Storage trends over time

### Visualizations

- Files vs. Directories pie chart
- File type distribution bar chart
- File age distribution chart
- Average file size by age chart

## Usage

### Basic Usage

```bash
# Display basic file statistics
python -m query.analytics.file_statistics

# Generate comprehensive report with visualizations
python -m query.analytics.file_statistics --report --visualize --output ./report
```

### Options

- `--report`, `-r`: Generate a comprehensive report
- `--visualize`, `-v`: Generate visualizations
- `--output`, `-o`: Specify output directory (default: current directory)
- `--db-config`: Specify path to database configuration file

## Integration with Query CLI

The analytics features can be accessed through the Indaleko Query CLI using the `/analytics` command:

```
# First, enable analytics in the CLI
python -m query.cli --analytics

# Then use analytics commands within the CLI
Indaleko Search> /analytics files
Indaleko Search> /analytics types
Indaleko Search> /analytics ages
Indaleko Search> /analytics report --visualize --output ./reports
```

### Analytics CLI Commands

The following commands are available through the `/analytics` command:

- `/analytics stats` - Show basic file statistics summary
- `/analytics files` - Analyze file counts and sizes
- `/analytics types` - Analyze file type distribution
- `/analytics ages` - Analyze file age distribution
- `/analytics report` - Generate a comprehensive report with visualizations
- `/analytics help` - Show help information

Each command can be run with additional options:

```
# Generate visualizations
Indaleko Search> /analytics report --visualize

# Specify output directory
Indaleko Search> /analytics report --output ./my_reports

# Combine options
Indaleko Search> /analytics report --visualize --output ./my_reports
```

## Extending Analytics

You can extend the analytics capabilities by:

1. Creating new modules in the `query/analytics/` directory
2. Implementing specialized queries for different types of analysis
3. Integrating with the Query CLI through the appropriate hooks

## Performance Considerations

Analytical queries may be resource-intensive, especially on large datasets. The tools are designed to:

1. Use indexes when available
2. Implement caching for repeated queries
3. Provide progress feedback for long-running operations
4. Support batch processing for large result sets

## Requirements

- pandas
- matplotlib
- numpy

Install required packages:

```bash
pip install pandas matplotlib numpy
```
