"""
CLI tool for analyzing errors in the Indaleko query system.

This tool provides error analysis and statistics for the Indaleko query system,
helping to identify and diagnose issues with LLM responses.

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
import datetime
import json
import logging
import os
import sys
import time
from typing import Any

import matplotlib.pyplot as plt
from tabulate import tabulate

# Set up environment variables and paths
current_path = os.path.dirname(os.path.abspath(__file__))
os.environ["INDALEKO_ROOT"] = current_path if not os.environ.get("INDALEKO_ROOT") else os.environ.get("INDALEKO_ROOT")
if os.environ["INDALEKO_ROOT"] not in sys.path:
    sys.path.append(os.environ["INDALEKO_ROOT"])

# Import Indaleko components
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from db.db_config import IndalekoDBConfig
from query.history.data_models.query_history import QueryHistoryData
from query.query_processing.nl_parser import NLParser
from query.query_processing.query_history import QueryHistory
from query.utils.llm_connector.openai_connector import OpenAIConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Test query categories
TEST_QUERIES = {
    "simple_search": [
        "Show me files with test in the name",
        "Find documents about Indaleko",
        "Search for PDF files",
    ],
    "counting_queries": [
        "How many files do I have with test in the name?",
        "Count documents modified last week",
        "How many PDF files are in my documents folder?",
    ],
    "filtering_queries": [
        "Find files larger than 1MB",
        "Show me images modified yesterday",
        "List all documents created in January",
    ],
    "complex_queries": [
        "Show me files with test in the name that are larger than 10MB",
        "Find PDF files I modified last week that contain the word 'budget'",
        "List Excel files shared with Bob in the last month",
    ],
    "analytical_queries": [
        "What is the average size of my documents?",
        "Show me the distribution of file types in my downloads folder",
        "Which file has the most versions?",
    ],
}


def load_api_key() -> str:
    """Load the OpenAI API key from config file."""
    import configparser

    config_dir = os.path.join(os.environ["INDALEKO_ROOT"], "config")
    config_file = os.path.join(config_dir, "openai-key.ini")

    if not os.path.exists(config_file):
        raise ValueError(f"API key file not found: {config_file}")

    config = configparser.ConfigParser()
    config.read(config_file, encoding="utf-8-sig")

    if "openai" not in config or "api_key" not in config["openai"]:
        raise ValueError("OpenAI API key not found in config file")

    openai_key = config["openai"]["api_key"]

    # Clean up the key if it has quotes
    if openai_key[0] in ["'", '"'] and openai_key[-1] in ["'", '"']:
        openai_key = openai_key[1:-1]

    return openai_key


def initialize_parser() -> tuple[NLParser, QueryHistory]:
    """Initialize the NL parser and query history with necessary components."""
    # Load API key
    api_key = load_api_key()
    logger.info("API key loaded")

    # Initialize DB config
    db_config = IndalekoDBConfig(
        config_file=os.path.join(
            os.environ["INDALEKO_ROOT"],
            "config",
            "indaleko-db-config.ini",
        ),
    )
    logger.info("DB config initialized")

    # Initialize collections metadata
    collections_metadata = IndalekoDBCollectionsMetadata(db_config)
    logger.info("Collections metadata initialized")

    # Initialize LLM connector
    llm_connector = OpenAIConnector(api_key=api_key, model="gpt-4o-mini")
    logger.info("LLM connector initialized")

    # Initialize and return NL parser
    nl_parser = NLParser(collections_metadata, llm_connector)
    logger.info("NL parser initialized")

    # Initialize query history
    query_history = QueryHistory(db_config)
    logger.info("Query history initialized")

    return nl_parser, query_history


def run_queries(
    nl_parser: NLParser,
    query_history: QueryHistory,
    queries: list[str],
) -> dict[str, Any]:
    """Run a list of queries through the parser and collect error statistics."""
    results = {
        "total_queries": len(queries),
        "successful_queries": 0,
        "error_queries": 0,
        "queries": [],
    }

    for query in queries:
        try:
            logger.info(f"Processing query: {query}")
            start_time = time.time()
            start_datetime = datetime.datetime.now(datetime.UTC)

            # Parse the query
            parsed_results = nl_parser.parse(query)

            end_time = time.time()
            end_datetime = datetime.datetime.now(datetime.UTC)
            elapsed_time = end_time - start_time

            # Create empty fields required by QueryHistoryData
            from query.query_processing.data_models.query_input import StructuredQuery
            from query.query_processing.data_models.translator_response import (
                TranslatorOutput,
            )

            # Record the query in history
            query_history_data = QueryHistoryData(
                OriginalQuery=query,
                ParsedResults=parsed_results,
                LLMName=nl_parser.llm_connector.get_llm_name(),
                LLMQuery=StructuredQuery(query=query, search_type="query"),
                TranslatedOutput=TranslatorOutput(
                    aql_query="",
                    bind_vars={},
                    confidence=1.0,
                    explanation="Test query for error analysis",
                ),
                RawResults=[],
                AnalyzedResults=[],
                Facets={},
                RankedResults=[],
                StartTimestamp=start_datetime,
                EndTimestamp=end_datetime,
                ElapsedTime=elapsed_time,
            )

            # Store in query history
            query_history.add(query_history_data)
            logger.info(f"Query '{query}' recorded in query history")

            # Record successful query
            results["successful_queries"] += 1
            results["queries"].append(
                {"query": query, "success": True, "time": elapsed_time},
            )

        except Exception as e:
            logger.error(f"Error processing query '{query}': {e}")
            results["error_queries"] += 1
            results["queries"].append(
                {"query": query, "success": False, "error": str(e)},
            )

    return results


def display_error_statistics(nl_parser: NLParser) -> None:
    """Display error statistics collected by the parser."""
    stats = nl_parser.get_error_stats()

    print("\n=== Error Statistics ===")
    print(f"Total errors: {stats['error_counts']['total']}")
    print(f"Error rate: {stats['error_rate'] * 100:.2f}%")

    # Print error counts by category
    print("\nErrors by Category:")
    error_categories = {k: v for k, v in stats["error_counts"].items() if k != "total"}
    for category, count in error_categories.items():
        print(f"  {category}: {count}")

    # Print common errors
    if stats["common_errors"]:
        print("\nMost Common Errors:")
        error_table = []
        for error in stats["common_errors"][:5]:  # Show top 5 errors
            error_table.append(
                [
                    error["error"],
                    error["count"],
                    ", ".join(error["stages"]),
                    "; ".join(error["samples"][:2]),  # Show up to 2 sample queries
                ],
            )

        print(
            tabulate(
                error_table,
                headers=["Error", "Count", "Stages", "Sample Queries"],
                tablefmt="grid",
            ),
        )


def generate_error_visualizations(nl_parser: NLParser, output_dir: str) -> None:
    """Generate error visualizations based on parser statistics."""
    stats = nl_parser.get_error_stats()
    os.makedirs(output_dir, exist_ok=True)

    # Pie chart of error types
    error_categories = {k: v for k, v in stats["error_counts"].items() if k != "total" and v > 0}
    if error_categories:
        plt.figure(figsize=(10, 6))
        plt.pie(
            error_categories.values(),
            labels=error_categories.keys(),
            autopct="%1.1f%%",
            startangle=90,
        )
        plt.axis("equal")
        plt.title("Error Distribution by Category")
        plt.savefig(os.path.join(output_dir, "error_distribution.png"))
        plt.close()

    # Bar chart of common errors
    if stats["common_errors"]:
        common_errors = stats["common_errors"][:10]  # Top 10 errors
        error_names = [err["error"][:20] + "..." if len(err["error"]) > 20 else err["error"] for err in common_errors]
        error_counts = [err["count"] for err in common_errors]

        plt.figure(figsize=(12, 6))
        plt.bar(error_names, error_counts)
        plt.xticks(rotation=45, ha="right")
        plt.title("Most Common Errors")
        plt.ylabel("Count")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "common_errors.png"))
        plt.close()

    # Error stage distribution
    stage_counts = {}
    for error in nl_parser.error_log:
        stage = error.get("stage", "unknown")
        if stage not in stage_counts:
            stage_counts[stage] = 0
        stage_counts[stage] += 1

    if stage_counts:
        plt.figure(figsize=(10, 6))
        plt.bar(stage_counts.keys(), stage_counts.values())
        plt.title("Errors by Processing Stage")
        plt.ylabel("Count")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "errors_by_stage.png"))
        plt.close()


def test_parser_robustness(
    output_file: str | None = None,
    visualizations_dir: str | None = None,
) -> None:
    """Test the parser's robustness by running various query types and analyzing errors."""
    # Initialize parser and query history
    nl_parser, query_history = initialize_parser()

    # Run all query categories
    all_results = {}
    for category, queries in TEST_QUERIES.items():
        logger.info(f"Testing {category} queries")
        results = run_queries(nl_parser, query_history, queries)
        all_results[category] = results

    # Display overall results
    total_queries = sum(results["total_queries"] for results in all_results.values())
    total_successful = sum(results["successful_queries"] for results in all_results.values())

    print("\n=== Robustness Test Results ===")
    print(f"Total queries tested: {total_queries}")
    print(f"Successful queries: {total_successful}")
    print(f"Success rate: {total_successful / total_queries * 100:.2f}%")

    # Display results by category
    print("\nResults by Query Category:")
    category_table = []
    for category, results in all_results.items():
        success_rate = results["successful_queries"] / results["total_queries"] * 100
        category_table.append(
            [
                category,
                results["total_queries"],
                results["successful_queries"],
                f"{success_rate:.2f}%",
            ],
        )

    print(
        tabulate(
            category_table,
            headers=["Category", "Total", "Successful", "Success Rate"],
            tablefmt="grid",
        ),
    )

    # Display error statistics
    display_error_statistics(nl_parser)

    # Generate visualizations if directory is provided
    if visualizations_dir:
        generate_error_visualizations(nl_parser, visualizations_dir)

    # Save results to file if provided
    if output_file:
        result_data = {
            "summary": {
                "total_queries": total_queries,
                "successful_queries": total_successful,
                "success_rate": total_successful / total_queries,
            },
            "categories": all_results,
            "error_stats": nl_parser.get_error_stats(),
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=2)

        logger.info(f"Results saved to {output_file}")


