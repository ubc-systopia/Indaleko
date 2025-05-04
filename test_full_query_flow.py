#!/usr/bin/env python3
"""
Test script for the full query flow with different LLM providers.

This script tests the complete flow from natural language query to AQL execution
using various LLM providers.

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
import logging
import os
import sys
import time
from datetime import datetime

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from db import IndalekoDBConfig
from query.assistants.conversation import ConversationManager
from query.utils.llm_connector.factory import LLMConnectorFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"full_query_flow_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
    ],
)
logger = logging.getLogger(__name__)


def test_query_flow(provider="openai", model=None, query=None, verbose=False):
    """
    Test the full query flow with a specific LLM provider.

    Args:
        provider (str): The LLM provider to use.
        model (str): The model to use (provider-specific).
        query (str): The query to test with (or use default if None).
        verbose (bool): Whether to print verbose information.

    Returns:
        dict: The results of the query execution.
    """
    # Set default model based on provider if not specified
    if model is None:
        if provider == "openai":
            model = "gpt-4o-mini"
        elif provider == "anthropic":
            model = "claude-3-sonnet-20240229"
        elif provider == "gemma":
            model = "gemma"
        else:
            model = "gpt-4o-mini"  # Default fallback

    # Set default query if not specified
    if query is None:
        query = "Find PDF files created last week"

    logger.info(f"Testing full query flow with provider: {provider}, model: {model}")
    logger.info(f"Query: {query}")

    try:
        # Set up database config
        config_dir = os.path.join(os.environ.get("INDALEKO_ROOT"), "config")
        config_path = os.path.join(config_dir, "indaleko-db-config.ini")
        db_config = IndalekoDBConfig(config_file=config_path)

        # Initialize conversation manager with the specified provider
        start_time = time.time()
        conversation_manager = ConversationManager(model=model, llm_provider=provider, db_config=db_config)
        init_time = time.time() - start_time
        logger.info(f"Conversation manager initialized in {init_time:.2f}s")

        # Create a conversation
        conversation = conversation_manager.create_conversation()
        conversation_id = conversation.conversation_id
        logger.info(f"Created conversation with ID: {conversation_id}")

        # Step 1: Parse the natural language query
        logger.info("Step 1: Parsing natural language query")
        start_time = time.time()
        nl_parser_result = conversation_manager.execute_tool(
            conversation_id=conversation_id,
            tool_name="nl_parser",
            parameters={"query": query},
        )
        parsing_time = time.time() - start_time

        if not nl_parser_result.success:
            logger.error(f"Parser error: {nl_parser_result.error}")
            return {"error": f"Failed to parse query: {nl_parser_result.error}"}

        # Log the parser result
        parser_output = nl_parser_result.result
        intent = parser_output["intent"]
        entities = parser_output["entities"]

        logger.info(f"Parsing completed in {parsing_time:.2f}s")
        logger.info(f"Detected intent: {intent}")
        logger.info(f"Extracted entities: {len(entities)} entities")
        if verbose:
            for i, entity in enumerate(entities):
                logger.info(f"  Entity {i+1}: {entity['name']} ({entity['type']})")

        # Step 2: Translate to AQL
        logger.info("Step 2: Translating structured query to AQL")
        start_time = time.time()
        structured_query = {
            "original_query": query,
            "intent": intent,
            "entities": entities,
        }

        aql_translator_result = conversation_manager.execute_tool(
            conversation_id=conversation_id,
            tool_name="aql_translator",
            parameters={"structured_query": structured_query},
        )
        translation_time = time.time() - start_time

        if not aql_translator_result.success:
            logger.error(f"Translation error: {aql_translator_result.error}")
            return {"error": f"Failed to translate query: {aql_translator_result.error}"}

        # Log the translator result
        translator_output = aql_translator_result.result
        aql_query = translator_output["aql_query"]
        bind_vars = translator_output["bind_vars"]

        logger.info(f"Translation completed in {translation_time:.2f}s")
        logger.info(f"Generated AQL query: {aql_query}")

        # Step 3: Execute the query
        logger.info("Step 3: Executing AQL query")
        start_time = time.time()
        executor_result = conversation_manager.execute_tool(
            conversation_id=conversation_id,
            tool_name="query_executor",
            parameters={
                "query": aql_query,
                "bind_vars": bind_vars,
                "include_plan": True,
                "collect_performance": True,
            },
        )
        execution_time = time.time() - start_time

        if not executor_result.success:
            logger.error(f"Execution error: {executor_result.error}")
            return {"error": f"Failed to execute query: {executor_result.error}"}

        # Log the execution result
        executor_output = executor_result.result
        result_count = len(executor_output.get("results", []))

        logger.info(f"Execution completed in {execution_time:.2f}s")
        logger.info(f"Found {result_count} results")

        # Calculate total time
        total_time = parsing_time + translation_time + execution_time
        logger.info(f"Total query processing time: {total_time:.2f}s")

        # Return the complete result
        return {
            "provider": provider,
            "model": model,
            "query": query,
            "success": True,
            "parsing_time": parsing_time,
            "translation_time": translation_time,
            "execution_time": execution_time,
            "total_time": total_time,
            "result_count": result_count,
            "aql_query": aql_query,
        }

    except Exception as e:
        logger.error(f"Error in query flow with {provider}: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return {"provider": provider, "model": model, "query": query, "success": False, "error": str(e)}


def run_benchmark(providers=None, queries=None, verbose=False):
    """
    Run a benchmark of multiple providers with various queries.

    Args:
        providers (list): List of providers to test.
        queries (list): List of queries to test.
        verbose (bool): Whether to print verbose information.
    """
    # Get available providers if none specified
    if providers is None:
        providers = LLMConnectorFactory.get_available_connectors()
        # Skip special providers
        providers = [p for p in providers if p not in ["random"]]

    # Default queries if none specified
    if queries is None:
        queries = [
            "Find PDF files created last week",
            "Show me documents with report in the title",
            "Find all images larger than 1MB",
            "Search for documents about machine learning",
            "List Excel files created in the last month",
        ]

    logger.info(f"Running benchmark with providers: {providers}")
    logger.info(f"Testing {len(queries)} queries")

    # Run tests and collect results
    all_results = []
    for provider in providers:
        for query in queries:
            result = test_query_flow(provider=provider, query=query, verbose=verbose)
            all_results.append(result)

    # Generate summary report
    logger.info("\n=== Benchmark Results ===")
    logger.info(f"{'Provider':<10} | {'Query':<30} | {'Success':<7} | {'Time(s)':<10} | {'Results':<10}")
    logger.info(f"{'-'*10}-+-{'-'*30}-+-{'-'*7}-+-{'-'*10}-+-{'-'*10}")

    for result in all_results:
        success = "✅" if result.get("success", False) else "❌"
        time_str = f"{result.get('total_time', 0):.2f}" if "total_time" in result else "N/A"
        result_count = result.get("result_count", "N/A")
        query = result.get("query", "")
        if len(query) > 27:
            query = query[:27] + "..."

        logger.info(
            f"{result.get('provider', 'unknown'):<10} | {query:<30} | {success:<7} | {time_str:<10} | {result_count:<10}",
        )

    # Calculate aggregate statistics
    success_count = sum(1 for r in all_results if r.get("success", False))
    success_rate = success_count / len(all_results) if all_results else 0

    avg_times = {}
    for provider in providers:
        provider_results = [r for r in all_results if r.get("provider") == provider and r.get("success", False)]
        if provider_results:
            avg_time = sum(r.get("total_time", 0) for r in provider_results) / len(provider_results)
            avg_times[provider] = avg_time

    # Print aggregate statistics
    logger.info("\n=== Summary Statistics ===")
    logger.info(f"Total tests: {len(all_results)}")
    logger.info(f"Successful tests: {success_count}")
    logger.info(f"Success rate: {success_rate:.2%}")
    logger.info("\nAverage query times by provider:")
    for provider, avg_time in avg_times.items():
        logger.info(f"{provider:<10}: {avg_time:.2f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test full query flow with multiple LLM providers")
    parser.add_argument("--provider", type=str, help="Test with a specific provider (e.g., openai, anthropic, gemma)")
    parser.add_argument("--model", type=str, help="Specify the model to use")
    parser.add_argument("--query", type=str, help="Specify the query to test")
    parser.add_argument("--benchmark", action="store_true", help="Run a benchmark of all providers")
    parser.add_argument("--verbose", action="store_true", help="Print detailed information")

    args = parser.parse_args()

    if args.benchmark:
        # Run benchmark with all available providers
        run_benchmark(verbose=args.verbose)
    elif args.provider:
        # Test a specific provider
        test_query_flow(provider=args.provider, model=args.model, query=args.query, verbose=args.verbose)
    else:
        # Default to openai
        test_query_flow(query=args.query, verbose=args.verbose)
