#!/usr/bin/env python3
"""
Minimal test for batch mode with an empty file.
"""

import os
import subprocess
import tempfile

# Create a temp file with just "exit" in it
with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
    f.write("exit\n")
    temp_path = f.name

print(f"Created test file at {temp_path}")

# Run with a very short timeout
try:
    cmd = f"python -m query.cli --input-file {temp_path} --debug"
    print(f"Running: {cmd}")

    # Very short timeout (5 seconds)
    result = subprocess.run(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5, check=False,
    )

    print(f"Exit code: {result.returncode}")
    print(f"Output: {result.stdout[:100]}")

except subprocess.TimeoutExpired:
    print("Command timed out - batch processing still broken")
finally:
    if os.path.exists(temp_path):
        os.unlink(temp_path)
        print(f"Removed test file: {temp_path}")
