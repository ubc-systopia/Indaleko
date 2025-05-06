#!/bin/bash
# Run the model-based data generator benchmark suite

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Go to the project root
PROJECT_ROOT="$SCRIPT_DIR/../../.."

# Activate virtual environment if it exists
if [ -f "$PROJECT_ROOT/.venv-linux-python3.13/bin/activate" ]; then
    source "$PROJECT_ROOT/.venv-linux-python3.13/bin/activate"
elif [ -f "$PROJECT_ROOT/.venv-macos-python3.12/bin/activate" ]; then
    source "$PROJECT_ROOT/.venv-macos-python3.12/bin/activate"
fi

# Set PYTHONPATH to include the project root
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Change to project root to run the script
cd "$PROJECT_ROOT"

# Default configuration
CONFIG_FILE=""
OUTPUT_DIR="benchmark_results"
SMALL_ONLY=""
SKIP_LARGE=""
REPORT_FORMATS="md json"
DOMAIN_SPECIFIC=""
COMPARE_LEGACY=""
REPEAT=1
VERBOSE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --small-only)
            SMALL_ONLY="--small-only"
            shift
            ;;
        --skip-large)
            SKIP_LARGE="--skip-large"
            shift
            ;;
        --domain-specific)
            DOMAIN_SPECIFIC="--domain-specific"
            shift
            ;;
        --compare-legacy)
            COMPARE_LEGACY="--compare-legacy"
            shift
            ;;
        --repeat)
            REPEAT="$2"
            shift 2
            ;;
        --report-formats)
            REPORT_FORMATS="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE="--verbose"
            shift
            ;;
        *)
            # Unknown argument, skip it
            shift
            ;;
    esac
done

echo "Running model-based data generator benchmark suite..."

# Build the command line
CMD="python -m tools.data_generator_enhanced.testing.run_benchmark"

if [ -n "$CONFIG_FILE" ]; then
    CMD="$CMD --config $CONFIG_FILE"
fi

CMD="$CMD --output-dir $OUTPUT_DIR"
CMD="$CMD --repeat $REPEAT"
CMD="$CMD --report-formats $REPORT_FORMATS"

if [ -n "$SMALL_ONLY" ]; then
    CMD="$CMD $SMALL_ONLY"
fi

if [ -n "$SKIP_LARGE" ]; then
    CMD="$CMD $SKIP_LARGE"
fi

if [ -n "$DOMAIN_SPECIFIC" ]; then
    CMD="$CMD $DOMAIN_SPECIFIC"
fi

if [ -n "$COMPARE_LEGACY" ]; then
    CMD="$CMD $COMPARE_LEGACY"
fi

if [ -n "$VERBOSE" ]; then
    CMD="$CMD $VERBOSE"
fi

echo "Executing: $CMD"
eval "$CMD"

echo "Benchmark complete. Results are available in $OUTPUT_DIR"
