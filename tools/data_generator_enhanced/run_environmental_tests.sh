#!/bin/bash
# Run tests for the Environmental Metadata Generator
# This script executes unit tests and database integration tests
# for the environmental metadata generator

# Ensure we're in the right directory
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

# Use the same Python that works with our manual tests
echo "========================================================"
echo "Running unit tests for Environmental Metadata Generator"
echo "========================================================"
cd "$BASE_DIR/../.."
python -m tools.data_generator_enhanced.testing.test_environmental_metadata_generator

# Return code from unit tests
UNIT_RESULT=$?

echo "========================================================"
echo "Running database integration tests for Environmental Metadata Generator"
echo "========================================================"
python -m tools.data_generator_enhanced.testing.test_environmental_db_integration

# Return code from integration tests
DB_RESULT=$?

echo "========================================================"
echo "Test Results:"
echo "Unit tests: $([ $UNIT_RESULT -eq 0 ] && echo 'PASSED' || echo 'FAILED')"
echo "DB Integration tests: $([ $DB_RESULT -eq 0 ] && echo 'PASSED' || echo 'FAILED')"
echo "========================================================"

# Exit with non-zero if any test failed
if [ $UNIT_RESULT -ne 0 ] || [ $DB_RESULT -ne 0 ]; then
    exit 1
fi

exit 0