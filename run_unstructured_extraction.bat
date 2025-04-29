@echo off
rem Batch script for extracting semantic data using the Unstructured tool
rem This script is designed to be run periodically (e.g., weekly) via Task Scheduler
rem
rem Project Indaleko
rem Copyright (C) 2024-2025 Tony Mason
rem

setlocal enabledelayedexpansion

rem Change to the Indaleko directory
cd /d "%~dp0"

rem Check if Docker is running
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker is not running or not accessible.
    echo Please start Docker Desktop and try again.
    exit /b 1
)

rem Set process priority to BELOW NORMAL - better for overnight runs but still controlled
wmic process where name="cmd.exe" AND ProcessId=%ProcessId% CALL setpriority "below normal" >nul 2>&1

rem Activate virtual environment
call .venv-win32-python3.12\Scripts\activate.bat

rem Configure which directories to process
set DOCUMENT_DIRS=C:\Users\TonyMason\Documents
rem Add additional directories separated by spaces if needed
rem set DOCUMENT_DIRS=C:\Path1 C:\Path2 C:\Path3

rem Configure processing limits - higher limits for 64GB machine running overnight
set MAX_SIZE_MB=100
set FILE_EXTENSIONS=pdf docx txt md xlsx pptx html
set DOCKER_MEMORY=16g

rem Create log directory if it doesn't exist
if not exist logs mkdir logs

rem Log start time
echo [%date% %time%] Starting unstructured extraction >> logs\unstructured_extraction.log

rem Process each directory
for %%d in (%DOCUMENT_DIRS%) do (
    echo Processing directory: %%d
    echo [%date% %time%] Processing directory: %%d >> logs\unstructured_extraction.log

    rem Run Unstructured processor with higher resource limits for 64GB machine
    rem Allocate more memory to Docker for better performance on large files
    python semantic\processors\unstructured_processor.py dir "%%d" ^
        --recursive ^
        --extensions %FILE_EXTENSIONS% ^
        --max-size %MAX_SIZE_MB%

    rem Record exit code
    set EXIT_CODE=%ERRORLEVEL%
    echo [%date% %time%] Directory %%d completed with exit code %EXIT_CODE% >> logs\unstructured_extraction.log

    rem Allow system to rest briefly between directories (shorter rest for overnight processing)
    echo Brief rest before next directory...
    timeout /t 20 /nobreak >nul
)

echo Processing complete.
echo [%date% %time%] Unstructured extraction completed >> logs\unstructured_extraction.log
echo Results are stored in the database and logs are in the logs directory.

rem Check for Docker resource usage and clean up if necessary
echo [%date% %time%] Checking for Docker cleanup... >> logs\unstructured_extraction.log
docker system df >> logs\unstructured_extraction.log 2>&1

rem Clean up Docker if disk usage is over 20GB (increased for higher capacity system)
for /f "tokens=3" %%a in ('docker system df --format "{{.Size}}" ^| findstr "^Total"') do (
    set SIZE=%%a
    echo Docker size: !SIZE! >> logs\unstructured_extraction.log
    if "!SIZE:~-2!"=="GB" (
        set SIZE_NUM=!SIZE:~0,-2!
        if !SIZE_NUM! GTR 20 (
            echo [%date% %time%] Docker size over 20GB, cleaning up... >> logs\unstructured_extraction.log
            docker system prune -f >> logs\unstructured_extraction.log 2>&1
        )
    )
)

rem Deactivate virtual environment
call deactivate

echo [%date% %time%] Script completed successfully >> logs\unstructured_extraction.log
exit /b 0
