#!/usr/bin/env python3
"""
Test script for the AQL Translator Tool with multiple LLM providers.

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

from query.tools.base import ToolInput
from query.tools.translation.aql_translator import AQLTranslatorTool
from query.utils.llm_connector.factory import LLMConnectorFactory

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_aql_translator_tool_with_provider(provider="openai"):
    """
    Test the AQL Translator Tool with a specific LLM provider.

    Args:
        provider (str): The LLM provider to use (openai, anthropic, gemma, etc.)
    """
    logger.info(f"Testing AQL Translator Tool with provider: {provider}")

    # Create LLM connector using factory
    try:
        llm_connector = LLMConnectorFactory.create_connector(connector_type=provider)

        # Create AQL Translator Tool with the connector
        aql_translator_tool = AQLTranslatorTool(llm_connector=llm_connector)

        # Create a sample structured query
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
            parameters={
                "structured_query": structured_query,
            },
            llm_connector=llm_connector,
        )

        # Execute the tool
        logger.info(f"Executing AQL Translator Tool with {provider}...")
        result = aql_translator_tool.execute(tool_input)

        # Check result
        if result.success:
            logger.info(f"AQL Translator Tool success with {provider}!")
            logger.info(f"Generated AQL query: {result.result['aql_query']}")
            logger.info(f"Bind variables: {result.result['bind_vars']}")
            return True
        else:
            logger.error(f"AQL Translator Tool failed with {provider}: {result.error}")
            return False

    except Exception as e:
        logger.error(f"Error testing AQL Translator Tool with {provider}: {e}")
        return False


def test_with_multiple_providers():
    """Test the AQL Translator Tool with multiple LLM providers."""
    # Get available providers from factory
    available_providers = LLMConnectorFactory.get_available_connectors()
    logger.info(f"Available LLM providers: {available_providers}")

    results = {}

    # Test with each provider
    for provider in available_providers:
        # Skip providers that are unlikely to work in typical setups (require special configuration)
        if provider in ["random"]:
            continue

        results[provider] = test_aql_translator_tool_with_provider(provider)

    # Print summary
    logger.info("\n--- Test Results Summary ---")
    for provider, success in results.items():
        logger.info(f"{provider}: {'✅ Success' if success else '❌ Failed'}")


if __name__ == "__main__":
    # Test with a single provider if specified on command line
    if len(sys.argv) > 1:
        provider = sys.argv[1]
        test_aql_translator_tool_with_provider(provider)
    else:
        # Test with multiple providers
        test_with_multiple_providers()
