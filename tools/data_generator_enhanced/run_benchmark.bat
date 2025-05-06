@echo off
REM Run the model-based data generator benchmark suite

setlocal enabledelayedexpansion

REM Activate virtual environment if it exists
if exist "%~dp0..\..\..\.venv-win32-python3.12\Scripts\activate.bat" (
    call "%~dp0..\..\..\.venv-win32-python3.12\Scripts\activate.bat"
)

REM Set PYTHONPATH to include the project root
set "PYTHONPATH=%~dp0..\..\..;%PYTHONPATH%"

REM Default configuration
set "CONFIG_FILE="
set "OUTPUT_DIR=benchmark_results"
set "SMALL_ONLY="
set "SKIP_LARGE="
set "REPORT_FORMATS=md json"
set "DOMAIN_SPECIFIC="
set "COMPARE_LEGACY="
set "REPEAT=1"
set "VERBOSE="

REM Parse arguments
:arg_loop
if "%~1"=="" goto :run_benchmark

if /i "%~1"=="--config" (
    set "CONFIG_FILE=%~2"
    shift
    shift
    goto :arg_loop
)

if /i "%~1"=="--output-dir" (
    set "OUTPUT_DIR=%~2"
    shift
    shift
    goto :arg_loop
)

if /i "%~1"=="--small-only" (
    set "SMALL_ONLY=--small-only"
    shift
    goto :arg_loop
)

if /i "%~1"=="--skip-large" (
    set "SKIP_LARGE=--skip-large"
    shift
    goto :arg_loop
)

if /i "%~1"=="--domain-specific" (
    set "DOMAIN_SPECIFIC=--domain-specific"
    shift
    goto :arg_loop
)

if /i "%~1"=="--compare-legacy" (
    set "COMPARE_LEGACY=--compare-legacy"
    shift
    goto :arg_loop
)

if /i "%~1"=="--repeat" (
    set "REPEAT=%~2"
    shift
    shift
    goto :arg_loop
)

if /i "%~1"=="--report-formats" (
    set "REPORT_FORMATS=%~2"
    shift
    shift
    goto :arg_loop
)

if /i "%~1"=="--verbose" (
    set "VERBOSE=--verbose"
    shift
    goto :arg_loop
)

if /i "%~1"=="-v" (
    set "VERBOSE=--verbose"
    shift
    goto :arg_loop
)

REM Unknown argument, skip it
shift
goto :arg_loop

:run_benchmark
echo Running model-based data generator benchmark suite...

REM Build the command line
set "CMD=python -m tools.data_generator_enhanced.testing.run_benchmark"

if not "%CONFIG_FILE%"=="" (
    set "CMD=!CMD! --config %CONFIG_FILE%"
)

set "CMD=!CMD! --output-dir %OUTPUT_DIR%"
set "CMD=!CMD! --repeat %REPEAT%"
set "CMD=!CMD! --report-formats %REPORT_FORMATS%"

if defined SMALL_ONLY (
    set "CMD=!CMD! %SMALL_ONLY%"
)

if defined SKIP_LARGE (
    set "CMD=!CMD! %SKIP_LARGE%"
)

if defined DOMAIN_SPECIFIC (
    set "CMD=!CMD! %DOMAIN_SPECIFIC%"
)

if defined COMPARE_LEGACY (
    set "CMD=!CMD! %COMPARE_LEGACY%"
)

if defined VERBOSE (
    set "CMD=!CMD! %VERBOSE%"
)

echo Executing: !CMD!
!CMD!

echo Benchmark complete. Results are available in %OUTPUT_DIR%

endlocal
