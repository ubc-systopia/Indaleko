#!/usr/bin/env python3
"""
Integration test for multi-LLM provider support in Indaleko.

This script tests the end-to-end flow with all updated components.

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
from datetime import datetime

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from db import IndalekoDBConfig
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from query.query_processing.data_models.translator_input import TranslatorInput
from query.query_processing.nl_parser import NLParser
from query.query_processing.query_translator.aql_translator import AQLTranslator
from query.tools.base import ToolInput
from query.tools.translation.aql_translator import AQLTranslatorTool
from query.tools.translation.nl_parser import NLParserTool
from query.utils.llm_connector.factory import LLMConnectorFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"llm_integration_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
    ],
)
logger = logging.getLogger(__name__)


def test_llm_factory(provider="openai"):
    """Test the LLM connector factory with the given provider."""
    logger.info(f"Testing LLM connector factory with provider: {provider}")
    try:
        connector = LLMConnectorFactory.create_connector(connector_type=provider)

        # Simple test with the connector
        response = connector.answer_question(
            "What is the capital of France?",
            "I want to know the capital of France.",
            {},
        )

        logger.info(f"Response from {provider}: {response[:100]}...")
        return True
    except Exception as e:
        logger.error(f"Error testing LLM factory with {provider}: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


def test_nl_parser_tool(provider="openai"):
    """Test the NL Parser Tool with the given provider."""
    logger.info(f"Testing NL Parser Tool with provider: {provider}")
    try:
        # Create LLM connector
        connector = LLMConnectorFactory.create_connector(connector_type=provider)

        # Create NL Parser Tool
        nl_parser_tool = NLParserTool(llm_connector=connector)

        # Create tool input
        tool_input = ToolInput(
            tool_name="nl_parser",
            parameters={"query": "Find PDF files created last week"},
            conversation_id="test_conversation",
            invocation_id="test_invocation",
            llm_connector=connector,
        )

        # Execute the tool
        result = nl_parser_tool.execute(tool_input)

        if result.success:
            logger.info(f"NL Parser Tool success with {provider}!")
            logger.info(f"Detected intent: {result.result['intent']}")
            logger.info(f"Extracted entities: {len(result.result['entities'])}")
            return True
        else:
            logger.error(f"NL Parser Tool failed with {provider}: {result.error}")
            return False

    except Exception as e:
        logger.error(f"Error testing NL Parser Tool with {provider}: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


def test_aql_translator_tool(provider="openai"):
    """Test the AQL Translator Tool with the given provider."""
    logger.info(f"Testing AQL Translator Tool with provider: {provider}")
    try:
        # Create LLM connector
        connector = LLMConnectorFactory.create_connector(connector_type=provider)

        # Create AQL Translator Tool
        aql_translator_tool = AQLTranslatorTool(llm_connector=connector)

        # Create a sample structured query for testing
        structured_query = {
            "original_query": "Find PDF files created last week",
            "intent": "search",
            "entities": [
                {"name": "PDF", "type": "file_extension", "value": "pdf"},
                {"name": "last week", "type": "time_range", "value": "last week"},
            ],
        }

        # Create tool input
        tool_input = ToolInput(
            tool_name="aql_translator",
            parameters={"structured_query": structured_query},
            conversation_id="test_conversation",
            invocation_id="test_invocation",
            llm_connector=connector,
        )

        # Execute the tool
        result = aql_translator_tool.execute(tool_input)

        if result.success:
            logger.info(f"AQL Translator Tool success with {provider}!")
            logger.info(f"Generated AQL query: {result.result['aql_query']}")
            return True
        else:
            logger.error(f"AQL Translator Tool failed with {provider}: {result.error}")
            return False

    except Exception as e:
        logger.error(f"Error testing AQL Translator Tool with {provider}: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


def test_nl_parser_implementation(provider="openai"):
    """Test the NL Parser implementation with the given provider."""
    logger.info(f"Testing NL Parser Implementation with provider: {provider}")
    try:
        # Set up database config
        config_path = os.path.join(os.environ.get("INDALEKO_ROOT"), "config", "indaleko-db-config.ini")
        db_config = IndalekoDBConfig(config_file=config_path)

        # Initialize collections metadata
        collections_metadata = IndalekoDBCollectionsMetadata(db_config)

        # Create a parser with the specified provider
        parser = NLParser(collections_metadata=collections_metadata, llm_provider=provider)

        # Parse a test query
        query = "Find PDF files created last week"
        result = parser.parse(query)

        logger.info(f"NL Parser success with {provider}!")
        logger.info(f"Detected intent: {result.Intent.intent}")
        logger.info(f"Extracted entities: {len(result.Entities.entities)}")
        return True

    except Exception as e:
        logger.error(f"Error testing NL Parser implementation with {provider}: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


def test_aql_translator_implementation(provider="openai"):
    """Test the AQL Translator implementation with the given provider."""
    logger.info(f"Testing AQL Translator Implementation with provider: {provider}")
    try:
        # Set up database config
        config_path = os.path.join(os.environ.get("INDALEKO_ROOT"), "config", "indaleko-db-config.ini")
        db_config = IndalekoDBConfig(config_file=config_path)

        # Initialize collections metadata
        collections_metadata = IndalekoDBCollectionsMetadata(db_config)

        # Create a translator with the specified provider
        translator = AQLTranslator(collections_metadata=collections_metadata, llm_provider=provider)

        # Create LLM connector for input
        connector = LLMConnectorFactory.create_connector(connector_type=provider)

        # Create a structured query for testing
        from data_models.named_entity import (
            IndalekoNamedEntityDataModel,
            IndalekoNamedEntityType,
            NamedEntityCollection,
        )
        from query.query_processing.data_models.query_input import StructuredQuery

        # Create entities
        entity1 = IndalekoNamedEntityDataModel(
            name="PDF",
            category=IndalekoNamedEntityType.file_extension,
            description="pdf",
        )
        entity2 = IndalekoNamedEntityDataModel(
            name="last week",
            category=IndalekoNamedEntityType.time_range,
            description="last week",
        )
        entities = NamedEntityCollection(entities=[entity1, entity2])

        # Create structured query
        structured_query = StructuredQuery(
            original_query="Find PDF files created last week",
            intent="search",
            entities=entities,
            db_info=[],
            db_indices={},
        )

        # Create translator input
        translator_input = TranslatorInput(Query=structured_query, Connector=connector)

        # Translate the query
        result = translator.translate(translator_input)

        logger.info(f"AQL Translator success with {provider}!")
        logger.info(f"Generated AQL query: {result.aql_query}")
        return True

    except Exception as e:
        logger.error(f"Error testing AQL Translator implementation with {provider}: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


def run_tests_with_provider(provider):
    """Run all tests with a specific provider."""
    logger.info(f"=== Running all tests with provider: {provider} ===")

    results = {
        "factory": test_llm_factory(provider),
        "nl_parser_tool": test_nl_parser_tool(provider),
        "aql_translator_tool": test_aql_translator_tool(provider),
        "nl_parser_implementation": test_nl_parser_implementation(provider),
        "aql_translator_implementation": test_aql_translator_implementation(provider),
    }

    logger.info(f"\n=== Test Results Summary for {provider} ===")
    for test_name, success in results.items():
        logger.info(f"{test_name}: {'✅ Success' if success else '❌ Failed'}")

    return results


def run_tests_with_all_providers():
    """Run all tests with all available providers."""
    # Get available providers
    available_providers = LLMConnectorFactory.get_available_connectors()
    logger.info(f"Available LLM providers: {available_providers}")

    # Skip providers that require special configuration
    skip_providers = ["random"]
    test_providers = [p for p in available_providers if p not in skip_providers]

    all_results = {}
    for provider in test_providers:
        all_results[provider] = run_tests_with_provider(provider)

    # Print consolidated results
    logger.info("\n=== Consolidated Test Results ===")
    logger.info(f"{'Test/Provider':<25} | {' | '.join(f'{p:<10}' for p in test_providers)}")
    logger.info(f"{'-'*25}-+-{'-+-'.join(['-'*10 for _ in test_providers])}")

    test_names = list(all_results[test_providers[0]].keys())
    for test_name in test_names:
        row = f"{test_name:<25} | "
        row += " | ".join(f"{'✅' if all_results[p][test_name] else '❌':<10}" for p in test_providers)
        logger.info(row)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test LLM integration progress")
    parser.add_argument("--provider", type=str, help="Test with a specific provider (e.g., openai, anthropic, gemma)")
    parser.add_argument(
        "--test",
        type=str,
        choices=[
            "factory",
            "nl_parser_tool",
            "aql_translator_tool",
            "nl_parser_implementation",
            "aql_translator_implementation",
            "all",
        ],
        default="all",
        help="Run a specific test",
    )

    args = parser.parse_args()

    if args.provider:
        # Run with specific provider
        if args.test == "factory":
            test_llm_factory(args.provider)
        elif args.test == "nl_parser_tool":
            test_nl_parser_tool(args.provider)
        elif args.test == "aql_translator_tool":
            test_aql_translator_tool(args.provider)
        elif args.test == "nl_parser_implementation":
            test_nl_parser_implementation(args.provider)
        elif args.test == "aql_translator_implementation":
            test_aql_translator_implementation(args.provider)
        else:
            run_tests_with_provider(args.provider)
    else:
        # Run with all providers
        run_tests_with_all_providers()