def run_specific_query(query: str) -> None:
    """Run a specific query and display detailed error analysis if it fails."""
    # Initialize parser and query history
    nl_parser, query_history = initialize_parser()

    try:
        # Process the query
        logger.info(f"Processing query: {query}")
        start_time = time.time()
        start_datetime = datetime.datetime.now(datetime.UTC)

        result = nl_parser.parse(query)

        end_time = time.time()
        end_datetime = datetime.datetime.now(datetime.UTC)
        elapsed_time = end_time - start_time

        # Create empty fields required by QueryHistoryData
        from query.query_processing.data_models.query_input import StructuredQuery
        from query.query_processing.data_models.translator_response import (
            TranslatorOutput,
        )

        # Record the query in history
        query_history_data = QueryHistoryData(
            OriginalQuery=query,
            ParsedResults=result,
            LLMName=nl_parser.llm_connector.get_llm_name(),
            LLMQuery=StructuredQuery(query=query, search_type="query"),
            TranslatedOutput=TranslatorOutput(
                aql_query="",
                bind_vars={},
                confidence=1.0,
                explanation="Test query for error analysis",
            ),
            RawResults=[],
            AnalyzedResults=[],
            Facets={},
            RankedResults=[],
            StartTimestamp=start_datetime,
            EndTimestamp=end_datetime,
            ElapsedTime=elapsed_time,
        )

        # Store in query history
        query_history.add(query_history_data)
        logger.info(f"Query '{query}' recorded in query history")

        # Display success
        print(f"\n=== Query: {query} ===")
        print("Status: Success")
        print(f"Processing time: {end_time - start_time:.4f} seconds")
        print(f"Intent: {result.intent}")
        print(f"Entities: {[entity.name for entity in result.entities.entities]}")
        print("Recorded in QueryHistory: Yes")

    except Exception as e:
        # Display error details
        print(f"\n=== Query: {query} ===")
        print("Status: Failed")
        print(f"Error: {e}")
        print("Recorded in QueryHistory: No")

        # Display error statistics
        display_error_statistics(nl_parser)


def main():
    """Main entry point for the error analysis tool."""
    parser = argparse.ArgumentParser(description="Indaleko Query Error Analysis Tool")

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Test robustness command
    test_parser = subparsers.add_parser(
        "test",
        help="Test parser robustness with predefined queries",
    )
    test_parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output JSON file for results",
    )
    test_parser.add_argument(
        "--visualize",
        "-v",
        type=str,
        help="Directory for error visualizations",
    )

    # Run specific query command
    query_parser = subparsers.add_parser(
        "query",
        help="Run a specific query and analyze errors",
    )
    query_parser.add_argument("query_text", type=str, help="Query text to process")

    args = parser.parse_args()

    # Execute the appropriate command
    if args.command == "test":
        test_parser_robustness(args.output, args.visualize)
    elif args.command == "query":
        run_specific_query(args.query_text)
    else:
        # Default to showing help
        parser.print_help()


if __name__ == "__main__":
    main()
