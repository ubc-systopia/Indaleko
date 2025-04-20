@echo off
:: Memory Consolidation Runner for Indaleko Cognitive Memory System
:: For Windows environments
:: 
:: This script runs the memory consolidation process for the Indaleko cognitive memory system,
:: which transfers information between different memory tiers (sensory → short-term → long-term → archival).
::
:: Usage:
::   run_memory_consolidation.bat --consolidate-sensory  # Consolidate from sensory to short-term
::   run_memory_consolidation.bat --consolidate-short    # Consolidate from short-term to long-term
::   run_memory_consolidation.bat --consolidate-long     # Consolidate from long-term to archival (future)
::   run_memory_consolidation.bat --consolidate-all      # Run all consolidation processes
::   run_memory_consolidation.bat --stats                # Get memory system statistics
::
:: Project Indaleko
:: Copyright (C) 2024-2025 Tony Mason

setlocal enabledelayedexpansion

:: Set script directory as Indaleko root
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "INDALEKO_ROOT=%SCRIPT_DIR%"

:: Print header
echo ========================================================
echo Indaleko Cognitive Memory System - Consolidation Runner
echo ========================================================
echo.

:: Find the memory consolidation script
set "MEMORY_CONSOLIDATION_SCRIPT=%INDALEKO_ROOT%\activity\recorders\storage\ntfs\memory\memory_consolidation.py"

:: Check if the script exists
if not exist "%MEMORY_CONSOLIDATION_SCRIPT%" (
    echo Error: Memory consolidation script not found at:
    echo %MEMORY_CONSOLIDATION_SCRIPT%
    echo Please ensure the script exists and try again.
    exit /b 1
)

:: Find the appropriate virtual environment
set "VENV_DIR="

if exist "%SCRIPT_DIR%\.venv-win32-python3.12" (
    set "VENV_DIR=%SCRIPT_DIR%\.venv-win32-python3.12"
) else if exist "%SCRIPT_DIR%\.venv-win32-python3.11" (
    set "VENV_DIR=%SCRIPT_DIR%\.venv-win32-python3.11"
) else if exist "%SCRIPT_DIR%\.venv-win32-python3.10" (
    set "VENV_DIR=%SCRIPT_DIR%\.venv-win32-python3.10"
) else if exist "%SCRIPT_DIR%\.venv" (
    set "VENV_DIR=%SCRIPT_DIR%\.venv"
)

:: Activate the virtual environment if available
if not "%VENV_DIR%"=="" (
    echo Activating virtual environment: %VENV_DIR%
    call "%VENV_DIR%\Scripts\activate.bat"
) else (
    echo Warning: No virtual environment found. Running with system Python.
    echo For best results, set up a virtual environment with 'uv pip install -e .'
)

:: Forward all arguments to the consolidation script
echo Running memory consolidation script...
python "%MEMORY_CONSOLIDATION_SCRIPT%" %*
set "EXIT_CODE=%ERRORLEVEL%"

:: Check the exit code
if %EXIT_CODE%==0 (
    echo Memory consolidation completed successfully.
) else (
    echo Memory consolidation failed with exit code: %EXIT_CODE%
)

:: Deactivate the virtual environment if it was activated
if not "%VENV_DIR%"=="" (
    call deactivate
)

exit /b %EXIT_CODE%