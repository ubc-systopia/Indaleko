#!/bin/bash
#
# Shell script wrapper for the integrated NTFS activity runner
#
# This script provides a convenient way to run the integrated NTFS activity
# collector and recorder on Linux and macOS systems. It maintains proper
# separation of concerns while providing an integrated experience.
#
# Usage:
#   ./run_ntfs_activity.sh [options]
#
# Common options:
#   --volumes C: D:         Volumes to monitor
#   --duration 24           Duration to run in hours
#   --interval 30           Collection interval in seconds
#   --ttl-days 4            Number of days to keep data in hot tier
#   --no-file-backup        Disable backup to files (database only)
#   --output-dir path       Directory for file backups (if enabled)
#   --verbose               Enable verbose logging
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

# Run the integrated activity runner
echo "Running integrated NTFS activity collector and recorder..."
python run_ntfs_activity.py "$@"
