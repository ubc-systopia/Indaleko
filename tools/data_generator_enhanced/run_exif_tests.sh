#!/bin/bash
# Run tests for the enhanced EXIF metadata generator

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Ensure we're in the project root
cd $(dirname $0)/../..

echo "Running EXIF Generator Tests..."
python -m tools.data_generator_enhanced.testing.test_exif_generator

echo "Running EXIF Generator Directly..."
python -m tools.data_generator_enhanced.agents.data_gen.tools.exif_generator

echo "Tests completed."