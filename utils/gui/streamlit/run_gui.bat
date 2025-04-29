@echo off
REM Script to launch Indaleko Streamlit GUI on Windows

REM Set the Indaleko root directory (this assumes run_gui.bat is in utils/gui/streamlit)
set "INDALEKO_ROOT=%~dp0..\..\.."

echo Setting INDALEKO_ROOT to %INDALEKO_ROOT%

REM Check if we have an active virtual environment
if not defined VIRTUAL_ENV (
    echo No active virtual environment detected. Activating...

    REM Try to find and activate a virtual environment
    if exist "%INDALEKO_ROOT%\.venv-win32-python3.12\Scripts\activate.bat" (
        echo Found .venv-win32-python3.12, activating...
        call "%INDALEKO_ROOT%\.venv-win32-python3.12\Scripts\activate.bat"
    ) else if exist "%INDALEKO_ROOT%\.venv\Scripts\activate.bat" (
        echo Found .venv, activating...
        call "%INDALEKO_ROOT%\.venv\Scripts\activate.bat"
    ) else (
        echo No virtual environment found at expected locations.
        echo Please create and activate a virtual environment and install dependencies:
        echo   uv venv
        echo   .venv\Scripts\activate
        echo   uv pip install -e .
        exit /b 1
    )
) else (
    echo Using active virtual environment: %VIRTUAL_ENV%
)

REM Check if streamlit is installed
pip show streamlit >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Streamlit is not installed. Installing required packages...
    pip install streamlit plotly pydeck pillow
)

REM Launch the Streamlit app
echo Launching Indaleko GUI...
cd "%INDALEKO_ROOT%\utils\gui\streamlit"
streamlit run app.py
