#!/usr/bin/env python
"""
Test script for the Cognitive Memory Query Tool.

This script tests the functionality of the cognitive memory query tool,
which provides a unified interface for querying all tiers of the cognitive memory system.

Usage:
    python test_cognitive_query.py --query="sample query" [--memory-tiers=all] [--debug]

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import argparse
import json
import logging
import os
import sys
from typing import Any

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import the cognitive memory query tool
try:
    from query.tools.base import ToolInput
    from query.tools.memory.cognitive_query import CognitiveMemoryQueryTool
except ImportError as e:
    print(f"Error importing Cognitive Memory Query Tool: {e}")
    sys.exit(1)


def run_test(
    query: str,
    memory_tiers: str = "all",
    importance_min: float = 0.0,
    w5h_filter: dict[str, list[str]] | None = None,
    concept_filter: list[str] | None = None,
    include_relationships: bool = False,
    limit: int = 10,
    db_config_path: str | None = None,
    debug: bool = False,
) -> dict[str, Any]:
    """
    Run a test query against the cognitive memory system.

    Args:
        query: The search query
        memory_tiers: Comma-separated list of memory tiers to query
        importance_min: Minimum importance score
        w5h_filter: Optional W5H filter dictionary
        concept_filter: Optional list of concepts to filter by
        include_relationships: Whether to include relationships
        limit: Maximum number of results per tier
        db_config_path: Path to the database configuration file
        debug: Whether to enable debug logging

    Returns:
        Dictionary with the query results
    """
    # Configure logging
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("cognitive_memory_test")

    try:
        # Create the tool
        logger.info("Creating cognitive memory query tool")
        tool = CognitiveMemoryQueryTool()

        # Create tool input parameters
        parameters = {
            "query": query,
            "memory_tiers": memory_tiers,
            "importance_min": importance_min,
            "include_relationships": include_relationships,
            "limit": limit,
        }

        # Only add optional parameters if they're provided
        if w5h_filter is not None:
            parameters["w5h_filter"] = w5h_filter

        if concept_filter is not None:
            parameters["concept_filter"] = concept_filter

        if db_config_path is not None:
            parameters["db_config_path"] = db_config_path

        # Create tool input
        input_data = ToolInput(
            tool_name="cognitive_memory_query",
            parameters=parameters,
        )

        # Define progress callback
        def progress_callback(progress_data):
            logger.info(
                f"Progress: {progress_data.stage} - {progress_data.message} ({progress_data.progress:.0%})",
            )

        # Set the progress callback
        tool.set_progress_callback(progress_callback)

        # Execute the tool
        logger.info(f"Executing query: {query}")
        start_time = time.time()
        result = tool.wrapped_execute(input_data)
        elapsed_time = time.time() - start_time

        # Check for success
        if result.success:
            logger.info(f"Query executed successfully in {elapsed_time:.2f} seconds")

            # Get result data
            result_data = result.result

            # Display tier statistics
            tier_stats = result_data.get("tier_stats", {})
            logger.info("Tier statistics:")
            for tier, stats in tier_stats.items():
                logger.info(
                    f"  {tier}: {stats['count']} results, avg importance: {stats['avg_importance']:.2f}",
                )

            # Display performance metrics
            performance = result_data.get("performance", {})
            logger.info(f"Performance: {performance}")

            # Return results
            return result_data
        else:
            logger.error(f"Query execution failed: {result.error}")
            if result.trace:
                logger.debug(f"Error trace:\n{result.trace}")
            return {"error": result.error}

    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        import traceback

        logger.debug(f"Exception trace:\n{traceback.format_exc()}")
        return {"error": str(e)}


def main():
    """Main function for the test script."""
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Test the cognitive memory query tool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Add arguments
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="The search query to execute",
    )
    parser.add_argument(
        "--memory-tiers",
        type=str,
        default="all",
        help="Memory tiers to include in the search (comma-separated list)",
    )
    parser.add_argument(
        "--importance-min",
        type=float,
        default=0.0,
        help="Minimum importance score for results",
    )
    parser.add_argument(
        "--w5h-filter",
        type=str,
        default=None,
        help='JSON string for W5H filter (e.g. \'{"what": ["document"]}\')',
    )
    parser.add_argument(
        "--concept-filter",
        type=str,
        default=None,
        help="Comma-separated list of concepts to filter by",
    )
    parser.add_argument(
        "--include-relationships",
        action="store_true",
        help="Include entity relationships in results",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of results per tier",
    )
    parser.add_argument(
        "--db-config",
        type=str,
        default=None,
        help="Path to the database configuration file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to save the results as JSON",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    # Add test mode arguments
    parser.add_argument(
        "--test-tier",
        type=str,
        default=None,
        help="Test a specific memory tier only (sensory, short_term, long_term, archival)",
    )
    parser.add_argument(
        "--test-w5h",
        action="store_true",
        help="Test W5H filtering with a sample filter",
    )
    parser.add_argument(
        "--test-concepts",
        action="store_true",
        help="Test concept filtering with sample concepts",
    )

    # Parse arguments
    args = parser.parse_args()

    # Handle test modes - override parameters as needed
    if args.test_tier:
        print(f"Testing specific memory tier: {args.test_tier}")
        args.memory_tiers = args.test_tier

    if args.test_w5h:
        print("Testing W5H filtering with sample filter")
        # Create a sample W5H filter for testing
        test_w5h = {
            "what": ["document", "text_file"],
            "where": ["documents_folder"],
            "why": ["project_work"],
        }
        args.w5h_filter = json.dumps(test_w5h)
        print(f"Using W5H filter: {args.w5h_filter}")

    if args.test_concepts:
        print("Testing concept filtering with sample concepts")
        args.concept_filter = "document,text,project"
        print(f"Using concept filter: {args.concept_filter}")

    # Process W5H filter if provided
    w5h_filter = None
    if args.w5h_filter:
        try:
            w5h_filter = json.loads(args.w5h_filter)
        except json.JSONDecodeError as e:
            print(f"Error parsing W5H filter: {e}")
            sys.exit(1)

    # Process concept filter if provided
    concept_filter = None
    if args.concept_filter:
        concept_filter = [concept.strip() for concept in args.concept_filter.split(",")]

    # Run the test
    results = run_test(
        query=args.query,
        memory_tiers=args.memory_tiers,
        importance_min=args.importance_min,
        w5h_filter=w5h_filter,
        concept_filter=concept_filter,
        include_relationships=args.include_relationships,
        limit=args.limit,
        db_config_path=args.db_config,
        debug=args.debug,
    )

    # Save results to file if requested
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {args.output}")

    # Print summary of results
    if "error" in results:
        print(f"Error: {results['error']}")
        sys.exit(1)
    else:
        # Print summary
        result_list = results.get("results", [])
        print(f"\nFound {len(result_list)} results across memory tiers")

        # Print tier statistics
        tier_stats = results.get("tier_stats", {})
        print("\nResults by memory tier:")
        for tier, stats in tier_stats.items():
            print(f"  {tier}: {stats['count']} results")

        # Print top results
        if result_list:
            print("\nTop results:")
            for i, result in enumerate(result_list[:5]):  # Show top 5
                memory_tier = result.get("memory_tier", "unknown")
                file_path = result.get("Record", {}).get("Data", {}).get("file_path", "unknown")
                importance = result.get("Record", {}).get("Data", {}).get("importance_score", 0.0)
                print(
                    f"  {i+1}. [{memory_tier}] {file_path} (importance: {importance:.2f})",
                )

    return 0


if __name__ == "__main__":
    import time

    sys.exit(main())
