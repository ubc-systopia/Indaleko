@echo off
:: Run the Indaleko NTFS Tier Transition from hot to warm tier
:: This script manages the transition of file activity data between tiers
:: in the Indaleko tiered memory architecture.

setlocal enabledelayedexpansion

:: Set script directory as Indaleko root
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "INDALEKO_ROOT=%SCRIPT_DIR%"

:: Find the appropriate virtual environment
set "VENV_DIR="

if exist "%SCRIPT_DIR%\.venv-win32-python3.12" (
    set "VENV_DIR=%SCRIPT_DIR%\.venv-win32-python3.12"
) else if exist "%SCRIPT_DIR%\.venv-win32-python3.11" (
    set "VENV_DIR=%SCRIPT_DIR%\.venv-win32-python3.11"
) else if exist "%SCRIPT_DIR%\.venv-win32-python3.10" (
    set "VENV_DIR=%SCRIPT_DIR%\.venv-win32-python3.10"
)

:: Display error and exit if no virtual environment found
if "%VENV_DIR%"=="" (
    echo Error: No appropriate virtual environment found.
    echo Please run 'uv pip install -e .' to create the environment.
    exit /b 1
)

:: Activate the virtual environment
call "%VENV_DIR%\Scripts\activate.bat"

:: Parse command line arguments
set "STATS_ONLY=0"
set "RUN_TRANSITION=0"
set "VERBOSE=0"
set "DEBUG=0"
set "AGE_HOURS=12"
set "BATCH_SIZE=1000"
set "MAX_BATCHES=10"
set "DB_CONFIG="

:: Process command line arguments
:parse_args
if "%~1"=="" goto end_parse_args

if "%~1"=="--stats-only" (
    set "STATS_ONLY=1"
    shift
    goto parse_args
)
if "%~1"=="--run" (
    set "RUN_TRANSITION=1"
    shift
    goto parse_args
)
if "%~1"=="--verbose" (
    set "VERBOSE=1"
    shift
    goto parse_args
)
if "%~1"=="--debug" (
    set "DEBUG=1"
    shift
    goto parse_args
)
if "%~1"=="--age-hours" (
    set "AGE_HOURS=%~2"
    shift
    shift
    goto parse_args
)
if "%~1"=="--batch-size" (
    set "BATCH_SIZE=%~2"
    shift
    shift
    goto parse_args
)
if "%~1"=="--max-batches" (
    set "MAX_BATCHES=%~2"
    shift
    shift
    goto parse_args
)
if "%~1"=="--db-config" (
    set "DB_CONFIG=%~2"
    shift
    shift
    goto parse_args
)
if "%~1"=="--help" (
    echo Indaleko NTFS Tier Transition Utility
    echo.
    echo Usage: %0 [options]
    echo.
    echo Options:
    echo   --stats-only         Show tier transition statistics without running transition
    echo   --run                Run the tier transition
    echo   --verbose            Show more detailed output
    echo   --debug              Enable debug logging
    echo   --age-hours N        Age threshold in hours for transition (default: 12)
    echo   --batch-size N       Number of activities to process in each batch (default: 1000)
    echo   --max-batches N      Maximum number of batches to process (default: 10)
    echo   --db-config PATH     Path to database configuration file
    echo   --help               Show this help message
    echo.
    exit /b 0
)

echo Unknown option: %1
echo Use --help for usage information
exit /b 1

:end_parse_args

:: If neither stats-only nor run is specified, default to stats-only
if %STATS_ONLY%==0 if %RUN_TRANSITION%==0 (
    set "STATS_ONLY=1"
)

:: Build command arguments
set "COMMAND_ARGS="

if %STATS_ONLY%==1 (
    set "COMMAND_ARGS=!COMMAND_ARGS! --stats"
)

if %RUN_TRANSITION%==1 (
    set "COMMAND_ARGS=!COMMAND_ARGS! --run"
)

if %VERBOSE%==1 (
    set "COMMAND_ARGS=!COMMAND_ARGS! --verbose"
)

if %DEBUG%==1 (
    set "COMMAND_ARGS=!COMMAND_ARGS! --debug"
)

set "COMMAND_ARGS=!COMMAND_ARGS! --age-hours %AGE_HOURS% --batch-size %BATCH_SIZE% --max-batches %MAX_BATCHES%"

if not "%DB_CONFIG%"=="" (
    set "COMMAND_ARGS=!COMMAND_ARGS! --db-config "%DB_CONFIG%""
)

:: Run the tier transition utility
echo Running NTFS Tier Transition Utility...
echo.

python -m activity.recorders.storage.ntfs.tiered.tier_transition%COMMAND_ARGS%

:: Deactivate the virtual environment
call deactivate