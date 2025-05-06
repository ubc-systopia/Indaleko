@echo off
rem Run activity semantic attributes tests

rem Get directory of this script (and normalize path)
set SCRIPT_DIR=%~dp0
set ROOT_DIR=%SCRIPT_DIR%..\..

rem Make sure we're in the root directory
cd /d "%ROOT_DIR%"

rem Set environment variable for imports
set INDALEKO_ROOT=%ROOT_DIR%
set PYTHONPATH=%ROOT_DIR%

rem Run semantic attributes test
echo Running activity semantic attribute tests...
python -m tools.data_generator_enhanced.testing.test_activity_semantic_attributes

rem Run integrated database test with activities
echo Running integrated database test with activities...
python -m tools.data_generator_enhanced.testing.test_db_integration --dataset-size 20 --output ./tools/data_generator_enhanced/results/activity_db_integration_results.json

echo All tests completed.