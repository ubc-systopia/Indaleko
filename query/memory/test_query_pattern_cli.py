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


    # Create a test instance that generates mock data
    test_obj = MockQueryGeneratorTests()
    test_obj.setUp()

    # Run the test that generates mock data
    test_obj.test_with_generated_queries()

    # Use the analyzer with the generated data
    analyzer = test_obj.analyzer

    # Run the complete analysis
    summary, suggestions = analyzer.analyze_and_generate()

    # Print the summary
    if summary and isinstance(summary, dict):

        if summary.get("top_entities"):
            pass

        if summary.get("top_intents"):
            pass
    else:
        pass

    # Print the patterns
    for _i, _pattern in enumerate(analyzer.data.query_patterns, 1):
        pass

    # Print the suggestions
    if suggestions:
        for _i, _suggestion in enumerate(suggestions, 1):
            pass

    # Calculate metrics
    metrics = analyzer.calculate_metrics()


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
