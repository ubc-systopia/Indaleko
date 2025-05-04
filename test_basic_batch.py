#!/usr/bin/env python3
"""
Test script for the most basic batch query functionality.
"""

import subprocess
from pathlib import Path

# Create a very basic test file with a simple query
test_query = "exit\n"  # Just exit immediately to test batch processing

# Write the test query to a file
test_file_path = Path("simple_test_query.txt").absolute()
test_file_path.write_text(test_query)

print(f"Created simple test file at {test_file_path}")
print(f"File contains: {test_query}")

# Test batch mode with a query that will just exit
print("\nTesting batch mode with simple exit command...")
cmd = f"python -m query.cli --input-file {test_file_path}"
print(f"Running command: {cmd}")

try:
    result = subprocess.run(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10, check=False,
    )

    print(f"\nExit code: {result.returncode}")
    if result.stdout:
        print(f"stdout: {result.stdout}")
    if result.stderr:
        print(f"stderr: {result.stderr}")

    # Check if the command completed successfully
    batch_success = result.returncode == 0

except subprocess.TimeoutExpired:
    print("Command timed out")
    batch_success = False
except Exception as e:
    print(f"Error: {e}")
    batch_success = False

# Clean up
if test_file_path.exists():
    test_file_path.unlink()
    print(f"\nRemoved test file: {test_file_path}")

# Report result
print(f"\nBatch mode test result: {'SUCCESS' if batch_success else 'FAILED'}")
