@echo off
REM Verification script wrapper for NtfsHotTierRecorder implementation
REM This script runs the verify_hot_tier.py script with appropriate arguments

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"

REM Change to the project root directory
cd /d "%SCRIPT_DIR%../../../../../../.."

REM Activate virtual environment if it exists
if exist ".venv-win32-python3.12\Scripts\activate.bat" (
    call .venv-win32-python3.12\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Set default values
set "DATABASE_URL=http://localhost:8529"
set "DATABASE=indaleko"
set "USERNAME=root"
set "PASSWORD="
set "DRY_RUN="
set "FIND_FILES="
set "LOAD_DATA="
set "VERIFY_ENTITIES="
set "TEST_TTL="
set "BENCHMARK="
set "QUERY_TEST="
set "FULL_VERIFICATION="
set "VERBOSE="
set "LIMIT="
set "FILE="
set "PATH_TO_SEARCH="

REM Parse command line arguments
:parse
if "%1"=="" goto execute

if "%1"=="--database-url" (
    set "DATABASE_URL=%2"
    shift
    shift
    goto parse
)
if "%1"=="--database" (
    set "DATABASE=%2"
    shift
    shift
    goto parse
)
if "%1"=="--username" (
    set "USERNAME=%2"
    shift
    shift
    goto parse
)
if "%1"=="--password" (
    set "PASSWORD=%2"
    shift
    shift
    goto parse
)
if "%1"=="--dry-run" (
    set "DRY_RUN=--dry-run"
    shift
    goto parse
)
if "%1"=="--find-files" (
    set "FIND_FILES=--find-files"
    shift
    goto parse
)
if "%1"=="--path" (
    set "PATH_TO_SEARCH=%2"
    shift
    shift
    goto parse
)
if "%1"=="--load-data" (
    set "LOAD_DATA=--load-data"
    shift
    goto parse
)
if "%1"=="--verify-entities" (
    set "VERIFY_ENTITIES=--verify-entities"
    shift
    goto parse
)
if "%1"=="--test-ttl" (
    set "TEST_TTL=--test-ttl"
    shift
    goto parse
)
if "%1"=="--benchmark" (
    set "BENCHMARK=--benchmark"
    shift
    goto parse
)
if "%1"=="--query-test" (
    set "QUERY_TEST=--query-test"
    shift
    goto parse
)
if "%1"=="--full-verification" (
    set "FULL_VERIFICATION=--full-verification"
    shift
    goto parse
)
if "%1"=="--verbose" (
    set "VERBOSE=--verbose"
    shift
    goto parse
)
if "%1"=="--limit" (
    set "LIMIT=--limit %2"
    shift
    shift
    goto parse
)
if "%1"=="--file" (
    set "FILE=--file %2"
    shift
    shift
    goto parse
)
if "%1"=="--help" (
    echo Usage: %0 [options]
    echo.
    echo Options:
    echo   --database-url URL      ArangoDB server URL (default: http://localhost:8529^)
    echo   --database NAME         Database name (default: indaleko^)
    echo   --username USER         Database username (default: root^)
    echo   --password PASS         Database password
    echo   --dry-run               Simulate operations without affecting database
    echo   --find-files            Find JSONL files with NTFS activity data
    echo   --path DIR              Path to search for JSONL files
    echo   --load-data             Load activity data to database
    echo   --verify-entities       Verify entity mapping functionality
    echo   --test-ttl              Test TTL expiration
    echo   --benchmark             Run performance benchmarks
    echo   --query-test            Test query capabilities
    echo   --full-verification     Run all verification steps
    echo   --verbose               Enable verbose output
    echo   --limit N               Limit the number of records to process
    echo   --file FILE             Specific JSONL file to process
    echo   --help                  Show this help message
    exit /b 0
)

echo Unknown option: %1
echo Use --help for usage information
exit /b 1

:execute
REM Build command
set "CMD=python activity/recorders/storage/ntfs/tiered/hot/verify_hot_tier.py"
set "CMD=%CMD% --database-url %DATABASE_URL%"
set "CMD=%CMD% --database %DATABASE%"
set "CMD=%CMD% --username %USERNAME%"

if not "%PASSWORD%"=="" (
    set "CMD=%CMD% --password %PASSWORD%"
)

if not "%DRY_RUN%"=="" (
    set "CMD=%CMD% %DRY_RUN%"
)

if not "%FIND_FILES%"=="" (
    set "CMD=%CMD% %FIND_FILES%"
)

if not "%PATH_TO_SEARCH%"=="" (
    set "CMD=%CMD% --path "%PATH_TO_SEARCH%""
)

if not "%LOAD_DATA%"=="" (
    set "CMD=%CMD% %LOAD_DATA%"
)

if not "%VERIFY_ENTITIES%"=="" (
    set "CMD=%CMD% %VERIFY_ENTITIES%"
)

if not "%TEST_TTL%"=="" (
    set "CMD=%CMD% %TEST_TTL%"
)

if not "%BENCHMARK%"=="" (
    set "CMD=%CMD% %BENCHMARK%"
)

if not "%QUERY_TEST%"=="" (
    set "CMD=%CMD% %QUERY_TEST%"
)

if not "%FULL_VERIFICATION%"=="" (
    set "CMD=%CMD% %FULL_VERIFICATION%"
)

if not "%VERBOSE%"=="" (
    set "CMD=%CMD% %VERBOSE%"
)

if not "%LIMIT%"=="" (
    set "CMD=%CMD% %LIMIT%"
)

if not "%FILE%"=="" (
    set "CMD=%CMD% %FILE%"
)

REM Print command if verbose
if not "%VERBOSE%"=="" (
    echo Running command: %CMD%
)

REM Execute command
%CMD%
