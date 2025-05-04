#!/usr/bin/env python3
"""
Batch query runner for Indaleko.

This script processes queries from a file using the CLI, but ensures
that the process exits properly when finished.
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Process queries from a file using the CLI."""
    # Check arguments
    if len(sys.argv) < 2:
        print("Usage: python run_batch.py <query_file> [cli_options]")
        print("Example: python run_batch.py queries.txt --enhanced-nl")
        return 1

    # Get query file path
    query_file = Path(sys.argv[1])
    if not query_file.exists():
        print(f"Error: File {query_file} not found")
        return 1

    # Build the CLI command with all additional arguments
    cli_options = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    cmd = f"python -m query.cli --input-file {query_file} {cli_options}"

    print(f"Running command: {cmd}")

    # Set a reasonable timeout (adjust as needed)
    timeout_seconds = 30

    try:
        # Run the command with timeout
        result = subprocess.run(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )

        # Print output
        print(f"\nExit code: {result.returncode}")
        if result.stdout:
            print("\nStandard output:")
            print(result.stdout)
        if result.stderr:
            print("\nStandard error:")
            print(result.stderr)

        # Check success
        if result.returncode != 0:
            print("Command failed")
            return result.returncode

        print("Batch processing completed successfully")
        return 0

    except subprocess.TimeoutExpired:
        print(f"Command timed out after {timeout_seconds} seconds")
        print("Batch processing might not be exiting properly.")
        print("\nTip: Try adding 'exit' as the last line in your query file.")
        return 1
    except Exception as e:
        print(f"Error running command: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
