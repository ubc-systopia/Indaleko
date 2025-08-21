# Enhanced Data Generator for Indaleko

This tool provides a comprehensive framework for generating synthetic metadata records to test and validate Indaleko's search capabilities. It builds on the original data_generator but adds improved configurability, automatic testing, and CI/CD integration.

## Key Features

- **Flexible Metadata Generation**: Creates realistic synthetic records across all Indaleko collection types
- **Statistical Modeling**: Supports configurable statistical distributions for data attributes
- **Relationship Patterns**: Generates realistic relationships between entities
- **Automated Testing**: Measures precision, recall, and other metrics for search results
- **CI/CD Integration**: Runs headless with configuration files for automated validation
- **Performance Tracking**: Leverages Indaleko's existing performance measurement framework
- **Test Query Library**: Includes a diverse set of natural language queries organized by type

## Development Plan

### Phase 1: Core Framework (Current)

- [x] Analyze existing data_generator implementation
- [x] Design enhanced architecture using CLI template pattern
- [ ] Create initial framework with handler mixin
- [ ] Implement configuration system (JSON-based)
- [ ] Add statistical distribution support for metadata values
- [ ] Create logging and testing metrics system

### Phase 2: Metadata Generation Modules

- [ ] Create modular metadata generators for each record type:
  - [ ] Storage metadata (POSIX attributes)
  - [ ] Semantic metadata (MIME types, checksums, etc.)
  - [ ] Activity context (location, music, temperature, etc.)
  - [ ] Machine configuration
- [ ] Implement relationship pattern generation
- [ ] Create "truth set" generation with known query matches
- [ ] Support for data volume scaling (hundreds to millions of records)

### Phase 3: Query Generation and Testing

- [ ] Create improved AQL query generation module
  - [ ] Template-based approach for valid AQL syntax
  - [ ] Parameter substitution for dynamic values
- [ ] Implement automated testing workflows
  - [ ] Multiple query patterns per test run
  - [ ] Comprehensive metrics (precision, recall, latency)
  - [ ] Result visualization and reporting
- [ ] Add regression testing capabilities

### Phase 4: CI/CD Integration

- [ ] Create command-line interface for headless operation
- [ ] Add configuration templates for common testing scenarios
- [ ] Implement result reporting for CI/CD pipelines
- [ ] Create performance comparison framework
- [ ] Document integration patterns for development workflows

## Usage

```bash
# Run with default configuration
python -m tools.data_generator_enhanced --config default

# Generate only specific metadata types
python -m tools.data_generator_enhanced --metadata-types storage,semantic

# Run with custom scaling factors
python -m tools.data_generator_enhanced --scale-factor 10 --truth-factor 0.1

# Run in test mode for CI/CD integration
python -m tools.data_generator_enhanced --headless --report-path ./test_results
```

## Directory Structure

```
tools/data_generator_enhanced/
├── __init__.py
├── __main__.py
├── cli.py
├── handler_mixin.py
├── README.md
├── config/
│   ├── default.json
│   └── distributions.json
├── generators/
│   ├── __init__.py
│   ├── base.py
│   ├── storage.py
│   ├── semantic.py
│   ├── activity.py
│   └── relationships.py
├── testing/
│   ├── __init__.py
│   ├── query_generator.py
│   ├── metrics.py
│   └── reporter.py
└── utils/
    ├── __init__.py
    ├── statistical.py
    └── dataset.py
```

## Configuration Format

The tool uses a JSON-based configuration format that supports:

```json
{
  "metadata": {
    "total_records": 10000,
    "truth_records": 50,
    "distributions": {
      "file_sizes": {"type": "lognormal", "mu": 8.5, "sigma": 2.0},
      "modification_times": {"type": "normal", "mean": "now-30d", "std": "15d"},
      "file_extensions": {"type": "weighted", "values": {".pdf": 0.2, ".docx": 0.3, ".txt": 0.5}}
    }
  },
  "query_patterns": [
    {
      "description": "Find documents modified in the last week",
      "nl_query": "Show me documents I've worked on in the last week",
      "expected_truth": 15
    },
    {
      "description": "Find large video files from a specific location",
      "nl_query": "Find video files larger than 1GB from my San Francisco trip",
      "expected_truth": 8
    }
  ],
  "reporting": {
    "format": "json",
    "metrics": ["precision", "recall", "latency", "result_count"]
  }
}
```

## Integration with Existing Codebase

This tool follows Indaleko's architectural principles:
- Uses the CLI template infrastructure for consistent command-line handling
- Leverages the performance tracking framework for automatic metrics
- Follows the separation of concerns principle with modular components
- Uses the standard configuration and logging mechanisms

## Best Practices

When extending the tool:
1. Add new metadata generators in the generators/ directory
2. Create corresponding test cases in testing/
3. Update configuration templates to include new options
4. Document new features in this README.md
