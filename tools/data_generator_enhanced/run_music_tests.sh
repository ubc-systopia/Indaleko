#!/bin/bash

# Run Music Activity Generator Tests Script
# This script runs both unit tests and database integration tests for the MusicActivityGeneratorTool

# Exit on error
set -e

# Determine the project root
PROJECT_ROOT=$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")
echo "Project root: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

# Activate virtual environment if it exists
if [ -d ".venv-linux-python3.13" ]; then
    echo "Activating virtual environment..."
    source .venv-linux-python3.13/bin/activate
elif [ -d ".venv-macos-python3.12" ]; then
    echo "Activating virtual environment..."
    source .venv-macos-python3.12/bin/activate
fi

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# First run the unit tests
echo "Running Music Activity Generator unit tests..."
python -m tools.data_generator_enhanced.testing.test_music_activity_generator

# Run the database integration tests
echo "Running Music Activity Generator database integration tests..."
python -m tools.data_generator_enhanced.testing.test_music_db_integration

echo "All tests completed."