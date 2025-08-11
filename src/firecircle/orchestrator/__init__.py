"""
Orchestrator module for Fire Circle.

This module provides functionality for orchestrating the interactions between
different specialized entities in the Fire Circle.
"""

import time
import uuid

from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple

from ..core import (
    FireCircleEntity,
    create_analyst,
    create_coordinator,
    create_critic,
    create_storyteller,
    create_synthesizer,
)
from ..protocol import ENTITY_PROFILES, EntityInterface, EntityRole


class CircleState(Enum):
    """State of a Fire Circle session."""

    INITIALIZING = auto()
    GATHERING_PERSPECTIVES = auto()
    SYNTHESIZING = auto()
    COMPLETED = auto()
    FAILED = auto()


class CircleSession:
    """Represents a session of a Fire Circle conversation."""

    def __init__(
        self,
        session_id: str | None = None,
        entities: list[FireCircleEntity] | None = None,
        coordinator: FireCircleEntity | None = None,
    ) -> None:
        """
        Initialize a new Fire Circle session.

        Args:
            session_id: Optional session ID (generates a UUID if not provided)
            entities: Optional list of pre-configured entities
            coordinator: Optional pre-configured coordinator entity
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.entities = entities or []
        self.coordinator = coordinator or create_coordinator()
        self.state = CircleState.INITIALIZING
        self.history: list[dict[str, Any]] = []
        self.perspectives: dict[EntityRole, str] = {}
        self.synthesis: str | None = None
        self.created_at = time.time()
        self.last_updated_at = self.created_at

    def add_entity(self, entity: FireCircleEntity) -> None:
        """
        Add an entity to this session.

        Args:
            entity: The entity to add
        """
        self.entities.append(entity)
        self.last_updated_at = time.time()

    def get_history(self) -> list[dict[str, Any]]:
        """Get the conversation history for this session."""
        return self.history

    def add_message(
        self,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Add a message to the conversation history.

        Args:
            role: The role of the message sender
            content: The message content
            metadata: Optional metadata for the message
        """
        self.history.append(
            {
                "id": str(uuid.uuid4()),
                "role": role,
                "content": content,
                "metadata": metadata or {},
                "timestamp": time.time(),
            },
        )
        self.last_updated_at = time.time()

    def get_all_perspectives(self) -> dict[EntityRole, str]:
        """Get all gathered perspectives for the current topic."""
        return self.perspectives


class FireCircleOrchestrator:
    """Orchestrates the interactions between Fire Circle entities."""

    def __init__(self) -> None:
        """Initialize a new Fire Circle orchestrator."""
        self.sessions: dict[str, CircleSession] = {}

    def create_session(
        self,
        entities: list[EntityRole] | None = None,
        session_id: str | None = None,
    ) -> CircleSession:
        """
        Create a new Fire Circle session.

        Args:
            entities: Optional list of entity roles to include
            session_id: Optional session ID

        Returns:
            The created session
        """
        # Create session
        session = CircleSession(session_id=session_id)

        # Add default entities or specified ones
        if entities:
            for role in entities:
                if role == EntityRole.STORYTELLER:
                    session.add_entity(create_storyteller())
                elif role == EntityRole.ANALYST:
                    session.add_entity(create_analyst())
                elif role == EntityRole.CRITIC:
                    session.add_entity(create_critic())
                elif role == EntityRole.SYNTHESIZER:
                    session.add_entity(create_synthesizer())
        else:
            # Add all four specialized roles by default
            session.add_entity(create_storyteller())
            session.add_entity(create_analyst())
            session.add_entity(create_critic())
            session.add_entity(create_synthesizer())

        # Store session
        self.sessions[session.session_id] = session

        return session

    def get_session(self, session_id: str) -> CircleSession | None:
        """
        Get a session by ID.

        Args:
            session_id: The session ID

        Returns:
            The session if found, None otherwise
        """
        return self.sessions.get(session_id)

    def process_message(
        self,
        session_id: str,
        message: str,
        gather_all_perspectives: bool = True,
    ) -> dict[str, Any]:
        """
        Process a message in a Fire Circle session.

        Args:
            session_id: The session ID
            message: The message to process
            gather_all_perspectives: Whether to gather perspectives from all entities

        Returns:
            A dictionary containing the results
        """
        # Get session
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Add user message to history
        session.add_message("user", message)

        # Determine which entities should respond
        if gather_all_perspectives:
            responding_entities = session.entities
        else:
            # Evaluate which entity is best suited for this message
            evaluations = []
            for entity in session.entities:
                score = entity.can_handle_task(message)
                evaluations.append((entity, score))

            # Sort by score descending
            evaluations.sort(key=lambda x: x[1], reverse=True)

            # Take the top entity
            responding_entities = [evaluations[0][0]] if evaluations else []

        # Gather perspectives
        session.perspectives = {}

        for entity in responding_entities:
            try:
                # Process message
                context = {"history": session.get_history()}
                response = entity.process_message(message, context)

                # Store perspective
                session.perspectives[entity.role] = response

                # Add to history
                session.add_message(
                    f"assistant.{entity.role.value}",
                    response,
                    {"entity_role": entity.role.value},
                )
            except Exception as e:
                # Log error
                error_message = f"Error processing message with {entity.role.value}: {e!s}"
                session.add_message(
                    "system",
                    error_message,
                    {"error": True, "entity_role": entity.role.value},
                )

        # If we have a synthesizer and multiple perspectives, generate synthesis
        synthesizer = next(
            (e for e in session.entities if e.role == EntityRole.SYNTHESIZER),
            None,
        )
        perspectives = session.perspectives

        if synthesizer and len(perspectives) > 1:
            # Prepare a synthesis prompt
            synthesis_prompt = f"""
            The following perspectives were provided by different specialized entities in response to: "{message}"

            {chr(10).join([f"## {role.value.capitalize()} Perspective{chr(10)}{perspective}" for role, perspective in perspectives.items() if role != EntityRole.SYNTHESIZER])}

            Please synthesize these perspectives into a coherent, unified response that integrates the insights from each specialized perspective.
            """

            try:
                # Process synthesis
                synthesis = synthesizer.process_message(synthesis_prompt)

                # Store synthesis
                session.synthesis = synthesis

                # Add to history
                session.add_message(
                    "assistant.synthesis",
                    synthesis,
                    {"entity_role": "synthesizer", "is_synthesis": True},
                )
            except Exception as e:
                # Log error
                error_message = f"Error generating synthesis: {e!s}"
                session.add_message(
                    "system",
                    error_message,
                    {"error": True, "entity_role": "synthesizer"},
                )

        # Update session state
        session.state = CircleState.COMPLETED

        # Return results
        return {
            "session_id": session.session_id,
            "perspectives": {role.value: perspective for role, perspective in session.perspectives.items()},
            "synthesis": session.synthesis,
            "history": session.get_history(),
        }

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: The session ID

        Returns:
            True if session was deleted, False otherwise
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
