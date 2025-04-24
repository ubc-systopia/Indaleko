"""
Simple Fire Circle Example.

This script demonstrates the basic functionality of the Fire Circle
implementation with a simple conversation between entities.

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

import logging
import os
import sys
import uuid

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("firecircle-example")

# Add parent directory to path to import firecircle
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Import firecircle modules
from firecircle.entities.base import Entity, EntityCapability
from firecircle.entities.registry import EntityRegistry
from firecircle.integration.indaleko import IndalekoIntegration
from firecircle.memory.context import CircleContext
from firecircle.memory.persistence import ConversationMemory, InsightMemory

from firecircle.protocol.message import CircleRequest, Message, MessageType
from firecircle.protocol.orchestrator import (
    CircleOrchestrator,
    ConversationPhase,
    TurnTakingPolicy,
)


class SimpleEntity(Entity):
    """
    A simple entity implementation for the example.

    This entity can respond to messages based on simple rules.
    """

    def __init__(
        self,
        name: str,
        description: str,
        knowledge_areas: list[str],
        response_templates: dict[str, list[str]],
        capabilities: set[EntityCapability] | None = None,
        entity_id: str | None = None,
    ):
        """
        Initialize the simple entity.

        Args:
            name: Human-readable name for this entity
            description: Description of the entity's purpose or role
            knowledge_areas: List of areas this entity has knowledge in
            response_templates: Templates for different types of responses
            capabilities: Set of capabilities this entity has
            entity_id: Optional UUID for this entity (generated if not provided)
        """
        super().__init__(
            name=name,
            description=description,
            capabilities=capabilities,
            entity_id=entity_id,
        )

        self.knowledge_areas = knowledge_areas
        self.response_templates = response_templates

    def process_message(self, message: Message) -> list[Message]:
        """
        Process a single message.

        Args:
            message: The message to process

        Returns:
            List of response messages from this entity
        """
        # Remember the message
        self.remember_message(message)

        # Determine response based on message type
        if message.type == MessageType.QUESTION:
            return self._respond_to_question(message)

        elif message.type == MessageType.STATEMENT:
            return self._respond_to_statement(message)

        elif message.type == MessageType.PROPOSAL:
            return self._respond_to_proposal(message)

        elif message.type == MessageType.CHALLENGE:
            return self._respond_to_challenge(message)

        # Default to empty response
        return []

    def process_request(self, request: CircleRequest) -> list[Message]:
        """
        Process a complete request.

        Args:
            request: The request to process

        Returns:
            List of response messages from this entity
        """
        responses = []

        # Process each message in the request
        for message in request.messages:
            responses.extend(self.process_message(message))

        return responses

    def _respond_to_question(self, message: Message) -> list[Message]:
        """Generate response to a question."""
        # Check if we have knowledge in any relevant areas
        relevant = False
        for area in self.knowledge_areas:
            if area.lower() in message.content.lower():
                relevant = True
                break

        # Select response template based on relevance
        templates = (
            self.response_templates.get("relevant_question", [])
            if relevant
            else self.response_templates.get("irrelevant_question", [])
        )

        if not templates:
            # Default response if no templates
            return [
                self.create_message(
                    "I don't have a specific response to that question.",
                    MessageType.STATEMENT,
                    references=[message.id],
                ),
            ]

        # Use first template for simplicity
        # In a real implementation, would select based on context
        template = templates[0]

        # Format template with entity and message information
        response_content = template.format(
            entity_name=self.name,
            entity_knowledgearea=", ".join(self.knowledge_areas),
            message_content=message.content,
            entity_sender=message.entity_id,
        )

        return [
            self.create_message(
                response_content,
                MessageType.STATEMENT,
                references=[message.id],
            ),
        ]

    def _respond_to_statement(self, message: Message) -> list[Message]:
        """Generate response to a statement."""
        # Select response template
        templates = self.response_templates.get("statement", [])

        if not templates:
            # Default to no response
            return []

        # Use first template for simplicity
        template = templates[0]

        # Format template
        response_content = template.format(
            entity_name=self.name,
            entity_knowledgearea=", ".join(self.knowledge_areas),
            message_content=message.content,
            entity_sender=message.entity_id,
        )

        return [
            self.create_message(
                response_content,
                MessageType.STATEMENT,
                references=[message.id],
            ),
        ]

    def _respond_to_proposal(self, message: Message) -> list[Message]:
        """Generate response to a proposal."""
        # Check if proposal is relevant to knowledge areas
        relevant = False
        for area in self.knowledge_areas:
            if area.lower() in message.content.lower():
                relevant = True
                break

        # Determine agreement or disagreement based on relevance
        if relevant:
            templates = self.response_templates.get("agreement", [])
            message_type = MessageType.AGREEMENT
        else:
            templates = self.response_templates.get("disagreement", [])
            message_type = MessageType.DISAGREEMENT

        if not templates:
            # Default response
            return []

        # Use first template
        template = templates[0]

        # Format template
        response_content = template.format(
            entity_name=self.name,
            entity_knowledgearea=", ".join(self.knowledge_areas),
            message_content=message.content,
            entity_sender=message.entity_id,
        )

        return [
            self.create_message(
                response_content,
                message_type,
                references=[message.id],
            ),
        ]

    def _respond_to_challenge(self, message: Message) -> list[Message]:
        """Generate response to a challenge."""
        # Check if challenge is in knowledge area
        relevant = False
        for area in self.knowledge_areas:
            if area.lower() in message.content.lower():
                relevant = True
                break

        # If relevant, provide clarification
        if relevant:
            templates = self.response_templates.get("clarification", [])
            message_type = MessageType.CLARIFICATION
        else:
            # If not relevant, don't respond
            return []

        if not templates:
            # Default response
            return []

        # Use first template
        template = templates[0]

        # Format template
        response_content = template.format(
            entity_name=self.name,
            entity_knowledgearea=", ".join(self.knowledge_areas),
            message_content=message.content,
            entity_sender=message.entity_id,
        )

        return [
            self.create_message(
                response_content,
                message_type,
                references=[message.id],
            ),
        ]

    def reflect_on_process(self) -> Message | None:
        """Generate a reflection on the circle's process."""
        if not self.can(EntityCapability.META_REFLECTION):
            return None

        # Check if we have enough messages to reflect on
        if len(self.message_history) < 5:
            return None

        # Use reflection template if available
        templates = self.response_templates.get("reflection", [])
        if not templates:
            return super().reflect_on_process()

        template = templates[0]

        # Format template with simple statistics
        message_types = {}
        for msg in self.message_history:
            if msg.type in message_types:
                message_types[msg.type] += 1
            else:
                message_types[msg.type] = 1

        stats = ", ".join(f"{k.value}: {v}" for k, v in message_types.items())

        response_content = template.format(
            entity_name=self.name,
            message_stats=stats,
            message_count=len(self.message_history),
        )

        return self.create_message(response_content, MessageType.REFLECTION)


