@echo off
rem Batch script wrapper for the integrated NTFS activity runner
rem
rem This script provides a convenient way to run the integrated NTFS activity
rem collector and recorder on Windows systems. It maintains proper separation
rem of concerns while providing an integrated experience.
rem
rem Usage:
rem   run_ntfs_activity.bat [options]
rem
rem Common options:
rem   --volumes C: D:         Volumes to monitor
rem   --duration 24           Duration to run in hours
rem   --interval 30           Collection interval in seconds
rem   --ttl-days 4            Number of days to keep data in hot tier
rem   --no-file-backup        Disable backup to files (database only)
rem   --output-dir path       Directory for file backups (if enabled)
rem   --verbose               Enable verbose logging
rem
rem Project Indaleko
rem Copyright (C) 2024-2025 Tony Mason
rem

rem Change to the script directory
cd /d "%~dp0"

rem Check if running as Administrator
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: This script requires Administrator privileges.
    echo Please right-click on the Command Prompt and select "Run as administrator".
    exit /b 1
)

rem Activate virtual environment if it exists
if exist .venv-win32-python3.12\Scripts\activate.bat (
    echo Activating virtual environment: .venv-win32-python3.12
    call .venv-win32-python3.12\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found: .venv-win32-python3.12
    echo Using system Python instead
)

rem Run the integrated activity runner
echo Running integrated NTFS activity collector and recorder...
python run_ntfs_activity.py %*

rem Return exit code from Python
exit /b %ERRORLEVEL%
