"""
Test script for LLM connector integration in Indaleko.

This script verifies that the LLM connector is properly passed through
the various components of the system.

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

import requests
from icecream import ic

# Set up Indaleko environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from query.assistants.conversation import ConversationManager
from query.utils.llm_connector.factory import LLMConnectorFactory


def test_nl_parser_with_connector(llm_connector_type):
    """
    Test the NL parser tool with the specified LLM connector.

    Args:
        llm_connector_type (str): The LLM connector type to use.
    """
    ic(f"Testing NL parser with {llm_connector_type} connector")

    # Set up additional kwargs for specific connectors
    kwargs = {}
    if llm_connector_type == "gemma" and "LM_STUDIO_BASE_URL" in os.environ:
        kwargs["api_base"] = os.environ["LM_STUDIO_BASE_URL"]
        ic(f"Using LM Studio at: {kwargs['api_base']}")

    # Create conversation manager with specified connector
    conversation = ConversationManager(llm_connector=llm_connector_type, **kwargs)
    conv_state = conversation.create_conversation()
    conv_id = conv_state.conversation_id

    # Execute NL parser tool
    start_time = time.time()
    result = conversation.execute_tool(
        conversation_id=conv_id,
        tool_name="nl_parser",
        parameters={"query": "Find documents related to machine learning", "llm_provider": llm_connector_type},
    )
    elapsed_time = time.time() - start_time

    # Verify result
    ic(f"NL parser execution time: {elapsed_time:.2f} seconds")
    ic(f"NL parser success: {result.success}")

    if result.success:
        ic(f"Detected intent: {result.result['intent']}")
        ic(f"Extracted entities: {result.result['entities']}")
        ic(f"Relevant categories: {result.result['categories']}")
    else:
        ic(f"Error: {result.error}")

    # Verify that the connector was passed through
    return result.success


def check_lm_studio_availability():
    """Check if LM Studio is available for Gemma testing."""

    # Try both localhost and the IP address
    urls = ["http://localhost:1234/v1/models", "http://192.168.111.139:1234/v1/models"]

    print("Checking LM Studio availability:")
    for url in urls:
        print(f"  Trying {url}...")
        try:
            response = requests.get(url, timeout=5)
            print(f"    Status code: {response.status_code}")
            if response.status_code == 200:
                base_url = url.replace("/models", "")
                print(f"    ✅ Found LM Studio at {base_url}")
                os.environ["LM_STUDIO_BASE_URL"] = base_url
                return True
        except Exception as e:
            print(f"    ❌ Error: {e!s}")
            continue

    print("❌ LM Studio not available. Will disable Gemma connector testing.")
    return False


def main():
    """Main function to run the tests."""
    parser = argparse.ArgumentParser(description="Test LLM connector integration")

    # Get available connectors
    available_connectors = LLMConnectorFactory.get_available_connectors()

    print("Checking available LLM providers:")
    for provider in available_connectors:
        print(f"  ✓ {provider.capitalize()} connector is available")

    # Check LM Studio availability for Gemma
    if "gemma" in available_connectors:
        lm_studio_available = check_lm_studio_availability()
        # Filter out Gemma if LM Studio is not available
        if not lm_studio_available:
            print("⚠️ LM Studio not detected. Gemma connector testing will be disabled.")
            available_connectors.remove("gemma")

    parser.add_argument(
        "--connector",
        type=str,
        default="openai",
        choices=available_connectors,
        help="LLM connector to test with",
    )

    args = parser.parse_args()

    # Display available connectors
    ic(f"Available LLM connectors: {available_connectors}")

    # Test with specified connector
    success = test_nl_parser_with_connector(args.connector)

    if success:
        print(f"✅ Successfully tested the {args.connector} LLM connector")
        return 0
    else:
        print(f"❌ Test failed for the {args.connector} LLM connector")
        return 1


if __name__ == "__main__":
    sys.exit(main())
