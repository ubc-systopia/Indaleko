#!/bin/bash
# Run ablation tests to evaluate metadata impact on query results

# Set up the environment
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INDALEKO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
export INDALEKO_ROOT

# Set up colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================================================${NC}"
echo -e "${YELLOW}Running Ablation Tests to Measure Metadata Impact on Query Results${NC}"
echo -e "${BLUE}==================================================================${NC}"

# Activate virtual environment if it exists
if [ -d "$INDALEKO_ROOT/.venv-linux-python3.13" ]; then
    echo -e "${GREEN}Activating Linux Python 3.13 virtual environment...${NC}"
    source "$INDALEKO_ROOT/.venv-linux-python3.13/bin/activate"
elif [ -d "$INDALEKO_ROOT/.venv" ]; then
    echo -e "${GREEN}Activating default virtual environment...${NC}"
    source "$INDALEKO_ROOT/.venv/bin/activate"
else
    echo -e "${YELLOW}No virtual environment found, using system Python${NC}"
fi

# Define output directory
OUTPUT_DIR="$INDALEKO_ROOT/ablation_test_results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="$OUTPUT_DIR/ablation_test_results_${TIMESTAMP}.json"
mkdir -p "$OUTPUT_DIR"

# Define test queries
TEST_QUERIES=(
    "Find all text files about ablation testing"
    "Find documents that mention database"
    "Show files edited by test-user"
    "Find all documents created in the last hour"
    "Find documents with keywords related to testing"
)

echo -e "${GREEN}Running enhanced ablation tests with real database...${NC}"
echo -e "${GREEN}Test queries:${NC}"
for query in "${TEST_QUERIES[@]}"; do
    echo "  - $query"
done

# Convert query array to command line arguments
QUERY_ARGS=""
for query in "${TEST_QUERIES[@]}"; do
    QUERY_ARGS="$QUERY_ARGS \"$query\""
done

# Run the enhanced ablation test
echo -e "\n${YELLOW}Running comprehensive ablation test...${NC}"
echo -e "${BLUE}This will test multiple collection combinations against all queries${NC}"

# First we need to run the unit tests to make sure the ablation mechanism works
echo -e "\n${GREEN}Running ablation unit tests...${NC}"
python -m tools.data_generator_enhanced.testing.test_ablation
UNIT_TEST_RESULT=$?

if [ $UNIT_TEST_RESULT -ne 0 ]; then
    echo -e "${RED}Ablation unit tests failed. Aborting comprehensive tests.${NC}"
    exit 1
fi

echo -e "\n${GREEN}Unit tests passed. Running comprehensive test...${NC}"

# Run the comprehensive test with test data generation
CMD="python -m tools.data_generator_enhanced.testing.test_ablation --generate-data --output $OUTPUT_FILE --log-level INFO --queries ${QUERY_ARGS}"
echo -e "${BLUE}Command: $CMD${NC}"
eval $CMD

# Check result
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Comprehensive ablation test completed successfully${NC}"
    echo -e "${BLUE}Results saved to: $OUTPUT_FILE${NC}"

    # Run the analyzer if available
    if [ -f "$SCRIPT_DIR/ablation_analyzer.py" ]; then
        echo -e "\n${YELLOW}Generating analysis report...${NC}"
        python -m tools.data_generator_enhanced.testing.ablation_analyzer "$OUTPUT_FILE"
    else
        echo -e "\n${YELLOW}Analysis tool not found. Skipping report generation.${NC}"
    fi
else
    echo -e "${RED}Comprehensive ablation test failed${NC}"
    exit 1
fi

# Optionally run database integration test with real data
echo -e "\n${YELLOW}Would you like to run the general database integration test? (y/n)${NC}"
read -r run_db_test

if [[ $run_db_test == "y" || $run_db_test == "Y" ]]; then
    echo -e "\n${GREEN}Running database integration test...${NC}"
    python -m tools.data_generator_enhanced.testing.test_db_integration --dataset-size 10 --skip-cleanup

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Database integration test completed successfully${NC}"
    else
        echo -e "${RED}Database integration test failed${NC}"
    fi
fi

echo -e "\n${GREEN}All tests completed.${NC}"
