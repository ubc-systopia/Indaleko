#!/bin/bash
# Setup script for Google Drive Activity Collector
# This script sets up the Google Drive Activity Collector to run on a schedule

set -e

# Default paths - can be overridden with environment variables
INDALEKO_PATH=${INDALEKO_PATH:-"$(pwd)"}
VENV_PATH=${VENV_PATH:-"$INDALEKO_PATH/.venv-linux-python3.13"}
CONFIG_DIR="$INDALEKO_PATH/config"
DATA_DIR="$INDALEKO_PATH/data"
LOGS_DIR="$INDALEKO_PATH/logs"
SCRIPT_PATH="$INDALEKO_PATH/activity/collectors/storage/cloud/run_gdrive_collector.sh"

# Create directories if they don't exist
mkdir -p "$CONFIG_DIR" "$DATA_DIR" "$LOGS_DIR"

# Check dependencies
echo "Checking dependencies..."
if ! command -v python3 &> /dev/null; then
  echo "Python 3 is required but not found. Please install Python 3."
  exit 1
fi

if ! command -v pip3 &> /dev/null; then
  echo "pip3 is required but not found. Please install pip3."
  exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_PATH" ]; then
  echo "Creating virtual environment at $VENV_PATH"
  python3 -m venv "$VENV_PATH"
fi

# Activate virtual environment and install dependencies
echo "Installing dependencies..."
source "$VENV_PATH/bin/activate"
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

# Create runner script
echo "Creating runner script..."
cat > "$SCRIPT_PATH" << 'EOF'
#!/bin/bash
# Google Drive Activity Collector Runner Script

# Get the script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Go up to Indaleko root directory
INDALEKO_PATH="$(dirname "$(dirname "$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")")")"
VENV_PATH="$INDALEKO_PATH/.venv-linux-python3.13"
PYTHON_SCRIPT="$SCRIPT_DIR/gdrive_activity_collector.py"
CONFIG_PATH="$INDALEKO_PATH/config/gdrive_collector_config.json"
LOG_FILE="$INDALEKO_PATH/logs/gdrive_collector.log"

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

# Log start time
echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting Google Drive activity collection" >> "$LOG_FILE"

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Run collector
python "$PYTHON_SCRIPT" --config "$CONFIG_PATH" --direct-to-db >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

# Log completion
echo "$(date '+%Y-%m-%d %H:%M:%S') - Google Drive activity collection completed with exit code: $EXIT_CODE" >> "$LOG_FILE"

exit $EXIT_CODE
EOF

# Make runner script executable
chmod +x "$SCRIPT_PATH"
echo "Created runner script at $SCRIPT_PATH"

# Create default configuration
echo "Creating default configuration..."
cat > "$CONFIG_DIR/gdrive_collector_config.json" << EOF
{
  "credentials_file": "$CONFIG_DIR/gdrive_client_secrets.json",
  "token_file": "$CONFIG_DIR/gdrive_token.json",
  "state_file": "$DATA_DIR/gdrive_collector_state.json",
  "output_file": "$DATA_DIR/gdrive_activities.jsonl",
  "direct_to_db": true,
  "db_config": {
    "use_default": true
  },
  "collection": {
    "max_results_per_page": 100,
    "max_pages_per_run": 10,
    "include_drive_items": true,
    "include_comments": true,
    "include_shared_drives": true,
    "filter_apps": ["docs", "sheets", "slides", "forms"]
  },
  "scheduling": {
    "interval_minutes": 15,
    "retry_delay_seconds": 60,
    "max_retries": 3
  },
  "logging": {
    "log_file": "$LOGS_DIR/gdrive_collector.log",
    "log_level": "INFO"
  }
}
EOF

echo "Created default configuration at $CONFIG_DIR/gdrive_collector_config.json"

# Prompt for OAuth setup
read -p "Do you want to set up Google Drive OAuth now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "Please follow these steps to set up Google Drive OAuth:"
  echo "1. Go to Google Cloud Console: https://console.cloud.google.com/"
  echo "2. Create a new project or select an existing one"
  echo "3. Enable the Drive API and Drive Activity API"
  echo "4. Create OAuth 2.0 credentials (Desktop app)"
  echo "5. Download the credentials JSON file"

  read -p "Enter the path to the downloaded credentials file: " CREDS_FILE
  if [ -f "$CREDS_FILE" ]; then
    cp "$CREDS_FILE" "$CONFIG_DIR/gdrive_client_secrets.json"
    echo "Credentials saved to $CONFIG_DIR/gdrive_client_secrets.json"
  else
    echo "File not found. You'll need to manually place your credentials at $CONFIG_DIR/gdrive_client_secrets.json"
  fi
else
  echo "Please manually place your Google Drive OAuth credentials at $CONFIG_DIR/gdrive_client_secrets.json"
fi

# Set up cron job
read -p "Do you want to set up a cron job to run the collector automatically? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  # Get current crontab
  TMPFILE=$(mktemp)
  crontab -l > "$TMPFILE" 2>/dev/null || true

  # Check if job already exists
  if grep -q "$SCRIPT_PATH" "$TMPFILE"; then
    echo "Cron job already exists."
  else
    # Set up cron job to run every 15 minutes
    echo "# Indaleko Google Drive Activity Collector - runs every 15 minutes" >> "$TMPFILE"
    echo "*/15 * * * * $SCRIPT_PATH" >> "$TMPFILE"

    # Install new crontab
    crontab "$TMPFILE"
    rm "$TMPFILE"

    echo "Cron job installed to run every 15 minutes."
  fi
else
  echo "No cron job installed. You can run the collector manually with:"
  echo "$SCRIPT_PATH"
fi

# Test run
read -p "Do you want to test run the collector now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "Running Google Drive Activity Collector..."
  "$SCRIPT_PATH"
  if [ $? -eq 0 ]; then
    echo "Test run successful!"
  else
    echo "Test run failed. Please check the logs at $LOGS_DIR/gdrive_collector.log"
  fi
fi

echo "Google Drive Activity Collector setup complete!"
echo "You can run the collector manually with: $SCRIPT_PATH"
echo "Log file location: $LOGS_DIR/gdrive_collector.log"
echo "Output file location: $DATA_DIR/gdrive_activities.jsonl"
