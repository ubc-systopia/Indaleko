#!/bin/bash
# create_analyzers.sh - Script to create custom analyzers for Indaleko
# 
# This script uses the analyzer_manager.py module to create custom analyzers
# for Indaleko using either the direct arangosh method or the Python API.
#
# Project Indaleko
# Copyright (C) 2024-2025 Tony Mason
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Set script directory
SCRIPT_DIR=$(dirname "$(realpath "$0")")
INDALEKO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Add Indaleko root to PYTHONPATH
export PYTHONPATH="$INDALEKO_ROOT:$PYTHONPATH"

# Check if Python is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
  echo "Warning: No virtual environment detected."
  echo "It's recommended to activate your Indaleko virtual environment before running this script."
  
  # Try to find and activate a virtual environment
  for venv in ".venv-linux-python3.13" ".venv-win32-python3.12" ".venv-macos-python3.12"; do
    if [[ -d "$INDALEKO_ROOT/$venv" ]]; then
      echo "Found virtual environment: $venv"
      echo "Activating..."
      source "$INDALEKO_ROOT/$venv/bin/activate"
      break
    fi
  done
  
  if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "Could not find or activate a virtual environment."
    echo "Continuing with system Python, which may cause issues if dependencies are missing."
  fi
fi

# Parse command line arguments
DIRECT=0
DEBUG=0

for arg in "$@"; do
  case $arg in
    --direct)
      DIRECT=1
      shift
      ;;
    --debug)
      DEBUG=1
      shift
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --direct   Use direct arangosh command execution"
      echo "  --debug    Enable debug output"
      echo "  --help     Show this help message"
      exit 0
      ;;
  esac
done

# Run the analyzer manager
if [[ $DIRECT -eq 1 ]]; then
  if [[ $DEBUG -eq 1 ]]; then
    python -m db.analyzer_manager --direct --debug
  else
    python -m db.analyzer_manager --direct
  fi
else
  if [[ $DEBUG -eq 1 ]]; then
    python -m db.analyzer_manager create --debug
  else
    python -m db.analyzer_manager create
  fi
fi

# Check exit status
STATUS=$?
if [[ $STATUS -eq 0 ]]; then
  echo "Custom analyzers created successfully"
  exit 0
else
  echo "Failed to create custom analyzers"
  echo "Try again with the --direct flag or --debug for more information"
  exit 1
fi