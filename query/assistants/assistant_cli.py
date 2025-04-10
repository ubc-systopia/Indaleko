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

import os
import sys
import argparse
import json
import readline
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from query.assistants.assistant import IndalekoAssistant
from query.tools.registry import get_registry
from query.tools.translation import nl_parser
from query.tools.translation import aql_translator
from query.tools.database import executor


class IndalekoAssistantCLI:
    """CLI for Indaleko Assistant using the OpenAI Assistant API."""
    
    PROMPT = "Indaleko> "
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o", debug: bool = False):
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
        readline.parse_and_bind('tab: complete')
        
        # Create initial conversation
        conversation = self.assistant.create_conversation()
        self.current_conversation_id = conversation.conversation_id
    
    def _register_tools(self):
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
                message_content=command
            )
            
            # Display the response
            self._display_response(response)
            
        except Exception as e:
            print(f"Error processing message: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
        
        return True
    
    def _print_help(self):
        """Print help information."""
        print("\nIndaleko Assistant CLI Help:")
        print("----------------------------")
        print("  exit, quit, bye - Exit the CLI")
        print("  help, ? - Show this help message")
        print("  tools - List available tools")
        print("  save - Save the current conversation")
        print("  new, clear - Start a new conversation")
        print("\nEnter natural language queries to search your personal data.")
        print("For example: 'Show me documents with report in the title'")
    
    def _list_tools(self):
        """List available tools."""
        registry = get_registry()
        print("\nAvailable Tools:")
        print("-----------------")
        for name, tool in registry.get_all_tools().items():
            print(f"  {name} - {tool.definition.description}")
    
    def _save_conversation(self):
        """Save the current conversation to a file."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        filename = f"conversation-{timestamp}.json"
        
        # Create directory if it doesn't exist
        log_dir = os.path.join(os.environ.get("INDALEKO_ROOT"), "logs", "conversations")
        os.makedirs(log_dir, exist_ok=True)
        
        # Save the conversation
        file_path = os.path.join(log_dir, filename)
        self.assistant.save_conversations(file_path)
        
        print(f"Conversation saved to {file_path}")
    
    def _new_conversation(self):
        """Start a new conversation."""
        conversation = self.assistant.create_conversation()
        self.current_conversation_id = conversation.conversation_id
        print("Started a new conversation.")
    
    def _display_response(self, response: Dict[str, Any]):
        """
        Display the assistant's response.
        
        Args:
            response (Dict[str, Any]): The response data.
        """
        if response.get("action") == "error":
            print(f"Error: {response.get('response', 'Unknown error')}")
            return
        
        print(f"\n{response.get('response', 'No response')}")
    
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
                if self.debug:
                    import traceback
                    traceback.print_exc()
    
    def run_batch(self, batch_file: str):
        """
        Run the CLI in batch mode.
        
        Args:
            batch_file (str): The batch file path.
        """
        print(f"Running batch file: {batch_file}")
        
        try:
            with open(batch_file, "r") as f:
                queries = f.readlines()
            
            for i, query in enumerate(queries, 1):
                query = query.strip()
                if not query or query.startswith("#"):
                    continue
                
                print(f"\n--- Query {i}: {query} ---")
                
                # Process the query
                response = self.assistant.process_message(
                    conversation_id=self.current_conversation_id,
                    message_content=query
                )
                
                # Display the response
                self._display_response(response)
                
        except FileNotFoundError:
            print(f"Error: Batch file not found: {batch_file}")
        except Exception as e:
            print(f"Error processing batch file: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Indaleko Assistant CLI with OpenAI Assistant API")
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
    
    print("Thank you for using Indaleko Assistant!")


if __name__ == "__main__":
    main()