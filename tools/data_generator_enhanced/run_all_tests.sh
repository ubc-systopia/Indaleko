#!/bin/bash
# Master test script for the Indaleko Data Generator Enhanced Tools
# This script runs all component tests and reports their status
#
# Project Indaleko
# Copyright (C) 2024-2025 Tony Mason

# Set colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ensure we're in the right directory
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

echo -e "${BLUE}========================================================${NC}"
echo -e "${BLUE}= Indaleko Data Generator Enhanced - Master Test Suite =${NC}"
echo -e "${BLUE}========================================================${NC}"
echo ""
echo -e "${YELLOW}Starting tests at $(date)${NC}"
echo ""

# Array of test scripts
TEST_SCRIPTS=(
    "run_location_tests.sh"
    "run_exif_tests.sh" 
    "run_activity_tests.sh"
    "run_named_entity_tests.sh"
    "run_social_media_tests.sh"
    "run_calendar_tests.sh"
    "run_cloud_storage_tests.sh"
    "run_checksum_tests.sh"
    "run_music_tests.sh"
    "run_environmental_tests.sh"
)

# Initialize counters
TOTAL_COUNT=0
PASS_COUNT=0
FAIL_COUNT=0

# Initialize results array
declare -A RESULTS

# Run each test script
for script in "${TEST_SCRIPTS[@]}"; do
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    
    # Extract component name for display
    COMPONENT=$(echo "$script" | sed 's/run_\(.*\)_tests\.sh/\1/')
    COMPONENT_DISPLAY=$(echo "$COMPONENT" | tr '_' ' ' | awk '{for(i=1;i<=NF;i++)sub(/./,toupper(substr($i,1,1)),$i)}1')
    
    echo -e "${YELLOW}Testing: ${COMPONENT_DISPLAY} Generator${NC}"
    echo -e "${BLUE}--------------------------------------------------------${NC}"
    
    # Make sure script is executable
    chmod +x "$script"
    
    # Run the test script
    ./"$script"
    TEST_RESULT=$?
    
    # Record the result
    if [ $TEST_RESULT -eq 0 ]; then
        echo -e "${GREEN}${COMPONENT_DISPLAY} Generator tests: PASSED${NC}"
        RESULTS["$COMPONENT"]="PASS"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo -e "${RED}${COMPONENT_DISPLAY} Generator tests: FAILED${NC}"
        RESULTS["$COMPONENT"]="FAIL"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    
    echo ""
done

# Print summary
echo -e "${BLUE}========================================================${NC}"
echo -e "${YELLOW}Test Summary:${NC}"
echo -e "${BLUE}--------------------------------------------------------${NC}"

# Print detailed results
for script in "${TEST_SCRIPTS[@]}"; do
    COMPONENT=$(echo "$script" | sed 's/run_\(.*\)_tests\.sh/\1/')
    COMPONENT_DISPLAY=$(echo "$COMPONENT" | tr '_' ' ' | awk '{for(i=1;i<=NF;i++)sub(/./,toupper(substr($i,1,1)),$i)}1')
    
    if [ "${RESULTS[$COMPONENT]}" = "PASS" ]; then
        echo -e "${GREEN}✅ ${COMPONENT_DISPLAY} Generator: PASSED${NC}"
    else
        echo -e "${RED}❌ ${COMPONENT_DISPLAY} Generator: FAILED${NC}"
    fi
done

echo -e "${BLUE}--------------------------------------------------------${NC}"
echo -e "Total: $TOTAL_COUNT | ${GREEN}Passed: $PASS_COUNT${NC} | ${RED}Failed: $FAIL_COUNT${NC}"
echo -e "${BLUE}========================================================${NC}"

# Return overall success/failure
if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}ALL TESTS PASSED! 🎉${NC}"
    exit 0
else
    echo -e "${RED}SOME TESTS FAILED! ❌${NC}"
    exit 1
fi