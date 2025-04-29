#!/bin/bash

# Run the recommendation integration test with Assistant API
echo "Running Recommendation Engine Integration with Assistant API Test..."

# Determine the Python command to use
if command -v python3 &> /dev/null; then
    PYTHON=python3
else
    PYTHON=python
fi

# Activate virtual environment if it exists
if [ -d ".venv-linux-python3.13" ]; then
    source .venv-linux-python3.13/bin/activate
elif [ -d ".venv-macos-python3.12" ]; then
    source .venv-macos-python3.12/bin/activate
elif [ -d ".venv-win32-python3.12" ]; then
    source .venv-win32-python3.12/bin/activate
fi

# Run the test script
$PYTHON query/assistants/test_recommendation_integration.py "$@"

# Print a message on completion
echo "Test completed. See output above for details."
