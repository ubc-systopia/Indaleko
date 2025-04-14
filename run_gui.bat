@echo off
REM Streamlit GUI launcher for Indaleko on Windows
REM This script ensures the correct Python path is set before launching

REM Get the directory where this batch file is located
SET SCRIPT_DIR=%~dp0
SET SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

REM Set PYTHONPATH to include the project root
SET PYTHONPATH=%SCRIPT_DIR%
SET INDALEKO_ROOT=%SCRIPT_DIR%

echo Using Python path: %PYTHONPATH%
echo Project root: %INDALEKO_ROOT%

REM Run the Streamlit app
cd "%SCRIPT_DIR%"
python "%SCRIPT_DIR%\utils\gui\streamlit\run.py" %*