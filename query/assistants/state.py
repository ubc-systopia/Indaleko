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
from typing import Any

from pydantic import BaseModel, Field

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


class Message(BaseModel):
    """A message in a conversation."""

    role: str = Field(
        ...,
        description="The role of the message sender: 'user', 'assistant', or 'system'",
    )
    content: str = Field(..., description="The content of the message")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When the message was created",
    )
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the message",
    )


class EntityInfo(BaseModel):
    """Information about an entity identified in a conversation."""

    name: str = Field(..., description="The name of the entity")
    type: str = Field(..., description="The type of the entity")
    value: Any = Field(..., description="The value of the entity")
    source: str = Field(
        ..., description="Where the entity value came from (e.g., 'user', 'database')",
    )
    confidence: float = Field(
        default=1.0, description="Confidence in the entity value (0.0-1.0)",
    )
    alternative_values: list[dict[str, Any]] | None = Field(
        default=None, description="Alternative values for the entity",
    )


class TopicSegment(BaseModel):
    """A segment of conversation focused on a particular topic."""

    segment_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this segment",
    )
    topic: str = Field(default="general", description="The topic of this segment")
    start_index: int = Field(
        ..., description="Index of the first message in this segment",
    )
    end_index: int | None = Field(
        default=None,
        description="Index of the last message in this segment (None if ongoing)",
    )
    entities: list[str] = Field(
        default_factory=list, description="Key entities relevant to this topic",
    )
    summary: str | None = Field(
        default=None, description="A summary of this conversation segment",
    )
    importance: float = Field(
        default=0.5, description="Importance score for this segment (0.0-1.0)",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this segment was created",
    )


class ReferencedMemory(BaseModel):
    """A reference to a memory item retrieved during the conversation."""

    memory_id: str = Field(..., description="ID of the referenced memory")
    memory_type: str = Field(
        ..., description="Type of memory (e.g., 'archival', 'pattern', 'insight')",
    )
    relevance_score: float = Field(
        default=0.7,
        description="How relevant this memory is to the current context (0.0-1.0)",
    )
    referenced_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this memory was referenced",
    )
    message_id: str | None = Field(
        default=None, description="Message ID where this memory was referenced",
    )
    summary: str | None = Field(
        default=None, description="Brief summary of the memory content",
    )


