"""
Test script for the Request-based Archivist assistant.

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

import colorama

from colorama import Fore, Style


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from archivist.request_assistant import RequestAssistant
from query.tools.database.executor import QueryExecutorTool
from query.tools.registry import get_registry
from query.tools.translation.aql_translator import AQLTranslatorTool
from query.tools.translation.nl_parser import NLParserTool


def run_basic_test(model: str = "gpt-4o", debug: bool = False) -> None:
    """
    Run a basic test of the Request-based assistant.

    Args:
        model (str): The model to use.
        debug (bool): Whether to enable debug mode.
    """
    colorama.init()

    # Initialize the assistant

    # Register tools
    registry = get_registry()
    registry.register_tool(NLParserTool)
    registry.register_tool(AQLTranslatorTool)
    registry.register_tool(QueryExecutorTool)

    time.time()
    assistant = RequestAssistant(model=model)

    # Create a conversation
    conversation = assistant.create_conversation()
    conversation_id = conversation.conversation_id


    # Test queries
    test_queries = [
        "Hello, how can you help me?",
        "What tools can you use?",
        "Show me some documents about Indaleko",
        "Look for files related to archivist memory",
    ]

    for query in test_queries:

        time.time()
        assistant.process_message(
            conversation_id=conversation_id,
            message_content=query,
        )
        time.time()


        if debug:
            pass

    # Generate and print a forward prompt
    assistant.get_forward_prompt()


def run_conversation_test(model: str = "gpt-4o", interactive: bool = False) -> None:
    """
    Run a test demonstrating a conversation with the Request-based assistant.

    Args:
        model (str): The model to use.
        interactive (bool): Whether to run in interactive mode.
    """
    colorama.init()

    # Initialize the assistant
    assistant = RequestAssistant(model=model)

    # Create a conversation
    conversation = assistant.create_conversation()
    conversation_id = conversation.conversation_id


    # Predefined conversation for non-interactive mode
    test_conversation = [
        "Hi, I'm looking for documents I saved at home last week.",
        "I think they were PDF files related to my taxes.",
        "Can you also check if I have any spreadsheets with budget information?",
        "Thanks for your help!",
    ]

    if interactive:
        # Interactive mode

        while True:
            user_input = input(f"\n{Fore.BLUE}User: {Style.RESET_ALL}")
            if not user_input.strip():
                break

            assistant.process_message(
                conversation_id=conversation_id,
                message_content=user_input,
            )

    else:
        # Run through predefined conversation
        for message in test_conversation:

            assistant.process_message(
                conversation_id=conversation_id,
                message_content=message,
            )


    # Save conversation to a file
    os.makedirs("conversations", exist_ok=True)
    filepath = os.path.join(
        "conversations",
        f"test_conversation_{int(time.time())}.json",
    )
    assistant.save_conversations(filepath)

    # Show memory insights gained from the conversation
    insights = assistant.archivist_memory.memory.insights
    for _insight in insights:
        pass

    # Show content preferences
    preferences = assistant.archivist_memory.memory.content_preferences
    for _content_type, _preference in sorted(
        preferences.items(),
        key=lambda x: x[1],
        reverse=True,
    ):
        pass


def run_tool_usage_test(model: str = "gpt-4o") -> None:
    """
    Test the assistant's ability to use tools through the Request API.

    Args:
        model (str): The model to use.
    """
    colorama.init()

    # Register tools
    registry = get_registry()
    registry.register_tool(NLParserTool)
    registry.register_tool(AQLTranslatorTool)
    registry.register_tool(QueryExecutorTool)

    # Initialize the assistant
    assistant = RequestAssistant(model=model)

    # Create a conversation
    conversation = assistant.create_conversation()
    conversation_id = conversation.conversation_id


    # Test tool-intensive query
    query = "Find all PDF documents modified in the last month and explain the query plan."


    time.time()
    assistant.process_message(
        conversation_id=conversation_id,
        message_content=query,
    )
    time.time()



def run_context_management_test(model: str = "gpt-4o") -> None:
    """
    Test the context management features to handle token limitations.

    Args:
        model (str): The model to use.
    """
    colorama.init()

    # Register tools needed for testing
    registry = get_registry()
    registry.register_tool(NLParserTool)
    registry.register_tool(AQLTranslatorTool)
    registry.register_tool(QueryExecutorTool)

    # Initialize the assistant
    assistant = RequestAssistant(model=model)

    # Create a conversation
    conversation = assistant.create_conversation()
    conversation_id = conversation.conversation_id


    # Test schema summarization

    # Get a complex schema to summarize
    complex_schema = {
        "type": "object",
        "title": "Test Schema",
        "description": "A complex schema for testing summarization",
        "properties": {
            "id": {"type": "string", "description": "Unique identifier"},
            "name": {"type": "string", "description": "Name of the item"},
            "details": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "created_at": {"type": "string", "format": "date-time"},
                            "updated_at": {"type": "string", "format": "date-time"},
                            "version": {"type": "integer"},
                            "status": {
                                "type": "string",
                                "enum": ["draft", "published", "archived"],
                            },
                        },
                    },
                },
            },
            "relationships": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "target_id": {"type": "string"},
                        "properties": {"type": "object"},
                    },
                },
            },
        },
    }

    # Generate a nested schema with many repeated elements to simulate a large schema
    for i in range(20):
        complex_schema["properties"][f"field_{i}"] = {
            "type": "object",
            "description": f"Nested field {i}",
            "properties": {
                "subfield_1": {"type": "string"},
                "subfield_2": {"type": "number"},
                "subfield_3": {"type": "boolean"},
            },
        }

    # Summarize the schema
    assistant._summarize_schema(complex_schema, max_tokens=500)


    # Test context refreshing

    # Send a few messages to build up context (using simple messages that don't trigger tools)
    test_messages = [
        "Hello, what is Indaleko?",
        "What features does it have?",
        "Tell me about the architecture of Indaleko.",
        "What is the purpose of the Archivist component?",
    ]

    for message in test_messages:

        response = assistant.process_message(
            conversation_id=conversation_id,
            message_content=message,
        )

        # Show partial response to save space
        response_text = response.get("response", "No response")
        if len(response_text) > 100:
            pass
        else:
            pass

    # Refresh the context

    assistant.refresh_context(conversation_id)


    # Test a message after refresh
    final_message = "Thanks for all that information. Can you summarize what we discussed?"

    response = assistant.process_message(
        conversation_id=conversation_id,
        message_content=final_message,
    )

    # Show response
    response_text = response.get("response", "No response")


def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(description="Test the Request-based Archivist")
    parser.add_argument("--model", default="gpt-4o", help="The OpenAI model to use")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode for conversation test",
    )
    parser.add_argument(
        "--test",
        choices=["basic", "conversation", "tools", "context", "all"],
        default="basic",
        help="Test to run (basic, conversation, tools, context, or all)",
    )

    args = parser.parse_args()

    try:
        if args.test in {"basic", "all"}:
            run_basic_test(model=args.model, debug=args.debug)

        if args.test in {"conversation", "all"}:
            run_conversation_test(model=args.model, interactive=args.interactive)

        if args.test in {"tools", "all"}:
            run_tool_usage_test(model=args.model)

        if args.test in {"context", "all"}:
            run_context_management_test(model=args.model)

    except KeyboardInterrupt:
        pass
    except Exception:
        if args.debug:
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
