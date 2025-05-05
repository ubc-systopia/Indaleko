#!/bin/bash
# Script to run social media generator tests

# Change to the Indaleko root directory
cd "$(dirname "$0")/../.." || exit

# Set up the Python path
export PYTHONPATH="$PWD"

# Check if virtual environment exists and activate it
if [ -d ".venv-linux-python3.13" ]; then
    echo "Activating virtual environment..."
    source .venv-linux-python3.13/bin/activate
elif [ -d ".venv-macos-python3.12" ]; then
    echo "Activating virtual environment..."
    source .venv-macos-python3.12/bin/activate
else
    echo "No virtual environment found. Using system Python."
fi

# Run the social media generator tests
echo "Running social media generator tests..."
python -m tools.data_generator_enhanced.testing.test_social_media_generator

# Return the exit code
exit_code=$?

# Print completion message
if [ $exit_code -eq 0 ]; then
    echo "Tests completed successfully!"
else
    echo "Tests failed with exit code: $exit_code"
fi

exit $exit_code