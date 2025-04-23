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
import json
import os
import readline
import sys
from typing import Any

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from query.assistants.conversation import ConversationManager
from query.tools.database import executor
from query.tools.registry import get_registry
from query.tools.translation import aql_translator, nl_parser


class IndalekoAssistantCLI:
    """CLI for Indaleko assistant."""

    PROMPT = "Indaleko> "

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini"):
        """
        Initialize the CLI.

        Args:
            api_key (Optional[str]): The OpenAI API key.
            model (str): The model to use.
        """
        self.conversation_manager = ConversationManager(api_key, model)
        self.current_conversation = None
        self.registry = get_registry()

        # Register tools
        self._register_tools()

        # Enable command history
        readline.parse_and_bind("tab: complete")

        # Create initial conversation
        self.current_conversation = self.conversation_manager.create_conversation()

    def _register_tools(self):
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

        # Step 1: Parse the natural language query
        nl_parser_result = self.conversation_manager.execute_tool(
            conversation_id=conversation_id,
            tool_name="nl_parser",
            parameters={"query": query},
        )

        if not nl_parser_result.success:
            return {"error": f"Failed to parse query: {nl_parser_result.error}"}

        # Extract the parser result
        parser_output = nl_parser_result.result
        intent = parser_output["intent"]
        entities = parser_output["entities"]
        categories = parser_output["categories"]

        # Step 2: Translate to AQL
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
            return {
                "error": f"Failed to translate query: {aql_translator_result.error}",
            }

        # Extract the AQL query
        translator_output = aql_translator_result.result
        aql_query = translator_output["aql_query"]
        bind_vars = translator_output["bind_vars"]

        # Step 3: Execute the query
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
            return {"error": f"Failed to execute query: {executor_result.error}"}

        # Extract the results
        executor_output = executor_result.result

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

        # Process as a query
        try:
            # Update conversation state
            self.current_conversation.set_current_query(command)

            # Process through our tool chain
            result = self._process_query_through_tools(command)

            # Display results
            if "error" in result:
                print(f"Error: {result['error']}")
            else:
                self._display_results(result)

        except Exception as e:
            print(f"Error processing query: {e}")

        return True

    def _print_help(self):
        """Print help information."""
        print("\nIndaleko Assistant CLI Help:")
        print("----------------------------")
        print("  exit, quit, bye - Exit the CLI")
        print("  help, ? - Show this help message")
        print("  tools - List available tools")
        print("\nEnter natural language queries to search your personal data.")
        print("For example: 'Show me documents with report in the title'")

    def _list_tools(self):
        """List available tools."""
        print("\nAvailable Tools:")
        print("-----------------")
        for name, tool in self.registry.get_all_tools().items():
            print(f"  {name} - {tool.definition.description}")

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
                (
                    path.split("/")[-1]
                    if "/" in path
                    else path.split("\\")[-1] if "\\" in path else path
                ),
            )
            size = attributes.get("Size", "Unknown size")
            timestamp = attributes.get(
                "Timestamp", attributes.get("CreateTime", "Unknown time"),
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

    def _display_results(self, results: dict[str, Any]):
        """
        Display query results.

        Args:
            results (Dict[str, Any]): The query results.
        """
        # Display query and AQL
        print("\nQuery: ", results["query"])
        print("Intent:", results["intent"])
        print("AQL:   ", results["aql_query"])

        # Display entities
        if results["entities"]:
            print("\nEntities:")
            for entity in results["entities"]:
                print(f"  {entity['name']} ({entity['type']}): {entity['value']}")

        # Display query results
        result_items = results.get("results", [])
        if result_items:
            print(f"\nResults ({len(result_items)} items):")

            # Limit display to 10 items for brevity
            display_limit = min(10, len(result_items))
            for i, item in enumerate(result_items[:display_limit], 1):
                print(f"\n{i}. {self._format_result_item(item)}")

            if len(result_items) > display_limit:
                print(f"\n... and {len(result_items) - display_limit} more items")
        else:
            print("\nNo results found.")

        # Display performance metrics if available
        performance = results.get("performance", {})
        if performance:
            print("\nPerformance:")
            print(
                f"  Execution time: {performance.get('execution_time_seconds', 'N/A')} seconds",
            )

            # Display CPU usage
            cpu = performance.get("cpu", {})
            if cpu:
                print(
                    f"  CPU: user={cpu.get('user_time', 'N/A')}s, system={cpu.get('system_time', 'N/A')}s",
                )

            # Display memory usage
            memory = performance.get("memory", {})
            if memory:
                rss_mb = memory.get("rss", 0) / (1024 * 1024)
                print(f"  Memory: {rss_mb:.2f} MB")

    def run_interactive(self):
        """Run the CLI in interactive mode."""
        print("Welcome to Indaleko Assistant CLI!")
        print("Type 'help' or '?' for help, 'exit' to quit.")

        while True:
            try:
                command = input(self.PROMPT)
                if not self.process_command(command):
                    break
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")

    def run_batch(self, batch_file: str):
        """
        Run the CLI in batch mode.

        Args:
            batch_file (str): The batch file path.
        """
        print(f"Running batch file: {batch_file}")

        try:
            with open(batch_file) as f:
                queries = f.readlines()

            for i, query in enumerate(queries, 1):
                query = query.strip()
                if not query or query.startswith("#"):
                    continue

                print(f"\n--- Query {i}: {query} ---")
                self.process_command(query)

        except FileNotFoundError:
            print(f"Error: Batch file not found: {batch_file}")
        except Exception as e:
            print(f"Error processing batch file: {e}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Indaleko Assistant CLI")
    parser.add_argument("--batch", help="Run in batch mode with the specified file")
    parser.add_argument("--model", default="gpt-4o-mini", help="The model to use")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")

    args = parser.parse_args()

    # Configure debug output
    if not args.debug:
        ic.disable()

    # Create CLI
    cli = IndalekoAssistantCLI(model=args.model)

    # Run in batch or interactive mode
    if args.batch:
        cli.run_batch(args.batch)
    else:
        cli.run_interactive()

    print("Thank you for using Indaleko Assistant!")


if __name__ == "__main__":
    main()
