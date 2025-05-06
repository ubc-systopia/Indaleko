@echo off
REM Run tests for the model-based data generator benchmark suite

setlocal enabledelayedexpansion

REM Activate virtual environment if it exists
if exist "%~dp0..\..\..\\.venv-win32-python3.12\Scripts\activate.bat" (
    call "%~dp0..\..\..\\.venv-win32-python3.12\Scripts\activate.bat"
)

REM Set PYTHONPATH to include the project root
set "PYTHONPATH=%~dp0..\..\..\;%PYTHONPATH%"

REM Run the tests
echo Running unit tests for the benchmark suite...
python -m unittest %~dp0\test_benchmark.py

echo Running integration tests for the benchmark suite...
python -m unittest %~dp0\test_integration.py

REM Check if any tests failed
if %ERRORLEVEL% EQU 0 (
    echo All tests passed!
    exit /b 0
) else (
    echo Some tests failed. Please check the output above for details.
    exit /b 1
)

endlocal
