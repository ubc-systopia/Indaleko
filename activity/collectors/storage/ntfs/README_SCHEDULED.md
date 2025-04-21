# NTFS USN Journal Collector: Scheduled Collection Guide

This document outlines how to set up and run the NTFS USN Journal collector as a scheduled task for continuous collection of file system activities.

## Overview

The NTFS USN Journal collector captures file system activity by reading the NTFS Update Sequence Number (USN) Journal. This journal tracks all changes to files and directories on NTFS volumes, providing a comprehensive record of file system activities.

Running this collector as a scheduled task allows Indaleko to maintain an up-to-date record of file activities without requiring constant manual intervention.

## Prerequisites

- Windows operating system (Windows 10/11 or Windows Server)
- NTFS formatted volumes
- Administrative access for USN journal reading
- Python 3.12 or newer
- Indaleko virtual environment properly configured

## Setup for Scheduled Collection

### 1. Configuration

Create a configuration file `ntfs_collector_config.json` in your Indaleko config directory:

```json
{
  "volumes": ["C:", "D:"],
  "state_file": "C:/path/to/indaleko/data/ntfs_usn_state.json",
  "output_file": "C:/path/to/indaleko/data/ntfs_activities.jsonl",
  "direct_to_db": true,
  "db_config": {
    "use_default": true
  },
  "log_file": "C:/path/to/indaleko/logs/ntfs_collector.log",
  "log_level": "INFO",
  "max_batch_size": 1000,
  "throttle_sleep": 0.1
}
```

### 2. Creating the Task Scheduler Job

#### Manual Setup

1. Open Task Scheduler (taskschd.msc)
2. Click "Create Basic Task"
3. Name: "Indaleko NTFS Activity Collector"
4. Description: "Collects file system activities from NTFS volumes"
5. Trigger: Daily, recur every 1 day
6. Action: Start a program
7. Program/script: `C:\path\to\indaleko\.venv-win32-python3.12\Scripts\python.exe`
8. Arguments: `C:\path\to\indaleko\activity\collectors\storage\ntfs\usn_journal_collector.py --config "C:\path\to\indaleko\config\ntfs_collector_config.json"`
9. Configure advanced settings:
   - Run with highest privileges: Checked
   - Configure for: Windows 10/11
   - Run task as soon as possible after a scheduled start is missed: Checked
   - Stop task if it runs longer than: 30 minutes
   - If the task fails, restart every: 5 minutes, attempt to restart up to 3 times

#### Using PowerShell Script

Save this as `setup_ntfs_collector_task.ps1`:

```powershell
# Setup NTFS Collector scheduled task
$taskName = "Indaleko NTFS Activity Collector"
$taskDescription = "Collects file system activities from NTFS volumes"

# Update these paths to match your environment
$indalekoPython = "C:\path\to\indaleko\.venv-win32-python3.12\Scripts\python.exe"
$collectorScript = "C:\path\to\indaleko\activity\collectors\storage\ntfs\usn_journal_collector.py"
$configFile = "C:\path\to\indaleko\config\ntfs_collector_config.json"

# Create action
$action = New-ScheduledTaskAction -Execute $indalekoPython -Argument "$collectorScript --config $configFile"

# Create trigger for frequent runs (every 15 minutes)
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 15) -RepetitionDuration (New-TimeSpan -Days 365)

# Create settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

# Create principal (run with highest privileges)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

# Register the task
Register-ScheduledTask -TaskName $taskName -Description $taskDescription -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force
```

Run the script with administrative privileges to create the scheduled task.

### 3. Monitoring Collection

The collector writes detailed logs to the configured log file. You can monitor these logs for any issues:

```powershell
Get-Content -Path "C:\path\to\indaleko\logs\ntfs_collector.log" -Tail 20 -Wait
```

You can also check the Task Scheduler history to verify that the task is running as expected.

### 4. Performance Tuning

If the collector is impacting system performance:

1. Adjust `max_batch_size` to control how many events are processed at once
2. Increase `throttle_sleep` to add more delay between batches
3. Schedule the task to run during periods of low system activity
4. Consider excluding high-churn directories like browser caches

## Implementation Enhancements for Scheduled Running

The collector has been enhanced for reliable scheduled execution:

1. **Robust State Management**:
   - State is persisted between runs in the configured state file
   - Last processed USN position is tracked per volume
   - Handles journal reset scenarios

2. **Error Handling and Recovery**:
   - Graceful handling of volume access issues
   - Recovery from database connection failures
   - Proper exception logging

3. **Resource Management**:
   - Batched processing to control memory usage
   - Configurable throttling to limit CPU impact
   - Timeout handling to prevent task hangs

4. **Locking Mechanism**:
   - File-based locking prevents concurrent execution
   - Graceful cleanup of lock files
   - Detection of abandoned locks

## Troubleshooting

### Common Issues

1. **Task fails immediately**:
   - Check that Python path is correct
   - Verify script path is accessible
   - Ensure configuration file exists

2. **Permission errors**:
   - Make sure task is running with administrative privileges
   - Check that volumes are accessible

3. **Database connection failures**:
   - Verify ArangoDB is running
   - Check database credentials
   - Ensure network connectivity if using remote database

4. **Missing or partial data**:
   - Verify USN journal is enabled on volumes
   - Check for journal wrapping (insufficient journal size)
   - Look for errors in collector log file

### Getting Help

If you encounter persistent issues:

1. Check the full log file for detailed error messages
2. Verify that the state file is being updated correctly
3. Test running the collector manually with the `--verbose` flag
4. Consult the Indaleko documentation or seek assistance from the development team

## Advanced Configuration

### Monitoring Multiple Volumes

To monitor multiple volumes, simply list them in the config file:

```json
"volumes": ["C:", "D:", "E:"]
```

### Filtering Specific Directories

You can add exclusion patterns to reduce noise:

```json
"exclusions": [
  "C:\\Windows\\Temp\\*",
  "C:\\Users\\*\\AppData\\Local\\Temp\\*",
  "C:\\Users\\*\\AppData\\Local\\Google\\Chrome\\*"
]
```

### Configuring Hot Tier Integration

For tiered storage integration:

```json
"hot_tier": {
  "enabled": true,
  "ttl_days": 4,
  "importance_threshold": 0.3
}
```

## Contact

For assistance with this collector, contact the Indaleko development team.