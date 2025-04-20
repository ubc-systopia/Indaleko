@echo off
REM
REM Load NTFS activity data into the hot tier database
REM
REM This script provides an easy way to run the NTFS Hot Tier Recorder
REM with common options.
REM
REM Project Indaleko
REM Copyright (C) 2024-2025 Tony Mason
REM

setlocal

REM Get the directory of this script
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Set INDALEKO_ROOT environment variable
set "INDALEKO_ROOT=%SCRIPT_DIR%"

REM Check for Python virtual environment and activate it
if exist "%SCRIPT_DIR%\.venv-win32-python3.12\Scripts\activate.bat" (
  echo Activating Windows Python 3.12 environment
  call "%SCRIPT_DIR%\.venv-win32-python3.12\Scripts\activate.bat"
) else if exist "%SCRIPT_DIR%\.venv-win32\Scripts\activate.bat" (
  echo Activating Windows Python environment
  call "%SCRIPT_DIR%\.venv-win32\Scripts\activate.bat"
) else if exist "%SCRIPT_DIR%\.venv\Scripts\activate.bat" (
  echo Activating Python environment
  call "%SCRIPT_DIR%\.venv\Scripts\activate.bat"
) else (
  echo Warning: No Python virtual environment found. Script may fail if dependencies are missing.
)

REM Add project root to Python path
set "PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%"

REM Help message function
if "%1"=="--help" goto :show_help
goto :main

:show_help
echo Usage: %0 [options]
echo.
echo Options:
echo   --help          Show this help message
echo   --list          List available NTFS activity files
echo   --simulate      Run in simulation mode (no database connection)
echo   --dry-run       Analyze files but don't load to database
echo   --all           Process all NTFS activity files found
echo   --report        Generate a summary report
echo   --file FILE     Process a specific JSONL file
echo   --ttl-days N    Set hot tier TTL to N days (default: 4)
echo   --verbose       Show more detailed output
echo.
echo Examples:
echo   %0 --list               # List available activity files
echo   %0 --simulate --report  # Test without affecting database
echo   %0 --all --report       # Process all files with report
echo   %0 --file path\to\file.jsonl  # Process specific file
goto :end

:main
REM Parse command line arguments
if "%1"=="" (
  REM No arguments, use default settings
  python "%SCRIPT_DIR%\activity\recorders\storage\ntfs\tiered\hot\load_to_database.py" --simulate
) else (
  REM Pass all arguments to the Python script
  python "%SCRIPT_DIR%\activity\recorders\storage\ntfs\tiered\hot\load_to_database.py" %*
)

:end
endlocal