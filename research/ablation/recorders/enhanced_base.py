"""Enhanced base implementation for ablation activity recorders with cross-collection support."""

import json
import logging
import sys
from typing import Dict, List, Optional, Set, Any
from uuid import UUID

from db.db_config import IndalekoDBConfig

from ..base import ISyntheticRecorder
from ..registry import SharedEntityRegistry
from .base import BaseActivityRecorder


class EnhancedActivityRecorder(BaseActivityRecorder):
    """Enhanced base class for synthetic activity recorders with cross-collection support.
    
    This recorder extends the BaseActivityRecorder with support for cross-collection
    entity references, enabling relationships between different activity types.
    """
    
    # Name of the field that stores references to other collections
    REFERENCES_FIELD = "references"
    
    def __init__(self, entity_registry: SharedEntityRegistry = None):
        """Initialize the enhanced activity recorder.
        
        Args:
            entity_registry: Optional shared entity registry. If not provided,
                             a new registry will be created.
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Use provided registry or create a new one
        self.entity_registry = entity_registry or SharedEntityRegistry()
    
    def add_entity_reference(self, data: Dict[str, Any], 
                           source_entity_id: UUID, 
                           target_entity_id: UUID,
                           relationship_type: str) -> Dict[str, Any]:
        """Add an entity reference to the activity data.
        
        This method adds a reference from one entity to another in a different collection,
        creating a cross-collection relationship.
        
        Args:
            data: The activity data to modify.
            source_entity_id: The UUID of the source entity (typically the ID of this activity).
            target_entity_id: The UUID of the target entity in another collection.
            relationship_type: The type of relationship (e.g., 'assigned_to', 'created_in').
            
        Returns:
            Dict[str, Any]: The modified activity data.
        """
        # Add the relationship to the registry
        self.entity_registry.add_relationship(
            source_entity_id, 
            target_entity_id, 
            relationship_type
        )
        
        # Initialize references field if it doesn't exist
        if self.REFERENCES_FIELD not in data:
            data[self.REFERENCES_FIELD] = {}
        
        # Initialize relationship type if it doesn't exist
        if relationship_type not in data[self.REFERENCES_FIELD]:
            data[self.REFERENCES_FIELD][relationship_type] = []
        
        # Add the reference to the data
        data[self.REFERENCES_FIELD][relationship_type].append(str(target_entity_id))
        
        return data
    
    def record_with_references(self, data: Dict[str, Any], 
                              references: Dict[str, List[UUID]] = None) -> bool:
        """Record activity data with cross-collection references.
        
        This method extends the basic record method to include support for
        cross-collection references.
        
        Args:
            data: The activity data to record.
            references: Dictionary mapping relationship types to lists of target entity IDs.
                        Example: {'assigned_to': [user_id1, user_id2], 'created_in': [meeting_id]}
            
        Returns:
            bool: True if recording was successful, False otherwise.
        """
        if not self.db:
            self.logger.critical("No database connection available")
            sys.exit(1)
        
        # Deep copy to avoid modifying the original data
        data_copy = json.loads(json.dumps(data))
        
        # Get or create source entity ID
        source_id = UUID(data.get("id")) if "id" in data else None
        
        # Add references if provided
        if references and source_id:
            for relationship_type, target_ids in references.items():
                for target_id in target_ids:
                    data_copy = self.add_entity_reference(
                        data_copy, 
                        source_id, 
                        target_id, 
                        relationship_type
                    )
        
        # Use the standard record method to save the modified data
        return super().record(data_copy)
    
    def record_batch_with_references(self, data_batch: List[Dict[str, Any]], 
                                    references_batch: List[Dict[str, List[UUID]]] = None) -> bool:
        """Record a batch of activity data with cross-collection references.
        
        Args:
            data_batch: List of activity data to record.
            references_batch: List of dictionaries mapping relationship types to lists of target entity IDs.
                              Must be the same length as data_batch.
            
        Returns:
            bool: True if recording was successful, False otherwise.
        """
        if not self.db:
            self.logger.critical("No database connection available")
            sys.exit(1)
        
        # Validate references batch if provided
        if references_batch and len(references_batch) != len(data_batch):
            self.logger.critical(
                f"References batch length ({len(references_batch)}) does not match data batch length ({len(data_batch)})"
            )
            sys.exit(1)
        
        # Process each item in the batch
        modified_batch = []
        for i, data in enumerate(data_batch):
            # Deep copy to avoid modifying the original data
            data_copy = json.loads(json.dumps(data))
            
            # Get or create source entity ID
            source_id = UUID(data.get("id")) if "id" in data else None
            
            # Add references if provided
            if references_batch and source_id and i < len(references_batch):
                references = references_batch[i]
                for relationship_type, target_ids in references.items():
                    for target_id in target_ids:
                        data_copy = self.add_entity_reference(
                            data_copy, 
                            source_id, 
                            target_id, 
                            relationship_type
                        )
            
            modified_batch.append(data_copy)
        
        # Use the standard batch record method to save the modified data
        return super().record_batch(modified_batch)
    
    def get_referenced_entities(self, entity_id: UUID, 
                              relationship_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get entities that are referenced by a specific entity.
        
        Args:
            entity_id: The UUID of the source entity.
            relationship_type: Optional filter for specific relationship types.
            
        Returns:
            List[Dict[str, Any]]: List of referenced entities.
        """
        if not self.db:
            self.logger.critical("No database connection available")
            sys.exit(1)
        
        # Get references from the registry
        references = self.entity_registry.get_entity_references(entity_id, relationship_type)
        
        if not references:
            return []
        
        # Retrieve the referenced entities from their respective collections
        entities = []
        for ref in references:
            try:
                document = self.db.collection(ref.collection_name).get(str(ref.entity_id))
                if document:
                    entities.append(document)
            except Exception as e:
                self.logger.error(f"Error retrieving referenced entity {ref.entity_id} from collection {ref.collection_name}: {e}")
        
        return entities