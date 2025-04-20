"""
Fire Circle Entity Base.

This module defines the base entity class and associated interfaces
for participants in the Fire Circle.

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
import enum
import uuid
import logging
from typing import Dict, List, Optional, Any, Set, Tuple, Union

from firecircle.protocol.message import Message, MessageType, CircleRequest, CircleResponse


class EntityCapability(str, enum.Enum):
    """Capabilities that an entity might have within the Fire Circle."""
    
    BASIC_CONVERSATION = "basic_conversation"  # Can participate in basic dialogue
    MEMORY_RETENTION = "memory_retention"      # Can remember past interactions
    CONSENSUS_BUILDING = "consensus_building"  # Can work toward consensus
    DISSENT_ARTICULATION = "dissent_articulation"  # Can articulate dissenting views
    META_REFLECTION = "meta_reflection"        # Can reflect on circle process
    SELF_EVALUATION = "self_evaluation"        # Can evaluate own contributions
    PATTERN_RECOGNITION = "pattern_recognition"  # Can identify patterns in conversation
    SPECIALIZED_KNOWLEDGE = "specialized_knowledge"  # Has domain-specific knowledge
    EMOTIONAL_INTELLIGENCE = "emotional_intelligence"  # Can perceive emotional context
    CREATIVE_SYNTHESIS = "creative_synthesis"  # Can creatively combine ideas
    CRITICAL_ANALYSIS = "critical_analysis"    # Can critically analyze arguments
    SUMMARY_GENERATION = "summary_generation"  # Can summarize discussions effectively


class Entity(abc.ABC):
    """
    Abstract base class for all entities in the Fire Circle.
    
    Entities are the participants in the Fire Circle conversation.
    Each entity has its own unique perspective, capabilities, and
    memory, while implementing a common interface for participation.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        capabilities: Optional[Set[EntityCapability]] = None,
        entity_id: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the entity.
        
        Args:
            name: Human-readable name for this entity
            description: Description of the entity's purpose or role
            capabilities: Set of capabilities this entity has
            entity_id: Optional UUID for this entity (generated if not provided)
            logger: Optional logger for entity events
        """
        self.name = name
        self.description = description
        self.capabilities = capabilities or {EntityCapability.BASIC_CONVERSATION}
        self.entity_id = entity_id or str(uuid.uuid4())
        self.logger = logger or logging.getLogger(f"{__name__}.{name}")
        
        # Initialize memory
        self.message_history: List[Message] = []
        self.context_variables: Dict[str, Any] = {}
        self.relationship_memory: Dict[str, Dict[str, Any]] = {}  # Memory about other entities
    
    @abc.abstractmethod
    def process_message(self, message: Message) -> List[Message]:
        """
        Process a single message.
        
        Args:
            message: The message to process
            
        Returns:
            List of response messages from this entity
        """
        pass
    
    @abc.abstractmethod
    def process_request(self, request: CircleRequest) -> List[Message]:
        """
        Process a complete request.
        
        Args:
            request: The request to process
            
        Returns:
            List of response messages from this entity
        """
        pass
    
    def can(self, capability: EntityCapability) -> bool:
        """
        Check if this entity has a specific capability.
        
        Args:
            capability: The capability to check for
            
        Returns:
            True if the entity has this capability, False otherwise
        """
        return capability in self.capabilities
    
    def remember_message(self, message: Message) -> None:
        """
        Store a message in this entity's memory.
        
        Args:
            message: The message to remember
        """
        self.message_history.append(message)
    
    def create_message(
        self,
        content: str,
        message_type: MessageType,
        references: Optional[List[str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """
        Create a new message from this entity.
        
        Args:
            content: The content of the message
            message_type: The type of message
            references: Optional list of referenced message IDs
            attributes: Optional additional attributes
            
        Returns:
            The created message
        """
        return Message(
            type=message_type,
            content=content,
            entity_id=self.entity_id,
            references=references or [],
            attributes=attributes or {},
        )
    
    def get_relevant_history(self, context: Dict[str, Any], limit: int = 10) -> List[Message]:
        """
        Get the most relevant messages from history given a context.
        
        Args:
            context: Context to determine relevance
            limit: Maximum number of messages to return
            
        Returns:
            List of relevant messages
        """
        # In a real implementation, this would use more sophisticated
        # relevance ranking. For now, just return the most recent messages.
        return self.message_history[-limit:]
    
    def update_relationship_memory(self, entity_id: str, attributes: Dict[str, Any]) -> None:
        """
        Update memory about relationship with another entity.
        
        Args:
            entity_id: The ID of the entity to update memory for
            attributes: Attributes to update in the relationship memory
        """
        if entity_id not in self.relationship_memory:
            self.relationship_memory[entity_id] = {}
        
        self.relationship_memory[entity_id].update(attributes)
    
    def get_relationship_memory(self, entity_id: str) -> Dict[str, Any]:
        """
        Get memory about relationship with another entity.
        
        Args:
            entity_id: The ID of the entity to get memory for
            
        Returns:
            Dictionary of relationship memory attributes
        """
        return self.relationship_memory.get(entity_id, {})
    
    def set_context_variable(self, key: str, value: Any) -> None:
        """
        Set a context variable.
        
        Args:
            key: The variable name
            value: The variable value
        """
        self.context_variables[key] = value
    
    def get_context_variable(self, key: str, default: Any = None) -> Any:
        """
        Get a context variable.
        
        Args:
            key: The variable name
            default: Default value if not found
            
        Returns:
            The variable value, or default if not found
        """
        return self.context_variables.get(key, default)
    
    def calculate_priority(self, context: Dict[str, Any]) -> float:
        """
        Calculate this entity's speaking priority given a context.
        
        This is used when the circle uses priority-based turn taking.
        
        Args:
            context: Context information for calculating priority
            
        Returns:
            Priority score between 0.0 and 1.0
        """
        # Default implementation - subclasses should override
        return 0.5
    
    def reflect_on_process(self) -> Optional[Message]:
        """
        Generate a reflection on the circle's process.
        
        Returns:
            A message containing process reflection, or None if not capable
        """
        if not self.can(EntityCapability.META_REFLECTION):
            return None
        
        # Default implementation - subclasses should override
        return self.create_message(
            content="I don't have specific reflections on our process at this time.",
            message_type=MessageType.REFLECTION
        )
    
    def evaluate_contribution(self, entity_id: str) -> Optional[Dict[str, float]]:
        """
        Evaluate another entity's contribution to the conversation.
        
        Args:
            entity_id: The entity to evaluate
            
        Returns:
            Dictionary of evaluation metrics, or None if not capable
        """
        if not self.can(EntityCapability.SELF_EVALUATION):
            return None
        
        # Default implementation - subclasses should override
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert entity to dictionary representation.
        
        Returns:
            Dictionary representation of this entity
        """
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "description": self.description,
            "capabilities": [c.value for c in self.capabilities],
            "message_history_count": len(self.message_history),
            "context_variables": {k: str(v) for k, v in self.context_variables.items()},
            "relationships": list(self.relationship_memory.keys())
        }