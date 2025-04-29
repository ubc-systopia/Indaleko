# Semantic Metadata Collection Scheduler

This document outlines the implementation plan for enhancing Indaleko's semantic metadata collection through scheduled background processing. Semantic extractors provide rich metadata that can significantly improve search relevance, entity understanding, and cross-source pattern detection.

## Current Semantic Extractors

Indaleko currently supports several semantic extractors, each specialized for different metadata types:

1. **MIME Type Detection**
   - Identifies actual file types through content analysis (regardless of extension)
   - Provides MIME type, encoding, and content categorization
   - Highly efficient processing with minimal system impact

2. **Checksum Generation**
   - Computes MD5, SHA1, SHA256, SHA512 and Dropbox Content Hash
   - Enables integrity verification and duplicate detection
   - Uses memory-mapped I/O for large files and optimized processing

3. **EXIF Metadata Extraction**
   - Extracts image/media metadata (camera, GPS, timestamps)
   - Provides rich context for media files
   - Supports geo-location correlation

4. **Unstructured Content Extraction**
   - Extracts text, headings, tables from documents
   - Analyzes PDF, Office documents, images with text
   - Uses Docker-based processing for isolation

## Implementation Approach

We will enhance these existing extractors to run on a scheduled basis, focusing on these priorities:

1. **Cross-Platform Scheduler**
   - Linux: Cron-based scheduling
   - Windows: Task Scheduler integration
   - Configuration-driven approach

2. **Performance-Aware Processing**
   - Low-priority background execution
   - Resource limitation to avoid system impact
   - Batch processing with configurable limits

3. **Incremental Processing**
   - Track processed files to avoid redundant work
   - State persistence across runs
   - Change detection for efficient updates

## Scheduler Design

### 1. Unified Command Interface

```bash
# Start semantic processing with all extractors
python -m semantic.run_scheduled --all

# Run specific extractors only
python -m semantic.run_scheduled --extractors mime,checksum

# Control resource usage
python -m semantic.run_scheduled --all --max-cpu 30 --max-memory 1024

# Specify batch processing parameters
python -m semantic.run_scheduled --all --batch-size 100 --interval 60

# Run for a specific time period
python -m semantic.run_scheduled --all --run-time 3600
```

### 2. Implementation for Linux

For Linux systems, we'll use cron scheduling:

```bash
# Edit crontab
crontab -e

# Add scheduled job (runs daily at 2 AM)
0 2 * * * cd /path/to/indaleko && source .venv-linux-python3.13/bin/activate && python -m semantic.run_scheduled --all --max-cpu 30 >> /path/to/logs/semantic.log 2>&1
```

**Configuration Example** (`semantic/config/linux_scheduler.json`):
```json
{
  "schedule": {
    "frequency": "daily",
    "time": "02:00"
  },
  "resources": {
    "max_cpu_percent": 30,
    "max_memory_mb": 1024,
    "nice_level": 19
  },
  "extractors": {
    "mime": {
      "enabled": true,
      "batch_size": 500,
      "interval_seconds": 10
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
      "enabled": true,
      "batch_size": 20,
      "interval_seconds": 120,
      "file_extensions": [".pdf", ".docx", ".txt", ".md", ".html"]
    }
  },
  "processing": {
    "max_run_time_seconds": 14400,
    "log_level": "INFO",
    "state_file": "data/semantic/processing_state.json"
  }
}
```

### 3. Implementation for Windows

For Windows systems, we'll create PowerShell scripts and Task Scheduler integration:

