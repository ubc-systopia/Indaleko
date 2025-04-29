@echo off
REM Run Indaleko Analytics Tool

REM Check for virtual environment and activate if found
if exist .venv-win32-python3.12\Scripts\activate.bat (
    call .venv-win32-python3.12\Scripts\activate.bat
)

REM Run the analytics tool with provided arguments
python -m query.analytics.file_statistics %*
