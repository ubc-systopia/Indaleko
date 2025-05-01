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

from tools.data_generator_enhanced.testing.query_analyzer import QueryAnalyzer
import logging

# Simple logging setup function
def setup_logging():
    """Set up basic logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
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
    report = analyzer.generate_report(output_dir / "query_analysis_report.md")
    configs = analyzer.generate_test_configurations(output_dir)
    
    print(f"Generated {len(configs)} test configurations")
    print(f"Report written to {output_dir / 'query_analysis_report.md'}")
    print("\nQuery Analysis Summary:")
    
    # Print top 10 tags
    tag_stats = analyzer.get_tag_statistics()
    print("\nTop Query Tags:")
    for tag, count in sorted(tag_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {tag}: {count}")
    
    # Print pattern counts
    analysis = analyzer.analyze_query_patterns()
    print("\nPattern Counts:")
    for pattern, count in analysis["pattern_counts"].items():
        percentage = 100 * count / analysis["total_queries"]
        print(f"  {pattern}: {count} ({percentage:.1f}%)")


if __name__ == "__main__":
    main()