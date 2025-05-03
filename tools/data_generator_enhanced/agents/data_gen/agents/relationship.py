"""
Relationship generator agent.

This module provides an agent for generating realistic relationship
records between different metadata types in the Indaleko system.
"""

import json
import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from db.db_collections import IndalekoDBCollections
from data_models.relationship import IndalekoRelationshipDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel

from ..core.llm import LLMProvider
from ..core.tools import ToolRegistry
from .base import DomainAgent


class RelationshipGeneratorAgent(DomainAgent):
    """Agent for generating relationship metadata."""
    
    def __init__(self, llm_provider: LLMProvider, tool_registry: ToolRegistry, config: Optional[Dict[str, Any]] = None):
        """Initialize the relationship generator agent.
        
        Args:
            llm_provider: LLM provider instance
            tool_registry: Tool registry instance
            config: Optional agent configuration
        """
        super().__init__(llm_provider, tool_registry, config)
        self.collection_name = IndalekoDBCollections.Indaleko_Relationship_Collection
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Relationship types and their weights (probability distribution)
        self.relationship_types = {
            "CONTAINS": 0.25,
            "DERIVED_FROM": 0.15,
            "RELATED_TO": 0.20,
            "MODIFIED_BY": 0.15,
            "ACCESSED_BY": 0.10,
            "CREATED_BY": 0.10,
            "OWNED_BY": 0.05
        }
        
        # Source identifiers for relationship creation
        self.source_identifiers = [
            "storage_indexer",
            "semantic_processor",
            "activity_monitor",
            "user_interaction",
            "relationship_discovery",
            "cross_device_sync"
        ]
    
    def generate(self, count: int, criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate relationship records.
        
        Args:
            count: Number of records to generate
            criteria: Optional criteria for generation
            
        Returns:
            List of generated records
        """
        self.logger.info(f"Generating {count} relationship records")
        
        # If we need to generate relationships between existing objects
        if criteria and ("objects" in criteria or "storage_objects" in criteria or 
                         "semantic_objects" in criteria or "activity_objects" in criteria):
            return self._generate_from_existing_objects(count, criteria)
        
        # Use direct generation for small counts
        if count <= 100:
            return self._direct_generation(count, criteria)
        
        # Use LLM-powered generation for larger counts or complex criteria
        instruction = f"Generate {count} realistic relationship records"
        if criteria:
            instruction += f" matching these criteria: {json.dumps(criteria)}"
        
        input_data = {
            "count": count,
            "criteria": criteria or {},
            "config": self.config,
            "collection_name": self.collection_name
        }
        
        # Generate in batches to avoid overwhelming the LLM
        results = []
        batch_size = min(count, 50)
        remaining = count
        
        while remaining > 0:
            current_batch = min(batch_size, remaining)
            self.logger.info(f"Generating batch of {current_batch} relationship records")
            
            # Update input data for this batch
            batch_input = input_data.copy()
            batch_input["count"] = current_batch
            
            # Run the agent
            response = self.run(instruction, batch_input)
            
            # Extract the generated records
            if "actions" in response:
                for action in response["actions"]:
                    if action["tool"] == "database_insert" or action["tool"] == "database_bulk_insert":
                        # If records were inserted directly, we need to query them
                        tool = self.tools.get_tool("database_query")
                        if tool:
                            query_result = tool.execute({
                                "query": f"FOR doc IN {self.collection_name} SORT RAND() LIMIT {current_batch} RETURN doc"
                            })
                            results.extend(query_result)
            
            remaining -= current_batch
        
        return results
    
    def _generate_from_existing_objects(self, count: int, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate relationship records between existing objects.
        
        Args:
            count: Number of records to generate
            criteria: Criteria containing object lists
            
        Returns:
            List of generated relationship records
        """
        self.logger.info("Generating relationships from existing objects")
        
        # Get object lists from criteria
        objects = criteria.get("objects", [])
        storage_objects = criteria.get("storage_objects", [])
        semantic_objects = criteria.get("semantic_objects", [])
        activity_objects = criteria.get("activity_objects", [])
        
        # If we have storage and semantic objects, prioritize linking those
        if storage_objects and semantic_objects:
            self.logger.info(f"Creating relationships between {len(storage_objects)} storage objects and {len(semantic_objects)} semantic objects")
            storage_semantic_pairs = self._match_storage_semantic_pairs(storage_objects, semantic_objects)
            
            # Create relationships for these pairs
            storage_semantic_relations = []
            for storage_obj, semantic_obj in storage_semantic_pairs:
                rel_type = "HAS_SEMANTIC_DATA"
                relationship = self._create_relationship_record(storage_obj, semantic_obj, rel_type)
                if relationship:
                    storage_semantic_relations.append(relationship)
            
            remaining = count - len(storage_semantic_relations)
            
            # If we've satisfied the count, return the relationships
            if remaining <= 0:
                return storage_semantic_relations[:count]
            
            # Otherwise, continue with other relationships
            relationships = storage_semantic_relations
        else:
            remaining = count
            relationships = []
        
        # If we have storage and activity objects, create relationships between them
        if storage_objects and activity_objects and remaining > 0:
            self.logger.info(f"Creating relationships between storage objects and activity objects")
            count_to_generate = min(remaining, len(storage_objects) * 2, len(activity_objects) * 2)
            
            for _ in range(count_to_generate):
                storage_obj = random.choice(storage_objects)
                activity_obj = random.choice(activity_objects)
                
                # Determine relationship type based on activity type
                rel_type = self._determine_activity_relationship_type(activity_obj)
                
                relationship = self._create_relationship_record(storage_obj, activity_obj, rel_type)
                if relationship:
                    relationships.append(relationship)
            
            remaining = count - len(relationships)
            
            # If we've satisfied the count, return the relationships
            if remaining <= 0:
                return relationships[:count]
        
        # If we have general objects or still need more relationships, create generic relationships
        if objects and remaining > 0:
            self.logger.info(f"Creating relationships between generic objects")
            
            # Combine all objects if not enough in the general list
            if len(objects) < 10:
                all_objects = objects + storage_objects + semantic_objects + activity_objects
                objects = all_objects
            
            # Generate random relationships between objects
            for _ in range(remaining):
                obj1, obj2 = random.sample(objects, 2)
                rel_type = self._weighted_relationship_type()
                
                relationship = self._create_relationship_record(obj1, obj2, rel_type)
                if relationship:
                    relationships.append(relationship)
        
        # If we still don't have enough relationships, create some with direct generation
        if len(relationships) < count:
            remaining = count - len(relationships)
            direct_rels = self._direct_generation(remaining, criteria)
            relationships.extend(direct_rels)
        
        return relationships[:count]
    
    def _match_storage_semantic_pairs(self, storage_objects: List[Dict[str, Any]], 
                                     semantic_objects: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """Match storage objects with their corresponding semantic objects.
        
        Args:
            storage_objects: List of storage objects
            semantic_objects: List of semantic objects
            
        Returns:
            List of matched (storage, semantic) object pairs
        """
        # Use ObjectIdentifier to match objects
        pairs = []
        
        # Create a mapping of ObjectIdentifier to semantic object
        semantic_map = {}
        for semantic_obj in semantic_objects:
            obj_id = semantic_obj.get("ObjectIdentifier")
            if obj_id:
                semantic_map[obj_id] = semantic_obj
        
        # For each storage object, find a matching semantic object
        for storage_obj in storage_objects:
            obj_id = storage_obj.get("ObjectIdentifier")
            if obj_id and obj_id in semantic_map:
                pairs.append((storage_obj, semantic_map[obj_id]))
        
        # If we don't have enough pairs, create some random ones
        if len(pairs) < min(len(storage_objects), len(semantic_objects)) // 2:
            random_storage = random.sample(storage_objects, min(10, len(storage_objects)))
            random_semantic = random.sample(semantic_objects, min(10, len(semantic_objects)))
            
            for i in range(min(len(random_storage), len(random_semantic))):
                pair = (random_storage[i], random_semantic[i])
                if pair not in pairs:
                    pairs.append(pair)
        
        return pairs
    
    def _determine_activity_relationship_type(self, activity_obj: Dict[str, Any]) -> str:
        """Determine the relationship type based on the activity type.
        
        Args:
            activity_obj: Activity object
            
        Returns:
            Relationship type
        """
        activity_type = activity_obj.get("ActivityType", "")
        
        if "FileCreation" in activity_type:
            return "CREATED_BY"
        elif "FileEdit" in activity_type:
            return "MODIFIED_BY"
        elif "FileAccess" in activity_type:
            return "ACCESSED_BY"
        elif "FileShare" in activity_type:
            return "SHARED_BY"
        else:
            return "RELATED_TO"
    
    def _weighted_relationship_type(self) -> str:
        """Get a relationship type based on the configured weights.
        
        Returns:
            Relationship type
        """
        rel_types = list(self.relationship_types.keys())
        weights = list(self.relationship_types.values())
        
        return random.choices(rel_types, weights=weights, k=1)[0]
    
    def _direct_generation(self, count: int, criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate relationship records directly without LLM.
        
        Args:
            count: Number of records to generate
            criteria: Optional criteria for generation
            
        Returns:
            List of generated records
        """
        self.logger.info(f"Direct generation of {count} relationship records")
        
        # First, we need to get or generate objects to relate
        objects = self._get_or_generate_objects(count * 2, criteria)
        
        if len(objects) < 2:
            self.logger.warning("Not enough objects to create relationships")
            return []
        
        relationships = []
        
        # Generate relationship records
        for _ in range(count):
            # Select two random objects
            object1, object2 = random.sample(objects, 2)
            
            # Determine relationship type
            rel_type = criteria.get("relationship_type") if criteria and "relationship_type" in criteria else self._weighted_relationship_type()
            
            # Create relationship record
            relationship = self._create_relationship_record(object1, object2, rel_type)
            if relationship:
                relationships.append(relationship)
        
        # Store the records if needed
        if self.config.get("store_directly", False):
            bulk_tool = self.tools.get_tool("database_bulk_insert")
            if bulk_tool:
                bulk_tool.execute({
                    "collection": self.collection_name,
                    "documents": relationships,
                    "edge": True
                })
        
        return relationships
    
    def _get_or_generate_objects(self, count: int, criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get existing objects or generate new ones.
        
        Args:
            count: Number of objects needed
            criteria: Optional criteria for generation
            
        Returns:
            List of objects
        """
        # If criteria specifies objects, use those
        if criteria:
            objects = criteria.get("objects", [])
            if objects:
                return objects
        
        # Otherwise, query for objects from the database
        tool = self.tools.get_tool("database_query")
        if not tool:
            self.logger.warning("Database query tool not available")
            return self._generate_placeholder_objects(count)
        
        # Try to get objects from the storage collection
        try:
            object_results = tool.execute({
                "query": f"FOR doc IN {IndalekoDBCollections.Indaleko_Object_Collection} SORT RAND() LIMIT {count} RETURN doc"
            })
            
            if object_results and len(object_results) >= 2:
                return object_results
        except Exception as e:
            self.logger.error(f"Error querying objects: {str(e)}")
        
        # If that fails, generate placeholder objects
        return self._generate_placeholder_objects(count)
    
    def _generate_placeholder_objects(self, count: int) -> List[Dict[str, Any]]:
        """Generate placeholder objects for relationships.
        
        Args:
            count: Number of objects to generate
            
        Returns:
            List of placeholder objects
        """
        objects = []
        
        for i in range(count):
            obj_id = str(uuid.uuid4())
            obj_type = random.choice(["File", "Directory", "Document", "Image", "User"])
            
            obj = {
                "_id": f"{IndalekoDBCollections.Indaleko_Object_Collection}/{obj_id}",
                "_key": obj_id,
                "ObjectIdentifier": obj_id,
                "Label": f"{obj_type}_{i}",
                "Type": obj_type
            }
            
            objects.append(obj)
        
        return objects
    
    def _create_relationship_record(self, source_obj: Dict[str, Any], target_obj: Dict[str, Any], 
                                  relationship_type: str) -> Optional[Dict[str, Any]]:
        """Create a relationship record between two objects.
        
        Args:
            source_obj: Source object
            target_obj: Target object
            relationship_type: Type of relationship
            
        Returns:
            Relationship record or None if creation failed
        """
        # Get object IDs
        source_id = source_obj.get("_id", "")
        target_id = target_obj.get("_id", "")
        
        # If _id is not available, try to create it from _key or ObjectIdentifier
        if not source_id:
            if "_key" in source_obj:
                source_id = f"{IndalekoDBCollections.Indaleko_Object_Collection}/{source_obj['_key']}"
            elif "ObjectIdentifier" in source_obj:
                source_id = f"{IndalekoDBCollections.Indaleko_Object_Collection}/{source_obj['ObjectIdentifier']}"
            elif "Handle" in source_obj:  # For activity objects
                source_id = f"{IndalekoDBCollections.Indaleko_ActivityContext_Collection}/{source_obj['Handle']}"
            else:
                source_id = f"{IndalekoDBCollections.Indaleko_Object_Collection}/{str(uuid.uuid4())}"
        
        if not target_id:
            if "_key" in target_obj:
                target_id = f"{IndalekoDBCollections.Indaleko_Object_Collection}/{target_obj['_key']}"
            elif "ObjectIdentifier" in target_obj:
                target_id = f"{IndalekoDBCollections.Indaleko_Object_Collection}/{target_obj['ObjectIdentifier']}"
            elif "Handle" in target_obj:  # For activity objects
                target_id = f"{IndalekoDBCollections.Indaleko_ActivityContext_Collection}/{target_obj['Handle']}"
            else:
                target_id = f"{IndalekoDBCollections.Indaleko_Object_Collection}/{str(uuid.uuid4())}"
        
        # Create a relationship UUID
        relationship_id = str(uuid.uuid4())
        
        # Create timestamp
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Create source identifier
        source_identifier = {
            "Source": random.choice(self.source_identifiers),
            "CreationTime": timestamp,
            "LastUpdateTime": timestamp
        }
        
        # Create semantic attribute for the relationship
        semantic_attribute = {
            "Name": relationship_type,
            "Source": source_identifier["Source"],
            "Confidence": random.uniform(0.7, 1.0)
        }
        
        # Create the relationship record
        relationship = {
            "_key": relationship_id,
            "_from": source_id,
            "_to": target_id,
            "objects": [source_id, target_id],
            "relationships": [semantic_attribute],
            "source_id": source_identifier
        }
        
        return relationship
    
    def generate_truth(self, count: int, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate truth relationship records with specific characteristics.
        
        Args:
            count: Number of truth records to generate
            criteria: Criteria that the truth records must satisfy
            
        Returns:
            List of generated truth records
        """
        self.logger.info(f"Generating {count} truth relationship records with criteria: {criteria}")
        
        # We need objects for the relationships
        objects = criteria.get("objects", [])
        
        # If no objects provided, try to get the ones specified by their IDs
        if not objects and "object_ids" in criteria:
            tool = self.tools.get_tool("database_query")
            if tool:
                object_ids = criteria["object_ids"]
                object_id_list = ", ".join([f'"{obj_id}"' for obj_id in object_ids])
                
                objects = tool.execute({
                    "query": f"""
                    FOR doc IN {IndalekoDBCollections.Indaleko_Object_Collection}
                    FILTER doc.ObjectIdentifier IN [{object_id_list}]
                    RETURN doc
                    """
                })
        
        # If still no objects or not enough, get or generate some
        if not objects or len(objects) < 2:
            objects = self._get_or_generate_objects(count * 2, criteria)
        
        if len(objects) < 2:
            self.logger.warning("Not enough objects to create truth relationships")
            return []
        
        # Create relationship records
        relationships = []
        relationship_type = criteria.get("relationship_type", self._weighted_relationship_type())
        
        for i in range(count):
            # For truth records, create deterministic pairs of objects
            idx1 = i % len(objects)
            idx2 = (i + 1) % len(objects)
            
            object1 = objects[idx1]
            object2 = objects[idx2]
            
            relationship = self._create_relationship_record(object1, object2, relationship_type)
            if relationship:
                relationships.append(relationship)
                
                # Track the truth records
                self.truth_list.append(relationship["_key"])
        
        # Store truth characteristics for later verification
        self.state["truth_criteria"] = criteria
        self.state["truth_count"] = len(relationships)
        self.state["truth_ids"] = self.truth_list
        
        # Store the records if needed
        if self.config.get("store_directly", False):
            bulk_tool = self.tools.get_tool("database_bulk_insert")
            if bulk_tool:
                bulk_tool.execute({
                    "collection": self.collection_name,
                    "documents": relationships,
                    "edge": True
                })
        
        return relationships
    
    def _build_context(self, instruction: str, input_data: Optional[Dict[str, Any]] = None) -> str:
        """Build the context for the LLM.
        
        Args:
            instruction: The instruction for the agent
            input_data: Optional input data
            
        Returns:
            Context string for the LLM
        """
        context = f"""
        You are a specialized agent for generating realistic relationship records between entities in the Indaleko system.
        
        Your task: {instruction}
        
        Generate relationship metadata that follows these guidelines:
        1. Create meaningful connections between different types of objects
        2. Use appropriate relationship types based on the nature of the connected objects
        3. Include proper timestamps and source identifiers
        4. Ensure all records have required fields for database insertion
        
        Relationship records should include the following fields:
        - _key: Unique identifier for the relationship
        - _from: The source entity document ID
        - _to: The target entity document ID
        - objects: Array of exactly two entity IDs [source_id, target_id]
        - relationships: Array of semantic attributes describing the relationship
        - source_id: Source identifier information
        
        Common relationship types include:
        - CONTAINS: Hierarchical containment (folder contains file)
        - DERIVED_FROM: One object is derived from another (PDF generated from DOCX)
        - RELATED_TO: General relationship between objects
        - MODIFIED_BY: Object modified by a user or activity
        - ACCESSED_BY: Object accessed by a user or activity
        - CREATED_BY: Object created by a user or activity
        - OWNED_BY: Object ownership
        
        """
        
        if input_data:
            # Don't include the full objects in the context to avoid token limits
            input_data_copy = input_data.copy()
            
            for field in ["objects", "storage_objects", "semantic_objects", "activity_objects"]:
                if field in input_data_copy.get("criteria", {}):
                    objects_count = len(input_data_copy["criteria"][field])
                    input_data_copy["criteria"][field] = f"[{objects_count} objects available]"
            
            context += f"Input data: {json.dumps(input_data_copy, indent=2)}\n\n"
        
        # Add tips for specific criteria if provided
        if input_data and "criteria" in input_data and input_data["criteria"]:
            context += "Special instructions for the criteria:\n"
            
            for key, value in input_data["criteria"].items():
                if key == "relationship_type":
                    context += f"- All relationships should be of type '{value}'\n"
                elif key in ["objects", "storage_objects", "semantic_objects", "activity_objects"]:
                    # Skip handled above
                    pass
                elif key != "object_ids":
                    context += f"- Apply the criterion '{key}': '{value}'\n"
        
        # If we have objects, provide instructions for using them
        object_provided = False
        for field in ["objects", "storage_objects", "semantic_objects", "activity_objects"]:
            if input_data and "criteria" in input_data and field in input_data["criteria"]:
                context += f"\nYou have {field} available. Create relationships between these objects using appropriate relationship types.\n"
                object_provided = True
        
        if not object_provided:
            context += "\nYou need to create objects or query existing ones to establish relationships between them.\n"
        
        # If generating truth records, add special instructions
        if input_data and input_data.get("truth", False):
            context += "\nIMPORTANT: You are generating TRUTH records. These records must EXACTLY match the criteria provided. These records will be used for testing and validation, so their properties must match the criteria precisely.\n"
        
        return context