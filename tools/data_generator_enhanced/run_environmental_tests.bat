@echo off
REM Run tests for the Environmental Metadata Generator
REM This script executes unit tests and database integration tests
REM for the environmental metadata generator

SETLOCAL

REM Ensure we're in the right directory
SET BASE_DIR=%~dp0
cd /d %BASE_DIR%

echo ========================================================
echo Running unit tests for Environmental Metadata Generator
echo ========================================================
cd /d %BASE_DIR%\..\..
python -m tools.data_generator_enhanced.testing.test_environmental_metadata_generator

REM Return code from unit tests
SET UNIT_RESULT=%ERRORLEVEL%

echo ========================================================
echo Running database integration tests for Environmental Metadata Generator
echo ========================================================
python -m tools.data_generator_enhanced.testing.test_environmental_db_integration

REM Return code from integration tests
SET DB_RESULT=%ERRORLEVEL%

echo ========================================================
echo Test Results:
IF %UNIT_RESULT% EQU 0 (
    echo Unit tests: PASSED
) ELSE (
    echo Unit tests: FAILED
)

IF %DB_RESULT% EQU 0 (
    echo DB Integration tests: PASSED
) ELSE (
    echo DB Integration tests: FAILED
)
echo ========================================================

REM Exit with non-zero if any test failed
IF %UNIT_RESULT% NEQ 0 EXIT /B 1
IF %DB_RESULT% NEQ 0 EXIT /B 1

EXIT /B 0