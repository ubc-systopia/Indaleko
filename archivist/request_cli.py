"""
Command-line interface for the Indaleko Request-based Assistant.

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
import time

from datetime import datetime

import colorama

from colorama import Fore, Style
from tqdm import tqdm


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from archivist.request_assistant import RequestAssistant
from utils.cli.base import IndalekoBaseCLI


class RequestArchivistCLI(IndalekoBaseCLI):
    """Command-line interface for the Request-based Archivist assistant."""

    def __init__(
        self,
        model: str = "gpt-4o",
        debug: bool = False,
        batch_mode: bool = False,
    ) -> None:
        """
        Initialize the CLI for the Request-based Archivist.

        Args:
            model (str): The model to use for the assistant.
            debug (bool): Whether to enable debug mode.
            batch_mode (bool): Whether to run in batch mode.
        """
        super().__init__()

        # Initialize colorama for colored output
        colorama.init()

        self.model = model
        self.debug = debug
        self.batch_mode = batch_mode
        self.assistant = None
        self.conversation_id = None
        self.conversation_file = None
        self.progress_bar = None

        # Add custom commands
        self.register_command("/help", self.show_help)
        self.register_command("/clear", self.clear_conversation)
        self.register_command("/save", self.save_conversation)
        self.register_command("/load", self.load_conversation)
        self.register_command("/forward", self.show_forward_prompt)
        self.register_command("/dump", self.dump_conversation)
        self.register_command("/debug", self.toggle_debug)
        self.register_command("/refresh", self.refresh_context)
        self.register_command("/entities", self.manage_entities)
        self.register_command("/exit", self.exit_cli)
        self.register_command("/quit", self.exit_cli)
        self.register_command("/memory", self.show_memory_commands)

        # Update help text
        self.help_text = """
Request-based Archivist CLI Commands:
  /help              - Show this help message
  /clear             - Clear the current conversation
  /save [filename]   - Save the conversation to a file
  /load [filename]   - Load a conversation from a file
  /forward           - Show the forward prompt
  /dump              - Dump the conversation state
  /debug             - Toggle debug mode
  /refresh           - Refresh the conversation context (for token limit issues)
  /entities          - List and manage named entities
  /memory            - Show memory commands
  /exit, /quit       - Exit the CLI

