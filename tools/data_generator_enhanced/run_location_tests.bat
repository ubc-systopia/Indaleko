@echo off
rem Run location metadata generator tests

rem Get directory of this script (and normalize path)
set SCRIPT_DIR=%~dp0
set ROOT_DIR=%SCRIPT_DIR%..\..

rem Make sure we're in the root directory
cd /d "%ROOT_DIR%"

rem Set environment variable for imports
set INDALEKO_ROOT=%ROOT_DIR%
set PYTHONPATH=%ROOT_DIR%

rem Run unit tests for location generator
echo Running location generator tests...
python -m tools.data_generator_enhanced.testing.test_location_generator

rem Run database integration tests
echo Running location database integration tests...
echo Skipping DB integration test for now - will be implemented in next phase

echo All tests completed.