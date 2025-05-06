@echo off
rem Run ablation tests to evaluate metadata impact on query results

setlocal enabledelayedexpansion

rem Set up the environment
set SCRIPT_DIR=%~dp0
set INDALEKO_ROOT=%SCRIPT_DIR%..\..\..
set PYTHON_CMD=python

echo ===================================================================
echo Running Ablation Tests to Measure Metadata Impact on Query Results
echo ===================================================================

rem Check for virtual environment
if exist "%INDALEKO_ROOT%\.venv-win32-python3.12\Scripts\activate.bat" (
    echo Activating Windows Python 3.12 virtual environment...
    call "%INDALEKO_ROOT%\.venv-win32-python3.12\Scripts\activate.bat"
) else if exist "%INDALEKO_ROOT%\.venv\Scripts\activate.bat" (
    echo Activating default virtual environment...
    call "%INDALEKO_ROOT%\.venv\Scripts\activate.bat"
) else (
    echo No virtual environment found, using system Python
)

rem Generate timestamp for output files
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "TIMESTAMP=%dt:~0,8%_%dt:~8,6%"

rem Define output directory
set OUTPUT_DIR=%INDALEKO_ROOT%\ablation_test_results
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"
set OUTPUT_FILE=%OUTPUT_DIR%\ablation_test_results_%TIMESTAMP%.json

rem Define test queries
echo Running enhanced ablation tests with real database...
echo Test queries:
set QUERIES[0]=Find all text files about ablation testing
set QUERIES[1]=Find documents that mention database
set QUERIES[2]=Show files edited by test-user
set QUERIES[3]=Find all documents created in the last hour
set QUERIES[4]=Find documents with keywords related to testing

rem Display queries
for /L %%i in (0,1,4) do (
    echo   - !QUERIES[%%i]!
)

echo.
echo Running comprehensive ablation test...
echo This will test multiple collection combinations against all queries

rem First run the unit tests to ensure the ablation mechanism works
echo.
echo Running ablation unit tests...
%PYTHON_CMD% -m tools.data_generator_enhanced.testing.test_ablation
if not !ERRORLEVEL! EQU 0 (
    echo Ablation unit tests failed. Aborting comprehensive tests.
    exit /b 1
)

echo.
echo Unit tests passed. Running comprehensive test...

rem Build the command with all queries
set QUERY_ARGS=--queries
for /L %%i in (0,1,4) do (
    set QUERY_ARGS=!QUERY_ARGS! "!QUERIES[%%i]!"
)

rem Run the comprehensive test with test data generation
echo Command: %PYTHON_CMD% -m tools.data_generator_enhanced.testing.test_ablation --generate-data --output "%OUTPUT_FILE%" --log-level INFO !QUERY_ARGS!
%PYTHON_CMD% -m tools.data_generator_enhanced.testing.test_ablation --generate-data --output "%OUTPUT_FILE%" --log-level INFO !QUERY_ARGS!

rem Check result
if not !ERRORLEVEL! EQU 0 (
    echo Comprehensive ablation test failed
    exit /b 1
)

echo Comprehensive ablation test completed successfully
echo Results saved to: %OUTPUT_FILE%

rem Run the analyzer if available
if exist "%SCRIPT_DIR%ablation_analyzer.py" (
    echo.
    echo Generating analysis report...
    %PYTHON_CMD% -m tools.data_generator_enhanced.testing.ablation_analyzer "%OUTPUT_FILE%"
) else (
    echo.
    echo Analysis tool not found. Skipping report generation.
)

rem Optionally run database integration test with real data
echo.
set /p RUN_DB_TEST="Would you like to run the general database integration test? (y/n): "
if /i "%RUN_DB_TEST%"=="y" (
    echo.
    echo Running database integration test...
    %PYTHON_CMD% -m tools.data_generator_enhanced.testing.test_db_integration --dataset-size 10 --skip-cleanup

    if !ERRORLEVEL! EQU 0 (
        echo Database integration test completed successfully
    ) else (
        echo Database integration test failed
    )
)

echo.
echo All tests completed.

endlocal
