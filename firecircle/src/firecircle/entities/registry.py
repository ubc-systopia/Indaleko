"""
Fire Circle Entity Registry.

This module provides a registry for entities participating in
the Fire Circle implementation.

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
import uuid
from typing import Any

from firecircle.entities.base import Entity, EntityCapability


class EntityRegistry:
    """
    Registry for Fire Circle entities.

    This class manages the registration and retrieval of entities
    that can participate in Fire Circle conversations.
    """

    _instance = None

    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super(EntityRegistry, cls).__new__(cls)
            cls._instance.entities: dict[str, Entity] = {}
            cls._instance.entity_types: dict[str, type[Entity]] = {}
            cls._instance.logger = logging.getLogger(__name__)
        return cls._instance

    def register_entity(self, entity: Entity) -> None:
        """
        Register an entity with the registry.

        Args:
            entity: The entity to register
        """
        if entity.entity_id in self.entities:
            self.logger.warning(
                f"Entity with ID {entity.entity_id} already registered, replacing",
            )

        self.entities[entity.entity_id] = entity
        self.logger.info(f"Registered entity: {entity.name} (ID: {entity.entity_id})")

    def register_entity_type(
        self,
        entity_type: type[Entity],
        type_name: str | None = None,
    ) -> None:
        """
        Register an entity type with the registry.

        Args:
            entity_type: The entity class to register
            type_name: Optional name for this entity type
        """
        type_name = type_name or entity_type.__name__

        if type_name in self.entity_types:
            self.logger.warning(
                f"Entity type {type_name} already registered, replacing",
            )

        self.entity_types[type_name] = entity_type
        self.logger.info(f"Registered entity type: {type_name}")

    def create_entity(
        self,
        type_name: str,
        name: str,
        description: str,
        capabilities: set[EntityCapability] | None = None,
        entity_id: str | None = None,
        **kwargs,
    ) -> Entity:
        """
        Create a new entity of a registered type.

        Args:
            type_name: The registered entity type name
            name: Human-readable name for this entity
            description: Description of the entity's purpose or role
            capabilities: Set of capabilities this entity has
            entity_id: Optional UUID for this entity (generated if not provided)
            **kwargs: Additional arguments for the entity constructor

        Returns:
            The created entity

        Raises:
            ValueError: If the entity type is not registered
        """
        if type_name not in self.entity_types:
            raise ValueError(f"Entity type {type_name} not registered")

        entity_type = self.entity_types[type_name]
        entity = entity_type(
            name=name,
            description=description,
            capabilities=capabilities,
            entity_id=entity_id or str(uuid.uuid4()),
            **kwargs,
        )

        # Automatically register the entity
        self.register_entity(entity)

        return entity

    def get_entity(self, entity_id: str) -> Entity | None:
        """
        Get an entity by ID.

        Args:
            entity_id: The entity ID to retrieve

        Returns:
            The entity if found, None otherwise
        """
        return self.entities.get(entity_id)

    def get_entities_by_capability(self, capability: EntityCapability) -> list[Entity]:
        """
        Get all entities with a specific capability.

        Args:
            capability: The capability to filter by

        Returns:
            List of entities with the specified capability
        """
        return [entity for entity in self.entities.values() if entity.can(capability)]

    def get_entities_by_name(
        self,
        name: str,
        partial_match: bool = False,
    ) -> list[Entity]:
        """
        Get entities by name.

        Args:
            name: The name to search for
            partial_match: Whether to allow partial matches

        Returns:
            List of matching entities
        """
        if partial_match:
            return [entity for entity in self.entities.values() if name.lower() in entity.name.lower()]
        else:
            return [entity for entity in self.entities.values() if entity.name.lower() == name.lower()]

    def remove_entity(self, entity_id: str) -> bool:
        """
        Remove an entity from the registry.

        Args:
            entity_id: The ID of the entity to remove

        Returns:
            True if the entity was removed, False if not found
        """
        if entity_id in self.entities:
            entity = self.entities.pop(entity_id)
            self.logger.info(f"Removed entity: {entity.name} (ID: {entity_id})")
            return True
        return False

    def get_all_entities(self) -> list[Entity]:
        """
        Get all registered entities.

        Returns:
            List of all registered entities
        """
        return list(self.entities.values())

    def get_all_entity_types(self) -> dict[str, type[Entity]]:
        """
        Get all registered entity types.

        Returns:
            Dictionary mapping type names to entity classes
        """
        return self.entity_types.copy()

    def clear(self) -> None:
        """Clear all registered entities and entity types."""
        self.entities.clear()
        self.entity_types.clear()
        self.logger.info("Cleared entity registry")

    def get_registry_info(self) -> dict[str, Any]:
        """
        Get information about the registry.

        Returns:
            Dictionary with registry information
        """
        return {
            "entity_count": len(self.entities),
            "entity_type_count": len(self.entity_types),
            "entity_types": list(self.entity_types.keys()),
            "entities": [
                {
                    "id": entity.entity_id,
                    "name": entity.name,
                    "type": type(entity).__name__,
                    "capabilities": [c.value for c in entity.capabilities],
                }
                for entity in self.entities.values()
            ],
        }
