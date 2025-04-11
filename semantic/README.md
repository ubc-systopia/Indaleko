# Semantic Data Extraction

Indaleko provides components for extracting semantic metadata from files, enhancing searchability and providing rich context. The system uses a collector/recorder pattern for all extractors and supports both on-demand and background processing modes.

## Background Processing

Indaleko includes a robust background processing system for semantic metadata extraction. This system:

1. Randomly selects files from the database that need semantic processing
2. Filters for files that are accessible on the local machine
3. Processes files at low priority to avoid impacting system performance
4. Gradually enhances metadata over time

### Running as a Background Service or Scheduled Task

Indaleko's semantic processor can run as a Windows service or scheduled task. This enables automatic background processing whenever the system is running.

#### Installation Options

```bash
# Run directly for testing
python semantic/run_bg_processor.py

# Install as a Windows service (requires NSSM utility)
python semantic/run_bg_processor.py --install-service 

# Uninstall the Windows service
python semantic/run_bg_processor.py --uninstall-service

# Install as a Windows scheduled task
python semantic/run_bg_processor.py --install-task

# Uninstall the Windows scheduled task
python semantic/run_bg_processor.py --uninstall-task
```

The service will start automatically at system startup and run with low priority, continuously processing files based on the configured schedule.

> Note: To install as a Windows service, you need to download the [NSSM utility](http://nssm.cc/download) and add it to your PATH.

### Using the Background Processor Directly

The unified background processor can be run with:

```bash
python -m semantic.background_processor [options]
```

Options include:
- `--config <file.json>`: Path to a configuration file
- `--processors mime checksum exif unstructured`: Specific processor types to enable
- `--run-time <seconds>`: Run for a specific duration (0 for indefinite)
- `--stats-file <path>`: Output file for processor statistics
- `--debug`: Enable debug logging

The background processor will continuously run until stopped, selecting files based on:
- Which semantic attributes are missing or outdated
- File types matching configured extensions
- Local accessibility of files

### Per-Processor Background Processing

Individual semantic processors can also be run directly:

#### MIME Type Processor

```bash
python -m semantic.collectors.mime.background_processor [options]
```

#### Checksum Processor

```bash
python -m semantic.collectors.checksum.background_processor [options]
```

#### EXIF Metadata Processor

```bash
python -m semantic.collectors.exif.background_processor [options]
```

### Configuration

Background processors can be configured via a JSON file (`semantic/bg_processor_config.json`):

```json
{
  "processors": ["mime", "checksum", "unstructured"],
  "mime": {
    "batch_size": 20,
    "interval": 300,
    "min_last_processed_days": 30
  },
  "checksum": {
    "batch_size": 10,
    "interval": 600,
    "min_last_processed_days": 60,
    "file_extensions": [".pdf", ".docx", ".xlsx", ".pptx", ".zip", ".exe"]
  },
  "unstructured": {
    "batch_size": 5,
    "interval": 1800,
    "min_last_processed_days": 90,
    "file_extensions": [".pdf", ".docx", ".txt", ".md", ".html"]
  }
}
```

## Semantic Extractors

### MIME Type Detection

MIME type detection examines file content to determine the actual file type, which may differ from what the file extension suggests.

**Manual Usage:**
```python
from semantic.collectors.mime.mime_collector import IndalekoSemanticMimeType
from semantic.recorders.mime.recorder import MimeTypeRecorder

collector = IndalekoSemanticMimeType()
recorder = MimeTypeRecorder()

# Process a single file
result = recorder.process_file("/path/to/file")

# Process a directory
results = recorder.process_directory("/path/to/directory", recursive=True)
```

### Checksum Generation

Checksum generation computes multiple hash values for files, supporting integrity verification and deduplication.

**Manual Usage:**
```python
from semantic.collectors.checksum.checksum import IndalekoSemanticChecksums
from semantic.recorders.checksum.recorder import ChecksumRecorder

collector = IndalekoSemanticChecksums()
recorder = ChecksumRecorder()

# Calculate checksums for a file
checksums = collector.compute_checksums("/path/to/file")

# Process and store a file's checksums
result = recorder.process_file("/path/to/file", object_id)
```

## How to use Unstructured

Note: This only works on Windows (due to file path conventions that are different from UNIX ones)

1. Ensure the ArangoDB instance is running on Docker, and there are files whose semantics need to be extracted

### Collector ###

2. Run `semantic\collectors\unstructured\unstructuredd.py` with parameter `lookup`. This command does two things:
    - Creates a configuration file in the config folder. For now, we assume that all files are located 
        in the C:\ drive. If files from other drives need to be analyzed, simply change the 'HostDrive' parameter 
        in the configuration file. This tells Docker to create a bind mount to your specified drive instead of the default C:\ drive.

    - Creates the file `unstructured_inputs.jsonl` in the `data\semantic` folder. Each line specifies a file that is eligible to be
        processed with unstructured. The URI of each file is converted to a UNIX-based path relative to HostDrive, so that the Docker container
        knows where to look when trying to process a file. The ObjectIdentifier, which points to the UUID of the file stored in the Objects
        Collection on ArangoDB, is also listed to aid us in mapping the results of unstructured back to the original file in Arango.

3. If you decide that there are too many files to be processed (Due to time constraints), you can simply remove some lines in the
    `unstructured_inputs.jsonl` file.

4. Important! The next step would be to run unstructured on all the specified files. However, you can first configure the unstructured
    Docker container to allocate enough computational resources (Especially memory as that is the bottleneck). You can do this by going
    to `semantic\collectors\unstructured\retrieve.py`, scroll to the bottom where the docker container is run, and set the `mem_limit`.

5. Run `semantic\collectors\unstructured\unstructuredd.py` with parameter `retrieve`. This command simply runs unstructured on all the files
    specified in `unstructured_inputs.jsonl`, and outputs the raw, unormalized results in `unstructured_outputs.jsonl`.

### Recorder ###

6. Now that the collector stage is finished, we now normalize the outputs from unstructured. This is done by running 
    `semantic\recorders\unstructured\recorder.py`, which creates the file `unstructured_recorder.jsonl`, which contains the normalized
    entry of each file. This is the final file that will get uploaded to ArangoDB via arangoimport.