class ConversationState(BaseModel):
    """The state of a conversation."""

    conversation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the conversation",
    )
    messages: list[Message] = Field(
        default_factory=list, description="The messages in the conversation",
    )
    current_query: str | None = Field(
        default=None, description="The current query being processed",
    )
    entities: dict[str, EntityInfo] = Field(
        default_factory=dict, description="Entities identified in the conversation",
    )
    pending_clarifications: list[dict[str, Any]] = Field(
        default_factory=list, description="Pending clarification questions",
    )
    query_history: list[str] = Field(
        default_factory=list,
        description="History of queries processed in this conversation",
    )
    execution_context: dict[str, Any] = Field(
        default_factory=dict, description="Context for query execution",
    )
    user_preferences: dict[str, Any] = Field(
        default_factory=dict, description="User preferences for query processing",
    )

    # Enhanced conversation context features
    topic_segments: list[TopicSegment] = Field(
        default_factory=list, description="Topic segments within this conversation",
    )
    active_topic_segment: str | None = Field(
        default=None, description="ID of the currently active topic segment",
    )
    conversation_summary: str | None = Field(
        default=None, description="Dynamic summary of the entire conversation",
    )
    key_takeaways: list[str] = Field(
        default_factory=list, description="Key takeaways from the conversation",
    )
    referenced_memories: list[ReferencedMemory] = Field(
        default_factory=list, description="Memories referenced during the conversation",
    )
    context_variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Context variables maintained across the conversation",
    )
    importance_score: float = Field(
        default=0.5, description="Overall importance of this conversation (0.0-1.0)",
    )
    continuation_pointer: str | None = Field(
        default=None,
        description="Pointer to continuation information if this conversation spans sessions",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the conversation was created",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the conversation was last updated",
    )

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

    def add_entity(
        self,
        name: str,
        entity_type: str,
        value: Any,
        source: str,
        confidence: float = 1.0,
    ) -> EntityInfo:
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
            confidence=confidence,
        )
        self.entities[name] = entity
        self.updated_at = datetime.utcnow()
        return entity

    def add_clarification(
        self,
        question: str,
        context: str,
        entity_type: str | None = None,
        options: list[str] | None = None,
    ) -> dict[str, Any]:
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
            "timestamp": datetime.utcnow(),
        }
        self.pending_clarifications.append(clarification)
        self.updated_at = datetime.utcnow()
        return clarification

    def get_conversation_messages(self) -> list[dict[str, str]]:
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

    def get_entity(self, name: str) -> EntityInfo | None:
        """
        Get an entity by name.

        Args:
            name (str): The name of the entity.

        Returns:
            Optional[EntityInfo]: The entity if found, None otherwise.
        """
        return self.entities.get(name)

    def start_topic_segment(
        self, topic: str, entities: list[str] = None,
    ) -> TopicSegment:
        """
        Start a new topic segment in the conversation.

        Args:
            topic (str): The topic of the segment.
            entities (List[str], optional): Key entities relevant to this topic.

        Returns:
            TopicSegment: The created topic segment.
        """
        # If there's an active segment, end it first
        if self.active_topic_segment:
            self.end_topic_segment()

        # Create a new segment
        segment = TopicSegment(
            topic=topic, start_index=len(self.messages), entities=entities or [],
        )

        # Add to segments and set as active
        self.topic_segments.append(segment)
        self.active_topic_segment = segment.segment_id
        self.updated_at = datetime.utcnow()

        return segment

    def end_topic_segment(self, summary: str = None) -> TopicSegment | None:
        """
        End the active topic segment.

        Args:
            summary (str, optional): A summary of this segment.

        Returns:
            Optional[TopicSegment]: The ended segment if there was an active one.
        """
        if not self.active_topic_segment:
            return None

        # Find the active segment
        for segment in self.topic_segments:
            if segment.segment_id == self.active_topic_segment:
                # Mark as ended
                segment.end_index = len(self.messages) - 1
                if summary:
                    segment.summary = summary
                self.active_topic_segment = None
                self.updated_at = datetime.utcnow()
                return segment

        return None

    def add_referenced_memory(
        self,
        memory_id: str,
        memory_type: str,
        relevance_score: float = 0.7,
        summary: str = None,
        message_id: str = None,
    ) -> ReferencedMemory:
        """
        Add a reference to a memory item retrieved during the conversation.

        Args:
            memory_id (str): ID of the referenced memory.
            memory_type (str): Type of memory.
            relevance_score (float, optional): Relevance score.
            summary (str, optional): Brief summary of the memory.
            message_id (str, optional): Message ID where this memory was referenced.

        Returns:
            ReferencedMemory: The created memory reference.
        """
        # Create the memory reference
        memory_ref = ReferencedMemory(
            memory_id=memory_id,
            memory_type=memory_type,
            relevance_score=relevance_score,
            summary=summary,
            message_id=message_id,
        )

        # Add to references
        self.referenced_memories.append(memory_ref)
        self.updated_at = datetime.utcnow()

        return memory_ref

    def update_conversation_summary(self, summary: str) -> None:
        """
        Update the dynamic summary of the entire conversation.

        Args:
            summary (str): The new conversation summary.
        """
        self.conversation_summary = summary
        self.updated_at = datetime.utcnow()

    def add_key_takeaway(self, takeaway: str) -> None:
        """
        Add a key takeaway from the conversation.

        Args:
            takeaway (str): The takeaway to add.
        """
        if takeaway not in self.key_takeaways:
            self.key_takeaways.append(takeaway)
            self.updated_at = datetime.utcnow()

    def set_importance_score(self, score: float) -> None:
        """
        Set the overall importance score for this conversation.

        Args:
            score (float): The importance score (0.0-1.0).
        """
        self.importance_score = max(0.0, min(1.0, score))
        self.updated_at = datetime.utcnow()

    def set_continuation_pointer(self, pointer: str) -> None:
        """
        Set a pointer to continuation information if this conversation spans sessions.

        Args:
            pointer (str): Pointer to continuation information.
        """
        self.continuation_pointer = pointer
        self.updated_at = datetime.utcnow()

    def set_context_variable(self, key: str, value: Any) -> None:
        """
        Set a context variable that persists across the conversation.

        Args:
            key (str): The variable key.
            value (Any): The variable value.
        """
        self.context_variables[key] = value
        self.updated_at = datetime.utcnow()

    def get_context_variable(self, key: str, default: Any = None) -> Any:
        """
        Get a context variable.

        Args:
            key (str): The variable key.
            default (Any, optional): Default value if not found.

        Returns:
            Any: The variable value or default.
        """
        return self.context_variables.get(key, default)

    def get_segment_messages(self, segment_id: str) -> list[Message]:
        """
        Get the messages in a specific segment.

        Args:
            segment_id (str): The segment ID.

        Returns:
            List[Message]: The messages in the segment.
        """
        # Find the segment
        for segment in self.topic_segments:
            if segment.segment_id == segment_id:
                end_index = (
                    segment.end_index
                    if segment.end_index is not None
                    else len(self.messages)
                )
                return self.messages[segment.start_index : end_index + 1]

        return []

    def get_recent_context(self, message_count: int = 5) -> list[dict[str, str]]:
        """
        Get the most recent context messages in a format suitable for the LLM API.

        Args:
            message_count (int): Maximum number of recent messages to include.

        Returns:
            List[Dict[str, str]]: The formatted recent messages.
        """
        recent_messages = (
            self.messages[-message_count:]
            if len(self.messages) > message_count
            else self.messages
        )
        return [{"role": msg.role, "content": msg.content} for msg in recent_messages]
