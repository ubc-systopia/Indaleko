"""
Test all available LLM providers in Indaleko.

This script will attempt to use each configured LLM provider to generate
a simple response, allowing you to verify that all providers are working correctly.

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
import os
import sys
import time

# Set up Indaleko environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from query.utils.llm_connector.factory import LLMConnectorFactory


def test_provider(provider_name):
    """
    Test a specific LLM provider.

    Args:
        provider_name (str): The name of the provider to test

    Returns:
        bool: True if the test was successful, False otherwise
    """
    print(f"\n=== Testing {provider_name.upper()} Provider ===")

    try:
        # Create connector
        connector = LLMConnectorFactory.create_connector(connector_type=provider_name)

        # Test basic functionality
        print(f"Using model: {connector.model}")

        # Simple text generation
        start_time = time.time()
        response = connector.generate_text(
            "What are the three most important principles in software engineering?",
            max_tokens=200,
        )
        elapsed_time = time.time() - start_time

        print(f"Response received in {elapsed_time:.2f} seconds")
        print(f"Response:\n{response}\n")

        # Test keyword extraction
        start_time = time.time()
        keywords = connector.extract_keywords(
            "Autonomous vehicles use machine learning algorithms to navigate complex traffic scenarios.",
            num_keywords=3,
        )
        elapsed_time = time.time() - start_time

        print(f"Keywords received in {elapsed_time:.2f} seconds")
        print(f"Keywords: {', '.join(keywords)}\n")

        return True
    except Exception as e:
        print(f"Error testing {provider_name}: {e}")
        return False


def main():
    """Main function to run the tests."""
    parser = argparse.ArgumentParser(description="Test all available LLM providers")

    parser.add_argument("--provider", type=str, help="Test only this specific provider")

    args = parser.parse_args()

    # Get available connectors
    available_connectors = LLMConnectorFactory.get_available_connectors()

    print("Available LLM providers:")
    for provider in available_connectors:
        print(f"  • {provider}")

    # Track results
    results = {}

    # Test providers
    if args.provider:
        if args.provider not in available_connectors:
            print(f"Error: Provider '{args.provider}' not available.")
            print(f"Available providers: {', '.join(available_connectors)}")
            return 1

        providers_to_test = [args.provider]
    else:
        providers_to_test = available_connectors

    for provider in providers_to_test:
        success = test_provider(provider)
        results[provider] = success

    # Print summary
    print("\n=== Summary ===")
    for provider, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{provider:10s}: {status}")

    # Return 0 if all tests passed, 1 otherwise
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
