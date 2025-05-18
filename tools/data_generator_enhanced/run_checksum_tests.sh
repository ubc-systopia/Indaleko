#!/bin/bash

# Run checksum generator tests
# This script runs the unit tests and database integration tests for the checksum generator

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Set the Indaleko root directory
export INDALEKO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$INDALEKO_ROOT"

# Run the unit tests
echo "Running checksum generator unit tests..."
python -m tools.data_generator_enhanced.testing.test_checksum_generator

# Run database integration tests
echo "Running checksum generator database integration tests..."
python -m tools.data_generator_enhanced.testing.test_checksum_db_integration --debug

# Display completion message
echo "Checksum generator tests completed."