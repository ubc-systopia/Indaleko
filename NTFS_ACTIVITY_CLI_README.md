# NTFS Activity CLI Template Implementation

This document describes the implementation of the NTFS Activity Collection and Recording script using the Indaleko CLI Template framework.

## Overview

The NTFS Activity Collector (`run_ntfs_activity_v2.py`) gathers and records file system activities on Windows systems. This implementation follows the Indaleko CLI template pattern while maintaining the architectural separation between collection and recording.

## Features

- **Proper Architectural Separation**: Maintains clear boundaries between collection and recording responsibilities
- **Real-time Activity Monitoring**: Tracks NTFS USN journal activities on specified volumes
- **Database Storage**: Records activities to the hot tier for efficient querying
- **File Backup**: Optionally stores activities in rotating JSONL files
- **Resilient Operation**: Automatic recovery from errors and empty collection cycles
- **Configurable Runtime**: Adjustable duration, collection intervals, and retention periods
- **CLI Template Integration**: Uses the standardized Indaleko CLI framework for consistent behavior
- **Platform Validation**: Proper platform checking to ensure compatibility

## Implementation Details

The original script (`run_ntfs_activity.py`) has been reimplemented using the CLI template pattern as `run_ntfs_activity_v2.py`. This demonstrates how existing CLI tools can be migrated to use the standard CLI template framework.

### Key Improvements

The CLI template implementation provides several advantages over the original script:

1. **Standardized Argument Handling** - Uses the common CLI argument parsing infrastructure
2. **Centralized Logging System** - Uses the new YAML-based logging configuration with unified console and file handlers
3. **Platform Verification** - Clear error messaging for platform-specific requirements
4. **Structured Error Handling** - Better error reporting and management
5. **Consistent File Naming** - Uses standard file naming conventions for logs and outputs
6. **Performance Monitoring** - Optional integration with performance tracking framework
7. **Type Safety** - Full type annotations throughout the code
8. **File Rotation** - Improved file rotation mechanism for backups
9. **Error Recovery** - Improved error recovery with configurable thresholds

### File Structure

- `run_ntfs_activity_v2.py` - The main script using the CLI template
- `NtfsActivityHandlerMixin` - Custom handler mixin defining CLI behavior
- `IntegratedNtfsActivityRunner` - The core implementation class (retained from original)

## Usage Examples

Basic usage:
```bash
python run_ntfs_activity_v2.py --volumes C: --duration 24 --interval 30
```

With debugging enabled:
```bash
python run_ntfs_activity_v2.py --debug --volumes C: --duration 24
```

File backup options:
```bash
python run_ntfs_activity_v2.py --no-file-backup --db-config-path config/custom-db-config.ini
```

Output configuration:
```bash
python run_ntfs_activity_v2.py --output-dir data/custom_path --max-file-size 200
```

Long-running collection with automatic error recovery:
```bash
python run_ntfs_activity_v2.py --volumes C: D: --duration 168 --error-threshold 5 --empty-threshold 10
```

### Command-Line Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--volumes` | `C:` | List of volumes to monitor for NTFS activity |
| `--duration` | `24` | Duration to run in hours (0 for unlimited) |
| `--interval` | `15` | Collection interval in seconds |
| `--ttl-days` | `4` | Number of days to keep data in hot tier |
| `--db-config-path` | (default path) | Path to database configuration file |
| `--no-file-backup` | (disabled) | Disable backup to files (database only) |
| `--output-dir` | `data/ntfs_activity` | Directory for file backups |
| `--max-file-size` | `100` | Maximum backup file size in MB before rotation |
| `--no-auto-reset` | (disabled) | Disable automatic state reset on persistent errors |
| `--error-threshold` | `3` | Number of consecutive errors before reset |
| `--empty-threshold` | `3` | Number of consecutive empty results before reset |
| `--use-state-file` | (disabled) | Enable state file persistence |
| `--debug` | (disabled) | Enable verbose logging and allow running on non-Windows platforms |
| `--logdir` | `logs` | Directory for log files |

## Architecture Details

### Collector/Recorder Separation

This implementation maintains proper separation of concerns:

- **NtfsUsnJournalCollector**: Only responsible for collecting raw activities
- **NtfsHotTierRecorder**: Only responsible for processing and storing activities

The integration point is the `_record_activities` method which passes collected data to the recorder, maintaining clear boundaries between responsibilities.

### Logging System

The implementation uses the new centralized logging system:

- **YAML-based Configuration**: Uses the repository-wide `logging.yaml` config
- **Unified Log Formats**: Consistent formatting across all CLI tools
- **Console & File Handlers**: Logs to both console and rotating files
- **Debug-level Control**: Automatically adjusts log level based on `--debug` flag
- **Module-specific Loggers**: Uses `logging.getLogger(__name__)` for component isolation

### Error Handling

The implementation includes comprehensive error handling:

- Recovers from collection errors with configurable thresholds
- Falls back to file-only mode if database connection fails
- Properly handles recursion errors in the USN Journal processing
- Uses timezone-aware datetimes throughout for database compatibility
- Provides detailed statistics upon completion

## Migration Strategy

When migrating an existing CLI script to the template pattern, follow these steps:

1. **Create a new file** - Don't modify the existing script until the new one is tested
2. **Implement the handler mixin** - Define command-line arguments and behavior
3. **Preserve core logic** - Keep the actual implementation classes unchanged
4. **Add platform checks** - Include explicit checks for platform requirements
5. **Test thoroughly** - Ensure all functionality works as expected

## Benefits of Using the CLI Template

- **Consistency** - All CLI tools share the same command-line interface pattern
- **Maintainability** - Easier to understand and modify
- **Extensibility** - Add new features without changing the core structure
- **Error handling** - Improved error reporting and diagnostics
- **Logging** - Standardized logging configuration
- **Configuration** - Consistent handling of configuration files
- **Type Safety** - Better static type checking and IDE integration
- **Standardization** - Common patterns for similar operations

## Future Improvements

1. **Backup Data Import** - Add ability to import backed-up data files
2. **Entity Mapping** - Implement improved entity resolution logic
3. **Progress Tracking** - Add detailed progress reporting for long-running sessions
4. **Automatic Optimization** - Integrate with database optimization routines
5. **Filtering** - Add support for filtering specific file types

## Next Steps

1. **Test on Windows** - Verify full functionality on Windows platforms
2. **Add automated tests** - Create unit tests for the CLI interface
3. **Migrate more scripts** - Apply this pattern to other CLI tools in the project

## Related Documentation

- **Collector Documentation**: `activity/collectors/storage/ntfs/README.md`
- **Recorder Documentation**: `activity/recorders/storage/ntfs/tiered/hot/README.md`
- **CLI Template**: `tools/cli_template/README.md`
- **Entity Mapping**: `activity/recorders/storage/ntfs/ENTITY_MAPPING.md`