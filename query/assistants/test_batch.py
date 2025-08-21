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

with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as temp_file:
    temp_file.write(test_query + "\n")
    temp_file_path = temp_file.name


# Build the command
cli_path = Path(__file__).parent / "cli.py"
cmd = f"python {cli_path} --input-file {temp_file_path} --verbose"


# Run the CLI in batch mode
try:
    process = subprocess.run(
        cmd,
        shell=True,
        check=True,
        capture_output=True,
        encoding="utf-8",
        timeout=120,  # 2 minute timeout
    )

    # Display results

    if process.stderr:
        pass

    success = process.returncode == 0

except subprocess.TimeoutExpired:
    success = False
except subprocess.CalledProcessError:
    success = False
except Exception:
    success = False
finally:
    # Clean up the temporary file
    if os.path.exists(temp_file_path):
        os.remove(temp_file_path)

# Report overall status
