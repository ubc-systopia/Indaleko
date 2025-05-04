#!/usr/bin/env python3
"""
Simplified batch mode processor for Indaleko queries.

This script reads a batch file and processes each query, exiting cleanly when done.
"""

import sys
from pathlib import Path

# Make sure Indaleko modules are accessible
current_path = Path(__file__).parent.resolve()
if str(current_path) not in sys.path:
    sys.path.insert(0, str(current_path))

# Import the necessary modules
import argparse

from query.cli import IndalekoQueryCLI


def main():
    """Process a batch file of queries."""
    # Create a simplified parser for batch mode
    parser = argparse.ArgumentParser(description="Indaleko Batch Query Processor")
    parser.add_argument("input_file", help="File containing queries to process (one per line)")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    # Check if input file exists
    batch_file_path = Path(args.input_file)
    if not batch_file_path.exists():
        print(f"Error: Input file {batch_file_path} not found.")
        return 1

    # Read queries from the file
    with batch_file_path.open(mode="r", encoding="utf-8") as batch_file:
        queries = [line.strip() for line in batch_file.readlines() if line.strip()]

    print(f"Loaded {len(queries)} queries from {batch_file_path}")

    # Create CLI instance with minimal configuration
    cli = IndalekoQueryCLI()

    # Process each query
    for i, query in enumerate(queries, 1):
        print(f"Processing query {i}/{len(queries)}: {query}")

        # Skip exit commands
        if query.lower() in ["exit", "quit", "bye", "leave"]:
            print("Skipping exit command")
            continue

        # Process the query
        try:
            # Simple processing implementation
            parsed_query = cli.nl_parser.parse(query=query)
            print(f"Query parsed successfully. Intent: {parsed_query.Intent.intent}")

            # Map entities and process further if needed
            # This is a simplified version just to demonstrate batch processing

        except Exception as e:
            print(f"Error processing query: {e}")

    print("Batch processing completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
