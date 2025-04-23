"""
Fire Circle Memory Persistence.

This module provides persistence capabilities for the Fire Circle
memory system, allowing memories to be stored and retrieved across
sessions.

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

import abc
import json
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


class CircleMemory(BaseModel):
    """
    Base class for memories stored by the Fire Circle.

    CircleMemory provides the foundation for different types of
    persistent memory in the Fire Circle.
    """

    memory_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this memory",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this memory was created",
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this memory was last updated",
    )

    entity_id: str = Field(..., description="ID of the entity that created this memory")

    memory_type: str = Field(
        ..., description="Type of memory (e.g., conversation, insight, pattern)",
    )

    importance: float = Field(
        default=0.5, description="Importance of this memory (0.0-1.0)",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata about this memory",
    )


class ConversationMemory(CircleMemory):
    """Memory of a conversation within the Fire Circle."""

    conversation_id: str = Field(
        ..., description="ID of the conversation this memory is about",
    )

    topic: str = Field(default="", description="The topic of the conversation")

    summary: str = Field(default="", description="Summary of the conversation")

    messages: list[dict[str, Any]] = Field(
        default_factory=list, description="Messages from the conversation",
    )

    participants: list[str] = Field(
        default_factory=list,
        description="Entity IDs of participants in the conversation",
    )

    context_snapshot: dict[str, Any] = Field(
        default_factory=dict,
        description="Snapshot of context variables at the end of the conversation",
    )


class InsightMemory(CircleMemory):
    """Memory of an insight derived from Fire Circle interactions."""

    insight: str = Field(..., description="The insight content")

    source_memories: list[str] = Field(
        default_factory=list, description="IDs of memories that led to this insight",
    )

    confidence: float = Field(
        default=0.5, description="Confidence in this insight (0.0-1.0)",
    )

    categories: list[str] = Field(
        default_factory=list, description="Categories this insight belongs to",
    )


class PatternMemory(CircleMemory):
    """Memory of a pattern discovered in Fire Circle interactions."""

    pattern_description: str = Field(..., description="Description of the pattern")

    pattern_type: str = Field(
        ..., description="Type of pattern (e.g., interaction, discourse, agreement)",
    )

    evidence: list[str] = Field(
        default_factory=list,
        description="IDs of memories that provide evidence for this pattern",
    )

    frequency: int = Field(
        default=1, description="How many times this pattern has been observed",
    )

    entities_involved: list[str] = Field(
        default_factory=list, description="Entity IDs involved in this pattern",
    )


class CommuniqueMemory(CircleMemory):
    """Memory of a formal communiqué produced by the Fire Circle."""

    title: str = Field(..., description="Title of the communiqué")

    content: str = Field(..., description="Content of the communiqué")

    consensus_level: float = Field(
        default=0.0, description="Level of consensus achieved (0.0-1.0)",
    )

    dissenting_views: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Dissenting views expressed about this communiqué",
    )

    source_conversation: str = Field(
        default="", description="ID of the conversation that produced this communiqué",
    )

    endorsing_entities: list[str] = Field(
        default_factory=list, description="Entity IDs endorsing this communiqué",
    )


T = TypeVar("T", bound=CircleMemory)


class MemoryStore(Generic[T], abc.ABC):
    """
    Abstract base class for memory storage backends.

    This class defines the interface for storing and retrieving
    memories in the Fire Circle.
    """

    def __init__(
        self,
        memory_class: type[T],
        logger: logging.Logger | None = None,
    ):
        """
        Initialize the memory store.

        Args:
            memory_class: The class of memory this store handles
            logger: Optional logger for store events
        """
        self.memory_class = memory_class
        self.logger = logger or logging.getLogger(
            f"{__name__}.{memory_class.__name__}Store",
        )

    @abc.abstractmethod
    def store(self, memory: T) -> str:
        """
        Store a memory.

        Args:
            memory: The memory to store

        Returns:
            The memory ID
        """

    @abc.abstractmethod
    def retrieve(self, memory_id: str) -> T | None:
        """
        Retrieve a memory by ID.

        Args:
            memory_id: The ID of the memory to retrieve

        Returns:
            The memory if found, None otherwise
        """

    @abc.abstractmethod
    def update(self, memory: T) -> bool:
        """
        Update a stored memory.

        Args:
            memory: The memory to update

        Returns:
            True if updated, False otherwise
        """

    @abc.abstractmethod
    def delete(self, memory_id: str) -> bool:
        """
        Delete a memory.

        Args:
            memory_id: The ID of the memory to delete

        Returns:
            True if deleted, False otherwise
        """

    @abc.abstractmethod
    def search(self, query: dict[str, Any], limit: int = 10) -> list[T]:
        """
        Search for memories matching a query.

        Args:
            query: The search query
            limit: Maximum number of results to return

        Returns:
            List of matching memories
        """

    @abc.abstractmethod
    def list_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        """
        List all stored memories.

        Args:
            limit: Maximum number of memories to return
            offset: Starting offset for pagination

        Returns:
            List of memories
        """


class FileMemoryStore(MemoryStore[T]):
    """
    File-based implementation of memory store.

    This class stores memories as JSON files on disk.
    """

    def __init__(
        self,
        memory_class: type[T],
        directory: str,
        logger: logging.Logger | None = None,
    ):
        """
        Initialize the file memory store.

        Args:
            memory_class: The class of memory this store handles
            directory: Directory to store memory files in
            logger: Optional logger for store events
        """
        super().__init__(memory_class, logger)
        self.directory = directory

        # Create directory if it doesn't exist
        os.makedirs(directory, exist_ok=True)

        self.logger.info(f"Initialized file memory store in {directory}")

    def _memory_path(self, memory_id: str) -> str:
        """
        Get the file path for a memory.

        Args:
            memory_id: The memory ID

        Returns:
            Path to the memory file
        """
        return os.path.join(self.directory, f"{memory_id}.json")

    def store(self, memory: T) -> str:
        """
        Store a memory.

        Args:
            memory: The memory to store

        Returns:
            The memory ID
        """
        # Ensure memory has an ID
        if not memory.memory_id:
            memory.memory_id = str(uuid.uuid4())

        # Write to file
        with open(self._memory_path(memory.memory_id), "w") as f:
            f.write(memory.model_dump_json(indent=2))

        self.logger.info(f"Stored memory {memory.memory_id}")
        return memory.memory_id

    def retrieve(self, memory_id: str) -> T | None:
        """
        Retrieve a memory by ID.

        Args:
            memory_id: The ID of the memory to retrieve

        Returns:
            The memory if found, None otherwise
        """
        path = self._memory_path(memory_id)

        if not os.path.exists(path):
            self.logger.warning(f"Memory {memory_id} not found")
            return None

        try:
            with open(path) as f:
                data = json.load(f)

            memory = self.memory_class.model_validate(data)
            self.logger.info(f"Retrieved memory {memory_id}")
            return memory

        except Exception as e:
            self.logger.error(f"Error retrieving memory {memory_id}: {e}")
            return None

    def update(self, memory: T) -> bool:
        """
        Update a stored memory.

        Args:
            memory: The memory to update

        Returns:
            True if updated, False otherwise
        """
        path = self._memory_path(memory.memory_id)

        if not os.path.exists(path):
            self.logger.warning(f"Memory {memory.memory_id} not found for update")
            return False

        try:
            # Update timestamp
            memory.updated_at = datetime.now(UTC)

            # Write to file
            with open(path, "w") as f:
                f.write(memory.model_dump_json(indent=2))

            self.logger.info(f"Updated memory {memory.memory_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error updating memory {memory.memory_id}: {e}")
            return False

    def delete(self, memory_id: str) -> bool:
        """
        Delete a memory.

        Args:
            memory_id: The ID of the memory to delete

        Returns:
            True if deleted, False otherwise
        """
        path = self._memory_path(memory_id)

        if not os.path.exists(path):
            self.logger.warning(f"Memory {memory_id} not found for deletion")
            return False

        try:
            os.remove(path)
            self.logger.info(f"Deleted memory {memory_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error deleting memory {memory_id}: {e}")
            return False

    def search(self, query: dict[str, Any], limit: int = 10) -> list[T]:
        """
        Search for memories matching a query.

        Args:
            query: The search query
            limit: Maximum number of results to return

        Returns:
            List of matching memories
        """
        results = []

        # Iterate through all memory files
        for filename in os.listdir(self.directory):
            if not filename.endswith(".json"):
                continue

            memory_id = filename[:-5]  # Remove .json extension
            memory = self.retrieve(memory_id)

            if memory is None:
                continue

            # Check if memory matches query
            match = True
            for key, value in query.items():
                if hasattr(memory, key):
                    memory_value = getattr(memory, key)

                    # Handle different comparison types
                    if isinstance(value, dict) and "__op" in value:
                        op = value["__op"]
                        compare_value = value["value"]

                        if op == "eq" and memory_value != compare_value or op == "ne" and memory_value == compare_value or (op == "gt" and memory_value <= compare_value or op == "lt" and memory_value >= compare_value) or (op == "gte" and memory_value < compare_value or op == "lte" and memory_value > compare_value or (op == "in" and memory_value not in compare_value or op == "contains" and compare_value not in memory_value)):
                            match = False
                    elif memory_value != value:
                        match = False
                else:
                    match = False

            if match:
                results.append(memory)

                if len(results) >= limit:
                    break

        self.logger.info(f"Search returned {len(results)} results")
        return results

    def list_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        """
        List all stored memories.

        Args:
            limit: Maximum number of memories to return
            offset: Starting offset for pagination

        Returns:
            List of memories
        """
        results = []

        # Get all memory IDs
        memory_ids = [
            filename[:-5]  # Remove .json extension
            for filename in os.listdir(self.directory)
            if filename.endswith(".json")
        ]

        # Sort by modification time (newest first)
        memory_ids.sort(
            key=lambda mid: os.path.getmtime(self._memory_path(mid)), reverse=True,
        )

        # Apply pagination
        memory_ids = memory_ids[offset : offset + limit]

        # Retrieve each memory
        for memory_id in memory_ids:
            memory = self.retrieve(memory_id)
            if memory is not None:
                results.append(memory)

        self.logger.info(f"Listed {len(results)} memories")
        return results
