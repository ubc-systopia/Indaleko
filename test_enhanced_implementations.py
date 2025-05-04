#!/usr/bin/env python3
"""
Test script for the Enhanced NL Parser and AQL Translator implementations with multiple LLM providers.

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
from query.query_processing.enhanced_nl_parser import EnhancedNLParser
from query.query_processing.query_translator.enhanced_aql_translator import (
    EnhancedAQLTranslator,
)
from query.utils.llm_connector.factory import LLMConnectorFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"enhanced_implementations_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
    ],
)
logger = logging.getLogger(__name__)


def test_enhanced_nl_parser(provider="openai"):
    """Test the Enhanced NL Parser with a specific provider."""
    logger.info(f"Testing Enhanced NL Parser with provider: {provider}")

    try:
        # Set up database config
        config_path = os.path.join(os.environ.get("INDALEKO_ROOT"), "config", "indaleko-db-config.ini")
        db_config = IndalekoDBConfig(config_file=config_path)

        # Initialize collections metadata
        collections_metadata = IndalekoDBCollectionsMetadata(db_config)

        # Create Enhanced NL Parser with the specified provider
        parser = EnhancedNLParser(collections_metadata=collections_metadata, llm_provider=provider)

        # Parse a test query
        query = "Find PDF documents about climate change from last year"
        logger.info(f"Parsing enhanced query: {query}")

        # Use enhanced parsing
        result = parser.parse_enhanced(query)

        # Log results
        logger.info(f"Enhanced NL Parser success with {provider}!")
        logger.info(f"Primary intent: {result.intent.primary_intent}")
        logger.info(f"Entities count: {len(result.entities)}")
        for i, entity in enumerate(result.entities):
            logger.info(f"  Entity {i+1}: {entity.original_text} ({entity.entity_type})")

        logger.info(f"Constraints count: {len(result.constraints)}")
        for i, constraint in enumerate(result.constraints):
            logger.info(f"  Constraint {i+1}: {constraint.field} {constraint.operation} {constraint.value}")

        logger.info(f"Target collections: {result.context.collections}")
        logger.info(f"Suggested facets: {len(result.suggested_facets or [])}")
        logger.info(f"Confidence: {result.confidence}")

        return True, result

    except Exception as e:
        logger.error(f"Error testing Enhanced NL Parser with {provider}: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False, None


def test_enhanced_aql_translator(provider="openai", enhanced_understanding=None):
    """Test the Enhanced AQL Translator with a specific provider."""
    logger.info(f"Testing Enhanced AQL Translator with provider: {provider}")

    try:
        # Set up database config
        config_path = os.path.join(os.environ.get("INDALEKO_ROOT"), "config", "indaleko-db-config.ini")
        db_config = IndalekoDBConfig(config_file=config_path)

        # Initialize collections metadata
        collections_metadata = IndalekoDBCollectionsMetadata(db_config)

        # Create Enhanced AQL Translator with the specified provider
        translator = EnhancedAQLTranslator(collections_metadata=collections_metadata, llm_provider=provider)

        # If no enhanced understanding is provided, create one by running the parser
        if enhanced_understanding is None:
            success, enhanced_understanding = test_enhanced_nl_parser(provider)
            if not success or enhanced_understanding is None:
                logger.error("Failed to create enhanced understanding for translator test")
                return False

        # Create LLM connector for input
        connector = LLMConnectorFactory.create_connector(connector_type=provider)

        # Create translator input
        translator_input = TranslatorInput(Query=enhanced_understanding.original_query, Connector=connector)

        # Translate the query
        logger.info(f"Translating enhanced query with {provider}...")
        result = translator.translate_enhanced(enhanced_understanding, translator_input)

        # Log results
        logger.info(f"Enhanced AQL Translator success with {provider}!")
        logger.info(f"Generated AQL query: {result.aql_query}")
        logger.info(f"Explanation: {result.explanation}")
        logger.info(f"Confidence: {result.confidence}")
        logger.info(f"Bind variables: {result.bind_vars}")

        return True

    except Exception as e:
        logger.error(f"Error testing Enhanced AQL Translator with {provider}: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


def run_tests_with_provider(provider):
    """Run all enhanced implementation tests with a specific provider."""
    logger.info(f"=== Running enhanced implementation tests with provider: {provider} ===")

    # Test Enhanced NL Parser
    parser_success, enhanced_understanding = test_enhanced_nl_parser(provider)

    # Test Enhanced AQL Translator
    translator_success = False
    if parser_success and enhanced_understanding:
        translator_success = test_enhanced_aql_translator(provider, enhanced_understanding)
    else:
        logger.error(f"Skipping Enhanced AQL Translator test with {provider} due to parser failure")

    # Log results
    logger.info(f"\n=== Enhanced Implementation Test Results for {provider} ===")
    logger.info(f"Enhanced NL Parser: {'✅ Success' if parser_success else '❌ Failed'}")
    logger.info(f"Enhanced AQL Translator: {'✅ Success' if translator_success else '❌ Failed'}")

    return {"enhanced_nl_parser": parser_success, "enhanced_aql_translator": translator_success}


def run_tests_with_all_providers():
    """Run enhanced implementation tests with all available providers."""
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
    logger.info("\n=== Consolidated Enhanced Implementation Test Results ===")
    logger.info(f"{'Test/Provider':<25} | {' | '.join(f'{p:<10}' for p in test_providers)}")
    logger.info(f"{'-'*25}-+-{'-+-'.join(['-'*10 for _ in test_providers])}")

    test_names = ["enhanced_nl_parser", "enhanced_aql_translator"]
    for test_name in test_names:
        row = f"{test_name:<25} | "
        row += " | ".join(f"{'✅' if all_results[p][test_name] else '❌':<10}" for p in test_providers)
        logger.info(row)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test enhanced implementations with multiple LLM providers")
    parser.add_argument("--provider", type=str, help="Test with a specific provider (e.g., openai, anthropic, gemma)")
    parser.add_argument(
        "--test",
        type=str,
        choices=["nl_parser", "aql_translator", "all"],
        default="all",
        help="Run a specific test",
    )

    args = parser.parse_args()

    if args.provider:
        # Run with specific provider
        if args.test == "nl_parser":
            test_enhanced_nl_parser(args.provider)
        elif args.test == "aql_translator":
            success, enhanced_understanding = test_enhanced_nl_parser(args.provider)
            if success:
                test_enhanced_aql_translator(args.provider, enhanced_understanding)
        else:
            run_tests_with_provider(args.provider)
    else:
        # Run with all providers
        run_tests_with_all_providers()
