#!/usr/bin/env python3
"""
Simple test script for batch mode in query CLI.
"""

import os
import subprocess
import tempfile

# Create a simple query file
queries = """find files
list documents
exit
"""

# Create a temporary file
with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as temp_file:
    temp_file.write(queries)
    temp_file_path = temp_file.name

try:
    print(f"Created temporary query file: {temp_file_path}")
    print(f"Content:\n{queries}")

    # Run the command with the temporary file
    cmd = f"python -m query.cli --input-file {temp_file_path}"
    print(f"\nRunning command: {cmd}")

    # Set a short timeout to avoid hanging
    result = subprocess.run(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=15,
        check=False,  # 15 second timeout
    )

    print(f"Exit code: {result.returncode}")
    print("\nStandard output:")
    print(result.stdout[:1000] + "..." if len(result.stdout) > 1000 else result.stdout)
    print("\nStandard error:")
    print(result.stderr[:1000] + "..." if len(result.stderr) > 1000 else result.stderr)

    print("\nTest completed successfully." if result.returncode == 0 else "\nTest failed.")

except subprocess.TimeoutExpired:
    print("Command timed out - batch processing may not be exiting correctly!")
except Exception as e:
    print(f"Error: {e}")
finally:
    # Clean up
    try:
        os.unlink(temp_file_path)
        print(f"Removed temporary file: {temp_file_path}")
    except:
        pass
