#!/bin/bash
# Run location metadata generator tests

# Get directory where script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$(dirname "$DIR")")"

# Make sure we're in the root directory
cd "$ROOT_DIR"

# Set environment variable for imports
export INDALEKO_ROOT="$ROOT_DIR"
export PYTHONPATH="$ROOT_DIR"

# Run unit tests for location generator
echo "Running location generator tests..."
python -m tools.data_generator_enhanced.testing.test_location_generator

# Run database integration tests
echo "Running location database integration tests..."
echo "Skipping DB integration test for now - will be implemented in next phase"

echo "All tests completed."