def run_simple_circle():
    """Run a simple Fire Circle example."""
    logger.info("Initializing Fire Circle example")

    # Initialize entity registry
    registry = EntityRegistry()

    # Create entities
    philosopher = SimpleEntity(
        name="Philosopher",
        description="Focuses on conceptual and ethical considerations",
        knowledge_areas=["ethics", "philosophy", "concepts", "theory"],
        response_templates={
            "relevant_question": [
                "As a philosopher, I believe {message_content} raises important conceptual questions. We should consider the broader implications for our understanding of knowledge and meaning.",
            ],
            "irrelevant_question": [
                "While I'm not an expert in this area, I wonder about the philosophical underpinnings of this question.",
            ],
            "statement": [
                "This statement has interesting philosophical dimensions. We might want to explore how it relates to fundamental concepts of knowledge and truth.",
            ],
            "agreement": [
                "I find this proposal philosophically sound. It aligns with principles of coherent knowledge organization.",
            ],
            "disagreement": [
                "I have some philosophical concerns about this approach. We should consider whether it truly captures the essence of knowledge.",
            ],
            "clarification": [
                "To clarify my philosophical position: I'm suggesting we consider how our conceptual frameworks shape our understanding of information.",
            ],
            "reflection": [
                "From a philosophical perspective, our conversation has covered various message types ({message_stats}) across {message_count} messages. I notice we've focused primarily on conceptual foundations rather than practical implementations.",
            ],
        },
        capabilities={
            EntityCapability.BASIC_CONVERSATION,
            EntityCapability.CRITICAL_ANALYSIS,
            EntityCapability.META_REFLECTION,
        },
    )

    engineer = SimpleEntity(
        name="Engineer",
        description="Focuses on practical implementation and technical feasibility",
        knowledge_areas=[
            "implementation",
            "technical",
            "architecture",
            "system",
            "database",
        ],
        response_templates={
            "relevant_question": [
                "From an engineering perspective, {message_content} has practical implications for our implementation. We should consider the technical requirements and constraints.",
            ],
            "irrelevant_question": [
                "While this isn't my core area, I can contribute some thoughts on how we might implement solutions related to this question.",
            ],
            "statement": [
                "I see some technical considerations here. We should think about how this would be implemented in the system architecture.",
            ],
            "agreement": [
                "This is technically feasible and aligns with good engineering practices. I support this approach.",
            ],
            "disagreement": [
                "I have some technical concerns about this proposal. We might face implementation challenges with this approach.",
            ],
            "clarification": [
                "To clarify the technical aspects: I'm suggesting we need to consider the system architecture implications and ensure we have the right infrastructure.",
            ],
            "reflection": [
                "Looking at our conversation from an engineering perspective, we've exchanged {message_count} messages with distribution {message_stats}. We've discussed several technical approaches but may need more concrete implementation plans.",
            ],
        },
        capabilities={
            EntityCapability.BASIC_CONVERSATION,
            EntityCapability.PATTERN_RECOGNITION,
            EntityCapability.META_REFLECTION,
        },
    )

    user_researcher = SimpleEntity(
        name="UserResearcher",
        description="Focuses on user needs and human factors",
        knowledge_areas=[
            "users",
            "humans",
            "experience",
            "interface",
            "needs",
            "design",
        ],
        response_templates={
            "relevant_question": [
                "As a user researcher, I think {message_content} relates to important user needs. We should consider how this affects the human experience with our system.",
            ],
            "irrelevant_question": [
                "While I can't speak directly to this, I'd encourage us to consider the user perspective and how this might impact their experience.",
            ],
            "statement": [
                "I'd like to add the user perspective to this discussion. How will this affect the people using our system?",
            ],
            "agreement": [
                "This approach seems to center user needs effectively. I support this direction as it will likely improve the overall experience.",
            ],
            "disagreement": [
                "I'm concerned this approach doesn't adequately address user needs. We should ensure we're designing with humans in mind.",
            ],
            "clarification": [
                "From a user perspective, I want to clarify that my concern is primarily about ensuring the system remains accessible and intuitive for people.",
            ],
            "reflection": [
                "From a user research perspective, our {message_count} messages ({message_stats}) have touched on human factors, but we might benefit from more direct consideration of user scenarios and needs.",
            ],
        },
        capabilities={
            EntityCapability.BASIC_CONVERSATION,
            EntityCapability.EMOTIONAL_INTELLIGENCE,
            EntityCapability.META_REFLECTION,
        },
    )

    # Register entities in registry
    registry.register_entity(philosopher)
    registry.register_entity(engineer)
    registry.register_entity(user_researcher)

    # Create orchestrator
    orchestrator = CircleOrchestrator(
        entity_ids=[entity.entity_id for entity in registry.get_all_entities()],
        turn_taking_policy=TurnTakingPolicy.ROUND_ROBIN_RANDOM,
        max_turns=12,
        initial_phase=ConversationPhase.OPENING,
    )

    # Create context
    context = CircleContext()

    # Set initial context variables
    context.set_variable(
        "topic",
        "knowledge organization in personal information systems",
        philosopher.entity_id,
    )

    context.set_variable(
        "key_question",
        "How can we balance philosophical coherence with technical feasibility and user needs?",
        philosopher.entity_id,
    )

    # Create integration with Indaleko
    integration = IndalekoIntegration()

    # Simulate a conversation
    logger.info("Starting simulated conversation")

    # Opening phase - Philosopher introduces the topic
    opening_message = philosopher.create_message(
        "I'd like to discuss how we approach knowledge organization in personal information systems. "
        "What philosophical principles should guide our understanding of how knowledge is structured?",
        MessageType.STATEMENT,
    )
    orchestrator.add_message(opening_message)

    # First turn - Engineer responds
    engineer_turn = orchestrator.get_next_turn()
    assert engineer_turn == engineer.entity_id

    engineer_response = engineer.process_message(opening_message)[0]
    orchestrator.add_message(engineer_response)

    # Second turn - User Researcher responds
    user_researcher_turn = orchestrator.get_next_turn()
    assert user_researcher_turn == user_researcher.entity_id

    user_response = user_researcher.process_message(opening_message)[0]
    orchestrator.add_message(user_response)

    # Third turn - Philosopher asks a question
    philosopher_turn = orchestrator.get_next_turn()
    assert philosopher_turn == philosopher.entity_id

    question = philosopher.create_message(
        "How do we ensure that our technical implementation aligns with users' mental models of knowledge organization?",
        MessageType.QUESTION,
        references=[opening_message.id],
    )
    orchestrator.add_message(question)

    # Fourth turn - Engineer responds to question
    engineer_turn = orchestrator.get_next_turn()
    assert engineer_turn == engineer.entity_id

    engineer_response = engineer.process_message(question)[0]
    orchestrator.add_message(engineer_response)

    # Force transition to Synthesis phase
    orchestrator.force_phase_transition(ConversationPhase.SYNTHESIS)

    # Fifth turn - User Researcher makes a proposal
    user_researcher_turn = orchestrator.get_next_turn()
    assert user_researcher_turn == user_researcher.entity_id

    proposal = user_researcher.create_message(
        "I propose we adopt a flexible knowledge organization system that allows users to create their own "
        "organizational structures while providing sensible defaults based on common patterns. "
        "This balances philosophical coherence with user autonomy and technical feasibility.",
        MessageType.PROPOSAL,
        references=[question.id, engineer_response.id],
    )
    orchestrator.add_message(proposal)

    # Sixth turn - Philosopher responds to proposal
    philosopher_turn = orchestrator.get_next_turn()
    assert philosopher_turn == philosopher.entity_id

    phil_response = philosopher.process_message(proposal)[0]
    orchestrator.add_message(phil_response)

    # Seventh turn - Engineer responds to proposal
    engineer_turn = orchestrator.get_next_turn()
    assert engineer_turn == engineer.entity_id

    eng_response = engineer.process_message(proposal)[0]
    orchestrator.add_message(eng_response)

    # Force transition to Communique phase
    orchestrator.force_phase_transition(ConversationPhase.COMMUNIQUE)

    # Eighth turn - Philosopher creates a communique
    philosopher_turn = orchestrator.get_next_turn()
    assert philosopher_turn == philosopher.entity_id

    communique = philosopher.create_message(
        "We have reached a consensus on knowledge organization in personal information systems: "
        "1. Systems should provide flexible structures that adapt to user mental models. "
        "2. Technical implementation should support both autonomous organization and intelligent defaults. "
        "3. The philosophical foundation should recognize knowledge as both personal and shared. "
        "This approach balances conceptual coherence, technical feasibility, and human needs.",
        MessageType.COMMUNIQUE,
        references=[proposal.id, phil_response.id, eng_response.id],
    )
    orchestrator.add_message(communique)

    # Force transition to Reflection phase
    orchestrator.force_phase_transition(ConversationPhase.REFLECTION)

    # Get reflections from entities
    reflections = []
    for entity in registry.get_all_entities():
        reflection = entity.reflect_on_process()
        if reflection:
            orchestrator.add_message(reflection)
            reflections.append(reflection)

    # End conversation
    orchestrator.force_phase_transition(ConversationPhase.CLOSING)

    # Get conversation summary
    summary = orchestrator.get_conversation_summary()

    # Create conversation memory
    conversation_memory = ConversationMemory(
        conversation_id=str(uuid.uuid4()),
        entity_id=philosopher.entity_id,
        memory_type="conversation",
        importance=0.8,
        topic="Knowledge Organization in Personal Information Systems",
        summary="Discussion about balancing philosophical coherence, technical feasibility, and user needs in knowledge organization",
        messages=[msg.model_dump() for msg in orchestrator.messages],
        participants=[entity.entity_id for entity in registry.get_all_entities()],
        context_snapshot=context.get_all_accessible_variables(philosopher.entity_id),
    )

    # Create insight memory
    insight_memory = InsightMemory(
        entity_id=philosopher.entity_id,
        memory_type="insight",
        importance=0.9,
        insight="Knowledge organization systems are most effective when they balance philosophical coherence, technical feasibility, and alignment with user mental models",
        confidence=0.85,
        categories=["knowledge organization", "system design", "user experience"],
    )

    # Export to Indaleko
    continuation_id = integration.export_circle_conversation(
        conversation_memory,
        store_in_archivist=True,
    )

    integration.export_circle_insights([insight_memory], store_in_archivist=True)

    # Print summary
    logger.info("Fire Circle Example Complete")
    logger.info(f"Messages: {len(orchestrator.messages)}")
    logger.info(f"Phases: {[phase for phase, _ in orchestrator.phase_history]}")
    logger.info(f"Continuation ID: {continuation_id}")

    return {
        "orchestrator": orchestrator,
        "registry": registry,
        "context": context,
        "conversation_memory": conversation_memory,
        "insight_memory": insight_memory,
        "continuation_id": continuation_id,
    }


if __name__ == "__main__":
    run_simple_circle()
