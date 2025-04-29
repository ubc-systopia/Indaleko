# Semantic Extractor Performance Monitoring

This module provides a comprehensive framework for monitoring and evaluating the performance of Indaleko's semantic metadata extractors.

> **Design Note**: The current implementation uses a custom machine identification mechanism rather than Indaleko's relationship model. Future versions should leverage the device-file relationship (UUID: f3dde8a2-cff5-41b9-bd00-0f41330895e1) defined in storage/i_relationship.py.
>
> **IMPORTANT**: The storage recorders MUST add this relationship between devices and files. This is critical because semantic extractors should ONLY run on the machine where the data is physically stored. This relationship is needed to:
> 1. Enforce locality constraints for extraction (preventing inefficient network transfers)
> 2. Track which machine performed extraction for a given file
> 3. Enable performance comparisons across different machine configurations
> 4. Properly route extraction tasks in distributed environments
>
> Implementing this relationship in storage recorders would benefit not just performance monitoring but the entire semantic extraction pipeline.

## Overview

The semantic extractor performance monitoring system allows you to:

1. **Track real-time performance metrics** for metadata extraction operations
2. **Run controlled experiments** to evaluate extractor performance characteristics
3. **Generate performance reports** with visualizations and analysis
4. **Project metadata coverage growth** over time
5. **Optimize database utilization** based on performance insights

## Components

### Performance Monitor (`performance_monitor.py`)

The core monitoring system that integrates with the existing Indaleko performance framework:

- `SemanticExtractorPerformance`: Singleton class for monitoring extraction operations
- `monitor_semantic_extraction`: Decorator for adding monitoring to extractor methods

```python
from semantic.performance_monitor import monitor_semantic_extraction

@monitor_semantic_extraction(extractor_name="MyExtractor")
def process_file(file_path):
    # Your extraction code here
    return result
```

### Experiment Driver (`experiment_driver.py`)

Framework for running controlled experiments with semantic extractors:

- `SemanticExtractorExperiment`: Class for running various experiment types
  - Throughput experiments
  - File type comparisons
  - Size scaling analysis
  - Coverage projection

```python
# Run a throughput experiment
experiment = SemanticExtractorExperiment()
results = experiment.run_throughput_experiment('mime', sample_size=100)

# Run all experiments
experiment.run_all_experiments()
```

## Usage

### Basic Monitoring

```python
from semantic.performance_monitor import SemanticExtractorPerformance, monitor_semantic_extraction
from semantic.collectors.mime.mime_collector import IndalekoSemanticMimeType

# Add decorator to extraction function
@monitor_semantic_extraction(extractor_name="MimeDetection")
def process_file(file_path):
    detector = IndalekoSemanticMimeType()
    return detector.detect_mime_type(file_path)

# Process files
results = []
for file in files:
    results.append(process_file(file))

# Get performance statistics
monitor = SemanticExtractorPerformance()
stats = monitor.get_stats()
print(f"Files processed: {stats['total_files']}")
print(f"Average time per file: {stats['avg_processing_time']:.4f} seconds")
print(f"Processing rate: {stats['files_per_second']:.2f} files/second")
```

### Running Experiments

```bash
# Run all experiments
python -m semantic.experiments.experiment_driver --all --sample-size 100

# Run throughput experiment for MIME detector
python -m semantic.experiments.experiment_driver --throughput --mime --sample-size 200

# Run file type comparison for all extractors
python -m semantic.experiments.experiment_driver --file-types --all-extractors

# Run size scaling experiment with database recording disabled
python -m semantic.experiments.experiment_driver --size-scaling --checksum --no-db-record
```

### Example Usage

See `semantic/examples/mime_monitor_example.py` for a complete example:

```bash
# Process a directory recursively and show performance stats
python -m semantic.examples.mime_monitor_example --dir /path/to/files --recursive --stats

# Process and save results to JSON
python -m semantic.examples.mime_monitor_example --dir /path/to/files --output results.json
```

## Experiment Types

### Throughput Experiment

Measures the raw processing speed of each extractor:
- Files processed per second
- Bytes processed per second
- CPU and memory utilization

### File Type Comparison

Compares performance across different file types:
- Processing time by file type
- Resource usage patterns
- Success rates and error types

### Size Scaling Analysis

Evaluates how performance scales with file size:
- Processing time versus file size
- Bandwidth scaling characteristics
- Resource usage growth patterns

### Coverage Projection

Projects metadata coverage growth over time:
- Time to reach coverage goals
- Database growth projections
- Resource requirements estimation

## Performance Metrics

The framework tracks a comprehensive set of metrics:

- **Temporal Metrics**
  - Total processing time
  - Average time per file
  - Time per MB of data

- **Throughput Metrics**
  - Files per second
  - MB per second
  - Operations per second

- **Resource Utilization**
  - CPU usage (user and system time)
  - Memory usage
  - I/O operations

- **File Type Statistics**
  - Performance by MIME type
  - Size distribution analysis
  - Error rates by file type

## Integration with Database

Performance data is stored in the `Performance` collection in ArangoDB, using the same infrastructure as other Indaleko performance metrics:

- `Record`: Standard Indaleko record structure
- `MachineConfigurationId`: Machine configuration identifier
- `StartTimestamp` and `EndTimestamp`: Operation timing
- `ElapsedTime`: Total operation time
- `UserCPUTime` and `SystemCPUTime`: CPU resource usage
- `ActivityStats`: Additional metrics and metadata

## Requirements

- `python-magic`: For MIME type detection
- `matplotlib`, `numpy`, `pandas`: For analysis and visualization
- `psutil`: For resource monitoring
- `tqdm`: For progress visualization

## Future Enhancements

- **Storage recorder device-file relationship**: Storage recorders need to implement the device-file relationship (UUID: f3dde8a2-cff5-41b9-bd00-0f41330895e1) to properly associate files with their physical storage locations.
- **Relationship-based machine identification**: Update the system to use Indaleko's device-file relationship rather than custom machine identification.
- **Extraction locality enforcement**: Use relationships to ensure semantic extractors only run on machines where data is physically stored.
- **Multi-process testing**: Add scalability analysis with multiple worker processes.
- **Distributed extraction coordination**: Support proper task routing and performance monitoring across nodes based on file location relationships.
- **Automated regression testing**: Add continuous monitoring for performance changes.
- **Machine learning for prediction**: Build models to predict extraction performance for new files.
- **Integration with query performance**: Connect semantic extraction costs with query performance benefits.
- **GitHub issue integration**: Use GitHub issues for tracking performance issues and improvements (potential integration with github-mcp-server).
