#!/bin/bash
# Run memory consolidation processes for the NTFS cognitive memory system
# Usage: ./run_memory_consolidation.sh [--consolidate-all] [--debug] [--dry-run]

# Set up environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
INDALEKO_ROOT="$(cd "${SCRIPT_DIR}/../../../../../../" &> /dev/null && pwd)"
export INDALEKO_ROOT
export PYTHONPATH="${INDALEKO_ROOT}:${PYTHONPATH}"

# Check for Python
if ! command -v python &> /dev/null; then
    echo "Error: Python not found"
    exit 1
fi

# Default options
CONSOLIDATE_ALL=false
DEBUG=""
DRY_RUN=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --consolidate-all)
            CONSOLIDATE_ALL=true
            shift
            ;;
        --debug)
            DEBUG="--debug"
            shift
            ;;
        --dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        *)
            # Unknown option
            echo "Error: Unknown option $1"
            echo "Usage: ./run_memory_consolidation.sh [--consolidate-all] [--debug] [--dry-run]"
            exit 1
            ;;
    esac
done

# Show menu if not running all
if [[ $CONSOLIDATE_ALL == false ]]; then
    echo "=== NTFS Cognitive Memory Consolidation ==="
    echo "1) Sensory → Short-Term Memory"
    echo "2) Short-Term → Long-Term Memory"
    echo "3) Long-Term → Archival Memory"
    echo "4) Run All Consolidation Processes"
    echo "5) Show Memory Statistics"
    echo "0) Exit"
    echo ""
    echo -n "Choose an option (0-5): "
    read -r OPTION
else
    OPTION=4
fi

# Process option
case $OPTION in
    1)
        echo "Running: Sensory → Short-Term Memory consolidation"
        python "${SCRIPT_DIR}/memory_consolidation.py" --consolidate-sensory $DEBUG $DRY_RUN
        ;;
    2)
        echo "Running: Short-Term → Long-Term Memory consolidation"
        python "${SCRIPT_DIR}/memory_consolidation.py" --consolidate-short $DEBUG $DRY_RUN
        ;;
    3)
        echo "Running: Long-Term → Archival Memory consolidation"
        python "${SCRIPT_DIR}/memory_consolidation.py" --consolidate-long $DEBUG $DRY_RUN
        ;;
    4)
        echo "Running: All memory consolidation processes"
        python "${SCRIPT_DIR}/memory_consolidation.py" --consolidate-all $DEBUG $DRY_RUN
        ;;
    5)
        echo "Getting memory statistics"
        python "${SCRIPT_DIR}/memory_consolidation.py" --stats $DEBUG
        ;;
    0)
        echo "Exiting"
        exit 0
        ;;
    *)
        echo "Error: Invalid option ${OPTION}"
        exit 1
        ;;
esac

echo "Done."
exit 0
