@echo off
REM Run Music Activity Generator Tests Script
REM This script runs both unit tests and database integration tests for the MusicActivityGeneratorTool

setlocal

REM Determine the project root (3 directories up from this script)
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%\..\..\"
set "PROJECT_ROOT=%CD%"
popd

echo Project root: %PROJECT_ROOT%
cd "%PROJECT_ROOT%"

REM Activate virtual environment if it exists
if exist .venv-win32-python3.12\Scripts\activate.bat (
    echo Activating virtual environment...
    call .venv-win32-python3.12\Scripts\activate.bat
)

REM Set PYTHONPATH
set "PYTHONPATH=%PROJECT_ROOT%;%PYTHONPATH%"

REM First run the unit tests
echo Running Music Activity Generator unit tests...
python -m tools.data_generator_enhanced.testing.test_music_activity_generator

REM Run the database integration tests
echo Running Music Activity Generator database integration tests...
python -m tools.data_generator_enhanced.testing.test_music_db_integration

echo All tests completed.

endlocal