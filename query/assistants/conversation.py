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
    
    # Enhanced system message template with context awareness and memory capabilities
    SYSTEM_MESSAGE = """You are Indaleko Assistant, a helpful AI that helps users find and understand their personal data.

Indaleko is a unified personal index system that helps users find, understand, and manage their data across multiple storage services and devices.

Your role is to:
1. Help users formulate queries to find their data
2. Ask clarifying questions when needed
3. Explain query results in a helpful way
4. Suggest refinements to improve search results
5. Maintain context across the conversation
6. Remember important information from previous exchanges
7. Consolidate insights for long-term memory

You have access to tools that can:
- Parse natural language queries
- Translate structured queries to AQL (ArangoDB Query Language)
- Execute queries against the database
- Analyze and present results
- Access information from previous sessions
- Store important insights for future reference

Always maintain a helpful, conversational tone while being concise and direct. You can refer to previous topics in the conversation and leverage insights stored in the archivist memory system.
"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o", 
                archivist_memory=None, db_config=None):
        """
        Initialize the conversation manager.
        
        Args:
            api_key (Optional[str]): The OpenAI API key.
            model (str): The model to use.
            archivist_memory: Optional pre-initialized archivist memory.
            db_config: Optional database configuration.
        """
        self.conversations = {}
        self.tool_registry = get_registry()
        self.api_key = api_key
        self.model = model
        self.db_config = db_config
        
        # Initialize archivist memory for long-term storage
        self.archivist_memory = archivist_memory
        
        # For tracking active conversations
        self.active_conversation_id = None
        
        # Load API key if not provided
        if self.api_key is None:
            self.api_key = self._load_api_key()
            
        # Initialize archivist memory if not provided
        if self.archivist_memory is None and self.db_config is not None:
            # Lazy import to avoid circular imports
            from query.memory.archivist_memory import ArchivistMemory
            self.archivist_memory = ArchivistMemory(db_config)
    
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
    
    def process_message(self, conversation_id: str, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a user message and generate a response with enhanced context management.
        
        Args:
            conversation_id (str): The conversation ID.
            message (str): The user message.
            context (Dict[str, Any], optional): Additional context for processing.
            
        Returns:
            Dict[str, Any]: The response data.
        """
        # Initialize context if not provided
        context = context or {}
        
        # Get or create conversation
        conversation = self.get_conversation(conversation_id)
        if conversation is None:
            conversation = self.create_conversation()
            conversation_id = conversation.conversation_id
            
            # Check if this is a continuation from another session
            continuation_pointer = context.get("continuation_pointer")
            if continuation_pointer and self.archivist_memory:
                # Attempt to retrieve continuation context
                continuation_data = self.archivist_memory.get_continuation_context(continuation_pointer)
                if continuation_data:
                    # Apply continuation context
                    conversation.set_continuation_pointer(continuation_pointer)
                    
                    # Add system message about continuation
                    continuation_summary = continuation_data.get('summary', 'Previous conversation')
                    conversation.add_message("system", 
                                            f"This conversation is a continuation from a previous session. "
                                            f"Context: {continuation_summary}")
                    
                    # Set key takeaways from previous session
                    for takeaway in continuation_data.get("key_takeaways", []):
                        conversation.add_key_takeaway(takeaway)
                        
                    # Add context variables
                    for key, value in continuation_data.get("context_variables", {}).items():
                        conversation.set_context_variable(key, value)
                        
                    # Set continuation info in execution context for assistant use
                    conversation.execution_context["continuation_info"] = {
                        "summary": continuation_summary,
                        "key_takeaways": continuation_data.get("key_takeaways", []),
                        "topics": continuation_data.get("topics", [])
                    }
        
        # Set as active conversation
        self.active_conversation_id = conversation_id
        
        # Analyze message for topic changes
        if not conversation.active_topic_segment:
            # Start initial topic segment
            conversation.start_topic_segment("general")
        else:
            # Check if we need to switch topics based on message content
            current_topic = None
            for segment in conversation.topic_segments:
                if segment.segment_id == conversation.active_topic_segment:
                    current_topic = segment.topic
                    break
                    
            # Topic change detection would go here
            # For now, we'll use a simple approach
            if message.startswith("Let's talk about ") or message.startswith("Can we discuss "):
                # Extract topic
                topic = message.replace("Let's talk about ", "").replace("Can we discuss ", "").split("?")[0].strip()
                
                # End current segment
                conversation.end_topic_segment()
                
                # Start new segment
                conversation.start_topic_segment(topic)
        
        # Add user message
        user_message = conversation.add_message("user", message)
        
        # Process the message using the advanced context-aware implementation
        # This is where we'll integrate with OpenAI's API or similar
        
        # Check for relevant memories in archivist memory
        referenced_memories = []
        if self.archivist_memory:
            # Search for relevant memories based on message content
            memories = self.archivist_memory.search_memories(message, max_results=3)
            for memory in memories:
                # Add as referenced memory
                memory_ref = conversation.add_referenced_memory(
                    memory_id=memory.get("memory_id", "unknown"),
                    memory_type=memory.get("memory_type", "unknown"),
                    relevance_score=memory.get("relevance", 0.7),
                    summary=memory.get("summary"),
                    message_id=user_message.id
                )
                referenced_memories.append(memory_ref)
        
        # For demonstration purposes, we'll create a more intelligent response
        # In a real implementation, this would use the assistant API
        response_content = self._generate_contextual_response(conversation, message, referenced_memories)
        
        # Create response data
        response = {
            "conversation_id": conversation_id,
            "response": response_content,
            "action": "response",
            "timestamp": datetime.utcnow().isoformat(),
            "referenced_memories": [m.memory_id for m in referenced_memories],
            "topic": self._get_active_topic(conversation)
        }
        
        # Add assistant response to conversation
        conversation.add_message("assistant", response_content)
        
        # Periodically update conversation summary
        if len(conversation.messages) % 10 == 0:
            self._update_conversation_summary(conversation)
            
        # Periodically extract key takeaways
        if len(conversation.messages) % 15 == 0:
            self._extract_key_takeaways(conversation)
            
        # Update importance score based on conversation progression
        self._update_importance_score(conversation)
        
        # Save conversation state to the database for persistence
        self._persist_conversation_state(conversation)
        
        return response
        
    def _generate_contextual_response(self, conversation, message, referenced_memories):
        """Generate a contextual response based on conversation state and referenced memories."""
        # This is a placeholder for integration with an actual LLM
        # In a real implementation, this would use OpenAI's API or similar
        
        # Access conversation context
        recent_messages = conversation.messages[-5:] if len(conversation.messages) >= 5 else conversation.messages
        topic = self._get_active_topic(conversation)
        
        # Simple context-aware response generation
        if "search" in message.lower() or "find" in message.lower():
            return f"I can help you search for that. What specific criteria should I use?"
        elif "remember" in message.lower() or "recall" in message.lower():
            if referenced_memories:
                memory = referenced_memories[0]
                return f"Yes, I remember {memory.summary or 'that'}. We can continue where we left off."
            else:
                return "I don't have specific memories about that. Can you provide more details?"
        elif len(recent_messages) > 3 and all(m.role == "user" for m in recent_messages[-3:]):
            return "I notice you've sent several messages. Let me address all of them together."
        elif topic != "general":
            return f"Regarding {topic}, I can provide more specific information if you'd like."
        else:
            return f"I understand you're asking about {message.split()[0] if message else 'this'}. How can I help further?"
    
    def _get_active_topic(self, conversation):
        """Get the active topic from the conversation."""
        if not conversation.active_topic_segment:
            return "general"
            
        for segment in conversation.topic_segments:
            if segment.segment_id == conversation.active_topic_segment:
                return segment.topic
                
        return "general"
    
    def _update_conversation_summary(self, conversation):
        """Update the conversation summary."""
        # In a real implementation, this would use an LLM to generate a summary
        # For now, we'll create a simple summary
        
        if len(conversation.messages) < 5:
            summary = "Conversation just started."
        else:
            topics = set()
            for segment in conversation.topic_segments:
                if segment.topic != "general":
                    topics.add(segment.topic)
            
            if topics:
                topics_str = ", ".join(topics)
                summary = f"Conversation covering topics: {topics_str}."
            else:
                summary = "General conversation about Indaleko."
        
        conversation.update_conversation_summary(summary)
    
    def _extract_key_takeaways(self, conversation):
        """Extract key takeaways from the conversation."""
        # In a real implementation, this would use an LLM to extract key points
        # For now, we'll use a simple approach
        
        # Check recent user messages for potential takeaways
        recent_messages = conversation.messages[-15:]
        for msg in recent_messages:
            if msg.role == "user":
                content = msg.content.lower()
                
                # Simple heuristics for takeaways
                if "important" in content or "remember" in content or "don't forget" in content:
                    # Consider this a potential takeaway
                    takeaway = msg.content
                    if len(takeaway) > 20:  # Only reasonably substantive takeaways
                        conversation.add_key_takeaway(takeaway)
    
    def _update_importance_score(self, conversation):
        """Update the conversation importance score."""
        # Calculate importance based on multiple factors
        score = 0.5  # Default score
        
        # Factor 1: Length of conversation
        if len(conversation.messages) > 20:
            score += 0.1
        if len(conversation.messages) > 50:
            score += 0.1
            
        # Factor 2: Number of topic segments
        if len(conversation.topic_segments) > 1:
            score += 0.05 * min(5, len(conversation.topic_segments))
            
        # Factor 3: Number of key takeaways
        if conversation.key_takeaways:
            score += 0.05 * min(5, len(conversation.key_takeaways))
            
        # Factor 4: Referenced memories
        if conversation.referenced_memories:
            score += 0.05 * min(5, len(conversation.referenced_memories))
            
        # Ensure score is in range [0.0, 1.0]
        score = max(0.0, min(1.0, score))
        
        conversation.set_importance_score(score)
    
    def _persist_conversation_state(self, conversation):
        """Save conversation state to archivist memory for persistence."""
        if not self.archivist_memory:
            return
            
        # Only persist if the conversation is important enough
        if conversation.importance_score < 0.4 and len(conversation.messages) < 10:
            return
            
        # Create a memory entry with key conversation information
        memory_data = {
            "conversation_id": conversation.conversation_id,
            "summary": conversation.conversation_summary or "Conversation with Indaleko Assistant",
            "key_takeaways": conversation.key_takeaways,
            "topics": [segment.topic for segment in conversation.topic_segments],
            "entities": list(conversation.entities.keys()),
            "importance_score": conversation.importance_score,
            "message_count": len(conversation.messages),
            "context_variables": conversation.context_variables
        }
        
        # Store in archivist memory
        self.archivist_memory.store_conversation_state(conversation.conversation_id, memory_data)
    
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