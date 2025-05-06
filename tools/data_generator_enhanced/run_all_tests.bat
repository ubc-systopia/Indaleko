@echo off
REM Master test script for the Indaleko Data Generator Enhanced Tools
REM This script runs all component tests and reports their status
REM
REM Project Indaleko
REM Copyright (C) 2024-2025 Tony Mason

SETLOCAL EnableDelayedExpansion

REM Ensure we're in the right directory
SET BASE_DIR=%~dp0
cd /d %BASE_DIR%

echo ========================================================
echo = Indaleko Data Generator Enhanced - Master Test Suite =
echo ========================================================
echo.
echo Starting tests at %date% %time%
echo.

REM Array of test scripts
SET TEST_SCRIPTS=^
  run_location_tests.bat^
  run_exif_tests.bat^
  run_activity_tests.bat^
  run_named_entity_tests.bat^
  run_social_media_tests.bat^
  run_calendar_tests.bat^
  run_cloud_storage_tests.bat^
  run_checksum_tests.bat^
  run_music_tests.bat^
  run_environmental_tests.bat

REM Initialize counters
SET TOTAL_COUNT=0
SET PASS_COUNT=0
SET FAIL_COUNT=0

REM Run each test script
FOR %%s IN (%TEST_SCRIPTS%) DO (
    SET /a TOTAL_COUNT+=1
    
    REM Extract component name for display
    SET SCRIPT=%%s
    SET COMPONENT=!SCRIPT:run_=!
    SET COMPONENT=!COMPONENT:_tests.bat=!
    
    REM Convert component name to title case for display
    SET COMPONENT_DISPLAY=!COMPONENT!
    
    echo Testing: !COMPONENT_DISPLAY! Generator
    echo --------------------------------------------------------
    
    REM Run the test script
    CALL %%s
    
    REM Record the result
    IF !ERRORLEVEL! EQU 0 (
        echo !COMPONENT_DISPLAY! Generator tests: PASSED
        SET "RESULTS_!COMPONENT!=PASS"
        SET /a PASS_COUNT+=1
    ) ELSE (
        echo !COMPONENT_DISPLAY! Generator tests: FAILED
        SET "RESULTS_!COMPONENT!=FAIL"
        SET /a FAIL_COUNT+=1
    )
    
    echo.
)

REM Print summary
echo ========================================================
echo Test Summary:
echo --------------------------------------------------------

REM Print detailed results
FOR %%s IN (%TEST_SCRIPTS%) DO (
    SET SCRIPT=%%s
    SET COMPONENT=!SCRIPT:run_=!
    SET COMPONENT=!COMPONENT:_tests.bat=!
    SET COMPONENT_DISPLAY=!COMPONENT!
    
    CALL SET RESULT=%%RESULTS_!COMPONENT!%%
    
    IF "!RESULT!"=="PASS" (
        echo [PASS] !COMPONENT_DISPLAY! Generator
    ) ELSE (
        echo [FAIL] !COMPONENT_DISPLAY! Generator
    )
)

echo --------------------------------------------------------
echo Total: %TOTAL_COUNT% ^| Passed: %PASS_COUNT% ^| Failed: %FAIL_COUNT%
echo ========================================================

REM Return overall success/failure
IF %FAIL_COUNT% EQU 0 (
    echo ALL TESTS PASSED!
    exit /b 0
) ELSE (
    echo SOME TESTS FAILED!
    exit /b 1
)