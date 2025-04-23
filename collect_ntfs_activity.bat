@echo off
setlocal EnableDelayedExpansion

REM NTFS Activity Generator for Indaleko
REM Collects NTFS file system activities

REM Default parameters
set VOLUMES=C:
set DURATION=24
set INTERVAL=30
set OUTPUT_DIR=data\ntfs_activity
set MAX_FILE_SIZE=100
set VERBOSE=false
set RESET_STATE=false
set CONTINUE_ON_ERROR=false

REM Parse command line arguments
:parse_args
if "%~1"=="" goto :end_parse_args
if /i "%~1"=="--volumes" set VOLUMES=%~2& shift & shift & goto :parse_args
if /i "%~1"=="--duration" set DURATION=%~2& shift & shift & goto :parse_args
if /i "%~1"=="--interval" set INTERVAL=%~2& shift & shift & goto :parse_args
if /i "%~1"=="--output-dir" set OUTPUT_DIR=%~2& shift & shift & goto :parse_args
if /i "%~1"=="--max-file-size" set MAX_FILE_SIZE=%~2& shift & shift & goto :parse_args
if /i "%~1"=="--verbose" set VERBOSE=true& shift & goto :parse_args
if /i "%~1"=="--reset-state" set RESET_STATE=true& shift & goto :parse_args
if /i "%~1"=="--continue-on-error" set CONTINUE_ON_ERROR=true& shift & goto :parse_args
if /i "%~1"=="--help" goto :show_help
echo Unknown option: %~1
goto :show_help
:end_parse_args

REM Check if running as Administrator
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: This script requires Administrator privileges.
    echo Please right-click on the Command Prompt and select "Run as administrator".
    exit /b 1
)

REM Check if Python is available
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: Python is not in the PATH. Please add it and try again.
    exit /b 1
)

REM Activate virtual environment if available
if exist .venv-win32-python3.12\Scripts\activate.bat (
    echo Activating virtual environment: .venv-win32-python3.12
    call .venv-win32-python3.12\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found: .venv-win32-python3.12
    echo Using system Python instead
)

REM Ensure output directory exists
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

REM Build command line
set CMD=python activity\collectors\storage\ntfs\activity_generator.py --volumes %VOLUMES% --duration %DURATION% --interval %INTERVAL% --output-dir %OUTPUT_DIR% --max-file-size %MAX_FILE_SIZE%

REM Add optional flags
if "%VERBOSE%"=="true" set CMD=%CMD% --verbose
if "%RESET_STATE%"=="true" set CMD=%CMD% --reset-state
if "%CONTINUE_ON_ERROR%"=="true" set CMD=%CMD% --continue-on-error

REM Display command
echo.
echo ============================================================
echo     NTFS Activity Generator for Indaleko
echo ============================================================
echo.
echo Starting NTFS Activity Generator with the following settings:
echo   Volumes:            %VOLUMES%
echo   Duration:           %DURATION% hours
echo   Interval:           %INTERVAL% seconds
echo   Output Dir:         %OUTPUT_DIR%
echo   Max File:           %MAX_FILE_SIZE% MB
echo   Verbose:            %VERBOSE%
echo   Reset State:        %RESET_STATE%
echo   Continue On Error:  %CONTINUE_ON_ERROR%
echo.
echo Press Ctrl+C to interrupt the collection at any time.
echo.
echo Starting collection process...
echo.

REM Run the command
%CMD%

echo.
echo Collection completed.
echo To record the collected data to the database, use:
echo record_ntfs_activity.bat --input [json_file_path]
echo Example: record_ntfs_activity.bat --input %OUTPUT_DIR%\ntfs_activity_20250422_123456.jsonl

exit /b 0

:show_help
echo.
echo NTFS Activity Generator for Indaleko
echo Usage: collect_ntfs_activity.bat [options]
echo.
echo Options:
echo   --volumes VOLUMES          Comma-separated list of volumes to monitor (default: C:)
echo   --duration HOURS           Duration to run in hours (default: 24, 0 for unlimited)
echo   --interval SECONDS         Collection interval in seconds (default: 30)
echo   --output-dir DIR           Directory to store output files (default: data\ntfs_activity)
echo   --max-file-size MB         Maximum JSONL file size in MB before rotation (default: 100)
echo   --verbose                  Enable verbose logging
echo   --reset-state              Reset the USN journal state file (useful after journal rotation)
echo   --continue-on-error        Continue processing when non-critical errors occur
echo   --help                     Show this help message
echo.
echo Examples:
echo   collect_ntfs_activity.bat --volumes C:,D: --duration 48
echo   collect_ntfs_activity.bat --interval 60 --verbose
echo.
echo Note: This script must be run with Administrator privileges for NTFS access.
echo       To record the collected data to the database, use record_ntfs_activity.bat afterward.
echo.
exit /b 0
