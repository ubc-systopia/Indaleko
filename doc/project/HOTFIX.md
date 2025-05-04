# NTFS Activity Collection and Recording: Architectural Refactoring and Robustness Improvements

## Overview

This hotfix addresses critical issues with the NTFS activity collection and recording system:

1. **Architectural Alignment**: Fixed violations of the Collector/Recorder pattern where collection and recording responsibilities were mixed in a single component.

2. **Error Handling**: Implemented robust error handling for USN journal rotation to ensure continuous data collection and prevent failures when the journal overwrites older entries.

3. **Command Line Interface**: Added new options to reset state and continue processing despite errors, improving resilience in production environments.

## Changes Made

### 1. Separated Collection and Recording Functionality

- Created a dedicated recorder CLI script: `record_ntfs_activity.py`
- Created shell script wrappers: `record_ntfs_activity.sh` and `record_ntfs_activity.bat`
- Created a dedicated recorder implementation: `ntfs_recorder_cli.py`
- Removed recorder-related code from `activity_generator.py`
- Updated `collect_ntfs_activity.sh` and `collect_ntfs_activity.bat` to focus solely on collection

### 2. Implemented Proper Wrapper Pattern for Integration

- Created an integrated runner: `run_ntfs_activity.py` that properly maintains separation of concerns
- Added script wrappers: `run_ntfs_activity.sh` and `run_ntfs_activity.bat`
- Ensured the integrated approach follows architectural principles by maintaining clear separation of responsibilities
- Implemented memory-based interface between collector and recorder for continuous operation

### 3. Improved Architectural Alignment

- Ensured proper separation of concerns between collectors and recorders
- Implemented file-based and memory-based interfaces for communication between components
- Added clear documentation about the separation of responsibilities
- Enhanced CLI help messages to guide users through the workflow options

## Multiple Workflow Options

The refactoring now supports multiple workflow options to accommodate different use cases:

### 1. Separate Collection and Recording (Batch Processing)

This approach is best for scenarios where you want to collect data and process it separately or on different machines.

1. **Collection**: Run `collect_ntfs_activity.sh` (or `.bat`) to collect NTFS activities to JSONL files
2. **Recording**: Run `record_ntfs_activity.sh` (or `.bat`) to process JSONL files and record to the database

### 2. Integrated Collection and Recording (Continuous Processing)

This approach is best for long-running data collection (days or weeks) where you want a single command to handle both collection and recording.

1. **Run Integrated**: `run_ntfs_activity.sh` (or `.bat`) to collect and record in a single process

## Benefits

- **Architectural Integrity**: Proper separation of concerns between collection and recording
- **Modularity**: Each component has a clear, focused responsibility
- **Flexibility**: Multiple workflow options to accommodate different use cases
- **Reliability**: Registration issues are resolved by handling registration properly in dedicated recorder components
- **Maintainability**: Simplified code with clearer responsibilities is easier to maintain

## Usage

### Option 1: Separate Collection and Recording

#### Collect NTFS Activities

```bash
# Linux/macOS - Basic usage
./collect_ntfs_activity.sh --volumes C: --duration 24 --interval 30 --output-dir data/ntfs_activity

# Linux/macOS - With error handling and reset options
./collect_ntfs_activity.sh --volumes C: --reset-state --continue-on-error --verbose

# Windows - Basic usage
collect_ntfs_activity.bat --volumes C: --duration 24 --interval 30 --output-dir data\ntfs_activity

# Windows - With error handling and reset options
collect_ntfs_activity.bat --volumes C: --reset-state --continue-on-error --verbose
```

#### Record Activities to Database

```bash
# Linux/macOS
./record_ntfs_activity.sh --input data/ntfs_activity/ntfs_activity_20250422_123456.jsonl --statistics

# Windows
record_ntfs_activity.bat --input data\ntfs_activity\ntfs_activity_20250422_123456.jsonl --statistics
```

### Option 2: Integrated Collection and Recording

```bash
# Linux/macOS - Basic usage
./run_ntfs_activity.sh --volumes C: --duration 168 --interval 30 --verbose

# Linux/macOS - With error handling options
./run_ntfs_activity.sh --volumes C: --reset-state --continue-on-error --verbose

# Windows - Basic usage
run_ntfs_activity.bat --volumes C: --duration 168 --interval 30 --verbose

# Windows - With error handling options
run_ntfs_activity.bat --volumes C: --reset-state --continue-on-error --verbose
```

### Error Recovery Options

For handling issues with the USN journal, use these options:

```bash
# Reset state after journal rotation (starts fresh from current journal position)
./collect_ntfs_activity.sh --reset-state --verbose

# Continue processing despite non-critical errors (good for unattended operation)
./collect_ntfs_activity.sh --continue-on-error --verbose

# Both options together for maximum resilience
./collect_ntfs_activity.sh --reset-state --continue-on-error --verbose
```

## Testing

### Testing the Integrated Approach

```bash
# Run for a short duration to test functionality
./run_ntfs_activity.sh --volumes C: --duration 0.1 --interval 10 --verbose
```

### Testing the Separate Components

1. Run the collector to generate JSONL files:
   ```
   ./collect_ntfs_activity.sh --duration 0.1 --interval 10
   ```

2. Record the collected data to the database:
   ```
   ./record_ntfs_activity.sh --input <path_to_generated_jsonl> --statistics
   ```

