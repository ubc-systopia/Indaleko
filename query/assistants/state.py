"""
Conversation state management for Indaleko assistants.

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
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


class Message(BaseModel):
    """A message in a conversation."""
    
    role: str = Field(..., description="The role of the message sender: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="The content of the message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the message was created")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the message")


class EntityInfo(BaseModel):
    """Information about an entity identified in a conversation."""
    
    name: str = Field(..., description="The name of the entity")
    type: str = Field(..., description="The type of the entity")
    value: Any = Field(..., description="The value of the entity")
    source: str = Field(..., description="Where the entity value came from (e.g., 'user', 'database')")
    confidence: float = Field(default=1.0, description="Confidence in the entity value (0.0-1.0)")
    alternative_values: Optional[List[Dict[str, Any]]] = Field(default=None, description="Alternative values for the entity")


class ConversationState(BaseModel):
    """The state of a conversation."""
    
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the conversation")
    messages: List[Message] = Field(default_factory=list, description="The messages in the conversation")
    current_query: Optional[str] = Field(default=None, description="The current query being processed")
    entities: Dict[str, EntityInfo] = Field(default_factory=dict, description="Entities identified in the conversation")
    pending_clarifications: List[Dict[str, Any]] = Field(default_factory=list, description="Pending clarification questions")
    query_history: List[str] = Field(default_factory=list, description="History of queries processed in this conversation")
    execution_context: Dict[str, Any] = Field(default_factory=dict, description="Context for query execution")
    user_preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences for query processing")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When the conversation was created")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="When the conversation was last updated")
    
    def add_message(self, role: str, content: str) -> Message:
        """
        Add a message to the conversation.
        
        Args:
            role (str): The role of the message sender.
            content (str): The content of the message.
            
        Returns:
            Message: The added message.
        """
        message = Message(role=role, content=content)
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
        return message
    
    def add_entity(self, name: str, entity_type: str, value: Any, source: str, confidence: float = 1.0) -> EntityInfo:
        """
        Add an entity to the conversation.
        
        Args:
            name (str): The name of the entity.
            entity_type (str): The type of the entity.
            value (Any): The value of the entity.
            source (str): Where the entity value came from.
            confidence (float): Confidence in the entity value.
            
        Returns:
            EntityInfo: The added entity.
        """
        entity = EntityInfo(
            name=name,
            type=entity_type,
            value=value,
            source=source,
            confidence=confidence
        )
        self.entities[name] = entity
        self.updated_at = datetime.utcnow()
        return entity
    
    def add_clarification(self, question: str, context: str, entity_type: Optional[str] = None, options: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Add a clarification question to the pending list.
        
        Args:
            question (str): The clarification question.
            context (str): Context for the question.
            entity_type (Optional[str]): The type of entity being clarified.
            options (Optional[List[str]]): Possible answer options.
            
        Returns:
            Dict[str, Any]: The added clarification.
        """
        clarification = {
            "question": question,
            "context": context,
            "entity_type": entity_type,
            "options": options,
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow()
        }
        self.pending_clarifications.append(clarification)
        self.updated_at = datetime.utcnow()
        return clarification
    
    def get_conversation_messages(self) -> List[Dict[str, str]]:
        """
        Get the conversation messages in a format suitable for the LLM API.
        
        Returns:
            List[Dict[str, str]]: The formatted messages.
        """
        return [{"role": msg.role, "content": msg.content} for msg in self.messages]
    
    def clear_pending_clarifications(self) -> None:
        """Clear pending clarification questions."""
        self.pending_clarifications = []
        self.updated_at = datetime.utcnow()
    
    def set_current_query(self, query: str) -> None:
        """
        Set the current query and add it to the history.
        
        Args:
            query (str): The query to set.
        """
        self.current_query = query
        self.query_history.append(query)
        self.updated_at = datetime.utcnow()
    
    def get_entity(self, name: str) -> Optional[EntityInfo]:
        """
        Get an entity by name.
        
        Args:
            name (str): The name of the entity.
            
        Returns:
            Optional[EntityInfo]: The entity if found, None otherwise.
        """
        return self.entities.get(name)