**PowerShell Script** (`semantic/scripts/Run-SemanticProcessing.ps1`):
```powershell
# Run-SemanticProcessing.ps1
param (
    [switch]$Install,
    [switch]$Uninstall,
    [switch]$Run
)

$IndalekoPath = "C:\path\to\indaleko"
$VenvPath = Join-Path $IndalekoPath ".venv-win32-python3.12"
$ScriptPath = Join-Path $IndalekoPath "semantic\scripts\Run-SemanticProcessing.ps1"
$PythonPath = Join-Path $VenvPath "Scripts\python.exe"
$LogPath = Join-Path $IndalekoPath "logs\semantic.log"

# Ensure log directory exists
if (-not (Test-Path (Split-Path $LogPath))) {
    New-Item -Path (Split-Path $LogPath) -ItemType Directory -Force
}

function Install-Task {
    $action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`" -Run"
    $trigger = New-ScheduledTaskTrigger -Daily -At 2AM
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -IdleSettings (New-ScheduledTaskIdleSettings -IdleDuration 00:10:00 -WaitTimeout 01:00:00)
    $principal = New-ScheduledTaskPrincipal -UserId (Get-CimInstance -ClassName Win32_ComputerSystem | Select-Object -ExpandProperty UserName) -LogonType S4U -RunLevel Lowest

    Register-ScheduledTask -TaskName "Indaleko_Semantic_Processing" -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Runs Indaleko semantic processing at low priority during idle time"

    Write-Host "Scheduled task 'Indaleko_Semantic_Processing' installed successfully"
}

function Uninstall-Task {
    Unregister-ScheduledTask -TaskName "Indaleko_Semantic_Processing" -Confirm:$false
    Write-Host "Scheduled task 'Indaleko_Semantic_Processing' removed"
}

function Run-Processing {
    Push-Location $IndalekoPath
    try {
        # Activate venv and run processor
        & "$VenvPath\Scripts\Activate.ps1"
        & $PythonPath -m semantic.run_scheduled --all --max-cpu 30 --max-memory 1024 | Tee-Object -FilePath $LogPath -Append
    }
    finally {
        Pop-Location
    }
}

if ($Install) {
    Install-Task
} elseif ($Uninstall) {
    Uninstall-Task
} elseif ($Run) {
    Run-Processing
}
```

**Install Commands**:
```powershell
# Install as scheduled task
.\semantic\scripts\Run-SemanticProcessing.ps1 -Install

# Run manually
.\semantic\scripts\Run-SemanticProcessing.ps1 -Run

# Uninstall task
.\semantic\scripts\Run-SemanticProcessing.ps1 -Uninstall
```

## Implementation Details

### 1. State Management

To ensure efficient incremental processing, we'll maintain state information in a JSON file:

```json
{
  "last_run": "2025-04-21T14:30:22.123456Z",
  "extractors": {
    "mime": {
      "last_run": "2025-04-21T14:30:22.123456Z",
      "processed_files": 1250,
      "skipped_files": 50,
      "error_files": 2,
      "last_file_id": "12345678-1234-5678-1234-567812345678"
    },
    "checksum": {
      "last_run": "2025-04-21T14:30:22.123456Z",
      "processed_files": 800,
      "skipped_files": 30,
      "error_files": 1,
      "last_file_id": "87654321-8765-4321-8765-432187654321"
    }
  },
  "database": {
    "last_connection": "2025-04-21T14:30:22.123456Z",
    "total_records": 2050
  }
}
```

### 2. Resource Control

We'll implement dynamic resource control through:

```python
def limit_cpu_usage(max_percent=30):
    """Limit CPU usage to specified percentage."""
    process = psutil.Process(os.getpid())

    if platform.system() == "Linux":
        # Set nice level on Linux
        os.nice(19)  # Lowest priority

    # Monitor and control CPU usage
    while True:
        cpu_percent = process.cpu_percent(interval=1)
        if cpu_percent > max_percent:
            # Sleep to reduce CPU usage
            time.sleep(1)
        else:
            # Allow processing to continue
            break

def process_batch(files, extractor, max_cpu=30, max_memory=1024):
    """Process a batch of files with resource constraints."""
    for file in files:
        # Check memory usage
        memory_used = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
        if memory_used > max_memory:
            # Sleep to allow memory release
            time.sleep(5)
            gc.collect()

        # Limit CPU usage
        limit_cpu_usage(max_cpu)

        # Process file
        try:
            extractor.process_file(file)
        except Exception as e:
            logger.error(f"Error processing {file}: {e}")
