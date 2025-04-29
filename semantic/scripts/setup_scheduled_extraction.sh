#!/bin/bash
# Setup script for Indaleko Scheduled Semantic Extraction
# This script sets up the scheduled semantic extraction for Indaleko on Linux systems

set -e

# Default paths - can be overridden with environment variables
INDALEKO_PATH=${INDALEKO_PATH:-"$(pwd)"}
VENV_PATH=${VENV_PATH:-"$INDALEKO_PATH/.venv-linux-python3.13"}
CONFIG_PATH="$INDALEKO_PATH/semantic/config/linux_scheduler.json"
SCRIPT_PATH="$INDALEKO_PATH/semantic/scripts/run_semantic.sh"
LOG_DIR="$INDALEKO_PATH/logs"

# Schedule options
SCHEDULE_TIME=${SCHEDULE_TIME:-"02:00"}  # Default to 2 AM

# Functions
print_header() {
    echo "=================================================="
    echo "  Indaleko Semantic Extraction Setup"
    echo "=================================================="
    echo ""
}

check_dependencies() {
    echo "Checking dependencies..."

    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo "Error: Python 3 not found"
        exit 1
    fi

    # Check if virtual environment exists
    if [ ! -d "$VENV_PATH" ]; then
        echo "Error: Virtual environment not found at $VENV_PATH"
        echo "Please create it with: python3 -m venv $VENV_PATH"
        exit 1
    fi

    # Check for cron
    if ! command -v crontab &> /dev/null; then
        echo "Error: crontab not found. Please install cron."
        exit 1
    fi

    echo "All dependencies found."
    echo ""
}

update_scripts() {
    echo "Updating script paths..."

    # Update run_semantic.sh with correct paths
    if [ -f "$SCRIPT_PATH" ]; then
        # Make backup
        cp "$SCRIPT_PATH" "$SCRIPT_PATH.bak"

        # Update paths
        sed -i "s|INDALEKO_PATH=.*|INDALEKO_PATH=\"$INDALEKO_PATH\"|" "$SCRIPT_PATH"
        sed -i "s|VENV_PATH=.*|VENV_PATH=\"$VENV_PATH\"|" "$SCRIPT_PATH"
        sed -i "s|LOG_PATH=.*|LOG_PATH=\"$LOG_DIR/semantic_processing.log\"|" "$SCRIPT_PATH"
        sed -i "s|CONFIG_PATH=.*|CONFIG_PATH=\"$CONFIG_PATH\"|" "$SCRIPT_PATH"

        # Make executable
        chmod +x "$SCRIPT_PATH"

        echo "Updated paths in $SCRIPT_PATH"
    else
        echo "Error: Script not found at $SCRIPT_PATH"
        exit 1
    fi

    echo ""
}

setup_config() {
    echo "Setting up configuration..."

    # Create config directory if it doesn't exist
    mkdir -p "$(dirname "$CONFIG_PATH")"

    # Create default config if it doesn't exist
    if [ ! -f "$CONFIG_PATH" ]; then
        cat > "$CONFIG_PATH" << EOF
{
  "resources": {
    "max_cpu_percent": 30,
    "max_memory_mb": 1024,
    "nice_level": 19
  },
  "extractors": {
    "mime": {
      "enabled": true,
      "batch_size": 500,
      "interval_seconds": 10,
      "file_extensions": ["*"]
    },
    "checksum": {
      "enabled": true,
      "batch_size": 200,
      "interval_seconds": 30,
      "file_extensions": [".pdf", ".docx", ".xlsx", ".jpg", ".png"]
    }
  },
  "processing": {
    "max_run_time_seconds": 14400,
    "log_level": "INFO",
    "state_file": "$INDALEKO_PATH/data/semantic/processing_state.json"
  },
  "database": {
    "connection_retries": 3,
    "batch_commit_size": 50
  }
}
EOF
        echo "Created default configuration at $CONFIG_PATH"
    else
        echo "Configuration already exists at $CONFIG_PATH"
    fi

    # Create log directory
    mkdir -p "$LOG_DIR"

    echo ""
}

install_cron_job() {
    echo "Installing cron job..."

    # Extract hour and minute from SCHEDULE_TIME
    HOUR=$(echo "$SCHEDULE_TIME" | cut -d ':' -f 1)
    MINUTE=$(echo "$SCHEDULE_TIME" | cut -d ':' -f 2)

    # Create temporary file for crontab
    TMP_CRON=$(mktemp)

    # Get existing crontab
    crontab -l > "$TMP_CRON" 2>/dev/null || true

    # Check if job already exists
    if grep -q "$SCRIPT_PATH" "$TMP_CRON"; then
        echo "Cron job for semantic extraction already exists. Updating..."
        sed -i "/.*$SCRIPT_PATH.*/d" "$TMP_CRON"
    fi

    # Add new job
    echo "$MINUTE $HOUR * * * $SCRIPT_PATH" >> "$TMP_CRON"

    # Install new crontab
    crontab "$TMP_CRON"
    rm "$TMP_CRON"

    echo "Installed cron job to run at $SCHEDULE_TIME daily"
    echo ""
}

test_extraction() {
    echo "Testing semantic extraction..."

    # Activate virtual environment
    source "$VENV_PATH/bin/activate"

    # Run in test mode
    python -m semantic.run_scheduled --extractors mime --batch-size 1 --run-time 60 --debug

    echo "Test completed. Please check the output for any errors."
    echo ""
}

# Main
print_header

echo "Indaleko path: $INDALEKO_PATH"
echo "Virtual environment: $VENV_PATH"
echo "Configuration: $CONFIG_PATH"
echo "Script: $SCRIPT_PATH"
echo "Schedule time: $SCHEDULE_TIME"
echo ""

read -p "Is this information correct? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled"
    exit 1
fi
echo ""

check_dependencies
update_scripts
setup_config

read -p "Would you like to install the cron job? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    install_cron_job
fi

read -p "Would you like to run a test extraction? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    test_extraction
fi

echo "Setup completed successfully!"
echo "You can manually run the semantic extraction with:"
echo "  $SCRIPT_PATH"
echo ""
echo "To view logs:"
echo "  tail -f $LOG_DIR/semantic_processing.log"
echo ""
