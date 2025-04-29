@echo off
rem Batch script wrapper for record_ntfs_activity.py
rem
rem This script provides a convenient way to run the NTFS activity recorder
rem on Windows systems. It ensures the proper Python environment is activated
rem before running the recorder.
rem
rem Usage:
rem   record_ntfs_activity.bat --input activities.jsonl [additional options]
rem
rem Project Indaleko
rem Copyright (C) 2024-2025 Tony Mason
rem

rem Change to the script directory
cd /d "%~dp0"

rem Activate virtual environment if it exists
if exist .venv-win32-python3.12\Scripts\activate.bat (
    echo Activating virtual environment: .venv-win32-python3.12
    call .venv-win32-python3.12\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found: .venv-win32-python3.12
    echo Using system Python instead
)

rem Run the recorder CLI
echo Running NTFS activity recorder...
python record_ntfs_activity.py %*

rem Return exit code from Python
exit /b %ERRORLEVEL%
