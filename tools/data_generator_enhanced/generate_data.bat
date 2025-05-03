@echo off
REM Script to run the enhanced data generator on Windows using the Indaleko CLI framework

REM Get the script directory
set "SCRIPT_DIR=%~dp0"

REM Move to the project root to ensure proper imports
cd %SCRIPT_DIR%\..\..

REM Activate the virtual environment if it exists
if exist ".venv-win32-python3.12\Scripts\activate.bat" (
    call ".venv-win32-python3.12\Scripts\activate.bat"
)

REM Run the generator script
python "%SCRIPT_DIR%generate_data.py" %*

REM Exit with the Python script's exit code
exit /b %ERRORLEVEL%