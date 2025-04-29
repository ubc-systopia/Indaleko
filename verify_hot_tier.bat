@echo off
REM Root wrapper script for Hot Tier Recorder verification
REM This script calls the verify_hot_tier.bat script in the appropriate directory

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"

REM Call the actual verification script
call "%SCRIPT_DIR%activity\recorders\storage\ntfs\tiered\hot\verify_hot_tier.bat" %*
