#!/bin/bash
# Indaleko Semantic Processing Script
# This script runs the scheduled semantic metadata extraction for Indaleko
# It is designed to be called from cron

# Configuration
# Change these paths to match your environment
INDALEKO_PATH="/path/to/indaleko"
VENV_PATH="$INDALEKO_PATH/.venv-linux-python3.13"
LOG_PATH="$INDALEKO_PATH/logs/semantic_processing.log"
CONFIG_PATH="$INDALEKO_PATH/semantic/config/linux_scheduler.json"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_PATH")"

# Record start time
echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting semantic processing" >> "$LOG_PATH"

# Change to Indaleko directory
cd "$INDALEKO_PATH" || {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Failed to change to Indaleko directory: $INDALEKO_PATH" >> "$LOG_PATH"
    exit 1
}

# Check if Python virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Virtual environment not found: $VENV_PATH" >> "$LOG_PATH"
    exit 1
fi

# Activate virtual environment and run processor
echo "$(date '+%Y-%m-%d %H:%M:%S') - Activating virtual environment" >> "$LOG_PATH"
source "$VENV_PATH/bin/activate" || {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Failed to activate virtual environment" >> "$LOG_PATH"
    exit 1
}

# Verify we can import required modules
python -c "import semantic.collectors.mime.mime_collector; import semantic.collectors.checksum.checksum" || {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Failed to import required modules" >> "$LOG_PATH"
    exit 1
}

# Run the semantic processor
echo "$(date '+%Y-%m-%d %H:%M:%S') - Running semantic processor" >> "$LOG_PATH"
python -m semantic.run_scheduled --all --config "$CONFIG_PATH" >> "$LOG_PATH" 2>&1
EXIT_CODE=$?

# Record completion
echo "$(date '+%Y-%m-%d %H:%M:%S') - Semantic processing completed with exit code: $EXIT_CODE" >> "$LOG_PATH"

# Exit with the Python script's exit code
exit $EXIT_CODE
