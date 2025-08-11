"""
CLI for the Indaleko Assistant using OpenAI's Assistant API.

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
import readline
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


class IndalekoAssistantCLI:
    """CLI for Indaleko Assistant using the OpenAI Assistant API."""

    PROMPT = "Indaleko> "

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
        debug: bool = False,
    ) -> None:
        """
        Initialize the CLI.

        Args:
            api_key (Optional[str]): The OpenAI API key.
            model (str): The model to use.
            debug (bool): Whether to enable debug output.
        """
        # Register tools
        self._register_tools()

        # Initialize the assistant
        self.assistant = IndalekoAssistant(api_key, model)
        self.current_conversation_id = None
        self.debug = debug

        # Enable command history
        readline.parse_and_bind("tab: complete")

        # Create initial conversation
        conversation = self.assistant.create_conversation()
        self.current_conversation_id = conversation.conversation_id

    def _register_tools(self) -> None:
        """Register the required tools."""
        # Manually register our tools
        registry = get_registry()
        registry.register_tool(nl_parser.NLParserTool)
        registry.register_tool(aql_translator.AQLTranslatorTool)
        registry.register_tool(executor.QueryExecutorTool)

    def process_command(self, command: str) -> bool:
        """
        Process a CLI command.

        Args:
            command (str): The command to process.

        Returns:
            bool: True if the CLI should continue, False if it should exit.
        """
        # Handle built-in commands
        command = command.strip()

        if command.lower() in ["exit", "quit", "bye"]:
            return False

        if command.lower() in ["help", "?"]:
            self._print_help()
            return True

        if command.lower() == "tools":
            self._list_tools()
            return True

        if command.lower() == "save":
            self._save_conversation()
            return True

        if command.lower() == "clear" or command.lower() == "new":
            self._new_conversation()
            return True

        # Process as a message
        try:
            # Send the message to the assistant
            response = self.assistant.process_message(
                conversation_id=self.current_conversation_id,
                message_content=command,
            )

            # Display the response
            self._display_response(response)

        except Exception:
            if self.debug:
                import traceback

                traceback.print_exc()

        return True

    def _print_help(self) -> None:
        """Print help information."""

    def _list_tools(self) -> None:
        """List available tools."""
        registry = get_registry()
        for _name, _tool in registry.get_all_tools().items():
            pass

    def _save_conversation(self) -> None:
        """Save the current conversation to a file."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        filename = f"conversation-{timestamp}.json"

        # Create directory if it doesn't exist
        log_dir = os.path.join(os.environ.get("INDALEKO_ROOT"), "logs", "conversations")
        os.makedirs(log_dir, exist_ok=True)

        # Save the conversation
        file_path = os.path.join(log_dir, filename)
        self.assistant.save_conversations(file_path)


    def _new_conversation(self) -> None:
        """Start a new conversation."""
        conversation = self.assistant.create_conversation()
        self.current_conversation_id = conversation.conversation_id

    def _display_response(self, response: dict[str, Any]) -> None:
        """
        Display the assistant's response.

        Args:
            response (Dict[str, Any]): The response data.
        """
        if response.get("action") == "error":
            return


    def run_interactive(self) -> None:
        """Run the CLI in interactive mode."""
        while True:
            try:
                command = input(self.PROMPT)
                if not self.process_command(command):
                    break
            except KeyboardInterrupt:
                break
            except Exception:
                if self.debug:
                    import traceback

                    traceback.print_exc()

    def run_batch(self, batch_file: str) -> None:
        """
        Run the CLI in batch mode.

        Args:
            batch_file (str): The batch file path.
        """
        try:
            with open(batch_file) as f:
                queries = f.readlines()

            for _i, query in enumerate(queries, 1):
                query = query.strip()
                if not query or query.startswith("#"):
                    continue


                # Process the query
                response = self.assistant.process_message(
                    conversation_id=self.current_conversation_id,
                    message_content=query,
                )

                # Display the response
                self._display_response(response)

        except FileNotFoundError:
            pass
        except Exception:
            if self.debug:
                import traceback

                traceback.print_exc()


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Indaleko Assistant CLI with OpenAI Assistant API",
    )
    parser.add_argument("--batch", help="Run in batch mode with the specified file")
    parser.add_argument("--model", default="gpt-4o", help="The model to use")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--save-dir", help="Directory to save conversations to")

    args = parser.parse_args()

    # Configure debug output
    if not args.debug:
        ic.disable()

    # Create CLI
    cli = IndalekoAssistantCLI(model=args.model, debug=args.debug)

    # Run in batch or interactive mode
    if args.batch:
        cli.run_batch(args.batch)
    else:
        cli.run_interactive()



if __name__ == "__main__":
    main()
