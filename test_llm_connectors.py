#!/usr/bin/env python3
"""
Test script for LLM connectors with minimal dependencies.

This script tests the basic functionality of various LLM connectors
without requiring a full database setup or additional components.

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
import json
import logging
import os
import sys
from pathlib import Path

# Set up path to include Indaleko modules
current_path = Path(__file__).parent.resolve()
os.environ["INDALEKO_ROOT"] = str(current_path)
sys.path.insert(0, str(current_path))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import LLM connector components
try:
    # New imports
    from query.utils.llm_connector.deepseek_connector import DeepseekConnector
    from query.utils.llm_connector.factory_updated import LLMFactory
    from query.utils.llm_connector.grok_connector import GrokConnector
except ImportError as e:
    logger.error(f"Failed to import LLM connector components: {e}")
    sys.exit(1)


def test_provider(provider_name, args):
    """Test a specific LLM provider."""
    logger.info(f"Testing {provider_name} connector...")

    try:
        # Create the LLM interface
        llm = LLMFactory.get_llm(
            provider=provider_name,
            use_guardian=args.use_guardian,
        )

        logger.info(f"Created {provider_name} interface with model: {llm.model}")

        # Test simple completion
        prompt = "What is the capital of France?"
        logger.info(f"Testing simple completion with prompt: '{prompt}'")

        completion, metadata = llm.get_completion(
            user_prompt=prompt,
            system_prompt="You are a helpful assistant that provides concise responses.",
            temperature=0,
        )

        logger.info(f"Response: {completion}")
        logger.info(f"Metadata: {json.dumps(metadata, indent=2)}")

        return True

    except Exception as e:
        logger.error(f"Error testing {provider_name}: {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test LLM connectors")
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "google", "deepseek", "grok", "gemma", "all"],
        default="all",
        help="LLM provider to test",
    )
    parser.add_argument(
        "--no-guardian",
        dest="use_guardian",
        action="store_false",
        help="Disable LLMGuardian",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    # Set logging level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    # Display available providers
    available_providers = LLMFactory.get_available_connectors()
    logger.info(f"Available providers: {', '.join(available_providers)}")

    # Register new connectors if not already registered
    if "deepseek" not in available_providers:
        LLMFactory.register_connector("deepseek", DeepseekConnector)
        logger.info("Registered Deepseek connector")

    if "grok" not in available_providers:
        LLMFactory.register_connector("grok", GrokConnector)
        logger.info("Registered Grok connector")

    # Test selected provider(s)
    if args.provider == "all":
        providers_to_test = available_providers
    else:
        providers_to_test = [args.provider]

    results = {}
    for provider in providers_to_test:
        results[provider] = test_provider(provider, args)

    # Display summary
    logger.info("\nTest Results:")
    for provider, success in results.items():
        status = "PASSED" if success else "FAILED"
        logger.info(f"{provider}: {status}")

    # Return success if all tests passed
    return all(results.values())


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
