"""
CLI for Indaleko assistant.

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
import configparser
import json
import os
import readline
import sys
import time

from pathlib import Path
from typing import Any

from arango.cursor import Cursor
from icecream import ic


# Global verbose mode flag
VERBOSE_MODE = False

def verbose_ic(_message: str, *, timestamp: bool = True) -> None:
    """Print a message if verbose mode is enabled.

    Args:
        message (str): The message to print
        timestamp (bool): Whether to include a timestamp
    """
    if VERBOSE_MODE:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        ic(_message, timestamp=timestamp, prefix=f"[{ts}] " if timestamp else "")


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
# ruff: noqa: E402
from db.db_config import IndalekoDBConfig
from query.assistants.conversation import ConversationManager
from query.tools.database import executor
from query.tools.registry import get_registry
from query.tools.translation import aql_translator, nl_parser
from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel


# ruff: qa: E402
# pylint: enable=wrong-import-position



class IndalekoAssistantCLI(IndalekoBaseCLI):
    """CLI for Indaleko assistant."""

    PROMPT = "Indaleko Assistant> "

    def __init__(self) -> None:
        """Initialize the CLI."""
        self.cli_data = IndalekoBaseCliDataModel(
            RegistrationServiceName="Indaleko Assistant CLI",
            FileServiceName="Indaleko Assistant CLI",
        )
        self.features = IndalekoBaseCLI.cli_features(
            machine_config=False,
            input=False,
            output=False,
            offline=False,
            logging=False,
            performance=False,
            platform=False,
        )
        super().__init__(
            cli_data=self.cli_data,
            handler_mixin=IndalekoAssistantCLI.query_cli_handler_mixin,
            features=self.features,
        )
        self.args = self.get_args()

        # Get model and LLM provider from args
        model = self.args.model
        llm_provider = self.args.llm

        config_data = self.get_config_data()
        config_file_path = Path(config_data["ConfigDirectory"]) / config_data["DBConfigFile"]
        self.db_config = IndalekoDBConfig(config_file=str(config_file_path))

        # We'll let the ConversationManager handle API key loading based on the provider
        api_key = None

        # Try to get the list of available providers
        try:
            from query.utils.llm_connector.factory import LLMConnectorFactory
            available_providers = LLMConnectorFactory.get_available_connectors()
            ic(f"Available LLM providers: {available_providers}")

            # Validate the selected provider
            if llm_provider not in available_providers:
                ic(f"Warning: Selected provider '{llm_provider}' not in available providers. Using openai as fallback.")
                llm_provider = "openai"
        except NotImplementedError as e:
            ic(f"Error getting available providers: {e}")

        # Initialize conversation manager with LLM provider
        ic('***Calling ConversationManager***')
        self.conversation_manager = ConversationManager(
            api_key=api_key,  # Let ConversationManager handle API key loading
            model=model,
            llm_provider=llm_provider,
        )

        self.current_conversation = None
        self.registry = get_registry()


        # Set global verbose mode flag
        global VERBOSE_MODE
        VERBOSE_MODE = self.args.verbose if hasattr(self.args, 'verbose') else False

        # Register tools
        self._register_tools()

        # Enable command history
        readline.parse_and_bind("tab: complete")

        # Create initial conversation
        self.current_conversation = self.conversation_manager.create_conversation()

    class QueryAssistantMixin(IndalekoBaseCLI.default_handler_mixin):
        """Mixin for query assistant."""

        @staticmethod
        def get_pre_parser() -> argparse.ArgumentParser | None:
            """"Build base parser."""
            parser = argparse.ArgumentParser(description="Indaleko Assistant CLI", add_help=False)
            parser.add_argument("--model", default="gpt-4o-mini", help="The model to use")
            parser.add_argument("--llm", default="openai",
                              help="The LLM provider to use (e.g., openai, anthropic, gemma, deepseek, grok)")
            parser.add_argument("--debug", action="store_true", help="Enable debug output")
            parser.add_argument("--verbose", action="store_true",
                                help="Show detailed progress information")
            parser.add_argument("--output", help="Output file to write results (in batch mode)")
            parser.add_argument("--summarize", action="store_true",
                                help="Show summary of execution results (in batch mode)")
            # now let's check and see if a file name has been provided
            args = parser.parse_known_args()
            ic(args)
            if (len(args[1]) == 1 and
                Path(args[1][0]).exists() and
                Path(args[1][0]).is_file()):
                # If only one argument is passed and it is a file
                # if it is, this is a batch request.
                parser.add_argument(
                    "input_file",
                    nargs=1,
                    type=Path,
                    default=Path(args[1][0]),
                    help="Input file containing queries to process (one per line)."
                    " Runs in batch mode.",
                )
            else:
                # Add interactive only options
                parser.add_argument(
                    "--interactive",
                    action="store_true",
                    help="Enable interactive facet refinement mode",
                )
            return parser

    query_cli_handler_mixin = QueryAssistantMixin

    def _get_api_key(self, api_key_file: str | None = None, provider: str = "openai") -> str:
        """
        Get the API key for the specified provider from config.

        Args:
            api_key_file (Optional[str]): Path to the API key file. If None, uses default location.
            provider (str): The LLM provider to get the key for.

        Returns:
            str: The API key.

        Raises:
            FileNotFoundError: If the API key file is not found.
            ValueError: If the API key is not found in the config file.
        """
        if api_key_file is None:
            # First try the unified llm-keys.ini
            unified_key_file = Path(self.config_data["ConfigDirectory"]) / "llm-keys.ini"
            if unified_key_file.exists() and unified_key_file.is_file():
                api_key_file = unified_key_file
            else:
                # Fall back to legacy openai-key.ini
                api_key_file = Path(self.config_data["ConfigDirectory"]) / "openai-key.ini"

        if not api_key_file.exists():
            raise FileNotFoundError(f"API key file ({api_key_file}) not found")
        if not api_key_file.is_file():
            raise FileNotFoundError(f"API key file ({api_key_file}) is not a file")

        config = configparser.ConfigParser()
        config.read(api_key_file, encoding="utf-8-sig")

        # Try to get key for specified provider
        if api_key_file.name == "llm-keys.ini" and provider in config and "api_key" in config[provider]:
            api_key = config[provider]["api_key"]
        # Fall back to OpenAI for legacy or if provider not found
        elif "openai" in config and "api_key" in config["openai"]:
            api_key = config["openai"]["api_key"]
            ic(f"Key for provider '{provider}' not found, using OpenAI key as fallback")
        else:
            raise ValueError(f"API key for '{provider}' not found in config file")

        # Clean up quotes if present
        if api_key[0] in ['"', "'"] and api_key[-1] in ['"', "'"]:
            api_key = api_key[1:-1]

        return api_key


    def _register_tools(self) -> None:
        """Register the required tools."""
        # Manually register our tools
        # In a full implementation, this would use autodiscovery
        self.registry.register_tool(nl_parser.NLParserTool)
        self.registry.register_tool(aql_translator.AQLTranslatorTool)
        self.registry.register_tool(executor.QueryExecutorTool)

    def _process_query_through_tools(self, query: str) -> dict[str, Any]:
        """
        Process a query through our tool chain.

        Args:
            query (str): The user's query.

        Returns:
            Dict[str, Any]: The results.
        """
        conversation_id = self.current_conversation.conversation_id
        verbose_ic(f"Processing query: '{query}'")
        verbose_ic(f"Conversation ID: {conversation_id}")

        try:
            # Step 1: Parse the natural language query
            verbose_ic("Step 1: Parsing natural language query with nl_parser tool")
            nl_parser_result = self.conversation_manager.execute_tool(
                conversation_id=conversation_id,
                tool_name="nl_parser",
                parameters={"query": query},
            )

            if not nl_parser_result.success:
                verbose_ic(f"Parser error: {nl_parser_result.error}")
                return {"error": f"Failed to parse query: {nl_parser_result.error}"}

            # Extract the parser result
            parser_output = nl_parser_result.result
            intent = parser_output["intent"]
            entities = parser_output["entities"]
            categories = parser_output["categories"]

            verbose_ic(f"Query intent: {intent}")
            verbose_ic(f"Entities: {json.dumps(entities, indent=2)}")
            verbose_ic(f"Categories: {categories}")

            # Step 2: Translate to AQL
            verbose_ic("Step 2: Translating structured query to AQL")
            structured_query = {
                "original_query": query,
                "intent": intent,
                "entities": entities,
            }

            aql_translator_result = self.conversation_manager.execute_tool(
                conversation_id=conversation_id,
                tool_name="aql_translator",
                parameters={"structured_query": structured_query},
            )

            if not aql_translator_result.success:
                verbose_ic(f"Translation error: {aql_translator_result.error}")
                return {
                    "error": f"Failed to translate query: {aql_translator_result.error}",
                }

            # Extract the AQL query
            translator_output = aql_translator_result.result
            aql_query = translator_output["aql_query"]
            bind_vars = translator_output["bind_vars"]

            verbose_ic(f"Generated AQL query: {aql_query}")
            verbose_ic(f"Bind variables: {json.dumps(bind_vars, indent=2)}")

            # Step 3: Execute the query
            verbose_ic("Step 3: Executing AQL query")
            executor_result = self.conversation_manager.execute_tool(
                conversation_id=conversation_id,
                tool_name="query_executor",
                parameters={
                    "query": aql_query,
                    "bind_vars": bind_vars,
                    "include_plan": True,
                    "collect_performance": True,
                },
            )

            if not executor_result.success:
                verbose_ic(f"Execution error: {executor_result.error}")
                return {"error": f"Failed to execute query: {executor_result.error}"}

            # Extract the results
            executor_output = executor_result.result

            # Ensure cursor objects are fully consumed
            # This is a safeguard in case the cursor wasn't already converted by execute_tool
            from arango.cursor import Cursor
            if "results" in executor_output and isinstance(executor_output["results"], Cursor):
                executor_output["results"] = [doc for doc in executor_output["results"]]

            # Also check lists that might contain cursors
            if "results" in executor_output and isinstance(executor_output["results"], list):
                for i, item in enumerate(executor_output["results"]):
                    if isinstance(item, Cursor):
                        executor_output["results"][i] = list(item)

            result_count = len(executor_output.get("results", []))
            verbose_ic(f"Query execution complete. Found {result_count} results.")

            if "performance" in executor_output:
                perf = executor_output["performance"]
                if "execution_time_seconds" in perf:
                    verbose_ic(f"Execution time: {perf['execution_time_seconds']:.3f} seconds")

            # Combine all results
            return {
                "query": query,
                "intent": intent,
                "entities": entities,
                "categories": categories,
                "aql_query": aql_query,
                "bind_vars": bind_vars,
                "results": executor_output.get("results", []),
                "execution_plan": executor_output.get("execution_plan", {}),
                "performance": executor_output.get("performance", {}),
            }
        except (GeneratorExit , RecursionError , MemoryError , NotImplementedError ) as e:
            import traceback
            verbose_ic(f"Error processing query: {str(e)}")
            verbose_ic(traceback.format_exc())
            return {"error": f"Error processing query: {str(e)}"}

    def process_command(self, command: str) -> bool:
        """
        Process a CLI command.

        Args:
            command (str): The command to process.

        Returns:
            bool: True if the command was successful, False if it failed or
                 the CLI should exit (in interactive mode).
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

        # Process as a query
        try:
            # Update conversation state
            self.current_conversation.set_current_query(command)

            # Process through our tool chain
            result = self._process_query_through_tools(command)

            # Display results
            if "error" in result:
                return False
            self._display_results(result)
            return True

        except OSError:
            return False

    def _print_help(self) -> None:
        """Print help information."""

    def _list_tools(self) -> None:
        """List available tools."""
        for _name, _tool in self.registry.get_all_tools().items():
            pass

    def _format_result_item(self, item: dict[str, Any], indent: int = 2) -> str:
        """
        Format a result item for display.

        Args:
            item (Dict[str, Any]): The result item.
            indent (int): The indentation level.

        Returns:
            str: The formatted item.
        """
        indent_str = " " * indent
        result = []

        # Handle different types of results based on what information is available
        if "Record" in item and "Attributes" in item["Record"]:
            attributes = item["Record"]["Attributes"]

            # Try to extract the most relevant information
            path = attributes.get("Path", "Unknown path")
            name = attributes.get(
                "Label",
                (path.split("/")[-1] if "/" in path else path.split("\\")[-1] if "\\" in path else path),
            )
            size = attributes.get("Size", "Unknown size")
            timestamp = attributes.get(
                "Timestamp",
                attributes.get("CreateTime", "Unknown time"),
            )

            result.append(f"{indent_str}Name: {name}")
            result.append(f"{indent_str}Path: {path}")
            result.append(f"{indent_str}Size: {size} bytes")
            result.append(f"{indent_str}Timestamp: {timestamp}")

        elif "name" in item or "Name" in item:
            name = item.get("name", item.get("Name", "Unknown"))
            result.append(f"{indent_str}Name: {name}")

            # Add other fields
            for key, value in item.items():
                if key.lower() not in ["name"]:
                    result.append(f"{indent_str}{key}: {value}")
        else:
            # Generic fallback
            result.append(f"{indent_str}{json.dumps(item, indent=2, default=str)}")

        return "\n".join(result)

    def _display_results(self, results: dict[str, Any]) -> None:
        """
        Display query results.

        Args:
            results (Dict[str, Any]): The query results.
        """
        # Display query and AQL

        # Display entities
        if results["entities"]:
            for _entity in results["entities"]:
                pass

        # Display query results
        result_items = results.get("results", [])
        if result_items:

            # Limit display to 10 items for brevity
            display_limit = min(10, len(result_items))
            for _i, _item in enumerate(result_items[:display_limit], 1):
                pass

            if len(result_items) > display_limit:
                pass
        else:
            pass

        # Display performance metrics if available
        performance = results.get("performance", {})
        if performance:

            # Display CPU usage
            cpu = performance.get("cpu", {})
            if cpu:
                pass

            # Display memory usage
            memory = performance.get("memory", {})
            if memory:
                memory.get("rss", 0) / (1024 * 1024)

    def run(self) -> None:
        """"Run the CLI."""
        if not self.args:
            self.args = self.pre_parser.parse_args()

        batch_file = None
        output_file = None

        try:
            # Check if a positional argument (file path) was provided
            if hasattr(self.args, "input_file") and self.args.input_file:
                if isinstance(self.args.input_file, list):
                    input_file = Path(self.args.input_file[0])
                else:
                    input_file = Path(self.args.input_file)
                batch_file = input_file.open("r", encoding="utf-8")

            # Set up output file if requested
            if batch_file and hasattr(self.args, "output") and self.args.output:
                output_path = Path(self.args.output)
                output_file = output_path.open("w", encoding="utf-8")

                verbose_ic(f"Running in batch mode. Processing queries from {input_file}")
                if output_file:
                    verbose_ic(f"Writing results to {self.args.output}")


            # Process queries one by one
            while True:
                if batch_file:
                    # Read a line
                    query = batch_file.readline().strip()

                    if not query:
                        # done processing the file
                        break
                else:
                    query = input(self.PROMPT).strip()
                    if not query:
                        # empty query, continue to next iteration
                        continue
                    # Handle exit commands in interactive mode
                    if query.lower() in ["exit", "quit", "bye", "leave"]:
                        break

                verbose_ic(f"Processing query: {query}")
                self.process_query(query)

        except (GeneratorExit , RecursionError , MemoryError , NotImplementedError ) as e:
            import traceback
            verbose_ic(f"Error in batch processing: {e!s}")
            verbose_ic(traceback.format_exc())

        finally:
            if batch_file:
                batch_file.close()
            if output_file:
                output_file.close()

    def _make_serializable(self, obj: object) -> object:
        """Convert an object to a JSON-serializable format. Now with 100% more MATCH."""

        match obj:
            case dict():  # Handle dicts
                return {k: self._make_serializable(v) for k, v in obj.items()}
            case list() | Cursor():  # Handle lists AND Arango cursors in one branch
                return [self._make_serializable(item) for item in obj]
            case _ if hasattr(obj, "__dict__"):  # Handle custom objects
                return self._make_serializable(obj.__dict__)
            case _:  # Default fallthrough
                return obj

    def process_query(self, query: str) -> dict[str, Any]:
        """
        Process a query and return the results.

        Args:
            query (str): The query to process.

        Returns:
            dict[str, Any]: The query results or error information.
        """
        verbose_ic(f"Processing query: {query}")

        try:
            # Update conversation state
            self.current_conversation.set_current_query(query)

            # Process through our tool chain
            result = self._process_query_through_tools(query)

            # Display results if no error
            if "error" not in result:
                self._display_results(result)
                return result
            else:
                verbose_ic(f"Error: {result['error']}")
                return result

        except (GeneratorExit , RecursionError , MemoryError , NotImplementedError ) as e:
            import traceback
            error_msg = f"Error processing query: {str(e)}"
            verbose_ic(error_msg)
            verbose_ic(traceback.format_exc())
            return {"error": error_msg, "query": query}


def main() -> None:
    """Main function."""
    # Create and run CLI with specified model and LLM connector
    IndalekoAssistantCLI().run()



if __name__ == "__main__":
    main()
