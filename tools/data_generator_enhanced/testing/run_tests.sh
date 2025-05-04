#!/bin/bash
# Run tests for the model-based data generator benchmark suite

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Go to the project root
PROJECT_ROOT="$SCRIPT_DIR/../../../"

# Activate virtual environment if it exists
if [ -f "$PROJECT_ROOT/.venv-linux-python3.13/bin/activate" ]; then
    source "$PROJECT_ROOT/.venv-linux-python3.13/bin/activate"
elif [ -f "$PROJECT_ROOT/.venv-macos-python3.12/bin/activate" ]; then
    source "$PROJECT_ROOT/.venv-macos-python3.12/bin/activate"
fi

# Set PYTHONPATH to include the project root
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Run the tests
echo "Running unit tests for the benchmark suite..."
python -m unittest $SCRIPT_DIR/test_benchmark.py

echo "Running integration tests for the benchmark suite..."
python -m unittest $SCRIPT_DIR/test_integration.py

# Check if any tests failed
if [ $? -eq 0 ]; then
    echo "All tests passed!"
    exit 0
else
    echo "Some tests failed. Please check the output above for details."
    exit 1
fi
