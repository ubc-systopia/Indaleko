#!/bin/bash
# Run Indaleko Analytics Tool

# Check for virtual environment and activate if found
if [ -d .venv-linux-python3.13 ]; then
    source .venv-linux-python3.13/bin/activate
elif [ -d .venv-macos-python3.12 ]; then
    source .venv-macos-python3.12/bin/activate
fi

# Run the analytics tool with provided arguments
python -m query.analytics.file_statistics "$@"
