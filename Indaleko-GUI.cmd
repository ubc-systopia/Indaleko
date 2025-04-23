@echo off
title Indaleko GUI
color 0A

REM Get the directory where this batch file is located
SET SCRIPT_DIR=%~dp0
SET SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

REM Set PYTHONPATH to include ONLY the project root
SET PYTHONPATH=%SCRIPT_DIR%
SET INDALEKO_ROOT=%SCRIPT_DIR%

echo *********************************************************
echo *                  INDALEKO GUI LAUNCHER                *
echo *********************************************************
echo.
echo Starting Indaleko Unified Personal Index GUI...
echo.
echo Make sure you have run: uv pip install -e ".[gui]"
echo.
echo Using Python path: %PYTHONPATH%
echo Project root: %INDALEKO_ROOT%
echo.

REM Change directory to the project root to ensure proper imports
cd "%SCRIPT_DIR%"

REM Activate the virtual environment if it exists
if exist "%SCRIPT_DIR%\.venv-win32-python3.12\Scripts\activate.bat" (
    echo Activating virtual environment...
    call "%SCRIPT_DIR%\.venv-win32-python3.12\Scripts\activate.bat"
)

REM Check if streamlit is installed
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo.
    echo Error: Streamlit is not installed.
    echo Please install with: uv pip install -e ".[gui]"
    echo.
    pause
    exit /b 1
)

REM Run the Streamlit app
echo.
echo Launching Indaleko GUI...
echo.
echo When done, close this window or press Ctrl+C to exit.
echo.
python "%SCRIPT_DIR%\utils\gui\streamlit\run.py" --browser

REM Keep the window open in case of error
if errorlevel 1 (
    echo.
    echo Error occurred while running the GUI.
    echo.
    pause
)
