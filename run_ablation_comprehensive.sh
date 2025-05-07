#!/bin/bash
# Comprehensive ablation test runner
# Project Indaleko
# Copyright (C) 2024-2025 Tony Mason

set -e  # Exit on error

echo "Starting comprehensive ablation test process..."

# Reset the database to ensure clean test data
echo "Resetting database..."
python -m db.db_config reset

# Initialize the database structure properly
echo "Initializing database structure..."
python -m db.db_setup check

# Make sure output directory exists
mkdir -p ./ablation_results

# Generate test data with both positive and negative examples
echo "Generating test data using Indaleko data models..."
python tools/data_generator_enhanced/testing/generate_ablation_test_data_model.py --positive-count 5 --negative-count 45 --output-dir ./ablation_results

# Run the fixed comprehensive ablation test
echo "Running comprehensive ablation test..."
python test_ablation_comprehensive_fixed.py --dataset-size 50 --output-dir ./ablation_results

echo "Ablation test complete! Results are in the ablation_results directory."
echo "To visualize the results, check the CSV and summary files in that directory."

# Optional: Create a simple summary of the results
echo "Generating summary report..."
latest_summary=$(ls -t ablation_results/ablation_summary_* 2>/dev/null | head -1)

if [ -f "$latest_summary" ]; then
    echo "Latest summary: $latest_summary"
    echo "Summary Results:"
    echo "================"
    cat "$latest_summary" | grep -A 4 "Collection Impact Metrics" | head -15
else
    echo "No summary file found."
fi

echo "Ablation testing completed."