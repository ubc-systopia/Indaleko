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

### Phase 1: Core Framework (Completed)

- [x] Analyze existing data_generator implementation
- [x] Design enhanced architecture using CLI template pattern
- [x] Create initial framework with handler mixin
- [x] Implement configuration system (JSON-based)
- [x] Add statistical distribution support for metadata values
- [x] Create logging and testing metrics system

### Phase 2: Metadata Generation Modules (Complete)

- [x] Create modular metadata generators for each record type:
  - [x] Storage metadata (POSIX attributes)
  - [x] Semantic metadata (MIME types, checksums, etc.)
  - [x] Activity context (location, music, temperature, etc.)
  - [x] Machine configuration (desktop, laptop, mobile devices)
- [x] Implement relationship pattern generation
- [x] Create "truth set" generation with known query matches
- [x] Support for data volume scaling (hundreds to millions of records)

### Phase 3: Query Generation and Testing (Current)

- [ ] Create improved AQL query generation module
  - [ ] Template-based approach for valid AQL syntax
  - [ ] Parameter substitution for dynamic values
- [ ] Implement automated testing workflows
  - [ ] Multiple query patterns per test run
  - [ ] Comprehensive metrics (precision, recall, latency)
  - [ ] Result visualization and reporting
- [ ] Add regression testing capabilities

### Phase 4: CI/CD Integration (In Progress)

- [x] Create command-line interface for headless operation
- [x] Add configuration templates for common testing scenarios (scenarios.py)
- [ ] Implement result reporting for CI/CD pipelines
- [ ] Create performance comparison framework
- [ ] Document integration patterns for development workflows

## Usage

The tool provides a comprehensive command-line interface via the `generate_data.py` script:

```bash
# Basic usage with default scenario
python generate_data.py

# Generate a specific scenario using a configuration file
python generate_data.py --config config/model_generation.json

# Generate with model-based tools
python generate_data.py --model-based

# Generate with relationship strategy
python generate_data.py --relationship-strategy storage_semantic_focused

# Generate with activity focus
python generate_data.py --activity-focus recent

# Generate with activity sequences
python generate_data.py --activity-sequences --activity-sequence-count 20

# Configure content extraction for semantic metadata
python generate_data.py --content-extraction 0.8

# Specify MIME types to prioritize
python generate_data.py --mime-types "application/pdf,image/jpeg,video/mp4"

# Export statistics and truth dataset
python generate_data.py --export-statistics "stats.json" --export-truth "truth.json"

# Run tests after generation
python generate_data.py --run-tests --report-path "./test_results"

# Customize metadata types
python generate_data.py --metadata-types "storage,semantic,activity"

# Customize dataset size
python generate_data.py --scale-factor 2.0 --truth-factor 0.05

# Verbose output
python generate_data.py -v
```

### Available Scenarios

- **basic** - Small dataset for quick testing
- **realistic** - Medium-sized dataset with balanced distribution
- **large** - Large dataset for performance testing
- **document_focused** - Focus on document formats for content search
- **activity_focused** - Focus on activity patterns for temporal queries
- **multi_device** - Simulate usage across multiple devices
- **relationship_focused** - Complex object relationships for graph queries
- **minimal** - Minimal dataset for development testing

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
│   ├── ACTIVITY_GENERATOR.md
│   ├── MACHINE_CONFIG_GENERATOR.md
│   ├── RELATIONSHIP_GENERATOR.md
│   ├── SCHEMA_VALIDATION.md
│   ├── base.py
│   ├── storage.py
│   ├── semantic.py
│   ├── activity.py
│   ├── relationships.py
│   └── machine_config.py
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

## Model-Based Generation

The enhanced data generator includes support for model-based generation, which uses Indaleko's actual data models to generate more realistic and consistent metadata:

### Key Features

- **Integration with Core Models**: Uses IndalekoActivityDataModel, IndalekoObjectDataModel, IndalekoRelationshipDataModel, and other core Indaleko models
- **Improved Cross-Domain Relationships**: Creates more meaningful relationships between different domains (storage, semantic, activity)
- **Realistic Activity Sequences**: Generates temporal patterns of related activities
- **Strategic Relationship Generation**: Supports different relationship strategies:
  - `balanced`: Even distribution across all domains
  - `storage_semantic_focused`: Prioritizes relationships between files and their semantic metadata
  - `activity_focused`: Prioritizes activity-related relationships
- **Activity Focus Strategies**:
  - `balanced`: Random selection of objects for activities
  - `recent`: Focus on recently modified objects
  - `popular`: Focus on objects that would be frequently accessed
  - `diverse`: Even distribution across different file types
- **Content Extraction**: Configurable content extraction for semantic metadata
- **Time Distribution Patterns**: Realistic temporal patterns for activities

### Command-Line Options

The model-based generation features are exposed through the following CLI options:

```
--model-based                     Use model-based generation (uses actual data models)
--relationship-strategy STRATEGY  Strategy for relationship generation pattern
--activity-focus FOCUS            Focus strategy for activity generation
--activity-sequences              Generate activity sequences
--activity-sequence-count COUNT   Number of activity sequences to generate
--content-extraction PERCENTAGE   Percentage of semantic objects with extracted content
--mime-types TYPES                Comma-separated list of mime types to prioritize
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
