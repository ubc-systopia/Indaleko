@echo off
REM Run the ablation integration test with default settings

REM Set the Indaleko root directory
set "SCRIPT_DIR=%~dp0"
set "INDALEKO_ROOT=%SCRIPT_DIR%"

REM Activate the appropriate virtual environment if it exists
if exist "%SCRIPT_DIR%\.venv-win32-python3.12\Scripts\activate.bat" (
    echo Activating Windows Python 3.12 virtual environment...
    call "%SCRIPT_DIR%\.venv-win32-python3.12\Scripts\activate.bat"
) else if exist "%SCRIPT_DIR%\.venv\Scripts\activate.bat" (
    echo Activating generic virtual environment...
    call "%SCRIPT_DIR%\.venv\Scripts\activate.bat"
)

REM Run the test with default settings
python "%SCRIPT_DIR%\run_ablation_integration_test.py" %*

REM Capture the exit code
set EXIT_CODE=%ERRORLEVEL%

REM Deactivate the virtual environment if it was activated
if defined VIRTUAL_ENV (
    deactivate
)

exit /b %EXIT_CODE%