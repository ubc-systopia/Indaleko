#!/bin/bash
# 
# Load NTFS activity data into the hot tier database
#
# This script provides an easy way to run the NTFS Hot Tier Recorder
# with common options.
#
# Project Indaleko
# Copyright (C) 2024-2025 Tony Mason
#

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Set INDALEKO_ROOT environment variable
export INDALEKO_ROOT="$SCRIPT_DIR"

# Check for Python virtual environment and activate it
if [ -d "$SCRIPT_DIR/.venv-linux-python3.13" ]; then
  echo "Activating Linux Python 3.13 environment"
  source "$SCRIPT_DIR/.venv-linux-python3.13/bin/activate"
elif [ -d "$SCRIPT_DIR/.venv-linux-python3.12" ]; then
  echo "Activating Linux Python 3.12 environment"
  source "$SCRIPT_DIR/.venv-linux-python3.12/bin/activate"
elif [ -d "$SCRIPT_DIR/.venv-linux" ]; then
  echo "Activating Linux Python environment"
  source "$SCRIPT_DIR/.venv-linux/bin/activate"
elif [ -d "$SCRIPT_DIR/.venv" ]; then
  echo "Activating Python environment"
  source "$SCRIPT_DIR/.venv/bin/activate"
else
  echo "Warning: No Python virtual environment found. Script may fail if dependencies are missing."
fi

# Add project root to Python path
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Help message
function show_help() {
  echo "Usage: $0 [options]"
  echo ""
  echo "Options:"
  echo "  --help          Show this help message"
  echo "  --list          List available NTFS activity files"
  echo "  --simulate      Run in simulation mode (no database connection)"
  echo "  --dry-run       Analyze files but don't load to database"
  echo "  --all           Process all NTFS activity files found"
  echo "  --report        Generate a summary report"
  echo "  --file FILE     Process a specific JSONL file"
  echo "  --ttl-days N    Set hot tier TTL to N days (default: 4)"
  echo "  --verbose       Show more detailed output"
  echo ""
  echo "Examples:"
  echo "  $0 --list               # List available activity files"
  echo "  $0 --simulate --report  # Test without affecting database"
  echo "  $0 --all --report       # Process all files with report"
  echo "  $0 --file path/to/file.jsonl  # Process specific file"
}

# Parse command line arguments
if [ "$#" -eq 0 ]; then
  # No arguments, use default settings
  python "$SCRIPT_DIR/activity/recorders/storage/ntfs/tiered/hot/load_to_database.py" --simulate
else
  # Pass all arguments to the Python script
  if [ "$1" == "--help" ]; then
    show_help
  else
    python "$SCRIPT_DIR/activity/recorders/storage/ntfs/tiered/hot/load_to_database.py" "$@"
  fi
fi