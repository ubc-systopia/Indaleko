@echo off
:: Run calendar event generator tests
:: This script runs the database integration tests for the calendar event generator

:: Set the Indaleko root directory
set SCRIPT_DIR=%~dp0
cd %SCRIPT_DIR%\..\..

:: Run the standard tests
echo Running calendar event basic tests...
python -m tools.data_generator_enhanced.testing.test_calendar_event_generator

:: Run database integration tests
echo Running calendar event database integration tests...
python -m tools.data_generator_enhanced.testing.test_calendar_db_integration --debug

:: Display completion message
echo Calendar event tests completed.
pause