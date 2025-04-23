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
