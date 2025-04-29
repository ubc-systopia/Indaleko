"""
Test script for the Recommendation Integration with Assistant API.

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

from colorama import Fore, Style
from colorama import init as colorama_init

# Set up path for imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from query.assistants.assistant import HAS_RECOMMENDATIONS, IndalekoAssistant
from query.context.recommendations.engine import RecommendationEngine
from query.memory.archivist_memory import ArchivistMemory


def print_colored(text: str, color: str = Fore.WHITE, bold: bool = False) -> None:
    """Print colored text."""
    if bold:
        print(f"{color}{Style.BRIGHT}{text}{Style.RESET_ALL}")
    else:
        print(f"{color}{text}{Style.RESET_ALL}")


def run_test_conversation(assistant: IndalekoAssistant, model: str = "gpt-4o") -> None:
    """
    Run a test conversation with recommendation integration.

    Args:
        assistant: The IndalekoAssistant instance
        model: The model to use
    """
    # Create a conversation
    conversation = assistant.create_conversation()
    conversation_id = conversation.conversation_id

    # Run a series of related queries to generate interesting recommendations
    queries = [
        "Find documents related to Indaleko",
        "Show me PDF files from last week",
        "What files did I create yesterday?",
        "Search for documents I shared with colleagues",
    ]

    print_colored(
        "\nStarting test conversation with recommendation integration...\n",
        Fore.CYAN,
        bold=True,
    )

    for i, query in enumerate(queries, 1):
        print_colored(f"\nQuery {i}: {query}", Fore.YELLOW, bold=True)

        # Process the query
        response = assistant.process_message(conversation_id, query)

        # Display the response
        print_colored("\nAssistant: ", Fore.GREEN)
        print(response["response"])

        # Display recommendations if available
        conv = assistant.get_conversation(conversation_id)
        recommendations = conv.get_context_variable("recommendations")

        if recommendations:
            print_colored("\nRecommendations: ", Fore.MAGENTA, bold=True)
            for j, rec in enumerate(recommendations, 1):
                print_colored(f"  {j}. {rec['query']}", Fore.MAGENTA)
                print_colored(f"     {rec['description']}", Fore.WHITE)
                print_colored(
                    f"     Source: {rec['source']}, Confidence: {rec['confidence']:.2f}",
                    Fore.CYAN,
                )
        else:
            print_colored("\nNo recommendations available.", Fore.MAGENTA)

    # Test using the recommendation tool directly
    print_colored("\nTesting recommendation tool directly...", Fore.YELLOW, bold=True)

    direct_query = "What are the most important files in my system?"
    print_colored(f"\nQuery: {direct_query}", Fore.YELLOW)

    # Process the query
    response = assistant.process_message(conversation_id, direct_query)

    # Display the response
    print_colored("\nAssistant: ", Fore.GREEN)
    print(response["response"])

    # Save the conversation for reference
    file_path = os.path.join(
        os.environ.get("INDALEKO_ROOT"),
        "conversation_with_recommendations.json",
    )
    assistant.save_conversations(file_path)
    print_colored(f"\nConversation saved to {file_path}", Fore.CYAN)


def main():
    """Run the test script."""
    colorama_init()

    parser = argparse.ArgumentParser(
        description="Test Recommendation Integration with Assistant API",
    )
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    # Check if recommendation integration is available
    if not HAS_RECOMMENDATIONS:
        print_colored(
            "Recommendation Integration is not available. Please check your installation.",
            Fore.RED,
            bold=True,
        )
        return

    print_colored(
        "Testing Recommendation Integration with Assistant API",
        Fore.CYAN,
        bold=True,
    )
    print_colored("=" * 60, Fore.CYAN)

    # Initialize recommendation engine
    print_colored("Initializing recommendation engine...", Fore.GREEN)
    recommendation_engine = RecommendationEngine(debug=args.debug)

    # Initialize Archivist memory for integration
    print_colored("Initializing Archivist memory...", Fore.GREEN)
    archivist_memory = ArchivistMemory()

    # Add some test data to memory
    archivist_memory.add_long_term_goal(
        "Knowledge Management",
        "Organize personal knowledge base",
        progress=0.4,
    )
    archivist_memory.add_insight(
        "document_management",
        "User frequently searches for recent documents",
        0.8,
    )
    archivist_memory.add_insight(
        "file_types",
        "PDF and DOCX are the most common file types",
        0.9,
    )

    # Initialize Assistant with recommendation integration
    print_colored(f"Initializing Assistant with model {args.model}...", Fore.GREEN)

    # Create assistant with recommendations enabled
    assistant = IndalekoAssistant(
        model=args.model,
        enable_query_context=True,
        enable_recommendations=True,
        archivist_memory=archivist_memory,
        recommendation_engine=recommendation_engine,
        debug=args.debug,
    )

    # Run test conversation
    run_test_conversation(assistant, args.model)

    print_colored("\nTest completed successfully!", Fore.CYAN, bold=True)


if __name__ == "__main__":
    main()
