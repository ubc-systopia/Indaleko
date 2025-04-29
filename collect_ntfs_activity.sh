#!/bin/bash

# NTFS Activity Generator for Indaleko
# Collects NTFS file system activities

# Default parameters
VOLUMES="C:"
DURATION=24
INTERVAL=30
OUTPUT_DIR="data/ntfs_activity"
MAX_FILE_SIZE=100
VERBOSE=false
RESET_STATE=false
CONTINUE_ON_ERROR=false

# Function to show help
show_help() {
    echo
    echo "NTFS Activity Generator for Indaleko"
    echo "Usage: collect_ntfs_activity.sh [options]"
    echo
    echo "Options:"
    echo "  --volumes VOLUMES          Comma-separated list of volumes to monitor (default: C:)"
    echo "  --duration HOURS           Duration to run in hours (default: 24, 0 for unlimited)"
    echo "  --interval SECONDS         Collection interval in seconds (default: 30)"
    echo "  --output-dir DIR           Directory to store output files (default: data/ntfs_activity)"
    echo "  --max-file-size MB         Maximum JSONL file size in MB before rotation (default: 100)"
    echo "  --verbose                  Enable verbose logging"
    echo "  --reset-state              Reset the USN journal state file (useful after journal rotation)"
    echo "  --continue-on-error        Continue processing when non-critical errors occur"
    echo "  --help                     Show this help message"
    echo
    echo "Examples:"
    echo "  ./collect_ntfs_activity.sh --volumes C:,D: --duration 48"
    echo "  ./collect_ntfs_activity.sh --interval 60 --verbose"
    echo
    echo "Note: This script must be run with Administrator privileges when using Windows."
    echo "      To record the collected data to the database, use record_ntfs_activity.sh afterward."
    echo
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --volumes)
            VOLUMES="$2"
            shift 2
            ;;
        --duration)
            DURATION="$2"
            shift 2
            ;;
        --interval)
            INTERVAL="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --max-file-size)
            MAX_FILE_SIZE="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --reset-state)
            RESET_STATE=true
            shift
            ;;
        --continue-on-error)
            CONTINUE_ON_ERROR=true
            shift
            ;;
        --help)
            show_help
            ;;
        *)
            echo "Unknown argument: $1"
            show_help
            ;;
    esac
done

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo "Error: Python is not installed or not in the PATH."
    exit 1
fi

# Check if running on Windows (since this is for NTFS)
if [[ "$(uname)" != CYGWIN* ]] && [[ "$(uname)" != MINGW* ]] && [[ "$(uname)" != MSYS* ]]; then
    if [[ ! -f "/proc/version" ]] || ! grep -qi microsoft "/proc/version"; then
        echo "Warning: This script is designed for Windows or WSL. NTFS support may be limited."
    fi
fi

# Determine platform-specific virtual environment
if [[ "$(uname)" == "Darwin" ]]; then
    # macOS
    VENV_DIR=".venv-macos-python3.12"
elif [[ "$(uname)" == "Linux" ]]; then
    # Linux
    VENV_DIR=".venv-linux-python3.13"
else
    # Windows/WSL/Cygwin
    VENV_DIR=".venv-win32-python3.12"
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

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Build command
CMD="python activity/collectors/storage/ntfs/activity_generator.py"
CMD="$CMD --volumes $VOLUMES"
CMD="$CMD --duration $DURATION"
CMD="$CMD --interval $INTERVAL"
CMD="$CMD --output-dir $OUTPUT_DIR"
CMD="$CMD --max-file-size $MAX_FILE_SIZE"

# Add optional flags
if [ "$VERBOSE" = true ]; then
    CMD="$CMD --verbose"
fi

if [ "$RESET_STATE" = true ]; then
    CMD="$CMD --reset-state"
fi

if [ "$CONTINUE_ON_ERROR" = true ]; then
    CMD="$CMD --continue-on-error"
fi

# Display configuration
echo
echo "============================================================"
echo "     NTFS Activity Generator for Indaleko"
echo "============================================================"
echo
echo "Starting NTFS Activity Generator with the following settings:"
echo "  Volumes:            $VOLUMES"
echo "  Duration:           $DURATION hours"
echo "  Interval:           $INTERVAL seconds"
echo "  Output Dir:         $OUTPUT_DIR"
echo "  Max File:           $MAX_FILE_SIZE MB"
echo "  Verbose:            $VERBOSE"
echo "  Reset State:        $RESET_STATE"
echo "  Continue On Error:  $CONTINUE_ON_ERROR"
echo
echo "Press Ctrl+C to interrupt the collection at any time."
echo
echo "Starting collection process..."
echo

# Run the command
$CMD

echo
echo "Collection completed."
echo "To record the collected data to the database, use:"
echo "./record_ntfs_activity.sh --input <json_file_path>"
echo "Example: ./record_ntfs_activity.sh --input $OUTPUT_DIR/ntfs_activity_20250422_123456.jsonl"
