#!/usr/bin/env python3
"""
Relationship generator.

This module provides the implementation for generating realistic
relationships between metadata records.
"""

import hashlib
import json
import logging
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union, cast

from data_models.base import IndalekoBaseModel
from data_models.record import IndalekoRecordDataModel
from data_models.relationship import IndalekoRelationshipDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from storage.i_relationship import IndalekoRelationship
from db.db_collections import IndalekoDBCollections
from db.db_config import IndalekoDBConfig
from pydantic import Field

from tools.data_generator_enhanced.generators.base import RelationshipGenerator
from tools.data_generator_enhanced.utils.statistical import Distribution


class RelationshipRecord(IndalekoBaseModel):
    """Relationship record model for the relationship collection."""
    
    # Edge collection fields
    _from: str  # Source vertex
    _to: str  # Target vertex
    _key: Optional[str] = None
    
    # Required fields from IndalekoRelationshipDataModel
    Record: Dict[str, Any]  # Contains metadata like timestamps
    Objects: Tuple[str, str]  # The two UUIDs representing the objects in the relationship
    Relationships: List[Dict[str, Any]]  # List of semantic attributes defining the relationship type


class RelationshipGeneratorImpl(RelationshipGenerator):
    """Generator for relationship metadata with direct database integration."""
    
    def __init__(self, config: Dict[str, Any], db_config: Optional[IndalekoDBConfig] = None, seed: Optional[int] = None):
        """Initialize the relationship generator.
        
        Args:
            config: Configuration dictionary for the generator
            db_config: Database configuration for direct insertion
            seed: Optional random seed for reproducible generation
        """
        super().__init__(config, seed)
        
        # Set random seed if provided
        if seed is not None:
            random.seed(seed)
        
        # Initialize database connection
        self.db_config = db_config or IndalekoDBConfig()
        self.db_config.setup_database(self.db_config.config["database"]["database"])
        
        # Make sure the relationship collection exists
        self._ensure_collections_exist()
        
        # Define relationship types
        self.relationship_types = {
            # File-File relationships
            "DERIVED_FROM": {"uuid": str(uuid.uuid4()), "name": "derived_from", "weight": 0.2},
            "CONTAINS": {"uuid": str(uuid.uuid4()), "name": "contains", "weight": 0.2},
            "CONTAINED_BY": {"uuid": str(uuid.uuid4()), "name": "contained_by", "weight": 0.2},
            "RELATED_TO": {"uuid": str(uuid.uuid4()), "name": "related_to", "weight": 0.2},
            "SAME_FOLDER": {"uuid": str(uuid.uuid4()), "name": "same_folder", "weight": 0.1},
            "VERSION_OF": {"uuid": str(uuid.uuid4()), "name": "version_of", "weight": 0.1},
            
            # File-Activity relationships
            "CREATED_AT": {"uuid": str(uuid.uuid4()), "name": "created_at", "weight": 0.3},
            "MODIFIED_AT": {"uuid": str(uuid.uuid4()), "name": "modified_at", "weight": 0.3},
            "ACCESSED_AT": {"uuid": str(uuid.uuid4()), "name": "accessed_at", "weight": 0.3},
            "PLAYING_MUSIC": {"uuid": str(uuid.uuid4()), "name": "playing_music", "weight": 0.05},
            "TEMPERATURE_CONTEXT": {"uuid": str(uuid.uuid4()), "name": "temperature_context", "weight": 0.05},
        }
        
        # Initialize truth list
        self.truth_list = []
    
    def _ensure_collections_exist(self):
        """Ensure the relationship collection exists in the database."""
        try:
            if not self.db_config.db.has_collection(IndalekoDBCollections.Indaleko_Relationship_Collection):
                self.logger.info(f"Creating Relationship collection as an edge collection")
                self.db_config.db.create_collection(
                    IndalekoDBCollections.Indaleko_Relationship_Collection,
                    edge=True  # This is important for ArangoDB to recognize it as an edge collection
                )
        except Exception as e:
            self.logger.error(f"Error ensuring collections exist: {e}")
            raise
    
    def generate(self, count: int) -> List[Dict[str, Any]]:
        """Generate random relationship records.
        
        Args:
            count: Number of relationship records to generate
            
        Returns:
            List of generated relationship records
        """
        try:
            # First, get all available storage, semantic, and activity records from the database
            metadata = self._get_metadata_from_database()
            
            # Generate relationships between these records
            return self.generate_relationships(metadata)
        except Exception as e:
            self.logger.error(f"Error generating relationships: {e}")
            return []
    
    def _get_metadata_from_database(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get metadata records from the database.
        
        Returns:
            Dictionary mapping metadata types to lists of metadata records
        """
        metadata = {
            "storage": [],
            "semantic": [],
            "location": [],
            "music": [],
            "temperature": []
        }
        
        try:
            # Get storage records
            objects_collection = self.db_config.db.collection(IndalekoDBCollections.Indaleko_Object_Collection)
            cursor = self.db_config.db.aql.execute(f"FOR doc IN {IndalekoDBCollections.Indaleko_Object_Collection} RETURN doc")
            metadata["storage"] = [doc for doc in cursor]
            self.logger.info(f"Found {len(metadata['storage'])} storage records")
            
            # Get semantic records
            semantic_collection = self.db_config.db.collection(IndalekoDBCollections.Indaleko_SemanticData_Collection)
            cursor = self.db_config.db.aql.execute(f"FOR doc IN {IndalekoDBCollections.Indaleko_SemanticData_Collection} RETURN doc")
            metadata["semantic"] = [doc for doc in cursor]
            self.logger.info(f"Found {len(metadata['semantic'])} semantic records")
            
            # Get location activity records
            cursor = self.db_config.db.aql.execute(f"FOR doc IN {IndalekoDBCollections.Indaleko_GeoActivityData_Collection} RETURN doc")
            metadata["location"] = [doc for doc in cursor]
            self.logger.info(f"Found {len(metadata['location'])} location records")
            
            # Get music activity records
            cursor = self.db_config.db.aql.execute(f"FOR doc IN {IndalekoDBCollections.Indaleko_MusicActivityData_Collection} RETURN doc")
            metadata["music"] = [doc for doc in cursor]
            self.logger.info(f"Found {len(metadata['music'])} music records")
            
            # Get temperature activity records
            cursor = self.db_config.db.aql.execute(f"FOR doc IN {IndalekoDBCollections.Indaleko_TempActivityData_Collection} RETURN doc")
            metadata["temperature"] = [doc for doc in cursor]
            self.logger.info(f"Found {len(metadata['temperature'])} temperature records")
            
            return metadata
        except Exception as e:
            self.logger.error(f"Error retrieving metadata from database: {e}")
            raise
    
    def generate_relationships(self, metadata: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Generate relationships between metadata records.
        
        Args:
            metadata: Dictionary mapping metadata types to lists of metadata records
            
        Returns:
            List of generated relationship records
        """
        relationships = []
        
        try:
            # Generate file-file relationships between storage records
            file_file_relationships = self._generate_file_file_relationships(metadata["storage"])
            relationships.extend(file_file_relationships)
            self.logger.info(f"Generated {len(file_file_relationships)} file-file relationships")
            
            # Generate file-semantic relationships (connection between files and their semantic metadata)
            file_semantic_relationships = self._generate_file_semantic_relationships(
                metadata["storage"], metadata["semantic"]
            )
            relationships.extend(file_semantic_relationships)
            self.logger.info(f"Generated {len(file_semantic_relationships)} file-semantic relationships")
            
            # Generate file-activity relationships
            file_activity_relationships = self._generate_file_activity_relationships(
                metadata["storage"], 
                metadata["location"], 
                metadata["music"], 
                metadata["temperature"]
            )
            relationships.extend(file_activity_relationships)
            self.logger.info(f"Generated {len(file_activity_relationships)} file-activity relationships")
            
            # Insert all relationship records into the database
            self._insert_relationships(relationships)
            
            return relationships
        except Exception as e:
            self.logger.error(f"Error generating relationships: {e}")
            return []
    
    def _generate_file_file_relationships(self, storage_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate relationships between files.
        
        Args:
            storage_records: List of storage metadata records
            
        Returns:
            List of generated relationship records
        """
        relationships = []
        
        # Ensure we have at least 2 records
        if len(storage_records) < 2:
            self.logger.warning("Not enough storage records to generate file-file relationships")
            return relationships
        
        # Generate a random number of file-file relationships (about 30% of storage records)
        relationship_count = max(1, int(len(storage_records) * 0.3))
        
        for _ in range(relationship_count):
            # Select two random storage records
            source_record, target_record = random.sample(storage_records, 2)
            
            # Determine the relationship type based on weighted probabilities
            relationship_type = self._select_weighted_relationship_type(
                ["DERIVED_FROM", "CONTAINS", "CONTAINED_BY", "RELATED_TO", "SAME_FOLDER", "VERSION_OF"]
            )
            
            # Create the relationship record
            relationship = self._create_relationship_record(
                source_record,
                target_record,
                relationship_type
            )
            
            if relationship:
                relationships.append(relationship)
        
        return relationships
    
    def _generate_file_semantic_relationships(
        self, storage_records: List[Dict[str, Any]], semantic_records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate relationships between files and semantic metadata.
        
        Args:
            storage_records: List of storage metadata records
            semantic_records: List of semantic metadata records
            
        Returns:
            List of generated relationship records
        """
        relationships = []
        
        if not storage_records or not semantic_records:
            self.logger.warning("Not enough records to generate file-semantic relationships")
            return relationships
        
        # For each semantic record, create a relationship to its corresponding storage record
        for semantic_record in semantic_records:
            # Find the corresponding storage record using the Object field
            object_key = semantic_record.get("Object")
            if not object_key:
                continue
                
            # Find the storage record with this key
            source_record = None
            for record in storage_records:
                if record.get("_key") == object_key:
                    source_record = record
                    break
            
            if source_record:
                # Create a related_to relationship
                relationship = self._create_relationship_record(
                    source_record,
                    semantic_record,
                    "RELATED_TO"
                )
                
                if relationship:
                    relationships.append(relationship)
        
        return relationships
    
    def _generate_file_activity_relationships(
        self, 
        storage_records: List[Dict[str, Any]],
        location_records: List[Dict[str, Any]], 
        music_records: List[Dict[str, Any]], 
        temperature_records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate relationships between files and activity metadata.
        
        Args:
            storage_records: List of storage metadata records
            location_records: List of location activity records
            music_records: List of music activity records
            temperature_records: List of temperature activity records
            
        Returns:
            List of generated relationship records
        """
        relationships = []
        
        if not storage_records:
            self.logger.warning("No storage records available for file-activity relationships")
            return relationships
        
        # Process location records
        for location_record in location_records:
            object_key = location_record.get("Object")
            if not object_key:
                continue
                
            # Find the storage record with this key
            source_record = None
            for record in storage_records:
                if record.get("_key") == object_key:
                    source_record = record
                    break
            
            if source_record:
                # Create a created_at relationship (since location often relates to where a file was created)
                relationship = self._create_relationship_record(
                    source_record,
                    location_record,
                    "CREATED_AT"
                )
                
                if relationship:
                    relationships.append(relationship)
        
        # Process music records
        for music_record in music_records:
            object_key = music_record.get("Object")
            if not object_key:
                continue
                
            # Find the storage record with this key
            source_record = None
            for record in storage_records:
                if record.get("_key") == object_key:
                    source_record = record
                    break
            
            if source_record:
                # Create a playing_music relationship
                relationship = self._create_relationship_record(
                    source_record,
                    music_record,
                    "PLAYING_MUSIC"
                )
                
                if relationship:
                    relationships.append(relationship)
        
        # Process temperature records
        for temperature_record in temperature_records:
            object_key = temperature_record.get("Object")
            if not object_key:
                continue
                
            # Find the storage record with this key
            source_record = None
            for record in storage_records:
                if record.get("_key") == object_key:
                    source_record = record
                    break
            
            if source_record:
                # Create a temperature_context relationship
                relationship = self._create_relationship_record(
                    source_record,
                    temperature_record,
                    "TEMPERATURE_CONTEXT"
                )
                
                if relationship:
                    relationships.append(relationship)
        
        return relationships
    
    def _select_weighted_relationship_type(self, allowed_types: List[str]) -> str:
        """Select a relationship type based on weighted probabilities.
        
        Args:
            allowed_types: List of allowed relationship types
            
        Returns:
            Selected relationship type
        """
        # Filter the relationship types to only include allowed types
        filtered_types = {
            rel_type: self.relationship_types[rel_type] 
            for rel_type in allowed_types 
            if rel_type in self.relationship_types
        }
        
        # Extract weights
        weights = [rel_info["weight"] for rel_info in filtered_types.values()]
        
        # Select a type based on weights
        return random.choices(list(filtered_types.keys()), weights=weights, k=1)[0]
    
    def _create_relationship_record(
        self, source_record: Dict[str, Any], target_record: Dict[str, Any], relationship_type: str
    ) -> Optional[Dict[str, Any]]:
        """Create a relationship record between two metadata records.
        
        Args:
            source_record: Source metadata record
            target_record: Target metadata record
            relationship_type: Type of relationship to create
            
        Returns:
            Generated relationship record or None if creation failed
        """
        try:
            # Determine the collection for each record based on its structure
            source_collection = self._determine_collection(source_record)
            target_collection = self._determine_collection(target_record)
            
            if not source_collection or not target_collection:
                self.logger.warning(f"Could not determine collection for records")
                return None
            
            # Create _from and _to fields for the edge
            from_id = f"{source_collection}/{source_record['_key']}"
            to_id = f"{target_collection}/{target_record['_key']}"
            
            # Create a unique key for the relationship
            relationship_key = hashlib.md5(f"{from_id}:{to_id}:{relationship_type}".encode()).hexdigest()
            
            # Create semantic attribute for the relationship
            relationship_info = self.relationship_types.get(relationship_type)
            if not relationship_info:
                self.logger.warning(f"Unknown relationship type: {relationship_type}")
                return None
                
            # Get object identifiers
            source_id = source_record.get("ObjectIdentifier", str(uuid.uuid4()))
            target_id = target_record.get("ObjectIdentifier", str(uuid.uuid4()))
            
            # Create a source identifier for the relationship
            source_identifier = IndalekoSourceIdentifierDataModel(
                SourceIdentifierUUID=str(uuid.uuid4()),
                Source="IndalekoDG",
                Timestamp=datetime.now(timezone.utc).timestamp()
            )
            
            # Create a record for the relationship
            record = IndalekoRecordDataModel(
                RecordUUID=str(uuid.uuid4()),
                SourceIdentifier=source_identifier.dict(),
                Timestamp=datetime.now(timezone.utc).timestamp()
            )
            
            # Create the semantic attribute for the relationship
            semantic_attribute = IndalekoSemanticAttributeDataModel(
                SemanticAttributeUUID=relationship_info["uuid"],
                Name=relationship_info["name"],
                AttributeType="relationship",
                Value=True,
                Timestamp=datetime.now(timezone.utc).timestamp()
            )
            
            # Build the relationship using the approach from storage/recorders/base.py
            relationship = IndalekoRelationship(
                objects=(source_id, target_id),
                relationships=[semantic_attribute.dict()],
                source_id=source_identifier.dict()
            )
            
            # Convert to dictionary format and add edge collection fields
            relationship_dict = relationship.dict()
            relationship_dict["_key"] = relationship_key
            relationship_dict["_from"] = from_id
            relationship_dict["_to"] = to_id
            relationship_dict["Record"] = record.dict()
            
            return relationship_dict
        except Exception as e:
            self.logger.error(f"Error creating relationship record: {e}")
            return None
    
    def _determine_collection(self, record: Dict[str, Any]) -> Optional[str]:
        """Determine the collection name for a record based on its structure.
        
        Args:
            record: Metadata record
            
        Returns:
            Collection name or None if unknown
        """
        # Get the collection from _id if available
        if "_id" in record and "/" in record["_id"]:
            return record["_id"].split("/")[0]
        
        # Check for fields that indicate the record type
        if "MIMEType" in record:
            return IndalekoDBCollections.Indaleko_SemanticData_Collection
        
        if "Path" in record and "Name" in record:
            return IndalekoDBCollections.Indaleko_Object_Collection
        
        if "latitude" in record and "longitude" in record:
            return IndalekoDBCollections.Indaleko_GeoActivityData_Collection
        
        if "artist" in record and "track" in record:
            return IndalekoDBCollections.Indaleko_MusicActivityData_Collection
        
        if "temperature" in record and "device" in record:
            return IndalekoDBCollections.Indaleko_TempActivityData_Collection
        
        return None
    
    def _insert_relationships(self, relationships: List[Dict[str, Any]]) -> None:
        """Insert relationship records into the database.
        
        Args:
            relationships: List of relationship records to insert
        """
        if not relationships:
            self.logger.info("No relationships to insert")
            return
        
        try:
            # Get the relationship collection
            relationship_collection = self.db_config.db.collection(IndalekoDBCollections.Indaleko_Relationship_Collection)
            
            # Insert the relationships
            success_count = 0
            for relationship in relationships:
                try:
                    # Check if the relationship already exists
                    if relationship_collection.get(relationship["_key"]):
                        self.logger.debug(f"Relationship {relationship['_key']} already exists, skipping")
                        continue
                    
                    # Insert the relationship
                    relationship_collection.insert(relationship)
                    success_count += 1
                except Exception as e:
                    self.logger.error(f"Error inserting relationship {relationship.get('_key')}: {e}")
            
            self.logger.info(f"Successfully inserted {success_count} relationships")
        except Exception as e:
            self.logger.error(f"Error inserting relationships: {e}")
    
    def generate_truth(self, count: int, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate truth relationship records based on specific criteria.
        
        Args:
            count: Number of truth records to generate
            criteria: Criteria that the truth records must satisfy
            
        Returns:
            List of generated truth relationship records
        """
        truth_relationships = []
        
        try:
            # Extract criteria for relationship generation
            relationship_criteria = criteria.get("relationship_criteria", {})
            relationship_type = relationship_criteria.get("type", "RELATED_TO")
            
            # Get the source and target keys
            source_keys = criteria.get("source_keys", [])
            target_keys = criteria.get("target_keys", [])
            
            if not source_keys or not target_keys:
                self.logger.warning("Missing source or target keys for truth relationship generation")
                return truth_relationships
            
            # For each source-target pair, create a relationship
            for source_key in source_keys:
                for target_key in target_keys:
                    # Get the source and target records
                    source_record = self._get_record_by_key(source_key)
                    target_record = self._get_record_by_key(target_key)
                    
                    if not source_record or not target_record:
                        continue
                    
                    # Create the relationship
                    relationship = self._create_relationship_record(
                        source_record,
                        target_record,
                        relationship_type
                    )
                    
                    if relationship:
                        truth_relationships.append(relationship)
                        
                        # Add to truth list
                        self.truth_list.append(relationship["_key"])
            
            # Insert the relationships into the database
            self._insert_relationships(truth_relationships)
            
            return truth_relationships
        except Exception as e:
            self.logger.error(f"Error generating truth relationships: {e}")
            return []
    
    def _get_record_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a record from the database by its key.
        
        Args:
            key: Record key
            
        Returns:
            Record or None if not found
        """
        try:
            # Try to find the record in each collection
            collections = [
                IndalekoDBCollections.Indaleko_Object_Collection,
                IndalekoDBCollections.Indaleko_SemanticData_Collection,
                IndalekoDBCollections.Indaleko_GeoActivityData_Collection,
                IndalekoDBCollections.Indaleko_MusicActivityData_Collection,
                IndalekoDBCollections.Indaleko_TempActivityData_Collection
            ]
            
            for collection_name in collections:
                collection = self.db_config.db.collection(collection_name)
                record = collection.get(key)
                if record:
                    return record
            
            self.logger.warning(f"Record with key {key} not found in any collection")
            return None
        except Exception as e:
            self.logger.error(f"Error getting record by key {key}: {e}")
            return None
