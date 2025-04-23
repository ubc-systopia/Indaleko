"""
Test script for the Indaleko Assistant.

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
import os
import sys
from datetime import UTC, datetime
from typing import Any

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from query.assistants.assistant import IndalekoAssistant
from query.tools.database import executor
from query.tools.registry import get_registry
from query.tools.translation import aql_translator, nl_parser


def register_tools():
    """Register the required tools."""
    registry = get_registry()
    registry.register_tool(nl_parser.NLParserTool)
    registry.register_tool(aql_translator.AQLTranslatorTool)
    registry.register_tool(executor.QueryExecutorTool)


def test_initialization():
    """Test assistant initialization."""
    print("Testing assistant initialization...")
    assistant = IndalekoAssistant()
    assert assistant.assistant_id is not None, "Assistant ID should not be None"
    print(f"Assistant initialized with ID: {assistant.assistant_id}")
    return assistant


def test_conversation_creation(assistant: IndalekoAssistant):
    """Test conversation creation."""
    print("\nTesting conversation creation...")
    conversation = assistant.create_conversation()
    assert (
        conversation.conversation_id is not None
    ), "Conversation ID should not be None"
    assert (
        "thread_id" in conversation.execution_context
    ), "Thread ID should be in execution context"
    print(f"Conversation created with ID: {conversation.conversation_id}")
    print(f"Thread ID: {conversation.execution_context['thread_id']}")
    return conversation.conversation_id


def test_basic_message(assistant: IndalekoAssistant, conversation_id: str):
    """Test sending a basic message."""
    print("\nTesting basic message...")
    response = assistant.process_message(
        conversation_id=conversation_id,
        message_content="Hello, how can Indaleko help me today?",
    )
    assert response["action"] == "text", "Response action should be 'text'"
    assert "response" in response, "Response should contain a response field"
    print(f"Response: {response['response']}")
    return response


def test_tool_use(assistant: IndalekoAssistant, conversation_id: str, query: str):
    """Test sending a message that requires tool use."""
    print(f"\nTesting tool use with query: {query}")
    response = assistant.process_message(
        conversation_id=conversation_id, message_content=query,
    )
    assert response["action"] == "text", "Response action should be 'text'"
    assert "response" in response, "Response should contain a response field"
    print(f"Response: {response['response']}")
    return response


def save_results(results: list[dict[str, Any]], output_file: str):
    """Save test results to a file."""
    print(f"\nSaving results to {output_file}...")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("Results saved.")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test the Indaleko Assistant")
    parser.add_argument("--model", default="gpt-4o", help="The model to use")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument(
        "--output", default="test_results.json", help="Output file for results",
    )

    args = parser.parse_args()

    # Configure debug output
    if not args.debug:
        ic.disable()

    # Register tools
    register_tools()

    # Run tests
    results = []

    # Test initialization
    assistant = test_initialization()

    # Test conversation creation
    conversation_id = test_conversation_creation(assistant)

    # Test basic message
    basic_response = test_basic_message(assistant, conversation_id)
    results.append(
        {
            "test": "basic_message",
            "query": "Hello, how can Indaleko help me today?",
            "response": basic_response,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )

    # Test queries that should use tools
    test_queries = [
        "Show me documents with report in the title.",
        "Find files I edited on my phone while traveling last month.",
        "Get documents I exchanged with Dr. Jones regarding the conference paper.",
    ]

    for query in test_queries:
        tool_response = test_tool_use(assistant, conversation_id, query)
        results.append(
            {
                "test": "tool_use",
                "query": query,
                "response": tool_response,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    # Save results
    save_results(results, args.output)


if __name__ == "__main__":
    main()
