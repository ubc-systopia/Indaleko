#!/bin/bash
# Run the Indaleko NTFS Tier Transition from hot to warm tier
# This script manages the transition of file activity data between tiers
# in the Indaleko tiered memory architecture.

# Get script directory for setting environment
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export INDALEKO_ROOT="$SCRIPT_DIR"

# Set up the Python environment
VENV_DIR=""

# Find the appropriate virtual environment based on platform
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

# Display error and exit if no virtual environment found
if [ -z "$VENV_DIR" ]; then
    echo "Error: No appropriate virtual environment found."
    echo "Please run 'uv pip install -e .' to create the environment."
    exit 1
fi

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

# Parse command line arguments
STATS_ONLY=0
RUN_TRANSITION=0
VERBOSE=0
DEBUG=0
AGE_HOURS=12
BATCH_SIZE=1000
MAX_BATCHES=10
DB_CONFIG=""

# Process command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --stats-only)
            STATS_ONLY=1
            shift
            ;;
        --run)
            RUN_TRANSITION=1
            shift
            ;;
        --verbose)
            VERBOSE=1
            shift
            ;;
        --debug)
            DEBUG=1
            shift
            ;;
        --age-hours)
            AGE_HOURS="$2"
            shift 2
            ;;
        --batch-size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        --max-batches)
            MAX_BATCHES="$2"
            shift 2
            ;;
        --db-config)
            DB_CONFIG="$2"
            shift 2
            ;;
        --help)
            echo "Indaleko NTFS Tier Transition Utility"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --stats-only         Show tier transition statistics without running transition"
            echo "  --run                Run the tier transition"
            echo "  --verbose            Show more detailed output"
            echo "  --debug              Enable debug logging"
            echo "  --age-hours N        Age threshold in hours for transition (default: 12)"
            echo "  --batch-size N       Number of activities to process in each batch (default: 1000)"
            echo "  --max-batches N      Maximum number of batches to process (default: 10)"
            echo "  --db-config PATH     Path to database configuration file"
            echo "  --help               Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# If neither stats-only nor run is specified, default to stats-only
if [ $STATS_ONLY -eq 0 ] && [ $RUN_TRANSITION -eq 0 ]; then
    STATS_ONLY=1
fi

# Build command arguments
COMMAND_ARGS=""

if [ $STATS_ONLY -eq 1 ]; then
    COMMAND_ARGS="$COMMAND_ARGS --stats"
fi

if [ $RUN_TRANSITION -eq 1 ]; then
    COMMAND_ARGS="$COMMAND_ARGS --run"
fi

if [ $VERBOSE -eq 1 ]; then
    COMMAND_ARGS="$COMMAND_ARGS --verbose"
fi

if [ $DEBUG -eq 1 ]; then
    COMMAND_ARGS="$COMMAND_ARGS --debug"
fi

COMMAND_ARGS="$COMMAND_ARGS --age-hours $AGE_HOURS --batch-size $BATCH_SIZE --max-batches $MAX_BATCHES"

if [ ! -z "$DB_CONFIG" ]; then
    COMMAND_ARGS="$COMMAND_ARGS --db-config '$DB_CONFIG'"
fi

# Run the tier transition utility
echo "Running NTFS Tier Transition Utility..."
echo ""

python -m activity.recorders.storage.ntfs.tiered.tier_transition $COMMAND_ARGS

# Deactivate the virtual environment
deactivate
