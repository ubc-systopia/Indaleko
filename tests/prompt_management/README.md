# Prompt Management System Performance Benchmarks

This directory contains tools for benchmarking the performance of the Indaleko Prompt Management System (PMS). The benchmarks measure various aspects of the system's performance, including token optimization effectiveness, verification speed, caching efficiency, and overall response time.

## Overview

The benchmark suite evaluates the following aspects of the PMS:

1. **Token Optimization:** Measures how effectively different optimization strategies reduce token counts
2. **Verification Performance:** Tests the speed and effectiveness of prompt verification at different levels
3. **Caching Performance:** Evaluates the time savings achieved through caching
4. **Response Time:** Compares response times with and without the guardian
5. **Memory Usage:** Measures memory consumption of different components
6. **Template Performance:** Tests template-based prompt creation efficiency

## Running Benchmarks

You can run the benchmarks using the provided wrapper script:

```bash
python run_prompt_benchmarks.py [OPTIONS]
```

### Command-Line Options

- `--output-dir DIR`: Directory to save benchmark results (default: "./benchmark_results")
- `--repeats N`: Number of repetitions for each test (default: 5)
- `--providers PROVIDER [PROVIDER ...]`: LLM providers to test (default: "openai")
  - Available providers: "openai", "anthropic", "gemma", "google"
- `--use-db`: Use database for templates and caching
- `--skip-token-optimization`: Skip token optimization benchmarks
- `--skip-verification`: Skip verification benchmarks
- `--skip-caching`: Skip caching benchmarks
- `--skip-response-time`: Skip response time benchmarks
- `--skip-memory`: Skip memory benchmarks
- `--skip-templates`: Skip template benchmarks

### Examples

Run all benchmarks with default settings:
```bash
python run_prompt_benchmarks.py
```

Run with specific providers and more repeats:
```bash
python run_prompt_benchmarks.py --providers openai anthropic --repeats 10
```

Run only token optimization and template benchmarks:
```bash
python run_prompt_benchmarks.py --skip-verification --skip-caching --skip-response-time --skip-memory
```

## Benchmark Results

The benchmark results are saved in the specified output directory (default: "./benchmark_results") with the following files:

1. `benchmark_results_TIMESTAMP.json`: JSON file containing all raw results data
2. Visualization files:
   - `token_optimization_TIMESTAMP.png`: Token optimization effectiveness charts
   - `verification_performance_TIMESTAMP.png`: Verification performance charts
   - `caching_performance_TIMESTAMP.png`: Caching performance charts
   - `response_time_TIMESTAMP.png`: Response time comparison charts
   - `memory_usage_TIMESTAMP.png`: Memory usage charts
   - `template_performance_TIMESTAMP.png`: Template performance charts
   - `summary_TIMESTAMP.png`: Overall summary chart

## Interpreting Results

### Token Optimization

The token optimization charts show the percentage of tokens saved by different optimization strategies across various prompt types. Higher percentages indicate more effective optimization strategies.

### Verification Performance

The verification performance charts show the execution time and acceptance rate of different verification levels. This helps identify the trade-off between strictness and performance.

### Caching Performance

The caching performance charts compare cache miss vs. hit times and show time savings achieved through caching. This demonstrates the efficiency of the two-tier caching system.

### Response Time

The response time charts compare response times with and without the guardian, showing the overhead introduced by the prompt management system.

### Memory Usage

The memory usage charts show the memory consumption of different components and their growth during operations.

### Template Performance

The template performance charts compare creation times and token savings of regular vs. optimized template-based prompts.

## Adding Custom Benchmarks

To add custom benchmarks or test cases:

1. Modify `benchmark_performance.py` to add new test prompts, templates, or benchmark methods.
2. Run the benchmarks with your custom configurations.

## Troubleshooting

If you encounter errors while running the benchmarks:

1. **API Key Issues**: Ensure the required API keys for the tested providers are set in your environment.
2. **Database Connection Issues**: If using `--use-db`, verify that the database connection is configured correctly.
3. **Missing Dependencies**: Install required dependencies:
   ```bash
   pip install matplotlib numpy
   ```
4. **Log Output**: Check the console output for detailed error messages and warnings.

## Performance Tuning Recommendations

Based on benchmark results, consider the following optimizations:

1. **Token Optimization**: Choose optimization strategies based on the token savings vs. execution time trade-off.
2. **Verification Level**: Adjust verification levels based on the security requirements and performance constraints.
3. **Caching Strategy**: Configure cache TTLs based on your usage patterns and response time requirements.
4. **Template Usage**: Use templates with optimization for frequently used prompt patterns.