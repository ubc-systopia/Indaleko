#!/usr/bin/env python3
"""
Script to analyze test queries and generate configurations.

This script analyzes the test queries and generates test configurations
and a report on query patterns.
"""

import os
import sys

from pathlib import Path


# Bootstrap project root so imports work
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    # Walk up until we find the project entry point
    while not (current_path / "Indaleko.py").exists():
        current_path = current_path.parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

import logging

from tools.data_generator_enhanced.testing.query_analyzer import QueryAnalyzer


# Simple logging setup function
def setup_logging():
    """Set up basic logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    """Main function for the query analyzer script."""
    # Set up logging
    setup_logging()

    # Set paths
    this_dir = Path(__file__).parent
    query_file = this_dir / "config" / "test_data" / "test_queries.json"
    output_dir = this_dir / "config" / "test_configs"

    # Create the output directory
    os.makedirs(output_dir, exist_ok=True)

    # Analyze queries
    analyzer = QueryAnalyzer(query_file)
    analyzer.generate_report(output_dir / "query_analysis_report.md")
    analyzer.generate_test_configurations(output_dir)


    # Print top 10 tags
    tag_stats = analyzer.get_tag_statistics()
    for _tag, count in sorted(tag_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
        pass

    # Print pattern counts
    analysis = analyzer.analyze_query_patterns()
    for count in analysis["pattern_counts"].values():
        100 * count / analysis["total_queries"]


if __name__ == "__main__":
    main()
