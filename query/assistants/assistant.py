"""
OpenAI Assistant API implementation for Indaleko.

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
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone

from icecream import ic
import openai

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from query.assistants.state import ConversationState, Message
from query.tools.registry import get_registry
from query.tools.base import ToolInput, ToolOutput


class IndalekoAssistant:
    """
    Indaleko Assistant implementation using OpenAI's Assistant API.
    """
    
    # System instructions for the assistant
    ASSISTANT_INSTRUCTIONS = """You are Indaleko Assistant, a helpful AI that helps users find and understand their personal data.

    Indaleko is a unified personal index system that helps users find, understand, and manage their data across multiple storage services and devices.

    Your role is to:
    1. Help users formulate queries to find their data
    2. Ask clarifying questions when needed
    3. Explain query results in a helpful way
    4. Suggest refinements to improve search results

    You have access to tools that can:
    - Parse natural language queries
    - Translate structured queries to AQL (ArangoDB Query Language)
    - Execute queries against the database
    - Analyze and present results

    Follow these guidelines:
    1. Be conversational but concise
    2. Ask clarifying questions when the query is ambiguous
    3. Explain what you're doing when using tools
    4. Format results in a clear, readable way
    5. For large result sets, summarize the key findings
    6. Suggest related queries when appropriate
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        """
        Initialize the Indaleko Assistant.
        
        Args:
            api_key (Optional[str]): The OpenAI API key. If None, will be loaded from config.
            model (str): The model to use for the assistant.
        """
        self.api_key = api_key if api_key else self._load_api_key()
        self.model = model
        self.client = openai.OpenAI(api_key=self.api_key)
        self.tool_registry = get_registry()
        self.assistant_id = None
        self.conversations = {}
        
        # Create or retrieve the assistant
        self._initialize_assistant()
    
    def _load_api_key(self) -> str:
        """
        Load the OpenAI API key from the config file.
        
        Returns:
            str: The API key.
        """
        config_dir = os.path.join(os.environ.get("INDALEKO_ROOT"), "config")
        api_key_file = os.path.join(config_dir, "openai-key.ini")
        
        import configparser
        config = configparser.ConfigParser()
        config.read(api_key_file, encoding="utf-8-sig")
        
        api_key = config["openai"]["api_key"]
        
        # Clean up quotes if present
        if api_key[0] in ["'", '"'] and api_key[-1] in ["'", '"']:
            api_key = api_key[1:-1]
        
        return api_key
    
    def _initialize_assistant(self) -> None:
        """
        Initialize the OpenAI Assistant, creating a new one if needed.
        """
        # Check if the assistant configuration is stored on disk
        config_dir = os.path.join(os.environ.get("INDALEKO_ROOT"), "config")
        assistant_config_file = os.path.join(config_dir, "assistant-config.json")
        
        if os.path.exists(assistant_config_file):
            # Load existing configuration
            with open(assistant_config_file, "r") as f:
                config = json.load(f)
                self.assistant_id = config.get("assistant_id")
                
            # Verify the assistant still exists
            try:
                self.client.beta.assistants.retrieve(self.assistant_id)
                ic(f"Using existing assistant: {self.assistant_id}")
                return
            except Exception as e:
                ic(f"Error retrieving assistant: {e}")
                self.assistant_id = None
        
        # Create a new assistant
        tool_definitions = self._get_tool_definitions()
        
        assistant = self.client.beta.assistants.create(
            name="Indaleko Assistant",
            description="An assistant for finding and understanding personal data in Indaleko",
            instructions=self.ASSISTANT_INSTRUCTIONS,
            model=self.model,
            tools=tool_definitions
        )
        
        self.assistant_id = assistant.id
        ic(f"Created new assistant: {self.assistant_id}")
        
        # Save the configuration
        os.makedirs(config_dir, exist_ok=True)
        with open(assistant_config_file, "w") as f:
            json.dump({"assistant_id": self.assistant_id}, f)
    
    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Get OpenAI-compatible tool definitions from the registry.
        
        Returns:
            List[Dict[str, Any]]: Tool definitions in OpenAI format.
        """
        tools = []
        
        # Get all registered tools
        registered_tools = self.tool_registry.get_all_tools()
        
        for tool_name, tool in registered_tools.items():
            # Convert our tool definition to OpenAI format
            definition = tool.definition
            
            # Create parameter schema
            parameters = {
                "type": "object",
                "properties": {},
                "required": []
            }
            
            for param in definition.parameters:
                param_schema = {
                    "type": param.type,
                    "description": param.description
                }
                
                # Add default value if specified
                if param.default is not None:
                    param_schema["default"] = param.default
                
                parameters["properties"][param.name] = param_schema
                
                if param.required:
                    parameters["required"].append(param.name)
            
            # Add the tool
            tools.append({
                "type": "function",
                "function": {
                    "name": definition.name,
                    "description": definition.description,
                    "parameters": parameters
                }
            })
        
        return tools
    
    def create_conversation(self) -> ConversationState:
        """
        Create a new conversation with the assistant.
        
        Returns:
            ConversationState: The conversation state.
        """
        # Create conversation state
        conversation = ConversationState()
        
        # Create thread in the Assistant API
        thread = self.client.beta.threads.create()
        
        # Store the thread ID in the execution context
        conversation.execution_context["thread_id"] = thread.id
        
        # Store in our conversations dictionary
        self.conversations[conversation.conversation_id] = conversation
        
        return conversation
    
    def get_conversation(self, conversation_id: str) -> Optional[ConversationState]:
        """
        Get a conversation by ID.
        
        Args:
            conversation_id (str): The conversation ID.
            
        Returns:
            Optional[ConversationState]: The conversation if found, None otherwise.
        """
        return self.conversations.get(conversation_id)
    
    def execute_tool(self, tool_call: Dict[str, Any], conversation_id: str) -> Dict[str, Any]:
        """
        Execute a tool call from the assistant.
        
        Args:
            tool_call (Dict[str, Any]): The tool call from the assistant.
            conversation_id (str): The conversation ID.
            
        Returns:
            Dict[str, Any]: The result of the tool execution.
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation not found: {conversation_id}")
        
        # Extract tool information
        function_name = tool_call["function"]["name"]
        arguments = json.loads(tool_call["function"]["arguments"])
        
        ic(f"Executing tool: {function_name} with arguments: {arguments}")
        
        # Create the tool input
        tool_input = ToolInput(
            tool_name=function_name,
            parameters=arguments,
            conversation_id=conversation_id,
            invocation_id=tool_call["id"]
        )
        
        # Execute the tool
        result = self.tool_registry.execute_tool(tool_input)
        
        # Convert the result to a dictionary for the API
        if result.success:
            output = {
                "output": json.dumps(result.result, default=str)
            }
        else:
            output = {
                "error": result.error,
                "output": json.dumps({"error": result.error}, default=str)
            }
        
        return output
    
    def process_message(self, conversation_id: str, message_content: str) -> Dict[str, Any]:
        """
        Process a user message in the conversation.
        
        Args:
            conversation_id (str): The conversation ID.
            message_content (str): The user message.
            
        Returns:
            Dict[str, Any]: The response data.
        """
        # Get the conversation state
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            # Create a new conversation if one doesn't exist
            conversation = self.create_conversation()
            conversation_id = conversation.conversation_id
        
        # Add the message to the conversation state
        conversation.add_message("user", message_content)
        
        # Get the thread ID
        thread_id = conversation.execution_context.get("thread_id")
        if not thread_id:
            raise ValueError(f"Thread ID not found for conversation: {conversation_id}")
        
        # Add the message to the thread
        self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message_content
        )
        
        # Create a run with the assistant
        run = self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=self.assistant_id
        )
        
        # Wait for the run to complete or require action
        response = self._wait_for_run(thread_id, run.id, conversation_id)
        
        return response
    
    def _wait_for_run(self, thread_id: str, run_id: str, conversation_id: str) -> Dict[str, Any]:
        """
        Wait for an assistant run to complete or require action.
        
        Args:
            thread_id (str): The thread ID.
            run_id (str): The run ID.
            conversation_id (str): The conversation ID.
            
        Returns:
            Dict[str, Any]: The response data.
        """
        # Start waiting for the run to complete
        while True:
            # Get the run status
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )
            
            # Check the status
            if run.status == "completed":
                # Get the latest messages
                messages = self.client.beta.threads.messages.list(
                    thread_id=thread_id
                )
                
                # Get the latest assistant message
                assistant_messages = [msg for msg in messages.data if msg.role == "assistant"]
                if not assistant_messages:
                    return {
                        "conversation_id": conversation_id,
                        "response": "No response generated.",
                        "action": "text",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                
                latest_message = assistant_messages[0]
                
                # Extract and process the content
                message_content = ""
                for content_part in latest_message.content:
                    if content_part.type == "text":
                        message_content += content_part.text.value
                
                # Add the message to our conversation state
                conversation = self.get_conversation(conversation_id)
                conversation.add_message("assistant", message_content)
                
                return {
                    "conversation_id": conversation_id,
                    "response": message_content,
                    "action": "text",
                    "message_id": latest_message.id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            elif run.status == "requires_action":
                # Handle required actions (tool calls)
                if run.required_action and run.required_action.type == "submit_tool_outputs":
                    tool_calls = run.required_action.submit_tool_outputs.tool_calls
                    tool_outputs = []
                    
                    for tool_call in tool_calls:
                        # Execute the tool
                        output = self.execute_tool(tool_call, conversation_id)
                        
                        # Add to outputs
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": output.get("output", json.dumps({"error": output.get("error", "Unknown error")}))
                        })
                    
                    # Submit the tool outputs
                    self.client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread_id,
                        run_id=run_id,
                        tool_outputs=tool_outputs
                    )
                
                # Continue waiting for completion
                continue
            
            elif run.status in ["failed", "cancelled", "expired"]:
                # Handle failure
                error_message = f"Run {run_id} {run.status}: {run.last_error.message if run.last_error else 'Unknown error'}"
                
                # Add the error to our conversation state
                conversation = self.get_conversation(conversation_id)
                conversation.add_message("system", f"Error: {error_message}")
                
                return {
                    "conversation_id": conversation_id,
                    "response": error_message,
                    "action": "error",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            # Wait before checking again
            time.sleep(1)
    
    def save_conversations(self, file_path: str) -> None:
        """
        Save all conversations to a file.
        
        Args:
            file_path (str): The file path.
        """
        data = {
            conversation_id: conversation.model_dump()
            for conversation_id, conversation in self.conversations.items()
        }
        
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
    
    def load_conversations(self, file_path: str) -> None:
        """
        Load conversations from a file.
        
        Args:
            file_path (str): The file path.
        """
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            
            for conversation_id, conversation_data in data.items():
                # Convert string timestamps back to datetime
                if "created_at" in conversation_data:
                    conversation_data["created_at"] = datetime.fromisoformat(conversation_data["created_at"])
                if "updated_at" in conversation_data:
                    conversation_data["updated_at"] = datetime.fromisoformat(conversation_data["updated_at"])
                
                for message in conversation_data.get("messages", []):
                    if "timestamp" in message:
                        message["timestamp"] = datetime.fromisoformat(message["timestamp"])
                
                # Recreate conversation state
                conversation = ConversationState(**conversation_data)
                self.conversations[conversation_id] = conversation
        except (FileNotFoundError, json.JSONDecodeError) as e:
            ic(f"Error loading conversations: {e}")