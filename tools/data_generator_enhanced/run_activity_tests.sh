#!/bin/bash
# Run activity semantic attributes tests

# Get directory where script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$(dirname "$DIR")")"

# Make sure we're in the root directory
cd "$ROOT_DIR"

# Set environment variable for imports
export INDALEKO_ROOT="$ROOT_DIR"
export PYTHONPATH="$ROOT_DIR"

# Run semantic attributes test
echo "Running activity semantic attribute tests..."
python -m tools.data_generator_enhanced.testing.test_activity_semantic_attributes

# Run integrated database test with activities
echo "Running integrated database test with activities..."
python -m tools.data_generator_enhanced.testing.test_db_integration --dataset-size 20 --output ./tools/data_generator_enhanced/results/activity_db_integration_results.json

echo "All tests completed."