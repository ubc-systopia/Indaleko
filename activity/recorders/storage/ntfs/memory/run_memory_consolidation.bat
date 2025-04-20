@echo off
rem Run memory consolidation processes for the NTFS cognitive memory system
rem Usage: run_memory_consolidation.bat [--consolidate-all] [--debug] [--dry-run]

setlocal EnableDelayedExpansion

rem Set up environment
set "SCRIPT_DIR=%~dp0"
set "INDALEKO_ROOT=%SCRIPT_DIR%..\..\..\..\..\.."
set "PYTHONPATH=%INDALEKO_ROOT%;%PYTHONPATH%"

rem Check for Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Python not found
    exit /b 1
)

rem Default options
set CONSOLIDATE_ALL=false
set "DEBUG="
set "DRY_RUN="

rem Parse arguments
:parse_args
if "%~1"=="" goto :done_parsing
if "%~1"=="--consolidate-all" (
    set CONSOLIDATE_ALL=true
    shift
    goto :parse_args
)
if "%~1"=="--debug" (
    set "DEBUG=--debug"
    shift
    goto :parse_args
)
if "%~1"=="--dry-run" (
    set "DRY_RUN=--dry-run"
    shift
    goto :parse_args
)
echo Error: Unknown option %~1
echo Usage: run_memory_consolidation.bat [--consolidate-all] [--debug] [--dry-run]
exit /b 1
:done_parsing

rem Show menu if not running all
if %CONSOLIDATE_ALL%==false (
    echo === NTFS Cognitive Memory Consolidation ===
    echo 1) Sensory -^> Short-Term Memory
    echo 2) Short-Term -^> Long-Term Memory
    echo 3) Long-Term -^> Archival Memory
    echo 4) Run All Consolidation Processes
    echo 5) Show Memory Statistics
    echo 0) Exit
    echo.
    set /p OPTION="Choose an option (0-5): "
) else (
    set OPTION=4
)

rem Process option
if "%OPTION%"=="1" (
    echo Running: Sensory -^> Short-Term Memory consolidation
    python "%SCRIPT_DIR%memory_consolidation.py" --consolidate-sensory %DEBUG% %DRY_RUN%
) else if "%OPTION%"=="2" (
    echo Running: Short-Term -^> Long-Term Memory consolidation
    python "%SCRIPT_DIR%memory_consolidation.py" --consolidate-short %DEBUG% %DRY_RUN%
) else if "%OPTION%"=="3" (
    echo Running: Long-Term -^> Archival Memory consolidation
    python "%SCRIPT_DIR%memory_consolidation.py" --consolidate-long %DEBUG% %DRY_RUN%
) else if "%OPTION%"=="4" (
    echo Running: All memory consolidation processes
    python "%SCRIPT_DIR%memory_consolidation.py" --consolidate-all %DEBUG% %DRY_RUN%
) else if "%OPTION%"=="5" (
    echo Getting memory statistics
    python "%SCRIPT_DIR%memory_consolidation.py" --stats %DEBUG%
) else if "%OPTION%"=="0" (
    echo Exiting
    exit /b 0
) else (
    echo Error: Invalid option %OPTION%
    exit /b 1
)

echo Done.
exit /b 0