#!/usr/bin/env python3
"""
Test script to run the assistants CLI in batch mode with a simple query.

This script:
1. Creates a temporary file with a test query
2. Runs the assistants CLI in batch mode with the file
3. Cleans up the temporary file

Usage:
  python test_batch.py
"""

import os
import subprocess
import tempfile
from pathlib import Path

# Create a temporary file with a test query
test_query = "What files did I access yesterday?"

with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
    temp_file.write(test_query + '\n')
    temp_file_path = temp_file.name

print(f"Created temporary query file: {temp_file_path}")

# Build the command
cli_path = Path(__file__).parent / "cli.py"
cmd = f"python {cli_path} --input-file {temp_file_path} --verbose"

print(f"Running command: {cmd}")

# Run the CLI in batch mode
try:
    process = subprocess.run(
        cmd, 
        shell=True, 
        check=True, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        encoding='utf-8',
        timeout=120  # 2 minute timeout
    )
    
    # Display results
    print("\nSTDOUT:")
    print(process.stdout)
    
    if process.stderr:
        print("\nSTDERR:")
        print(process.stderr)
    
    print(f"\nExited with code: {process.returncode}")
    success = process.returncode == 0
    
except subprocess.TimeoutExpired:
    print("ERROR: Process timed out after 120 seconds")
    success = False
except subprocess.CalledProcessError as e:
    print(f"ERROR: Process failed with code {e.returncode}")
    print("\nSTDOUT:")
    print(e.stdout)
    print("\nSTDERR:")
    print(e.stderr)
    success = False
except Exception as e:
    print(f"ERROR: An unexpected error occurred: {e}")
    success = False
finally:
    # Clean up the temporary file
    if os.path.exists(temp_file_path):
        os.remove(temp_file_path)
        print(f"Removed temporary file: {temp_file_path}")

# Report overall status
print("\nTEST SUMMARY:")
print(f"Status: {'SUCCESS' if success else 'FAILED'}")