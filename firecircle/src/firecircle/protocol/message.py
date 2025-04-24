"""
Fire Circle Message Protocol.

This module defines the message format used for communication within
the Fire Circle implementation. It provides structured message types
and formatting for inter-entity communication.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason and contributors

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

import enum
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, validator


class MessageType(str, enum.Enum):
    """Types of messages that can be exchanged in the Fire Circle."""

    # Standard message types
    QUESTION = "question"  # Asking for information or clarification
    STATEMENT = "statement"  # Providing information or context
    PROPOSAL = "proposal"  # Suggesting an idea or approach
    AGREEMENT = "agreement"  # Expressing agreement with another message
    DISAGREEMENT = "disagreement"  # Expressing disagreement with another message
    CLARIFICATION = "clarification"  # Clarifying a previous message
    ELABORATION = "elaboration"  # Expanding on a previous message
    CHALLENGE = "challenge"  # Challenging assumptions or reasoning
    SYNTHESIS = "synthesis"  # Combining multiple perspectives
    REFLECTION = "reflection"  # Metacognitive reflection on the conversation

    # Process-related message types
    META = "meta"  # Discussion about the circle process itself
    FACILITATION = "facilitation"  # Guiding the conversation flow
    SUMMARY = "summary"  # Summarizing discussion
    COMMUNIQUE = "communique"  # Formal joint statement
    DISSENT = "dissent"  # Formal expression of disagreement with consensus

    # Circle governance message types
    PROCESS_PROPOSAL = "process_proposal"  # Suggesting changes to circle process
    EVALUATION = "evaluation"  # Evaluating circle effectiveness


class Message(BaseModel):
    """
    A message within the Fire Circle conversation.

    This is the basic building block of communication between entities.
    Messages are structured and typed to facilitate organized discourse.
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this message",
    )

    type: MessageType = Field(
        ...,
        description="The type of message (question, statement, etc.)",
    )

    content: str = Field(..., description="The content of the message")

    entity_id: str = Field(
        ...,
        description="Identifier of the entity that created this message",
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this message was created (UTC)",
    )

    references: list[str] = Field(
        default_factory=list,
        description="List of message IDs this message references",
    )

    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional attributes for the message",
    )

    # Add validators to ensure proper formatting
    @validator("entity_id")
    def entity_id_must_be_valid(cls, v):
        """Ensure entity_id is a valid UUID string."""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError("entity_id must be a valid UUID string")

    @validator("references")
    def references_must_be_valid(cls, v):
        """Ensure all references are valid UUID strings."""
        for ref in v:
            try:
                uuid.UUID(ref)
            except ValueError:
                raise ValueError(f"Reference {ref} is not a valid UUID string")
        return v


class CircleRequest(BaseModel):
    """
    A request to the Fire Circle.

    This represents a complete message bundle submitted to the circle,
    which may contain multiple messages and contextual information.
    """

    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this request",
    )

    messages: list[Message] = Field(
        ...,
        description="The messages included in this request",
    )

    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Contextual information for processing the request",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the request",
    )


class CircleResponse(BaseModel):
    """
    A response from the Fire Circle.

    This represents the output of the circle's processing of a request,
    which may include multiple messages from different entities as well
    as any consensus or synthesis developed.
    """

    response_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this response",
    )

    request_id: str = Field(
        ...,
        description="The ID of the request this is responding to",
    )

    messages: list[Message] = Field(
        default_factory=list,
        description="The messages produced in response",
    )

    consensus: Message | None = Field(
        default=None,
        description="Any consensus message developed by the circle",
    )

    dissent: list[Message] = Field(
        default_factory=list,
        description="Any dissenting messages that diverge from consensus",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the response",
    )
