#!/bin/bash
# Comprehensive ablation test runner with cross-collection support
# Project Indaleko
# Copyright (C) 2024-2025 Tony Mason

set -e  # Exit on error

# Set up environment
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
export PYTHONPATH=$SCRIPT_DIR

echo "Starting comprehensive ablation test with cross-collection support..."

# Check for required Python packages
required_packages=("matplotlib" "pandas" "seaborn" "numpy")
missing_packages=()

for package in "${required_packages[@]}"; do
  if ! python -c "import $package" 2>/dev/null; then
    missing_packages+=("$package")
  fi
done

if [ ${#missing_packages[@]} -gt 0 ]; then
  echo "Warning: The following packages are missing for visualization: ${missing_packages[*]}"
  echo "You can install them with: pip install ${missing_packages[*]}"
  echo "Continuing without visualization..."
fi

# Reset the database to ensure clean test data
echo "Resetting database..."
python -m db.db_config reset

# Initialize the database structure properly
echo "Initializing database structure..."
python -m db.db_setup check

# Make sure output directory exists
timestamp=$(date +"%Y%m%d_%H%M%S")
output_dir="./ablation_results_${timestamp}"
mkdir -p "$output_dir"

# Define default parameters
count=100
queries=5
visualize=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --count=*)
      count="${1#*=}"
      shift
      ;;
    --queries=*)
      queries="${1#*=}"
      shift
      ;;
    --no-visualize)
      visualize=""
      shift
      ;;
    --visualize)
      visualize="--visualize"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--count=N] [--queries=N] [--visualize|--no-visualize]"
      exit 1
      ;;
  esac
done

# Run the improved ablation test with cross-collection support
echo "Running comprehensive ablation test..."
python "$SCRIPT_DIR/research/ablation/run_comprehensive_ablation.py" \
  --count "$count" \
  --queries "$queries" \
  --clear \
  --output-dir "$output_dir" \
  $visualize

# Check exit status
if [ $? -eq 0 ]; then
  echo "Ablation test completed successfully"
else
  echo "Error: Ablation test failed"
  exit 1
fi

# Display results summary
if [ -f "$output_dir/ablation_summary.md" ]; then
    echo "Summary Results:"
    echo "================"
    cat "$output_dir/ablation_summary.md" | head -20
    echo "..."
    echo "Full report available at: $output_dir/ablation_summary.md"
else
    echo "No summary file found."
fi

echo "Comprehensive ablation testing completed. Results are in $output_dir"