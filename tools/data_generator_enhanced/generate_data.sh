#!/bin/bash
# Script to run the enhanced data generator using the Indaleko CLI framework

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Move to the project root to ensure proper imports
cd "$(dirname "$SCRIPT_DIR")"

# Activate appropriate virtual environment if it exists
if [ -d ".venv-linux-python3.13" ]; then
    source ".venv-linux-python3.13/bin/activate"
elif [ -d ".venv-macos-python3.12" ]; then
    source ".venv-macos-python3.12/bin/activate"
fi

# Run the generator script
python "${SCRIPT_DIR}/generate_data.py" "$@"

# Exit with the Python script's exit code
exit $?