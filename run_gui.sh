#!/bin/bash
# Streamlit GUI launcher for Indaleko
# This script ensures the correct Python path is set before launching

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Set PYTHONPATH to include the project root
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH}"
export INDALEKO_ROOT="${SCRIPT_DIR}"

# Run the Streamlit app
python "${SCRIPT_DIR}/utils/gui/streamlit/run.py" "$@"
