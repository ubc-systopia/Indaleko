#!/bin/bash
# Memory Consolidation Runner for Indaleko Cognitive Memory System
# For Linux and macOS environments
#
# This script runs the memory consolidation process for the Indaleko cognitive memory system,
# which transfers information between different memory tiers (sensory → short-term → long-term → archival).
#
# Usage:
#   ./run_memory_consolidation.sh --consolidate-sensory  # Consolidate from sensory to short-term
#   ./run_memory_consolidation.sh --consolidate-short    # Consolidate from short-term to long-term
#   ./run_memory_consolidation.sh --consolidate-long     # Consolidate from long-term to archival (future)
#   ./run_memory_consolidation.sh --consolidate-all      # Run all consolidation processes
#   ./run_memory_consolidation.sh --stats                # Get memory system statistics
#
# Project Indaleko
# Copyright (C) 2024-2025 Tony Mason

# Find and set the Indaleko root directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INDALEKO_ROOT="$SCRIPT_DIR"
export INDALEKO_ROOT

# Set up color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print header
echo -e "${BLUE}=======================================================${NC}"
echo -e "${BLUE}Indaleko Cognitive Memory System - Consolidation Runner${NC}"
echo -e "${BLUE}=======================================================${NC}"
echo ""

# Find the appropriate virtual environment based on platform
VENV_DIR=""
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux environment
    if [ -d "$SCRIPT_DIR/.venv-linux-python3.13" ]; then
        VENV_DIR="$SCRIPT_DIR/.venv-linux-python3.13"
    elif [ -d "$SCRIPT_DIR/.venv-linux-python3.12" ]; then
        VENV_DIR="$SCRIPT_DIR/.venv-linux-python3.12"
    elif [ -d "$SCRIPT_DIR/.venv-linux-python3.11" ]; then
        VENV_DIR="$SCRIPT_DIR/.venv-linux-python3.11"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS environment
    if [ -d "$SCRIPT_DIR/.venv-macos-python3.12" ]; then
        VENV_DIR="$SCRIPT_DIR/.venv-macos-python3.12"
    elif [ -d "$SCRIPT_DIR/.venv-macos-python3.11" ]; then
        VENV_DIR="$SCRIPT_DIR/.venv-macos-python3.11"
    fi
fi

# Fall back to generic .venv if no specific venv found
if [ -z "$VENV_DIR" ] && [ -d "$SCRIPT_DIR/.venv" ]; then
    VENV_DIR="$SCRIPT_DIR/.venv"
fi

# Find the memory consolidation script
MEMORY_CONSOLIDATION_SCRIPT="$INDALEKO_ROOT/activity/recorders/storage/ntfs/memory/memory_consolidation.py"

# Check if the script exists
if [ ! -f "$MEMORY_CONSOLIDATION_SCRIPT" ]; then
    echo -e "${RED}Error: Memory consolidation script not found at:${NC}"
    echo -e "${RED}$MEMORY_CONSOLIDATION_SCRIPT${NC}"
    echo -e "${YELLOW}Please ensure the script exists and try again.${NC}"
    exit 1
fi

# Activate the virtual environment if available
if [ -n "$VENV_DIR" ]; then
    echo -e "${GREEN}Activating virtual environment: $VENV_DIR${NC}"
    source "$VENV_DIR/bin/activate"
else
    echo -e "${YELLOW}Warning: No virtual environment found. Running with system Python.${NC}"
    echo -e "${YELLOW}For best results, set up a virtual environment with 'uv pip install -e .'${NC}"
fi

# Forward all arguments to the consolidation script
echo -e "${BLUE}Running memory consolidation script...${NC}"
python "$MEMORY_CONSOLIDATION_SCRIPT" "$@"
EXIT_CODE=$?

# Check the exit code
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}Memory consolidation completed successfully.${NC}"
else
    echo -e "${RED}Memory consolidation failed with exit code: $EXIT_CODE${NC}"
fi

# Deactivate the virtual environment if it was activated
if [ -n "$VENV_DIR" ]; then
    deactivate
fi

exit $EXIT_CODE
