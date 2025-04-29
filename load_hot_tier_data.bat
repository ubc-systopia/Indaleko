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
