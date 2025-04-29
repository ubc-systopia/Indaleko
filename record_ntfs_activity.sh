#!/bin/bash
#
# Shell script wrapper for record_ntfs_activity.py
#
# This script provides a convenient way to run the NTFS activity recorder
# on Linux and macOS systems. It ensures the proper Python environment
# is activated before running the recorder.
#
# Usage:
#   ./record_ntfs_activity.sh --input activities.jsonl [additional options]
#
# Project Indaleko
# Copyright (C) 2024-2025 Tony Mason
#

# Determine script location
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$SCRIPT_DIR" || exit 1

# Determine platform-specific virtual environment
if [[ "$(uname)" == "Darwin" ]]; then
    # macOS
    VENV_DIR=".venv-macos-python3.12"
elif [[ "$(uname)" == "Linux" ]]; then
    # Linux
    VENV_DIR=".venv-linux-python3.13"
else
    echo "Unsupported platform: $(uname)"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "$VENV_DIR" ]; then
    echo "Activating virtual environment: $VENV_DIR"
    # shellcheck disable=SC1090
    source "$VENV_DIR/bin/activate"
else
    echo "Warning: Virtual environment not found: $VENV_DIR"
    echo "Using system Python instead"
fi

# Run the recorder CLI
echo "Running NTFS activity recorder..."
python record_ntfs_activity.py "$@"
