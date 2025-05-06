#!/usr/bin/env python3
"""
Test script for the enhanced query generator.

This script demonstrates the capabilities of the ModelBasedQueryGenerator
by generating queries from various sample inputs.
"""

import argparse
import logging
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add the project root to the Python path
current_path = Path(__file__).parent.resolve()
while not (current_path / "Indaleko.py").exists() and current_path != current_path.parent:
    current_path = current_path.parent
os.environ["INDALEKO_ROOT"] = str(current_path)
sys.path.insert(0, str(current_path))

from tools.data_generator_enhanced.testing.enhanced_query_generator import ModelBasedQueryGenerator


def setup_logging():
    """Set up logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Test enhanced query generation")

    parser.add_argument(
        "--output",
        type=str,
        help="Path to output file",
        default="query_test_results.json"
    )

    parser.add_argument(
        "--examples",
        type=int,
        help="Number of examples to generate",
        default=10
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    return parser.parse_args()


def generate_sample_queries():
    """Generate a set of sample natural language queries."""
    return [
        "Find all PDF files",
        "Show me documents modified in the last week",
        "Find large video files",
        "Show me spreadsheets in the Documents folder",
        "Find files containing the word 'budget'",
        "Show me files I edited yesterday",
        "Find images from San Francisco",
        "Show me files related to Project X",
        "Find documents from my laptop",
        "Show me recently modified large files",
        "Find PDF files that I've accessed recently",
        "Show me files shared by John",
        "Find files with checksum abc123",
        "Show me files in my Downloads folder",
        "Find emails with attachments",
        "Show me all video files larger than 1GB",
        "Find files related to document xyz789",
        "Show me all files created by Photoshop",
        "Find spreadsheets with financial data",
        "Show me all files accessed from my work computer"
    ]


def generate_sample_criteria():
    """Generate sample criteria for query generation."""
    return [
        {"name": "%report%"},
        {"extension": "pdf", "min_size": 1000000},
        {"path": "%/Documents/%", "max_size": 10000000},
        {"mime_type": "application/pdf", "content_pattern": "%budget%"},
        {"activity_type": "FileEdit", "user_id": "user123"},
        {"start_time": (datetime.now(timezone.utc).isoformat()),
         "end_time": (datetime.now(timezone.utc).isoformat())},
        {"machine_id": "laptop-001", "extension": "jpg"},
        {"sort_field": "size", "sort_direction": "DESC", "limit": 10},
        {"activity_type": "FileAccess", "start_time": (datetime.now(timezone.utc).isoformat())},
        {"mime_type": "video/mp4", "min_size": 100000000}
    ]


def main():
    """Main function."""
    # Parse arguments
    args = parse_args()

    # Set up logging
    setup_logging()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logging.info("Testing enhanced query generator")

    # Initialize query generator
    query_generator = ModelBasedQueryGenerator()

    # Generate sample natural language queries
    nl_queries = generate_sample_queries()
    nl_results = []

    # Generate queries from NL
    for i, query in enumerate(nl_queries[:args.examples]):
        logging.info(f"Generating AQL for NL query: {query}")

        # Create appropriate metadata context
        metadata_context = {}
        if "pdf" in query.lower():
            metadata_context["extension"] = "pdf"
            metadata_context["mime_type"] = "application/pdf"
        elif "video" in query.lower():
            metadata_context["extension"] = "mp4"
            metadata_context["mime_type"] = "video/mp4"
        elif "image" in query.lower():
            metadata_context["extension"] = "jpg"
            metadata_context["mime_type"] = "image/jpeg"
        elif "spreadsheet" in query.lower():
            metadata_context["extension"] = "xlsx"
            metadata_context["mime_type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        if "large" in query.lower():
            metadata_context["min_size"] = 1000000

        if "recent" in query.lower() or "last week" in query.lower():
            metadata_context["start_time"] = (datetime.now(timezone.utc).isoformat())
            metadata_context["end_time"] = (datetime.now(timezone.utc).isoformat())

        # Generate the AQL query
        aql_query = query_generator.generate_from_nl(query, metadata_context)

        # Add to results
        nl_results.append({
            "nl_query": query,
            "metadata_context": metadata_context,
            "aql_query": aql_query
        })

    # Generate sample criteria-based queries
    criteria_list = generate_sample_criteria()
    criteria_results = []

    # Generate queries from criteria
    for i, criteria in enumerate(criteria_list[:args.examples]):
        logging.info(f"Generating AQL for criteria: {criteria}")

        # Generate the AQL query
        aql_query = query_generator.generate_from_criteria(criteria)

        # Add to results
        criteria_results.append({
            "criteria": criteria,
            "aql_query": aql_query
        })

    # Combine results
    results = {
        "nl_queries": nl_results,
        "criteria_queries": criteria_results,
        "timestamp": datetime.now().isoformat()
    }

    # Save results
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)

    logging.info(f"Results saved to {args.output}")

    # Log some sample results
    logging.info("Sample NL query results:")
    for i, result in enumerate(nl_results[:3]):
        logging.info(f"Query: {result['nl_query']}")
        logging.info(f"AQL: {result['aql_query']}")
        logging.info("---")

    logging.info("Sample criteria query results:")
    for i, result in enumerate(criteria_results[:3]):
        logging.info(f"Criteria: {result['criteria']}")
        logging.info(f"AQL: {result['aql_query']}")
        logging.info("---")


if __name__ == "__main__":
    main()
