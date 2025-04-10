"""
Conversation management for Indaleko assistants.

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
import uuid
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from query.assistants.state import ConversationState, Message
from query.tools.registry import get_registry
from query.tools.base import ToolInput, ToolOutput


class ConversationManager:
    """Manager for conversations with the Indaleko assistant."""
    
    # System message template
    SYSTEM_MESSAGE = """You are Indaleko Assistant, a helpful AI that helps users find and understand their personal data.

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

Always maintain a helpful, conversational tone while being concise and direct.
"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize the conversation manager.
        
        Args:
            api_key (Optional[str]): The OpenAI API key.
            model (str): The model to use.
        """
        self.conversations = {}
        self.tool_registry = get_registry()
        self.api_key = api_key
        self.model = model
        
        # Load API key if not provided
        if self.api_key is None:
            self.api_key = self._load_api_key()
    
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
    
    def create_conversation(self) -> ConversationState:
        """
        Create a new conversation.
        
        Returns:
            ConversationState: The new conversation state.
        """
        # Create conversation with system message
        conversation = ConversationState()
        conversation.add_message("system", self.SYSTEM_MESSAGE)
        
        # Store the conversation
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
    
    def add_user_message(self, conversation_id: str, content: str) -> Message:
        """
        Add a user message to a conversation.
        
        Args:
            conversation_id (str): The conversation ID.
            content (str): The message content.
            
        Returns:
            Message: The added message.
            
        Raises:
            ValueError: If the conversation is not found.
        """
        conversation = self.get_conversation(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation not found: {conversation_id}")
        
        return conversation.add_message("user", content)
    
    def add_assistant_message(self, conversation_id: str, content: str) -> Message:
        """
        Add an assistant message to a conversation.
        
        Args:
            conversation_id (str): The conversation ID.
            content (str): The message content.
            
        Returns:
            Message: The added message.
            
        Raises:
            ValueError: If the conversation is not found.
        """
        conversation = self.get_conversation(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation not found: {conversation_id}")
        
        return conversation.add_message("assistant", content)
    
    def execute_tool(self, conversation_id: str, tool_name: str, parameters: Dict[str, Any]) -> ToolOutput:
        """
        Execute a tool in the context of a conversation.
        
        Args:
            conversation_id (str): The conversation ID.
            tool_name (str): The name of the tool to execute.
            parameters (Dict[str, Any]): The tool parameters.
            
        Returns:
            ToolOutput: The tool execution result.
            
        Raises:
            ValueError: If the conversation is not found or the tool is not found.
        """
        conversation = self.get_conversation(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation not found: {conversation_id}")
        
        # Create tool input
        tool_input = ToolInput(
            tool_name=tool_name,
            parameters=parameters,
            conversation_id=conversation_id,
            invocation_id=str(uuid.uuid4())
        )
        
        # Execute the tool
        result = self.tool_registry.execute_tool(tool_input)
        
        # Update conversation with tool result if appropriate
        # This can be expanded based on tool-specific logic
        
        return result
    
    def process_message(self, conversation_id: str, message: str) -> Dict[str, Any]:
        """
        Process a user message and generate a response.
        
        Args:
            conversation_id (str): The conversation ID.
            message (str): The user message.
            
        Returns:
            Dict[str, Any]: The response data.
        """
        # Get or create conversation
        conversation = self.get_conversation(conversation_id)
        if conversation is None:
            conversation = self.create_conversation()
            conversation_id = conversation.conversation_id
        
        # Add user message
        conversation.add_message("user", message)
        
        # Process the message using the assistant API
        # Note: This is a placeholder for the actual implementation using OpenAI's API
        # This would be replaced with actual API calls in a real implementation
        
        # For now, we'll create a simple echo response
        response = {
            "conversation_id": conversation_id,
            "response": f"Echo: {message}",
            "action": "echo",  # Placeholder action
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add assistant response to conversation
        conversation.add_message("assistant", response["response"])
        
        return response
    
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