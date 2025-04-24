"""
Simple test script to demonstrate the query pattern analysis functionality.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason and contributors

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
from datetime import UTC, datetime

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.memory.test_query_pattern_analysis import MockQueryGeneratorTests

# pylint: enable=wrong-import-position


def run_demo():
    """Run a demonstration of the query pattern analyzer functionality."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("Indaleko Query Pattern Analysis Demo")
    print("===================================\n")

    # Create a test instance that generates mock data
    test_obj = MockQueryGeneratorTests()
    test_obj.setUp()

    # Run the test that generates mock data
    print("Generating mock query data...")
    test_obj.test_with_generated_queries()

    # Use the analyzer with the generated data
    analyzer = test_obj.analyzer

    # Run the complete analysis
    print("\nRunning query pattern analysis...")
    summary, suggestions = analyzer.analyze_and_generate()

    # Print the summary
    print("\nQuery Pattern Analysis Results:")
    if summary and isinstance(summary, dict):
        print(f"- Processed {summary.get('query_count', 0)} mock queries")
        print(f"- Detected {summary.get('chain_count', 0)} query chains")
        print(f"- Identified {summary.get('pattern_count', 0)} patterns")

        if summary.get("top_entities"):
            print(f"\nTop entities: {', '.join(summary['top_entities'])}")

        if summary.get("top_intents"):
            print(f"Top intents: {', '.join(summary['top_intents'])}")
    else:
        print("- No summary information available")

    # Print the patterns
    print("\nDetected Query Patterns:")
    for i, pattern in enumerate(analyzer.data.query_patterns, 1):
        print(
            f"{i}. {pattern.pattern_name} ({pattern.pattern_type}, confidence: {pattern.confidence:.2f})",
        )
        print(f"   {pattern.description}")

    # Print the suggestions
    if suggestions:
        print("\nGenerated Suggestions:")
        for i, suggestion in enumerate(suggestions, 1):
            print(
                f"{i}. {suggestion.title} ({suggestion.suggestion_type}, confidence: {suggestion.confidence:.2f})",
            )
            print(f"   {suggestion.content}")

    # Calculate metrics
    print("\nCalculating query metrics...")
    metrics = analyzer.calculate_metrics()

    print("\nQuery Metrics Summary:")
    print(f"- Total queries: {metrics.total_queries}")
    print(f"- Success rate: {metrics.success_rate:.1%}")
    print(f"- Avg query length: {metrics.avg_query_length:.1f} characters")
    print(f"- Avg entity count: {metrics.avg_entity_count:.1f} entities per query")

    # Automatically save results to file
    filename = "query_patterns.json"

    # Prepare results for serialization
    results = {
        "timestamp": datetime.now(UTC).isoformat(),
        "query_count": (len(analyzer.data.queries) if hasattr(analyzer.data, "queries") else 0),
        "patterns": (
            [p.model_dump() for p in analyzer.data.query_patterns] if hasattr(analyzer.data, "query_patterns") else []
        ),
        "chains": (
            [c.model_dump() for c in analyzer.data.query_chains] if hasattr(analyzer.data, "query_chains") else []
        ),
        "entity_usage": (
            {k: v.model_dump() for k, v in analyzer.data.entity_usage.items()}
            if hasattr(analyzer.data, "entity_usage")
            else {}
        ),
        "metrics": metrics.model_dump() if metrics else None,
    }

    # Save to file
    with open(filename, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults saved to {filename}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test Query Pattern Analysis")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    run_demo()


if __name__ == "__main__":
    main()
