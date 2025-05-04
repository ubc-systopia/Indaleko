#!/usr/bin/env python3
"""
Test script for the NL Parser implementation with multiple LLM providers.

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

import logging
import os
import sys

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from db import IndalekoDBConfig
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from query.query_processing.nl_parser import NLParser
from query.utils.llm_connector.factory import LLMConnectorFactory

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_nl_parser_with_provider(provider="openai"):
    """
    Test the NL Parser implementation with a specific LLM provider.

    Args:
        provider (str): The LLM provider to use (openai, anthropic, gemma, etc.)
    """
    logger.info(f"Testing NL Parser with provider: {provider}")

    # Set up database config
    config_path = os.path.join(os.environ.get("INDALEKO_ROOT"), "config", "indaleko-db-config.ini")
    db_config = IndalekoDBConfig(config_file=config_path)

    # Initialize collections metadata
    collections_metadata = IndalekoDBCollectionsMetadata(db_config)

    try:
        # Initialize parser with specified provider
        parser = NLParser(collections_metadata=collections_metadata, llm_provider=provider)

        # Test parsing with a simple query
        query = "Find PDF files created last week"
        logger.info(f"Parsing query: {query}")

        result = parser.parse(query)

        # Log the results
        logger.info(f"Intent: {result.Intent.intent}")
        logger.info(f"Entity count: {len(result.Entities.entities)}")
        for i, entity in enumerate(result.Entities.entities):
            logger.info(f"  Entity {i+1}: {entity.name} (Type: {entity.category})")

        logger.info(f"Category count: {len(result.Categories.category_map)}")
        for i, category in enumerate(result.Categories.category_map):
            logger.info(f"  Category {i+1}: {category.collection} (Confidence: {category.confidence})")

        return True

    except Exception as e:
        logger.error(f"Error testing NL Parser with {provider}: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


def test_with_multiple_providers():
    """Test the NL Parser with multiple LLM providers."""
    # Get available providers from factory
    available_providers = LLMConnectorFactory.get_available_connectors()
    logger.info(f"Available LLM providers: {available_providers}")

    results = {}

    # Test with each provider
    for provider in available_providers:
        # Skip providers that are unlikely to work in typical setups (require special configuration)
        if provider in ["random"]:
            continue

        results[provider] = test_nl_parser_with_provider(provider)

    # Print summary
    logger.info("\n--- Test Results Summary ---")
    for provider, success in results.items():
        logger.info(f"{provider}: {'✅ Success' if success else '❌ Failed'}")


if __name__ == "__main__":
    # Test with a single provider if specified on command line
    if len(sys.argv) > 1:
        provider = sys.argv[1]
        test_nl_parser_with_provider(provider)
    else:
        # Test with multiple providers
        test_with_multiple_providers()
