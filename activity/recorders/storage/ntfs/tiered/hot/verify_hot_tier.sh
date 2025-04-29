#!/bin/bash
# Verification script wrapper for NtfsHotTierRecorder implementation
# This script runs the verify_hot_tier.py script with appropriate arguments

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Change to the project root directory (assuming standard project structure)
cd "$SCRIPT_DIR/../../../../../../.." || {
    echo "Error: Could not navigate to project root directory"
    exit 1
}

# Activate virtual environment if it exists
if [ -d ".venv-linux-python3.13" ]; then
    source .venv-linux-python3.13/bin/activate
elif [ -d ".venv-macos-python3.12" ]; then
    source .venv-macos-python3.12/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Set default values
DATABASE_URL="http://localhost:8529"
DATABASE="indaleko"
USERNAME="root"
PASSWORD=""
DRY_RUN=false
FIND_FILES=false
LOAD_DATA=false
VERIFY_ENTITIES=false
TEST_TTL=false
BENCHMARK=false
QUERY_TEST=false
FULL_VERIFICATION=false
VERBOSE=false
LIMIT=""
FILE=""
PATH_TO_SEARCH=""

# Parse command line arguments
while [ "$#" -gt 0 ]; do
    case "$1" in
        --database-url)
            DATABASE_URL="$2"
            shift 2
            ;;
        --database)
            DATABASE="$2"
            shift 2
            ;;
        --username)
            USERNAME="$2"
            shift 2
            ;;
        --password)
            PASSWORD="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --find-files)
            FIND_FILES=true
            shift
            ;;
        --path)
            PATH_TO_SEARCH="$2"
            shift 2
            ;;
        --load-data)
            LOAD_DATA=true
            shift
            ;;
        --verify-entities)
            VERIFY_ENTITIES=true
            shift
            ;;
        --test-ttl)
            TEST_TTL=true
            shift
            ;;
        --benchmark)
            BENCHMARK=true
            shift
            ;;
        --query-test)
            QUERY_TEST=true
            shift
            ;;
        --full-verification)
            FULL_VERIFICATION=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --limit)
            LIMIT="$2"
            shift 2
            ;;
        --file)
            FILE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --database-url URL      ArangoDB server URL (default: http://localhost:8529)"
            echo "  --database NAME         Database name (default: indaleko)"
            echo "  --username USER         Database username (default: root)"
            echo "  --password PASS         Database password"
            echo "  --dry-run               Simulate operations without affecting database"
            echo "  --find-files            Find JSONL files with NTFS activity data"
            echo "  --path DIR              Path to search for JSONL files"
            echo "  --load-data             Load activity data to database"
            echo "  --verify-entities       Verify entity mapping functionality"
            echo "  --test-ttl              Test TTL expiration"
            echo "  --benchmark             Run performance benchmarks"
            echo "  --query-test            Test query capabilities"
            echo "  --full-verification     Run all verification steps"
            echo "  --verbose               Enable verbose output"
            echo "  --limit N               Limit the number of records to process"
            echo "  --file FILE             Specific JSONL file to process"
            echo "  --help                  Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Build command
CMD="python activity/recorders/storage/ntfs/tiered/hot/verify_hot_tier.py"
CMD+=" --database-url $DATABASE_URL"
CMD+=" --database $DATABASE"
CMD+=" --username $USERNAME"

if [ -n "$PASSWORD" ]; then
    CMD+=" --password $PASSWORD"
fi

if [ "$DRY_RUN" = true ]; then
    CMD+=" --dry-run"
fi

if [ "$FIND_FILES" = true ]; then
    CMD+=" --find-files"
fi

if [ -n "$PATH_TO_SEARCH" ]; then
    CMD+=" --path \"$PATH_TO_SEARCH\""
fi

if [ "$LOAD_DATA" = true ]; then
    CMD+=" --load-data"
fi

if [ "$VERIFY_ENTITIES" = true ]; then
    CMD+=" --verify-entities"
fi

if [ "$TEST_TTL" = true ]; then
    CMD+=" --test-ttl"
fi

if [ "$BENCHMARK" = true ]; then
    CMD+=" --benchmark"
fi

if [ "$QUERY_TEST" = true ]; then
    CMD+=" --query-test"
fi

if [ "$FULL_VERIFICATION" = true ]; then
    CMD+=" --full-verification"
fi

if [ "$VERBOSE" = true ]; then
    CMD+=" --verbose"
fi

if [ -n "$LIMIT" ]; then
    CMD+=" --limit $LIMIT"
fi

if [ -n "$FILE" ]; then
    CMD+=" --file \"$FILE\""
fi

# Print command if verbose
if [ "$VERBOSE" = true ]; then
    echo "Running command: $CMD"
fi

# Execute command
eval "$CMD"
