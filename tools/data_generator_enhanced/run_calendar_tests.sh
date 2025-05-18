#!/bin/bash

# Run calendar event generator tests
# This script runs the database integration tests for the calendar event generator

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Set the Indaleko root directory
export INDALEKO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$INDALEKO_ROOT"

# Run the standard tests
echo "Running calendar event basic tests..."
python -m tools.data_generator_enhanced.testing.test_calendar_event_generator

# Run database integration tests
echo "Running calendar event database integration tests..."
python -m tools.data_generator_enhanced.testing.test_calendar_db_integration --debug

# Display completion message
echo "Calendar event tests completed."