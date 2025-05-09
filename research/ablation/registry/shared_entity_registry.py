"""Shared entity registry for cross-collection references in ablation testing."""

import logging
from typing import Dict, List, Optional, Set
from uuid import UUID

from ..utils.uuid_utils import generate_uuid_for_entity, generate_random_uuid


class EntityReference:
    """Reference to an entity in a specific collection.
    
    This class represents a reference to an entity in a specific collection,
    storing both the entity ID and the collection it belongs to.
    """
    
    def __init__(self, entity_id: UUID, collection_name: str):
        """Initialize an entity reference.
        
        Args:
            entity_id: The UUID of the entity.
            collection_name: The name of the collection the entity belongs to.
        """
        self.entity_id = entity_id
        self.collection_name = collection_name
    
    def __eq__(self, other):
        """Check if two entity references are equal."""
        if not isinstance(other, EntityReference):
            return False
        return (self.entity_id == other.entity_id and 
                self.collection_name == other.collection_name)
    
    def __hash__(self):
        """Hash function for EntityReference."""
        return hash((self.entity_id, self.collection_name))


class SharedEntityRegistry:
    """Registry for tracking entities across collections.
    
    This class manages entity references across different collections,
    enabling cross-collection relationships for ablation testing.
    """
    
    def __init__(self):
        """Initialize the shared entity registry."""
        self.logger = logging.getLogger(__name__)
        
        # Maps entity type and name to a primary UUID
        self.entities: Dict[str, Dict[str, UUID]] = {}
        
        # Maps entity UUID to all collections it appears in
        self.entity_collections: Dict[UUID, Set[str]] = {}
        
        # Maps (collection, entity_type) to specific UUIDs
        self.collection_entities: Dict[str, Dict[str, Set[UUID]]] = {}
        
        # Maps entity UUID to its references in other collections
        self.entity_references: Dict[UUID, Dict[str, Set[EntityReference]]] = {}
        
        # Maps relationship types between collections
        self.relationship_types: Dict[str, Dict[str, Set[str]]] = {}
    
    def register_entity(self, entity_type: str, entity_name: str, 
                        collection_name: str) -> UUID:
        """Register an entity in a specific collection.
        
        Args:
            entity_type: The type of entity (e.g., 'task', 'location', etc.)
            entity_name: The name or natural identifier of the entity.
            collection_name: The collection where this entity exists.
            
        Returns:
            UUID: The UUID for the entity.
        """
        # Initialize entity type dictionary if needed
        if entity_type not in self.entities:
            self.entities[entity_type] = {}
        
        # Generate or retrieve the entity UUID
        if entity_name not in self.entities[entity_type]:
            entity_id = generate_uuid_for_entity(entity_type, entity_name)
            self.entities[entity_type][entity_name] = entity_id
            self.entity_collections[entity_id] = set()
            self.entity_references[entity_id] = {}
        else:
            entity_id = self.entities[entity_type][entity_name]
        
        # Add collection to entity's collection list
        self.entity_collections[entity_id].add(collection_name)
        
        # Initialize collection entity tracking if needed
        if collection_name not in self.collection_entities:
            self.collection_entities[collection_name] = {}
        
        if entity_type not in self.collection_entities[collection_name]:
            self.collection_entities[collection_name][entity_type] = set()
        
        # Add entity to collection's entity list
        self.collection_entities[collection_name][entity_type].add(entity_id)
        
        return entity_id
    
    def add_relationship(self, source_entity_id: UUID, target_entity_id: UUID, 
                        relationship_type: str) -> bool:
        """Add a relationship between two entities.
        
        Args:
            source_entity_id: The UUID of the source entity.
            target_entity_id: The UUID of the target entity.
            relationship_type: The type of relationship (e.g., 'assigned_to', 'created_in').
            
        Returns:
            bool: True if the relationship was added successfully, False otherwise.
        """
        # Verify both entities exist
        if (source_entity_id not in self.entity_collections or 
            target_entity_id not in self.entity_collections):
            self.logger.error("Cannot add relationship between non-existent entities")
            return False
        
        # Get the collections for both entities
        source_collections = self.entity_collections[source_entity_id]
        target_collections = self.entity_collections[target_entity_id]
        
        # For each source collection
        for source_collection in source_collections:
            # Initialize relationship types for this collection pair if needed
            if source_collection not in self.relationship_types:
                self.relationship_types[source_collection] = {}
            
            # For each target collection
            for target_collection in target_collections:
                # Skip self-references within the same collection
                if source_collection == target_collection:
                    continue
                
                # Initialize relationship types for this collection pair if needed
                if target_collection not in self.relationship_types[source_collection]:
                    self.relationship_types[source_collection][target_collection] = set()
                
                # Add the relationship type
                self.relationship_types[source_collection][target_collection].add(relationship_type)
                
                # Create the entity reference
                target_ref = EntityReference(target_entity_id, target_collection)
                
                # Initialize relationship type dictionary if needed
                if relationship_type not in self.entity_references[source_entity_id]:
                    self.entity_references[source_entity_id][relationship_type] = set()
                
                # Add the reference
                self.entity_references[source_entity_id][relationship_type].add(target_ref)
        
        return True
    
    def get_entity_id(self, entity_type: str, entity_name: str) -> Optional[UUID]:
        """Get the UUID for a named entity.
        
        Args:
            entity_type: The type of entity (e.g., 'task', 'location', etc.)
            entity_name: The name of the entity.
            
        Returns:
            Optional[UUID]: The UUID for the entity, or None if not found.
        """
        if entity_type not in self.entities:
            return None
        
        return self.entities[entity_type].get(entity_name)
    
    def get_entity_references(self, entity_id: UUID, 
                             relationship_type: Optional[str] = None) -> List[EntityReference]:
        """Get all references to an entity, optionally filtered by relationship type.
        
        Args:
            entity_id: The UUID of the entity.
            relationship_type: Optional filter for specific relationship types.
            
        Returns:
            List[EntityReference]: List of entity references.
        """
        if entity_id not in self.entity_references:
            return []
        
        if relationship_type is not None:
            # Return references for a specific relationship type
            return list(self.entity_references[entity_id].get(relationship_type, set()))
        else:
            # Return all references across all relationship types
            all_references = set()
            for refs in self.entity_references[entity_id].values():
                all_references.update(refs)
            return list(all_references)
    
    def get_entities_by_collection(self, collection_name: str, 
                                  entity_type: Optional[str] = None) -> List[UUID]:
        """Get all entities in a specific collection, optionally filtered by type.
        
        Args:
            collection_name: The name of the collection.
            entity_type: Optional filter for specific entity types.
            
        Returns:
            List[UUID]: List of entity UUIDs.
        """
        if collection_name not in self.collection_entities:
            return []
        
        if entity_type is not None:
            # Return entities of a specific type
            return list(self.collection_entities[collection_name].get(entity_type, set()))
        else:
            # Return all entities across all types
            all_entities = set()
            for entities in self.collection_entities[collection_name].values():
                all_entities.update(entities)
            return list(all_entities)
    
    def get_relationship_types(self, source_collection: str, 
                              target_collection: str) -> List[str]:
        """Get all relationship types between two collections.
        
        Args:
            source_collection: The source collection.
            target_collection: The target collection.
            
        Returns:
            List[str]: List of relationship types.
        """
        if (source_collection not in self.relationship_types or
            target_collection not in self.relationship_types[source_collection]):
            return []
        
        return list(self.relationship_types[source_collection][target_collection])
    
    def get_collections_for_entity(self, entity_id: UUID) -> List[str]:
        """Get all collections an entity appears in.
        
        Args:
            entity_id: The UUID of the entity.
            
        Returns:
            List[str]: List of collection names.
        """
        if entity_id not in self.entity_collections:
            return []
        
        return list(self.entity_collections[entity_id])