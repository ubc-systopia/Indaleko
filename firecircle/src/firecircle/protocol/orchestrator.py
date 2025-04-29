"""
Fire Circle Orchestrator.

This module provides the conversation orchestration mechanisms for the
Fire Circle, including turn-taking, conversation flow management, and
phase transitions.

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
import logging
import random
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from firecircle.protocol.message import CircleRequest, CircleResponse, Message


class ConversationPhase(str, enum.Enum):
    """Phases of a Fire Circle conversation."""

    OPENING = "opening"  # Initial phase, setting context
    EXPLORATION = "exploration"  # Open exploration of the topic
    SYNTHESIS = "synthesis"  # Developing shared understanding
    COMMUNIQUE = "communique"  # Formal output development
    REFLECTION = "reflection"  # Meta-discussion about the process
    CLOSING = "closing"  # Concluding the conversation


class TurnTakingPolicy(str, enum.Enum):
    """Policies for determining turn order in the conversation."""

    ROUND_ROBIN = "round_robin"  # Each entity speaks in rotation
    RANDOM = "random"  # Random selection for each turn
    ROUND_ROBIN_RANDOM = "round_robin_random"  # Random order that cycles
    CONSENSUS_BASED = "consensus_based"  # Turn order determined by agreement
    PRIORITY_BASED = "priority_based"  # Based on entity-reported priority
    ADAPTIVE = "adaptive"  # Adapts based on conversation flow


class CircleOrchestrator:
    """
    Manages the conversation flow within the Fire Circle.

    This class handles turn-taking, phase transitions, and the overall
    orchestration of the dialogue between entities in the circle.
    """

    def __init__(
        self,
        entity_ids: list[str],
        turn_taking_policy: TurnTakingPolicy = TurnTakingPolicy.ROUND_ROBIN_RANDOM,
        max_turns: int = 20,
        initial_phase: ConversationPhase = ConversationPhase.OPENING,
        logger: logging.Logger | None = None,
    ):
        """
        Initialize the orchestrator.

        Args:
            entity_ids: List of entity IDs participating in the circle
            turn_taking_policy: Policy for determining turn order
            max_turns: Maximum number of turns in the conversation
            initial_phase: Starting phase for the conversation
            logger: Optional logger for orchestrator events
        """
        self.entity_ids = entity_ids
        self.turn_taking_policy = turn_taking_policy
        self.max_turns = max_turns
        self.current_phase = initial_phase
        self.logger = logger or logging.getLogger(__name__)

        # Set up state
        self.turn_counter = 0
        self.entity_order = self._generate_initial_order()
        self.current_entity_index = 0
        self.messages: list[Message] = []
        self.phase_history: list[tuple[ConversationPhase, datetime]] = [
            (initial_phase, datetime.now(UTC)),
        ]
        self.phase_transition_conditions: dict[ConversationPhase, Callable] = {}

    def _generate_initial_order(self) -> list[str]:
        """
        Generate the initial turn order based on the policy.

        Returns:
            List of entity IDs in the initial turn order
        """
        if self.turn_taking_policy == TurnTakingPolicy.ROUND_ROBIN:
            return self.entity_ids.copy()

        elif self.turn_taking_policy == TurnTakingPolicy.RANDOM:
            # Will be regenerated each turn
            return []

        elif self.turn_taking_policy == TurnTakingPolicy.ROUND_ROBIN_RANDOM:
            # Randomize once and use that order
            shuffled = self.entity_ids.copy()
            random.shuffle(shuffled)
            return shuffled

        elif self.turn_taking_policy == TurnTakingPolicy.CONSENSUS_BASED:
            # Start with random order, will be adjusted
            shuffled = self.entity_ids.copy()
            random.shuffle(shuffled)
            return shuffled

        elif self.turn_taking_policy == TurnTakingPolicy.PRIORITY_BASED:
            # Will be determined by priority signals
            return self.entity_ids.copy()

        elif self.turn_taking_policy == TurnTakingPolicy.ADAPTIVE:
            # Start with round robin
            return self.entity_ids.copy()

        else:
            # Default to round robin
            self.logger.warning(
                f"Unsupported turn taking policy: {self.turn_taking_policy}. " "Using round robin instead.",
            )
            return self.entity_ids.copy()

    def get_next_turn(self) -> str:
        """
        Get the entity ID for the next turn.

        Returns:
            The entity ID that should speak next
        """
        if self.turn_counter >= self.max_turns:
            raise ValueError("Maximum number of turns reached")

        # Handle different policies
        if self.turn_taking_policy == TurnTakingPolicy.ROUND_ROBIN:
            entity_id = self.entity_order[self.current_entity_index]
            self.current_entity_index = (self.current_entity_index + 1) % len(
                self.entity_ids,
            )

        elif self.turn_taking_policy == TurnTakingPolicy.RANDOM:
            entity_id = random.choice(self.entity_ids)

        elif self.turn_taking_policy == TurnTakingPolicy.ROUND_ROBIN_RANDOM:
            entity_id = self.entity_order[self.current_entity_index]
            self.current_entity_index = (self.current_entity_index + 1) % len(
                self.entity_ids,
            )

        elif self.turn_taking_policy == TurnTakingPolicy.CONSENSUS_BASED:
            # This would normally involve more complex logic based on agreement signals
            # For now, just use the current order
            entity_id = self.entity_order[self.current_entity_index]
            self.current_entity_index = (self.current_entity_index + 1) % len(
                self.entity_ids,
            )

        elif self.turn_taking_policy == TurnTakingPolicy.PRIORITY_BASED:
            # This would normally involve checking priority signals
            # For now, just use the current order
            entity_id = self.entity_order[self.current_entity_index]
            self.current_entity_index = (self.current_entity_index + 1) % len(
                self.entity_ids,
            )

        elif self.turn_taking_policy == TurnTakingPolicy.ADAPTIVE:
            # This would normally involve complex adaptation logic
            # For now, just use the current order
            entity_id = self.entity_order[self.current_entity_index]
            self.current_entity_index = (self.current_entity_index + 1) % len(
                self.entity_ids,
            )

        else:
            # Default to round robin
            entity_id = self.entity_order[self.current_entity_index]
            self.current_entity_index = (self.current_entity_index + 1) % len(
                self.entity_ids,
            )

        # Increment turn counter
        self.turn_counter += 1

        # Check for phase transitions
        self._check_phase_transitions()

        return entity_id

    def add_message(self, message: Message) -> None:
        """
        Add a message to the conversation.

        Args:
            message: The message to add
        """
        # Verify the entity is part of the circle
        if message.entity_id not in self.entity_ids:
            raise ValueError(f"Entity {message.entity_id} is not part of this circle")

        # Add message to the history
        self.messages.append(message)

        # Log the message
        self.logger.info(
            f"Message from {message.entity_id} of type {message.type}: {message.content[:50]}...",
        )

        # Check for phase transitions
        self._check_phase_transitions()

    def _check_phase_transitions(self) -> None:
        """Check if conditions are met for transitioning to a new phase."""
        # Skip if no conditions are defined
        if not self.phase_transition_conditions:
            return

        # Get the condition for the current phase
        condition = self.phase_transition_conditions.get(self.current_phase)
        if condition is None:
            return

        # Check if condition is met
        if condition(self):
            self._transition_to_next_phase()

    def _transition_to_next_phase(self) -> None:
        """Transition to the next conversation phase."""
        # Default phase transitions
        phase_sequence = [
            ConversationPhase.OPENING,
            ConversationPhase.EXPLORATION,
            ConversationPhase.SYNTHESIS,
            ConversationPhase.COMMUNIQUE,
            ConversationPhase.REFLECTION,
            ConversationPhase.CLOSING,
        ]

        # Find current phase index
        try:
            current_index = phase_sequence.index(self.current_phase)
        except ValueError:
            # If not found, just stay in current phase
            self.logger.warning(f"Unknown phase: {self.current_phase}")
            return

        # Get next phase
        if current_index < len(phase_sequence) - 1:
            next_phase = phase_sequence[current_index + 1]
        else:
            # Already at the end
            self.logger.info("Already at the final phase")
            return

        # Update phase
        self.current_phase = next_phase
        self.phase_history.append((next_phase, datetime.now(UTC)))

        # Log transition
        self.logger.info(f"Transitioned to phase: {next_phase}")

    def set_phase_transition_condition(
        self,
        phase: ConversationPhase,
        condition: Callable[["CircleOrchestrator"], bool],
    ) -> None:
        """
        Set a condition function for transitioning from a specific phase.

        Args:
            phase: The phase to set the condition for
            condition: Function that takes the orchestrator and returns True
                      if transition should occur
        """
        self.phase_transition_conditions[phase] = condition

    def force_phase_transition(self, new_phase: ConversationPhase) -> None:
        """
        Force transition to a specific phase.

        Args:
            new_phase: The phase to transition to
        """
        self.current_phase = new_phase
        self.phase_history.append((new_phase, datetime.now(UTC)))
        self.logger.info(f"Forced transition to phase: {new_phase}")

    def get_conversation_summary(self) -> dict[str, Any]:
        """
        Get a summary of the current conversation state.

        Returns:
            Dictionary with conversation summary
        """
        # Count message types
        message_type_counts = {}
        for message in self.messages:
            if message.type in message_type_counts:
                message_type_counts[message.type] += 1
            else:
                message_type_counts[message.type] = 1

        # Count entity participation
        entity_participation = {}
        for message in self.messages:
            if message.entity_id in entity_participation:
                entity_participation[message.entity_id] += 1
            else:
                entity_participation[message.entity_id] = 1

        # Calculate phase durations
        phase_durations = {}
        for i, (phase, timestamp) in enumerate(self.phase_history):
            # For all except the last entry, calculate duration
            if i < len(self.phase_history) - 1:
                next_timestamp = self.phase_history[i + 1][1]
                duration = (next_timestamp - timestamp).total_seconds()
                phase_durations[phase] = duration

        # For the current phase, calculate duration until now
        current_phase, current_timestamp = self.phase_history[-1]
        now = datetime.now(UTC)
        current_duration = (now - current_timestamp).total_seconds()
        phase_durations[current_phase] = current_duration

        return {
            "turn_count": self.turn_counter,
            "current_phase": self.current_phase,
            "message_count": len(self.messages),
            "message_type_distribution": message_type_counts,
            "entity_participation": entity_participation,
            "phase_durations": phase_durations,
            "phase_history": [(phase, ts.isoformat()) for phase, ts in self.phase_history],
        }

    def process_request(self, request: CircleRequest) -> CircleResponse:
        """
        Process a request to the circle.

        This is a placeholder for the full implementation, which would:
        1. Distribute the request to all entities
        2. Manage the turn-taking for responses
        3. Collect all messages
        4. Generate consensus if appropriate
        5. Return the complete response

        Args:
            request: The request to process

        Returns:
            Response from the circle
        """
        # This is a simplified implementation
        # In a real implementation, this would handle the full conversation flow

        # Add the request messages to our history
        for message in request.messages:
            self.add_message(message)

        # Create a response
        response = CircleResponse(
            request_id=request.request_id,
            messages=self.messages.copy(),  # In reality, this would be new messages
            metadata={"conversation_summary": self.get_conversation_summary()},
        )

        return response
