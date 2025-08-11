"""
Test script for validating the robustness of the Indaleko query processing.

This script will run a series of test queries through the Indaleko query processing
pipeline to ensure that it handles various query types correctly and consistently.
"""

import argparse
import datetime
import json
import logging
import os
import sys
import time

from typing import Any


# Set up environment variables
current_path = os.path.dirname(os.path.abspath(__file__))
os.environ["INDALEKO_ROOT"] = current_path
if current_path not in sys.path:
    sys.path.insert(0, current_path)

try:
    # Import necessary modules
    from db.db_collection_metadata import IndalekoDBCollectionsMetadata
    from db.db_config import IndalekoDBConfig
    from query.cli import IndalekoQueryCLI
    from query.history.data_models.query_history import QueryHistoryData
    from query.query_processing.nl_parser import NLParser
    from query.query_processing.query_history import QueryHistory
    from query.query_processing.query_translator.aql_translator import AQLTranslator
    from query.utils.llm_connector.openai_connector import OpenAIConnector
except ImportError:
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Test queries categorized by types
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

    config_file = os.path.join(
        os.environ.get("INDALEKO_ROOT"),
        "config",
        "openai-key.ini",
    )
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


def process_query(
    query: str,
    nl_parser: NLParser,
    translator: AQLTranslator,
    query_history: QueryHistory,
) -> dict[str, Any]:
    """Process a single query and return the results."""
    try:
        logger.info(f"Processing query: {query}")
        start_time = time.time()
        start_datetime = datetime.datetime.now(datetime.UTC)

        # Parse the query
        parsed_query = nl_parser.parse(query)

        # Create translator input
        from query.query_processing.data_models.translator_input import TranslatorInput

        translator_input = TranslatorInput(
            Query=parsed_query,
            Connector=nl_parser.llm_connector,
        )

        # Translate to AQL
        result = translator.translate(translator_input)

        end_time = time.time()
        end_datetime = datetime.datetime.now(datetime.UTC)
        elapsed_time = end_time - start_time

        # Check if view is used for text searches
        is_text_search = "test" in query.lower() or "find" in query.lower() or "search" in query.lower()
        uses_view = "ObjectsTextView" in result.aql_query if is_text_search else True
        uses_search_analyzer = "SEARCH ANALYZER" in result.aql_query if is_text_search else True

        # Record the query in history
        from query.query_processing.data_models.query_input import StructuredQuery

        query_history_data = QueryHistoryData(
            OriginalQuery=query,
            ParsedResults=parsed_query,
            LLMName=nl_parser.llm_connector.get_llm_name(),
            LLMQuery=StructuredQuery(query=query, search_type="query"),
            TranslatedOutput=result,
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

        # Return results
        return {
            "query": query,
            "aql_query": result.aql_query,
            "bind_vars": result.bind_vars,
            "confidence": result.confidence,
            "is_text_search": is_text_search,
            "uses_view": uses_view,
            "uses_search_analyzer": uses_search_analyzer,
            "success": True,
            "error": None,
            "recorded_in_history": True,
        }
    except Exception as e:
        logger.exception(f"Error processing query '{query}': {e}")
        return {
            "query": query,
            "success": False,
            "error": str(e),
            "recorded_in_history": False,
        }


def run_all_tests() -> dict[str, list[dict[str, Any]]]:
    """Run all test queries and return the results."""
    try:
        # Initialize components
        logger.info("Initializing components")

        # Load API key
        api_key = load_api_key()
        logger.info("API key loaded")

        # Initialize DB config
        db_config = IndalekoDBConfig(
            config_file=os.path.join(
                os.environ.get("INDALEKO_ROOT"),
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

        # Initialize NL parser
        nl_parser = NLParser(collections_metadata, llm_connector)
        logger.info("NL parser initialized")

        # Initialize translator
        translator = AQLTranslator(collections_metadata)
        logger.info("Translator initialized")

        # Initialize query history
        query_history = QueryHistory(db_config)
        logger.info("Query history initialized")

        # Process each category of queries
        results = {}
        for category, queries in TEST_QUERIES.items():
            logger.info(f"Processing {category} queries")
            category_results = []

            for query in queries:
                result = process_query(query, nl_parser, translator, query_history)
                category_results.append(result)

                # Log success or failure
                if result["success"]:
                    logger.info(f"Query '{query}' processed successfully")
                    logger.info(
                        f"Query recorded in history: {result.get('recorded_in_history', False)}",
                    )
                    if result.get("is_text_search", False) and not result.get(
                        "uses_view",
                        True,
                    ):
                        logger.warning(
                            f"Query '{query}' is a text search but does not use a view",
                        )
                else:
                    logger.error(f"Query '{query}' failed: {result.get('error')}")

            results[category] = category_results

        return results

    except Exception as e:
        logger.exception(f"Error initializing components: {e}")
        return {"error": str(e)}


def save_results(results: dict[str, list[dict[str, Any]]], output_file: str) -> None:
    """Save the test results to a file."""
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {output_file}")
    except Exception as e:
        logger.exception(f"Error saving results to {output_file}: {e}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Test the robustness of Indaleko query processing",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="query_test_results.json",
        help="Output file for test results",
    )
    args = parser.parse_args()

    # Run all tests
    logger.info("Starting query robustness tests")
    results = run_all_tests()

    # Save results
    save_results(results, args.output)

    # Print summary
    sum(len(queries) for queries in TEST_QUERIES.values())
    sum(
        sum(1 for result in category if result.get("success", False))
        for category, category_results in results.items()
        if isinstance(category_results, list)
    )

    sum(
        sum(1 for result in category if result.get("recorded_in_history", False))
        for category, category_results in results.items()
        if isinstance(category_results, list)
    )



if __name__ == "__main__":
    main()
