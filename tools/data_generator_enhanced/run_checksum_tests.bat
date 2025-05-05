@echo off
:: Run checksum generator tests
:: This script runs the unit tests and database integration tests for the checksum generator

:: Set the Indaleko root directory
set SCRIPT_DIR=%~dp0
cd %SCRIPT_DIR%\..\..

:: Run the unit tests
echo Running checksum generator unit tests...
python -m tools.data_generator_enhanced.testing.test_checksum_generator

:: Run database integration tests
echo Running checksum generator database integration tests...
python -m tools.data_generator_enhanced.testing.test_checksum_db_integration --debug

:: Display completion message
echo Checksum generator tests completed.
pause