3. Verify that activities are properly recorded in the database using the statistics output.

### Testing USN Journal Error Handling

To test the journal rotation error handling:

1. **Simulate Journal Rotation**:
   ```bash
   # Force state reset to a very old USN value that's likely been rotated
   python -c "import json; f=open('data/ntfs_activity/ntfs_state.json', 'w'); json.dump({'last_usn_positions': {'C:': 1000}, 'timestamp': '2025-04-22T12:00:00Z', 'provider_id': '7d8f5a92-35c7-41e6-b13d-6c4e89e7f2a5'}, f); f.close()"
   ```

2. **Run Collection with Continue-on-Error**:
   ```bash
   ./collect_ntfs_activity.sh --continue-on-error --verbose
   ```

3. **Expected Behavior**:
   - The collector should detect that the requested journal entry has been deleted
   - It should automatically reset to the lowest valid USN
   - Collection should continue from that point
   - Log messages should indicate the recovery from journal rotation

4. **Verify Recovery**:
   ```bash
   # Check that state file now has a valid USN position
   python -c "import json; f=open('data/ntfs_activity/ntfs_state.json'); print(json.load(f)); f.close()"
   ```

5. **Test Manual Reset**:
   ```bash
   # Manual reset if needed
   ./collect_ntfs_activity.sh --reset-state --verbose
   ```

## Recent Improvements (April 2025)

### 1. Robust USN Journal Error Handling

The USN Journal collector has been enhanced to gracefully handle journal rotation scenarios:

- **Problem**: When the USN journal (a circular buffer) overwrites older entries, the collector would fail with "journal entry has been deleted" errors
- **Solution**: Implemented automatic detection and recovery from journal rotation by:
  - Detecting specific error codes related to journal entry deletion
  - Automatically resetting to the lowest valid USN position
  - Providing CLI flags to manually reset state when needed
  - Adding continue-on-error options for production environments

### 2. Enhanced Command-Line Interface

Added new options to improve usability and handle error scenarios:

- `--reset-state`: Reset the USN journal state file to start fresh (useful after large journal rotations)
- `--continue-on-error`: Continue processing when non-critical errors occur (recommended for production)

Example usage:
```bash
./collect_ntfs_activity.sh --volumes C: --reset-state --continue-on-error
```

### 3. Improved State Management

- Added proper state file handling with reset capabilities
- Enhanced error detection and recovery for the USN journal reader
- Implemented graceful shutdown and state persistence
- Added detailed logging to improve traceability

## Previous Issues Fixed

In earlier versions, we addressed these issues:

1. **Fixed IndalekoRecordDataModel Validation Error**

   In the NtfsHotTierRecorder class in `activity/recorders/storage/ntfs/tiered/hot/recorder.py`, there was an incorrect field name used when creating the IndalekoRecordDataModel:

   ```python
   # BEFORE: Incorrect field names
   record = IndalekoRecordDataModel(
       SourceId=source_identifier,  # Wrong field name
       Timestamp=datetime.now(UTC),
       Data={},  # Wrong data type (should be encoded string)
   )

   # AFTER: Corrected field names and properly encoded data
   # Import data management utilities
   from utils.misc.data_management import encode_binary_data

   record = IndalekoRecordDataModel(
       SourceIdentifier=source_identifier,  # Correct field name
       Timestamp=datetime.now(UTC),
       Data=encode_binary_data(json.dumps({}).encode('utf-8')),  # Properly encoded data using encode_binary_data
   )
   ```

   This fix ensures that the record model passes validation when being registered with the service manager.

2. **Restored Missing NtfsUsnJournalCollector Class**

   The `usn_journal_collector.py` file was previously missing or corrupted, and we restored it from a backup file to ensure the NTFS collector functionality was available.

3. **Fixed TTL Index Creation in Hot Tier Recorder**

   Added robust error handling for TTL index creation to handle API variations in the ArangoDB drivers:

   ```python
   def _setup_ttl_index(self) -> None:
       """Set up TTL index for automatic expiration of hot tier data."""
       # Calculate TTL in seconds
       ttl_seconds = self._ttl_days * 24 * 60 * 60

       self._logger.info(
           "Setting up TTL index with %d day expiration (%d seconds)", self._ttl_days, ttl_seconds,
       )

       # Check if TTL index already exists
       existing_indices = self._collection.indexes()
       for index in existing_indices:
           if index.get("type") == "ttl":
               self._logger.info("TTL index already exists: %s", index)
               return

       # Create TTL index on ttl_timestamp field
       # Try different parameter names to handle API variations
       try:
           # First try with expireAfter (older versions)
           self._collection.add_ttl_index(
               fields=["Record.Data.ttl_timestamp"], expireAfter=ttl_seconds,
           )
       except TypeError:
           try:
               # Then try with ttl (newer versions)
               self._collection.add_ttl_index(
                   fields=["Record.Data.ttl_timestamp"], ttl=ttl_seconds,
               )
           except TypeError:
               # Finally fall back to positional arguments if needed
               self._logger.warning("Trying TTL index creation with positional arguments")
               self._collection.add_ttl_index(["Record.Data.ttl_timestamp"], ttl_seconds)

       self._logger.info("Created TTL index with %s day expiration", self._ttl_days)
   ```
