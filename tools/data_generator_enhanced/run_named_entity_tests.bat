@echo off
REM Script to run named entity generator tests

REM Change to the Indaleko root directory
cd %~dp0..\..

REM Set up the Python path
set PYTHONPATH=%CD%

REM Check if virtual environment exists and activate it
if exist .venv-win32-python3.12\Scripts\activate.bat (
    echo Activating virtual environment...
    call .venv-win32-python3.12\Scripts\activate.bat
) else (
    echo No virtual environment found. Using system Python.
)

REM Run the named entity generator tests
echo Running named entity generator tests...
python -m tools.data_generator_enhanced.testing.test_named_entity_generator

REM Store the exit code
set EXIT_CODE=%ERRORLEVEL%

REM Print completion message
if %EXIT_CODE% EQU 0 (
    echo Tests completed successfully!
) else (
    echo Tests failed with exit code: %EXIT_CODE%
)

exit /b %EXIT_CODE%