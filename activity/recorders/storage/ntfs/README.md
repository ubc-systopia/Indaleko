# NTFS Storage Activity Collector and Recorder

This module provides collectors and recorders for monitoring NTFS file system activities through the USN Journal. It is designed to integrate with Indaleko's activity tracking system to provide a comprehensive view of file operations on Windows systems.

## Features

- **Real-time monitoring** of file system changes via the NTFS USN Journal
- **Volume GUID support** for stable path references (immune to drive letter changes)
- **Timezone-aware datetime handling** for ArangoDB compatibility
- **Mock data generation** for cross-platform testing and development
- **Robust error handling** with fallback modes for various error conditions
- **Command-line interface** for testing and monitoring
- **Integration with Activity service** for proper collection registration

## Components

### NtfsStorageActivityCollector

Collects file system activities directly from the NTFS USN Journal and converts them to standardized activity records.

### NtfsStorageActivityRecorder

Records the collected activities to an ArangoDB database through the Indaleko registration service.

## System Requirements

- **Windows**: Required for actual USN Journal monitoring
- **Python 3.9+**: Required for proper type hints and functionality
- **pywin32**: Required for Windows API access
- **ArangoDB**: Required for database storage (optional, can run in no-db mode)

## Volume GUID Support

The collector uses Volume GUIDs instead of drive letters as the default path format. This provides several advantages:

1. **Stability**: Volume GUIDs remain constant even if drive letters change
2. **Uniqueness**: Each volume has a unique GUID that won't conflict
3. **Security**: GUIDs make it harder to manipulate paths through drive letter spoofing

Volume GUID paths follow this format: `\\?\Volume{GUID}\path\to\file`

## Usage

### Basic Usage

```python
from activity.collectors.storage.ntfs.ntfs_collector import NtfsStorageActivityCollector
from activity.recorders.storage.ntfs.ntfs_recorder import NtfsStorageActivityRecorder

# Create a collector (volume GUIDs used by default)
collector = NtfsStorageActivityCollector(
    volumes=["C:"],
    auto_start=True
)

# Create a recorder
recorder = NtfsStorageActivityRecorder(
    collector=collector
)

# Collect and store activities
activity_ids = recorder.collect_and_store_activities()

# Stop monitoring when done
collector.stop_monitoring()
```

### Command-line Usage

```bash
# Basic monitoring (volume GUIDs used by default)
python -m activity.recorders.storage.ntfs.ntfs_recorder --volume C: --duration 60

# Disable volume GUIDs if needed (not recommended)
python -m activity.recorders.storage.ntfs.ntfs_recorder --volume C: --no-volume-guids --duration 60

# Run in mock mode (for testing)
python -m activity.recorders.storage.ntfs.ntfs_recorder --mock --debug

# Run without database connection
python -m activity.recorders.storage.ntfs.ntfs_recorder --no-db --volume C:

# Show all options
python -m activity.recorders.storage.ntfs.ntfs_recorder --help
```

### Mock Mode

For testing on non-Windows platforms or in environments where USN journal access is not available, use mock mode:

```python
collector = NtfsStorageActivityCollector(
    mock=True,
    auto_start=True
)
```

## Testing

Three test scripts are provided to verify functionality:

1. **test_ntfs_collector.py**: Unit tests for the collector with emphasis on volume GUID mapping
2. **test_ntfs_recorder.py**: Unit tests for the recorder focusing on collection registration
3. **test_registration.py**: Verification of service registration and collection creation

Run the tests with:

```bash
# Test collector
python -m activity.collectors.storage.ntfs.test_ntfs_collector

# Test recorder
python -m activity.recorders.storage.ntfs.test_ntfs_recorder

# Test registration
python -m activity.recorders.storage.ntfs.test_registration
```

## Integration with Activity Context

The NTFS activity recorder integrates with Indaleko's Activity Context system, enabling:

- Cross-source activity correlation
- Enhanced temporal context for file activities
- Activity classification and pattern detection
- Timeline-based file operation analysis

## Future Enhancements

- Support for extended attributes and alternate data streams
- More sophisticated activity correlation between files
- Intelligent filtering based on file type and usage patterns
- Deeper integration with the Windows Activity Timeline
- Automated indexing of frequently accessed paths
EOF < /dev/null