```

### 3. Docker Container Control for Unstructured

For Unstructured extractor, we'll enhance Docker container management:

```python
def run_unstructured_container(files_batch, config):
    """Run Unstructured in Docker container with resource limits."""
    client = docker.from_env()

    # Configure container with resource limits
    container = client.containers.run(
        "unstructured-io/unstructured-api:latest",
        detach=True,
        volumes={
            os.path.abspath("input_files"): {"bind": "/inputs", "mode": "ro"},
            os.path.abspath("output"): {"bind": "/outputs", "mode": "rw"}
        },
        mem_limit=f"{config['max_memory_mb']}m",
        cpu_quota=int(100000 * (config['max_cpu_percent'] / 100)),
        cpu_period=100000,
        remove=True
    )

    # Monitor container for completion
    for line in container.logs(stream=True):
        logger.debug(line.decode("utf-8").strip())

    # Process results
    process_unstructured_output("output")
```

## Cross-Platform Testing

We'll develop a test script to verify the scheduler works correctly on both Linux and Windows:

```python
def test_scheduler():
    """Test the scheduler functionality."""
    # Test configuration loading
    config = load_config()
    assert "extractors" in config

    # Test resource monitoring
    process = psutil.Process(os.getpid())
    start_cpu = process.cpu_percent()

    # Run a small test batch
    run_small_test_batch()

    # Verify resource control worked
    end_cpu = process.cpu_percent()
    assert end_cpu <= config["resources"]["max_cpu_percent"]

    # Test state persistence
    assert os.path.exists(config["processing"]["state_file"])

    # Test database connection
    test_db_connection()
```

## Database Integration

All extractors will write their results directly to ArangoDB using the existing collection schema. We'll enhance the db_collections.py to properly define semantic collections if needed:

```python
class IndalekoDBCollections:
    # Existing collections...

    # Semantic collections
    Indaleko_Semantic_MIME = "SemanticMIME"
    Indaleko_Semantic_Checksum = "SemanticChecksum"
    Indaleko_Semantic_EXIF = "SemanticEXIF"
    Indaleko_Semantic_Unstructured = "SemanticUnstructured"

    Collections = {
        # Existing collections...

        Indaleko_Semantic_MIME: {
            "internal": False,
            "schema": MimeTypeDataModel.get_arangodb_schema(),
            "edge": False,
            "indices": {
                "mime_type": {
                    "fields": ["mime_type"],
                    "unique": False,
                    "type": "persistent",
                },
                "object_id": {
                    "fields": ["object_id"],
                    "unique": False,
                    "type": "persistent",
                }
            },
            "views": [
                {
                    "name": "MimeTypeView",
                    "fields": ["mime_type", "encoding"],
                    "analyzers": ["text_en"],
                    "stored_values": ["_key", "mime_type"]
                }
            ]
        },
        # Define other semantic collections similarly
    }
```

## Logging and Monitoring

We'll implement a comprehensive logging and monitoring system:

```python
def setup_logging(config):
    """Set up logging based on configuration."""
    log_level = getattr(logging, config["processing"]["log_level"])
    log_file = os.path.join("logs", "semantic_processing.log")

    # Configure logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    # Create performance logger
    perf_logger = logging.getLogger("semantic.performance")
    perf_handler = logging.FileHandler(os.path.join("logs", "semantic_performance.log"))
    perf_handler.setFormatter(logging.Formatter("%(asctime)s,%(message)s"))
    perf_logger.addHandler(perf_handler)

    return logging.getLogger("semantic.scheduler")
```

## Implementation Schedule

1. **Phase 1: Base Scheduler Implementation** (2 days)
   - Create Linux and Windows scheduler scripts
   - Implement resource control and monitoring
   - Add state persistence

2. **Phase 2: Extractor Integration** (3 days)
   - Integrate MIME Type extractor
   - Integrate Checksum extractor
   - Integrate EXIF extractor
   - Integrate Unstructured extractor

3. **Phase 3: Database Integration** (2 days)
   - Enhance collection definitions
   - Implement direct database writing
   - Add batch commit support

4. **Phase 4: Testing and Optimization** (3 days)
   - Create test scripts for cross-platform testing
   - Optimize resource usage
   - Fine-tune scheduling parameters

## Conclusion

This implementation plan provides a structured approach to enhancing Indaleko's semantic metadata collection through scheduled background processing. By leveraging existing extractors and implementing efficient scheduling and resource control, we can significantly improve the richness of metadata available for search and analysis without impacting system performance.

The design focuses on cross-platform compatibility, resource efficiency, and incremental processing to ensure optimal performance on both Linux and Windows environments.