To use the CLI, simply type your query and press Enter.
"""

    def update_progress(self, message: str, progress: float) -> None:
        """
        Update the progress bar.

        Args:
            message (str): The progress message.
            progress (float): The progress value (0.0-1.0).
        """
        if self.progress_bar is None:
            self.progress_bar = tqdm(total=100, desc=message, ncols=100)
        else:
            self.progress_bar.set_description_str(message)
            self.progress_bar.update(int(progress * 100) - self.progress_bar.n)

        # If progress is complete, close the progress bar
        if progress >= 1.0:
            self.progress_bar.close()
            self.progress_bar = None

    def initialize(self) -> None:
        """Initialize the CLI and assistant."""
        # Initialize the assistant with progress updates
        self.assistant = RequestAssistant(
            model=self.model,
            progress_callback=self.update_progress if not self.batch_mode else None,
        )

        # Create a new conversation
        conversation = self.assistant.create_conversation()
        self.conversation_id = conversation.conversation_id


    def run_interactive(self) -> None:
        """Run the CLI in interactive mode."""
        self.initialize()

        while True:
            try:
                # Get user input
                user_input = input(f"{Fore.BLUE}> {Style.RESET_ALL}")

                # Handle commands
                if user_input.startswith("/"):
                    command = user_input.split()[0]
                    args = user_input[len(command) :].strip()

                    if command in self.commands:
                        result = self.commands[command](args)
                        if result is False:  # Exit command
                            break
                    else:
                        pass
                else:
                    # Process user message
                    self.process_user_message(user_input)

            except KeyboardInterrupt:
                pass
            except EOFError:
                break

    def run_batch(self, input_file: str) -> None:
        """
        Run the CLI in batch mode.

        Args:
            input_file (str): The file containing queries to process.
        """
        self.initialize()

        try:
            with open(input_file) as f:
                queries = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]


            for _i, query in enumerate(queries):
                self.process_user_message(query)

        except FileNotFoundError:
            pass
        except Exception:
            pass

    def process_user_message(self, message: str) -> None:
        """
        Process a user message.

        Args:
            message (str): The user message.
        """
        if not message.strip():
            return

        try:
            # Process the message
            if not self.batch_mode:
                pass

            time.time()
            self.assistant.process_message(
                conversation_id=self.conversation_id,
                message_content=message,
            )
            time.time()

            # Print the response

            # Print debug info
            if self.debug:
                pass


        except Exception:
            pass

    # Command Handlers

    def show_help(self, args: str) -> None:
        """Show the help text."""

    def clear_conversation(self, args: str) -> None:
        """Clear the current conversation."""
        # Create a new conversation
        conversation = self.assistant.create_conversation()
        self.conversation_id = conversation.conversation_id


    def save_conversation(self, args: str) -> None:
        """
        Save the conversation to a file.

        Args:
            args (str): The filename to save to.
        """
        filename = args or f"conversation_{self.conversation_id}.json"

        try:
            # Create conversations directory if it doesn't exist
            os.makedirs("conversations", exist_ok=True)

            # Save the conversation
            filepath = os.path.join("conversations", filename)
            self.assistant.save_conversations(filepath)
            self.conversation_file = filepath


        except Exception:
            pass

    def load_conversation(self, args: str) -> None:
        """
        Load a conversation from a file.

        Args:
            args (str): The filename to load from.
        """
        if not args:
            return

        try:
            # Check if file exists in conversations directory
            filepath = os.path.join("conversations", args)
            if not os.path.exists(filepath):
                # Check if file exists as specified
                filepath = args
                if not os.path.exists(filepath):
                    return

            # Load the conversation
            self.assistant.load_conversations(filepath)

            # Get the first conversation ID
            self.conversation_id = next(iter(self.assistant.conversations.keys()))
            self.conversation_file = filepath


            # Print the latest messages
            conversation = self.assistant.get_conversation(self.conversation_id)
            if conversation and conversation.messages:
                for _i, _msg in enumerate(conversation.messages[-3:]):
                    pass

        except Exception:
            pass

    def show_forward_prompt(self, args: str) -> None:
        """Show the forward prompt from Archivist memory."""
        self.assistant.get_forward_prompt()


    def dump_conversation(self, args: str) -> None:
        """Dump the conversation state."""
        conversation = self.assistant.get_conversation(self.conversation_id)

        if not conversation:
            return


        if args == "full":
            for _i, _msg in enumerate(conversation.messages):
                pass

    def toggle_debug(self, args: str) -> None:
        """Toggle debug mode."""
        self.debug = not self.debug

    def refresh_context(self, args: str) -> None:
        """
        Refresh the conversation context to manage token limits.
        This creates a new thread with a summary of the current conversation.
        """
        try:

            # Refresh the context
            self.assistant.refresh_context(self.conversation_id)


            if self.debug:
                pass
        except Exception:
            pass

    def exit_cli(self, args: str) -> bool:
        """Exit the CLI."""
        return False  # Signal to exit

    def manage_entities(self, args: str) -> None:
        """
        List and manage named entities recognized by the system.

        Args:
            args (str): Command arguments for entity management.
        """
        if not args:
            return

        # Parse arguments
        parts = args.split(maxsplit=1)
        subcommand = parts[0]
        subargs = parts[1] if len(parts) > 1 else ""

        # Handle different subcommands
        if subcommand == "list":
            # List entities, optionally filtered by type
            entity_type = subargs.strip() if subargs else None
            self._list_entities(entity_type)

        elif subcommand == "add":
            # Add a new entity
            if not subargs:
                return

            # Parse entity information
            parts = subargs.split(":", 2)
            if len(parts) < 2:
                return

            entity_type = parts[0].strip().lower()
            entity_name = parts[1].strip()
            entity_description = parts[2].strip() if len(parts) > 2 else f"User-added {entity_type}"

            # Validate entity type
            valid_types = [
                "person",
                "location",
                "organization",
                "device",
                "event",
                "document",
            ]
            if entity_type not in valid_types:
                return

            # Create and store the entity
            self._add_entity(entity_type, entity_name, entity_description)

        elif subcommand == "delete":
            # Delete an entity by ID
            if not subargs:
                return

            entity_id = subargs.strip()
            self._delete_entity(entity_id)

        elif subcommand == "search":
            # Search for entities by name
            if not subargs:
                return

            search_term = subargs.strip()
            self._search_entities(search_term)

        elif subcommand == "types":
            # Show available entity types
            pass

        else:
            pass

    def _list_entities(self, entity_type: str | None = None) -> None:
        """
        List named entities, optionally filtered by type.

        Args:
            entity_type (Optional[str]): Filter entities by this type.
        """
        try:
            # Construct AQL query
            if entity_type:
                aql_query = """
                FOR e IN NamedEntities
                FILTER e.entity_type == @type
                SORT e.name ASC
                RETURN e
                """
                bind_vars = {"type": entity_type}
            else:
                aql_query = """
                FOR e IN NamedEntities
                SORT e.entity_type, e.name
                RETURN e
                """
                bind_vars = {}

            # Execute the query
            cursor = self.assistant.db_config._arangodb.aql.execute(
                aql_query,
                bind_vars=bind_vars,
            )
            entities = list(cursor)

            if not entities:
                return

            # Group by type if not filtered
            if entity_type:
                for entity in entities:
                    # Extract key if present
                    entity.get("_key") or entity.get("id", "unknown")
                    entity.get("confidence", 1.0)
                    if entity.get("description"):
                        pass
            else:
                # Group by type
                grouped = {}
                for entity in entities:
                    etype = entity.get("entity_type", "unknown")
                    if etype not in grouped:
                        grouped[etype] = []
                    grouped[etype].append(entity)

                # Print groups
                for etype, ents in grouped.items():
                    for entity in ents[:5]:  # Show first 5 per type
                        entity.get("_key") or entity.get("id", "unknown")
                        entity.get("confidence", 1.0)

                    if len(ents) > 5:
                        pass

        except Exception:
            pass

    def _add_entity(self, entity_type: str, name: str, description: str) -> None:
        """
        Add a new named entity to the database.

        Args:
            entity_type (str): The type of entity.
            name (str): The entity name.
            description (str): A description of the entity.
        """
        try:
            # Import needed data models
            from data_models.named_entity import IndalekoNamedEntityDataModel
            from data_models.record import IndalekoRecordDataModel
            from data_models.source_identifier import IndalekoSourceIdentifierDataModel

            # Create entity model
            entity_model = IndalekoNamedEntityDataModel(
                Record=IndalekoRecordDataModel(
                    SourceIdentifier=IndalekoSourceIdentifierDataModel(
                        Identifier=str(uuid.uuid4()),
                        Version="1.0",
                        Description="User-added Named Entity",
                    ),
                    Timestamp=datetime.now(timezone.utc),
                ),
                name=name,
                entity_type=entity_type,
                description=description,
                confidence=1.0,  # User-added entities have full confidence
                tags=[entity_type, "user_added"],
            )

            # Check if entity already exists
            aql_query = """
            FOR e IN NamedEntities
            FILTER LOWER(e.name) == LOWER(@name) AND e.entity_type == @type
            LIMIT 1
            RETURN e
            """

            cursor = self.assistant.db_config._arangodb.aql.execute(
                aql_query,
                bind_vars={"name": name, "type": entity_type},
            )

            existing = list(cursor)
            if existing:
                return

            # Save to database
            collection = self.assistant.db_config._arangodb.collection("NamedEntities")
            doc = json.loads(entity_model.model_dump_json())
            collection.insert(doc)


        except Exception:
            pass

    def _delete_entity(self, entity_id: str) -> None:
        """
        Delete a named entity by ID.

        Args:
            entity_id (str): The entity ID.
        """
        try:
            # Check if entity exists
            collection = self.assistant.db_config._arangodb.collection("NamedEntities")
            try:
                entity = collection.get(entity_id)
                if not entity:
                    return

                # Confirm deletion
                entity.get("name", "Unknown")
                entity.get("entity_type", "unknown")

                # Delete entity
                collection.delete(entity_id)

            except Exception:
                pass

        except Exception:
            pass

    def _search_entities(self, search_term: str) -> None:
        """
        Search for entities by name.

        Args:
            search_term (str): The search term.
        """
        try:
            # Construct AQL query
            aql_query = """
            FOR e IN NamedEntities
            FILTER CONTAINS(LOWER(e.name), LOWER(@term))
            SORT e.entity_type, e.name
            RETURN e
            """

            # Execute the query
            cursor = self.assistant.db_config._arangodb.aql.execute(
                aql_query,
                bind_vars={"term": search_term},
            )

            entities = list(cursor)

            if not entities:
                return

            # Show results

            current_type = None
            for entity in entities:
                etype = entity.get("entity_type", "unknown")

                # Print type header when changing types
                if etype != current_type:
                    current_type = etype

                # Print entity
                entity.get("_key") or entity.get("id", "unknown")
                entity.get("confidence", 1.0)
                if entity.get("description"):
                    pass

        except Exception:
            pass

    def show_memory_commands(self, args: str) -> None:
        """Show memory-related commands."""
        # Handle memory subcommands
        if args:
            parts = args.split(maxsplit=1)
            subcommand = parts[0]
            subargs = parts[1] if len(parts) > 1 else ""

            if subcommand == "save":
                self.assistant.archivist_memory.save_memory()

            elif subcommand == "goals":
                goals = self.assistant.archivist_memory.memory.long_term_goals
                if not goals:
                    pass
                else:
                    for _i, _goal in enumerate(goals):
                        pass

            elif subcommand == "add-goal":
                if not subargs:
                    return

                if ":" not in subargs:
                    return

                name, description = subargs.split(":", 1)
                self.assistant.archivist_memory.add_long_term_goal(
                    name.strip(),
                    description.strip(),
                )
                self.assistant.archivist_memory.save_memory()

            elif subcommand == "insights":
                insights = self.assistant.archivist_memory.memory.insights
                if not insights:
                    pass
                else:
                    for _i, _insight in enumerate(insights):
                        pass

            elif subcommand == "strategies":
                strategies = self.assistant.archivist_memory.memory.effective_strategies
                if not strategies:
                    pass
                else:
                    for _i, _strategy in enumerate(strategies):
                        pass

            elif subcommand == "topics":
                topics = self.assistant.archivist_memory.memory.semantic_topics
                if not topics:
                    pass
                else:
                    for _topic, _importance in sorted(
                        topics.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    ):
                        pass

            else:
                pass


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Request-based Archivist CLI")
    parser.add_argument("--model", default="gpt-4o", help="The OpenAI model to use")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument(
        "--batch",
        help="Run in batch mode with the specified input file",
    )

    args = parser.parse_args()

    # Create and run the CLI
    cli = RequestArchivistCLI(
        model=args.model,
        debug=args.debug,
        batch_mode=bool(args.batch),
    )

    if args.batch:
        # Run in batch mode
        cli.run_batch(args.batch)
    else:
        # Run in interactive mode
        cli.run_interactive()


if __name__ == "__main__":
    main()
