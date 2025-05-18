#!/bin/bash
# Run the ablation integration test with default settings

# Set the Indaleko root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export INDALEKO_ROOT="$SCRIPT_DIR"

# Activate the appropriate virtual environment if it exists
if [ -d "${SCRIPT_DIR}/.venv-linux-python3.13" ]; then
    echo "Activating Linux Python 3.13 virtual environment..."
    source "${SCRIPT_DIR}/.venv-linux-python3.13/bin/activate"
elif [ -d "${SCRIPT_DIR}/.venv-linux-python3.12" ]; then
    echo "Activating Linux Python 3.12 virtual environment..."
    source "${SCRIPT_DIR}/.venv-linux-python3.12/bin/activate"
elif [ -d "${SCRIPT_DIR}/.venv-macos-python3.12" ]; then
    echo "Activating macOS Python 3.12 virtual environment..."
    source "${SCRIPT_DIR}/.venv-macos-python3.12/bin/activate"
elif [ -d "${SCRIPT_DIR}/.venv" ]; then
    echo "Activating generic virtual environment..."
    source "${SCRIPT_DIR}/.venv/bin/activate"
fi

# Run the test with default settings
python "${SCRIPT_DIR}/run_ablation_integration_test.py" "$@"

# Capture the exit code
EXIT_CODE=$?

# Deactivate the virtual environment if it was activated
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi

exit $EXIT_CODE