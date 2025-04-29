# Linux Semantic Metadata Collection Guide

This guide provides detailed instructions for setting up and running Indaleko's semantic metadata extractors on Linux systems. These extractors enhance the richness of metadata available for search and analysis by extracting information directly from file content.

## Overview

Indaleko's semantic extractors work well on Linux systems, offering:
- Efficient metadata extraction with minimal system impact
- Scheduled background processing via cron
- Full integration with Indaleko's database
- Support for incremental processing to avoid redundant work

## Prerequisites

1. **Python Environment**
   - Python 3.9+ with venv
   - Indaleko dependencies installed via uv

2. **Required Packages**
   - `python-magic` for MIME type detection
   - `pillow` and `piexif` for EXIF extraction
   - `docker` for Unstructured extraction (optional)
   - `psutil` for resource monitoring

3. **Database Access**
   - Access to ArangoDB instance (local or remote)
   - Valid database credentials

## Installation

1. **Set up Python environment**

```bash
# Navigate to Indaleko directory
cd /path/to/indaleko

# Create virtual environment
python -m venv .venv-linux-python3.13

# Activate environment
source .venv-linux-python3.13/bin/activate

# Install dependencies
pip install uv
uv pip install -e .
```

2. **Install system dependencies**

```bash
# For Ubuntu/Debian
sudo apt update
sudo apt install libmagic1 python3-dev

# For Fedora/RHEL
sudo dnf install file-devel python3-devel
```

3. **Install Docker (optional, for Unstructured extractor)**

```bash
# For Ubuntu/Debian
sudo apt update
sudo apt install docker.io
sudo systemctl enable --now docker
sudo usermod -aG docker $USER  # Log out and back in after this

# Test Docker installation
docker --version
```

## Configuration

Create a configuration file at `semantic/config/linux_scheduler.json`:

```json
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
    },
    "exif": {
      "enabled": true,
      "batch_size": 300,
      "interval_seconds": 10,
      "file_extensions": [".jpg", ".png", ".tiff", ".heic"]
    },
    "unstructured": {
      "enabled": false,
      "batch_size": 20,
      "interval_seconds": 120,
      "file_extensions": [".pdf", ".docx", ".txt", ".md", ".html"]
    }
  },
  "processing": {
    "max_run_time_seconds": 14400,
    "log_level": "INFO",
    "state_file": "data/semantic/processing_state.json"
  },
  "database": {
    "connection_retries": 3,
    "batch_commit_size": 50
  }
}
```

## Manual Execution

To run semantic processing manually:

```bash
# Activate environment
cd /path/to/indaleko
source .venv-linux-python3.13/bin/activate

# Run all extractors
python -m semantic.run_scheduled --all

# Run specific extractors
python -m semantic.run_scheduled --extractors mime,checksum

# Override configuration settings
python -m semantic.run_scheduled --all --max-cpu 20 --batch-size 100
```

## Scheduled Execution (cron)

Set up automated scheduling with cron:

1. **Create a wrapper script** (`semantic/scripts/run_semantic.sh`):

```bash
#!/bin/bash
# Indaleko Semantic Processing Script

# Path configuration
INDALEKO_PATH="/path/to/indaleko"
VENV_PATH="$INDALEKO_PATH/.venv-linux-python3.13"
LOG_PATH="$INDALEKO_PATH/logs/semantic.log"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_PATH")"

# Change to Indaleko directory
cd "$INDALEKO_PATH" || exit 1

# Activate virtual environment and run processor
source "$VENV_PATH/bin/activate"
python -m semantic.run_scheduled --all >> "$LOG_PATH" 2>&1

# Exit with the Python script's exit code
exit $?
```

2. **Make the script executable**:

```bash
chmod +x semantic/scripts/run_semantic.sh
```

3. **Add to crontab**:

```bash
# Edit crontab
crontab -e

# Add the following line (runs daily at 2 AM)
0 2 * * * /path/to/indaleko/semantic/scripts/run_semantic.sh
```

## Monitoring and Logging

Logs are stored in the `logs` directory:

- `semantic_processing.log`: General processing logs
- `semantic_performance.log`: Performance metrics

View logs with:

```bash
# View processing logs
tail -f logs/semantic_processing.log

# Check for errors
grep ERROR logs/semantic_processing.log

# View performance metrics
column -t -s, logs/semantic_performance.log | less
```

## Testing

Verify the installation with:

```bash
# Run test suite
python -m semantic.tests.test_scheduler

# Process a test directory
python -m semantic.run_scheduled --test --directory /path/to/test/files
```

## Troubleshooting

### Common Issues

1. **Missing libraries**
   - Error: `ImportError: No module named 'magic'`
   - Solution: Install libmagic (`sudo apt install libmagic1`)

2. **Permission issues with Docker**
   - Error: `Permission denied when connecting to the Docker daemon socket`
   - Solution: Add user to docker group (`sudo usermod -aG docker $USER`) and log out/in

3. **Database connection failures**
   - Error: `Failed to connect to database`
   - Solution: Verify database is running and credentials are correct

4. **High resource usage**
   - Issue: System becomes unresponsive during processing
   - Solution: Lower CPU/memory limits in configuration

### Debug Mode

Run with debug logging for more information:

```bash
python -m semantic.run_scheduled --all --debug
```

## Additional Commands

```bash
# View current processing state
python -m semantic.run_scheduled --status

# Reset processing state
python -m semantic.run_scheduled --reset-state

# Generate performance report
python -m semantic.run_scheduled --report

# Test database connection
python -m semantic.run_scheduled --test-connection
```

## Performance Considerations

For optimal performance:

1. **Schedule during low-usage periods**
   - Set cron jobs for nighttime or when system is typically idle

2. **Balance batch size and frequency**
   - Smaller batches with shorter intervals for better responsiveness
   - Larger batches with longer intervals for better efficiency

3. **Use resource limits appropriately**
   - Set CPU limit to 20-30% for background usage
   - Set memory limit based on system capabilities

4. **Choose file types wisely**
   - Focus on high-value file types first
   - Limit resource-intensive extractors (like Unstructured) to specific extensions

## Conclusion

This guide provides all the necessary information to set up and run Indaleko's semantic extractors on Linux. By following these instructions, you can enhance your Indaleko installation with rich semantic metadata extraction while ensuring minimal system impact through proper scheduling and resource management.
