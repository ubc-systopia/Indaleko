#!/usr/bin/env python
"""
NTFS Archival Memory Recorder for Indaleko.

This module implements the "Archival Memory" component of the NTFS cognitive memory system,
providing permanent storage of the most significant file system activities.

Features:
- Knowledge-centric permanent storage of highly significant file activities
- Advanced semantic integration and ontology building
- Relationship graph construction for complex entity relationships
- Permanent retention of critical file system knowledge
- Integration with memory consolidation processes

Usage (command-line):
    # Process activities from long-term memory
    python recorder.py --consolidate-from-long-term

    # Generate statistics about archival memory
    python recorder.py --stats

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

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

import hashlib
import logging
import os
import socket
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.storage.data_models.storage_activity_data_model import (
    NtfsStorageActivityData,
    StorageActivityMetadata,
    StorageActivityType,
    StorageProviderType,
)
from activity.collectors.storage.semantic_attributes import StorageActivityAttributes
from activity.recorders.storage.base import StorageActivityRecorder

# Import ServiceManager upfront to avoid late binding issues


# pylint: enable=wrong-import-position


class NtfsArchivalMemoryRecorder(StorageActivityRecorder):
    """
    Archival Memory recorder for NTFS storage activities.

    Handles the permanent storage of highly significant file system activities that have
    persisted through the long-term memory stage, further enriching them with semantic
    meaning and contextual relationships. This implementation models human archival memory,
    which stores information that has lasting significance and provides historical context.

    Features:
    - Semantic enrichment and ontology building
    - Knowledge graph construction for entity relationships
    - Enhanced context preservation
    - Permanent retention of significant knowledge
    - Integration with the memory consolidation process
    """

    # Default settings
    DEFAULT_COLLECTION_NAME = "ntfs_activities_archival"
    DEFAULT_RECORDER_ID = uuid.UUID("d5e93f7c-6912-42ae-b31c-8f9a01d87a4e")
    ENTITY_COLLECTION_NAME = "file_entities"
    LONG_TERM_COLLECTION_NAME = "ntfs_activities_long_term"
    KNOWLEDGE_GRAPH_COLLECTION_NAME = "archival_knowledge_graph"
    IMPORTANCE_THRESHOLD = 0.8  # Higher threshold for archival memory

    def __init__(self, **kwargs: dict) -> None:
        """
        Initialize the archival memory recorder.

        Args:
            kwargs: Additional arguments for the recorder
            collection_name: Name of the archival memory collection
            entity_collection_name: Name of the entity collection
            long_term_collection_name: Name of the long-term memory collection
            importance_threshold: Minimum importance score for activities to be stored
            db_config_path: Path to database configuration
            debug: Whether to enable debug logging
            no_db: Whether to run without database connection
        """
        # Configure logging first
        logging.basicConfig(
            level=logging.DEBUG if kwargs.get("debug", False) else logging.INFO,
        )
        self._logger = logging.getLogger("NtfsArchivalMemoryRecorder")

        # Initialize instance variables
        self._collection_name = kwargs.get(
            "collection_name",
            self.DEFAULT_COLLECTION_NAME,
        )
        self._entity_collection_name = kwargs.get(
            "entity_collection_name",
            self.ENTITY_COLLECTION_NAME,
        )
        self._long_term_collection_name = kwargs.get(
            "long_term_collection_name",
            self.LONG_TERM_COLLECTION_NAME,
        )
        self._importance_threshold = kwargs.get(
            "importance_threshold",
            self.IMPORTANCE_THRESHOLD,
        )
        self._knowledge_graph_collection_name = kwargs.get(
            "knowledge_graph_collection_name",
            self.KNOWLEDGE_GRAPH_COLLECTION_NAME,
        )

        # Set recorder-specific defaults
        kwargs["name"] = kwargs.get("name", "NTFS Archival Memory Recorder")
        kwargs["recorder_id"] = kwargs.get("recorder_id", self.DEFAULT_RECORDER_ID)
        kwargs["provider_type"] = StorageProviderType.LOCAL_NTFS
        kwargs["description"] = kwargs.get(
            "description",
            "Records highly significant NTFS file system activities in archival memory",
        )

        # Use consistent collection name based on recorder ID to avoid conflicts
        if "collection_name" not in kwargs:
            recorder_id_hash = hashlib.md5(  # noqa: S324  - not used for security
                str(kwargs["recorder_id"]).encode(),
            ).hexdigest()
            kwargs["collection_name"] = f"{self._collection_name}_{recorder_id_hash[:8]}"

        # If no_db is specified, disable database connection
        if kwargs.get("no_db", False):
            kwargs["auto_connect"] = False
            self._logger.info("Running without database connection (no_db=True)")

        # Call parent initializer with updated kwargs
        try:
            super().__init__(**kwargs)
        except (ValueError, KeyError, AttributeError):  # Replace with specific exceptions
            self._logger.exception("Error during parent initialization")
            if not kwargs.get("no_db", False):
                raise  # Only re-raise if we're supposed to connect to the database

        # Add NTFS-specific metadata
        try:
            self._metadata = StorageActivityMetadata(
                provider_type=StorageProviderType.LOCAL_NTFS,
                provider_name=self._name,
                source_machine=socket.gethostname(),
                storage_location="archival_memory",
            )
        except Exception as e:
            self._logger.error(f"Error setting up metadata: {e}")
            # Create minimal metadata
            self._metadata = StorageActivityMetadata(
                provider_type=StorageProviderType.LOCAL_NTFS,
                provider_name=self._name,
                source_machine=socket.gethostname(),
            )

        # Set up collections and indices if connected to database
        if hasattr(self, "_db") and self._db:
            self._setup_collections()
            self._setup_indices()

        # Register with activity registration service if enabled
        if self._register_enabled and not kwargs.get("no_db", False):
            self._register_with_service_manager()

    def _register_with_service_manager(self) -> None:
        """Register with the activity service manager."""
        try:
            # Get semantic attributes for storage activity
            from activity.collectors.storage.semantic_attributes import (
                get_storage_activity_semantic_attributes,
            )

            attributes = get_storage_activity_semantic_attributes()
            semantic_attribute_ids = [str(attr.Identifier) for attr in attributes]

            # Import required components
            from activity.recorders.registration_service import (
                IndalekoActivityDataRegistrationService,
            )
            from data_models.record import IndalekoRecordDataModel
            from data_models.source_identifier import IndalekoSourceIdentifierDataModel

            # Create source identifier for the record
            source_identifier = IndalekoSourceIdentifierDataModel(
                SourceID=str(self._recorder_id),
                SourceIdName=self._name,
                SourceDescription=self._description,
                SourceVersion=self._version,
            )

            # Create record data model
            record = IndalekoRecordDataModel(
                SourceId=source_identifier,
                Timestamp=datetime.now(UTC),
                Data={},
            )

            # Add archival memory specific tag to identify this as a cognitive memory recorder
            archival_memory_tag = "archival_memory"

            # Prepare registration data
            registration_kwargs = {
                "Identifier": str(self._recorder_id),
                "Name": self._name,
                "Description": self._description,
                "Version": self._version,
                "Record": record,
                "DataProvider": f"{self._provider_type} Archival Memory Storage Activity",
                "DataProviderType": "Activity",
                "DataProviderSubType": "Storage",
                "DataProviderURL": "",
                "DataProviderCollectionName": self._collection_name,
                "DataFormat": "JSON",
                "DataFormatVersion": "1.0",
                "DataAccess": "Read",
                "DataAccessURL": "",
                "CreateCollection": True,
                "SourceIdentifiers": [
                    str(StorageActivityAttributes.STORAGE_ACTIVITY.value),
                    str(StorageActivityAttributes.STORAGE_NTFS.value),
                ],
                "SchemaIdentifiers": semantic_attribute_ids,
                "Tags": [
                    "storage",
                    "activity",
                    "ntfs",
                    archival_memory_tag,
                    "cognitive_memory",
                ],
            }

            # Register with service manager
            try:
                self._logger.info(
                    f"Registering with activity registration service: {self._recorder_id}",
                )
                service = IndalekoActivityDataRegistrationService()
                service.register_provider(**registration_kwargs)
                self._logger.info(
                    f"Successfully registered with service manager: {self._recorder_id}",
                )
            except Exception as e:
                self._logger.error(f"Error registering with service manager: {e}")
                # Log the error details to help troubleshoot registration issues
                import traceback

                self._logger.debug(
                    f"Registration error details: {traceback.format_exc()}",
                )

        except Exception as e:
            self._logger.error(f"Error creating registration data: {e}")
            import traceback

            self._logger.debug(
                f"Registration data error details: {traceback.format_exc()}",
            )

    def _setup_collections(self):
        """Set up required collections for the archival memory recorder."""
        try:
            # Activities collection should already be created by parent class

            # Ensure entity collection exists
            if not self._db.collection_exists(self._entity_collection_name):
                self._logger.info(
                    f"Creating entity collection: {self._entity_collection_name}",
                )
                entity_collection = self._db.create_collection(
                    self._entity_collection_name,
                )
                self._logger.info(
                    f"Created entity collection: {entity_collection.name}",
                )
            else:
                self._logger.info(
                    f"Entity collection already exists: {self._entity_collection_name}",
                )

            # Create knowledge graph collection if needed (specific to archival memory)
            if not self._db.collection_exists(self._knowledge_graph_collection_name):
                self._logger.info(
                    f"Creating knowledge graph collection: {self._knowledge_graph_collection_name}",
                )
                knowledge_graph_collection = self._db.create_collection(
                    self._knowledge_graph_collection_name,
                    edge=True,
                )
                self._logger.info(
                    f"Created knowledge graph collection: {knowledge_graph_collection.name}",
                )
            else:
                self._logger.info(
                    f"Knowledge graph collection already exists: {self._knowledge_graph_collection_name}",
                )

        except Exception as e:
            self._logger.error(f"Error setting up collections: {e}")
            if not getattr(self, "_no_db", False):
                raise

    def _setup_indices(self):
        """Set up required indices for the archival memory recorder."""
        try:
            # Set up indices for query performance
            self._logger.info("Setting up indices for archival memory...")

            # Index on entity_id for entity-based queries
            self._collection.add_hash_index(
                fields=["Record.Data.entity_id"],
                unique=False,
            )

            # Index on importance_score for consolidated queries
            self._collection.add_hash_index(
                fields=["Record.Data.importance_score"],
                unique=False,
            )

            # Index on activity_type for type-based queries
            self._collection.add_hash_index(
                fields=["Record.Data.activity_types"],
                unique=False,
            )

            # Index on timestamp for time-based queries
            self._collection.add_hash_index(
                fields=["Record.Data.first_seen"],
                unique=False,
            )
            self._collection.add_hash_index(
                fields=["Record.Data.last_activity"],
                unique=False,
            )

            # Index on semantic concepts for concept-based queries
            self._collection.add_hash_index(
                fields=["Record.Data.semantic_concepts"],
                unique=False,
            )

            # Index on ontology concepts for advanced semantic queries
            self._collection.add_hash_index(
                fields=["Record.Data.ontology.concepts"],
                unique=False,
            )

            # Set up indices for knowledge graph collection (if it exists)
            if self._db.collection_exists(self._knowledge_graph_collection_name):
                knowledge_graph_collection = self._db.get_collection(
                    self._knowledge_graph_collection_name,
                )

                # Index on relationship type
                knowledge_graph_collection.add_hash_index(fields=["type"], unique=False)

                # Index on creation date
                knowledge_graph_collection.add_hash_index(
                    fields=["created_at"],
                    unique=False,
                )

                # Index on strength
                knowledge_graph_collection.add_hash_index(
                    fields=["strength"],
                    unique=False,
                )

                # Index on semantic relationship
                knowledge_graph_collection.add_hash_index(
                    fields=["semantic_type"],
                    unique=False,
                )

            self._logger.info("Finished setting up archival memory indices")

        except Exception as e:
            self._logger.error(f"Error setting up indices: {e}")
            if not getattr(self, "_no_db", False):
                raise

    def _get_entity_from_entity_collection(self, entity_id: uuid.UUID) -> dict:
        """
        Get entity information from the entity collection.

        Args:
            entity_id: Entity UUID to look up

        Returns:
            Entity information
        """
        if not hasattr(self, "_db") or self._db is None:
            return {}

        try:
            # Query for the entity in the entity collection
            query = """
                FOR doc IN @@entity_collection
                FILTER doc._key == @entity_id
                LIMIT 1
                RETURN doc
            """

            cursor = self._db._arangodb.aql.execute(
                query,
                bind_vars={
                    "@entity_collection": self._entity_collection_name,
                    "entity_id": str(entity_id),
                },
            )

            # Get the entity
            entity = None
            for doc in cursor:
                entity = doc
                break

            if entity:
                return entity

            return {}

        except Exception as e:
            self._logger.error(f"Error getting entity from entity collection: {e}")
            return {}

    def _get_entity_from_long_term_memory(self, entity_id: uuid.UUID) -> dict:
        """
        Get entity information from long-term memory.

        Args:
            entity_id: Entity UUID to look up

        Returns:
            Entity information from long-term memory
        """
        if not hasattr(self, "_db") or self._db is None:
            return {}

        try:
            # Query for the entity in the long-term memory collection
            query = """
                FOR doc IN @@long_term_collection
                FILTER doc._key == @entity_id
                LIMIT 1
                RETURN doc
            """

            cursor = self._db._arangodb.aql.execute(
                query,
                bind_vars={
                    "@long_term_collection": self._long_term_collection_name,
                    "entity_id": str(entity_id),
                },
            )

            # Get the entity from long-term memory
            entity = None
            for doc in cursor:
                entity = doc
                break

            if entity:
                return entity

            return {}

        except Exception as e:
            self._logger.error(f"Error getting entity from long-term memory: {e}")
            return {}

    def _enhance_ontology(self, w5h_concepts: dict[str, list[str]]) -> dict:
        """
        Enhance the W5H concepts into a more structured ontology.

        This method applies additional semantic processing to create a
        more comprehensive ontology of concepts about the entity.

        Args:
            w5h_concepts: W5H concepts from long-term memory

        Returns:
            Enhanced ontology dictionary
        """
        # Start with the W5H concepts as a foundation
        ontology = {
            "w5h": w5h_concepts,
            "concepts": [],  # Flat list of all concepts (for backward compatibility)
            "relationships": [],  # Semantic relationships between concepts
            "categories": {},  # Higher-level categories
            "inferences": [],  # Inferred concepts not directly in the data
            "annotations": {},  # Additional metadata about concepts
        }

        # Collect all concepts in a flat list (for backward compatibility)
        for dimension, concepts in w5h_concepts.items():
            ontology["concepts"].extend(concepts)

        # Deduplicate
        ontology["concepts"] = list(set(ontology["concepts"]))

        # Identify higher-level categories based on concept patterns
        categories = {}

        # Document types category
        document_concepts = [
            c for c in w5h_concepts.get("what", []) if c in ["document", "report", "memo", "letter", "resume"]
        ]
        if document_concepts:
            categories["document_types"] = document_concepts

        # Code types category
        code_concepts = [
            c for c in w5h_concepts.get("what", []) if c in ["source_code", "python", "javascript", "java", "c_cpp"]
        ]
        if code_concepts:
            categories["code_types"] = code_concepts

        # Media types category
        media_concepts = [c for c in w5h_concepts.get("what", []) if c in ["image", "video", "audio"]]
        if media_concepts:
            categories["media_types"] = media_concepts

        # Location types category
        location_concepts = [
            c
            for c in w5h_concepts.get("where", [])
            if c
            in [
                "documents_folder",
                "desktop",
                "downloads_folder",
                "pictures_folder",
                "videos_folder",
                "music_folder",
            ]
        ]
        if location_concepts:
            categories["location_types"] = location_concepts

        # Usage patterns category
        usage_concepts = [
            c
            for c in w5h_concepts.get("how", [])
            if c
            in [
                "frequently_modified",
                "frequently_accessed",
                "reference_material",
                "active_reference",
                "balanced_usage",
                "work_in_progress",
            ]
        ]
        if usage_concepts:
            categories["usage_patterns"] = usage_concepts

        # Purpose category
        purpose_concepts = [
            c
            for c in w5h_concepts.get("why", [])
            if c
            in [
                "project_work",
                "work_related",
                "personal_use",
                "temporary_use",
                "backup_purpose",
                "high_importance",
                "very_high_importance",
            ]
        ]
        if purpose_concepts:
            categories["purpose"] = purpose_concepts

        # Add to ontology
        ontology["categories"] = categories

        # Generate inferences based on concept combinations
        inferences = []

        # Infer work documents from combinations
        if "work_related" in w5h_concepts.get(
            "why",
            [],
        ) and "document" in w5h_concepts.get("what", []):
            inferences.append("work_document")

        # Infer project code from combinations
        if "project_work" in w5h_concepts.get(
            "why",
            [],
        ) and "source_code" in w5h_concepts.get("what", []):
            inferences.append("project_code")

        # Infer active project from combinations
        if "project_work" in w5h_concepts.get("why", []) and any(
            c in w5h_concepts.get("how", []) for c in ["frequently_modified", "work_in_progress"]
        ):
            inferences.append("active_project")

        # Infer reference material from combinations
        if "reference_material" in w5h_concepts.get("how", []) and any(
            c in w5h_concepts.get("what", []) for c in ["document", "pdf"]
        ):
            inferences.append("reference_document")

        # Add inferences to ontology
        ontology["inferences"] = inferences

        # Generate knowledge relationships
        relationships = []

        # Example: Connect users with file types they work with
        for user in [c for c in w5h_concepts.get("who", []) if c.startswith("user:")]:
            for file_type in w5h_concepts.get("what", []):
                if file_type in ["document", "source_code", "image", "video", "audio"]:
                    relationships.append(
                        {
                            "source": user,
                            "relation": "works_with",
                            "target": file_type,
                            "confidence": 0.8,
                        },
                    )

        # Example: Connect file types with locations
        for file_type in w5h_concepts.get("what", []):
            for location in w5h_concepts.get("where", []):
                if location.endswith("_folder"):
                    relationships.append(
                        {
                            "source": file_type,
                            "relation": "stored_in",
                            "target": location,
                            "confidence": 0.7,
                        },
                    )

        # Add relationships to ontology
        ontology["relationships"] = relationships

        return ontology

    def _build_knowledge_graph_relationships(
        self,
        entity_id: uuid.UUID,
        entity_data: dict,
    ) -> list[dict]:
        """
        Build knowledge graph relationships for the entity.

        This method creates semantic relationships between this entity and others
        to construct a rich knowledge graph for archival memory.

        Args:
            entity_id: Entity UUID
            entity_data: Entity data from long-term memory

        Returns:
            List of knowledge graph relationship dictionaries
        """
        relationships = []

        if not hasattr(self, "_db") or self._db is None:
            return relationships

        try:
            # Extract file path and ontology
            file_path = entity_data.get("Record", {}).get("Data", {}).get("file_path", "")
            volume = entity_data.get("Record", {}).get("Data", {}).get("volume_name", "")
            w5h_concepts = entity_data.get("Record", {}).get("Data", {}).get("w5h_concepts", {})

            if not file_path:
                return relationships

            # Get parent directory
            parent_dir = os.path.dirname(file_path)

            if not parent_dir:
                return relationships

            # Find semantically related entities
            query = """
                FOR doc IN @@collection
                FILTER doc._key != @entity_id
                LET intersection = LENGTH(
                    INTERSECTION(
                        doc.Record.Data.w5h_concepts.what,
                        @what_concepts
                    )
                )
                FILTER intersection > 0
                SORT intersection DESC
                LIMIT 10
                RETURN {
                    "_key": doc._key,
                    "file_path": doc.Record.Data.file_path,
                    "w5h_concepts": doc.Record.Data.w5h_concepts,
                    "intersection_count": intersection
                }
            """

            cursor = self._db._arangodb.aql.execute(
                query,
                bind_vars={
                    "@collection": self._collection_name,
                    "entity_id": str(entity_id),
                    "what_concepts": w5h_concepts.get("what", []),
                },
            )

            # Create semantic relationships
            for related_entity in cursor:
                related_id = related_entity.get("_key", "")
                related_concepts = related_entity.get("w5h_concepts", {})

                if not related_id:
                    continue

                # Calculate semantic similarity
                intersection_count = related_entity.get("intersection_count", 0)
                similarity = min(1.0, intersection_count / 10)

                # Create relationship
                relationship = {
                    "_from": f"{self._collection_name}/{entity_id}",
                    "_to": f"{self._collection_name}/{related_id}",
                    "type": "semantically_related",
                    "semantic_type": "shared_concepts",
                    "strength": similarity,
                    "created_at": datetime.now(UTC).isoformat(),
                    "common_concepts": intersection_count,
                    "description": f"Entities share {intersection_count} common concepts",
                }

                # Add to relationships
                relationships.append(relationship)

            # Find project-related entities
            project_indicators = [c for c in w5h_concepts.get("why", []) if c.startswith("project:")]

            if project_indicators:
                project_query = """
                    FOR doc IN @@collection
                    FILTER doc._key != @entity_id
                    LET project_matches = LENGTH(
                        INTERSECTION(
                            doc.Record.Data.w5h_concepts.why,
                            @project_concepts
                        )
                    )
                    FILTER project_matches > 0
                    SORT project_matches DESC
                    LIMIT 10
                    RETURN {
                        "_key": doc._key,
                        "file_path": doc.Record.Data.file_path,
                        "project_matches": project_matches
                    }
                """

                project_cursor = self._db._arangodb.aql.execute(
                    project_query,
                    bind_vars={
                        "@collection": self._collection_name,
                        "entity_id": str(entity_id),
                        "project_concepts": project_indicators,
                    },
                )

                # Create project relationships
                for related_entity in project_cursor:
                    related_id = related_entity.get("_key", "")

                    if not related_id:
                        continue

                    # Create relationship
                    relationship = {
                        "_from": f"{self._collection_name}/{entity_id}",
                        "_to": f"{self._collection_name}/{related_id}",
                        "type": "project_related",
                        "semantic_type": "same_project",
                        "strength": 0.9,
                        "created_at": datetime.now(UTC).isoformat(),
                        "description": "Entities belong to the same project",
                    }

                    # Add to relationships
                    relationships.append(relationship)

            return relationships

        except Exception as e:
            self._logger.error(f"Error building knowledge graph relationships: {e}")
            return relationships

    def _build_archival_memory_document(
        self,
        entity_id: uuid.UUID,
        entity_data: dict,
        long_term_data: dict,
    ) -> dict:
        """
        Build a document for storing entity in archival memory.

        Args:
            entity_id: Entity UUID
            entity_data: Entity information from entity collection
            long_term_data: Entity data from long-term memory

        Returns:
            Document for the database
        """
        # Extract basic entity information
        long_term_record = long_term_data.get("Record", {})
        long_term_data_dict = long_term_record.get("Data", {})

        # Create basic document with extended lineage tracking
        document = {
            "_key": str(entity_id),  # Use entity ID as document key
            "Label": entity_data.get("file_path", f"Entity {entity_id}"),
            "ProviderID": str(self._recorder_id),
            "Record": {
                "RecordType": "NTFS_ArchivalMemory",
                "SourceId": {
                    "SourceID": str(self._recorder_id),
                    "SourceIdName": self._name,
                    "SourceDescription": self._description,
                    "SourceVersion": self._version,
                },
                "Timestamp": datetime.now(UTC).isoformat(),
                "Attributes": [
                    {
                        "Identifier": str(
                            StorageActivityAttributes.STORAGE_ACTIVITY.value,
                        ),
                        "Label": "Storage Activity",
                        "Description": "Activity related to storage operations",
                    },
                    {
                        "Identifier": str(StorageActivityAttributes.STORAGE_NTFS.value),
                        "Label": "NTFS Storage Activity",
                        "Description": "Storage activity from NTFS file system",
                    },
                    {
                        "Identifier": str(
                            uuid.uuid5(
                                uuid.NAMESPACE_URL,
                                "indaleko:attribute:archival_memory",
                            ),
                        ),
                        "Label": "Archival Memory",
                        "Description": "Activity in the archival memory of the cognitive memory system",
                    },
                ],
                "Data": {
                    "entity_id": str(entity_id),
                    "volume_name": entity_data.get("volume", ""),
                    "file_path": entity_data.get("file_path", ""),
                    "file_name": os.path.basename(entity_data.get("file_path", "")),
                    "is_directory": entity_data.get("is_directory", False),
                    "is_deleted": entity_data.get("deleted", False),
                    "first_seen": entity_data.get(
                        "created_at",
                        datetime.now(UTC).isoformat(),
                    ),
                    "last_modified": entity_data.get(
                        "last_modified",
                        datetime.now(UTC).isoformat(),
                    ),
                    "last_accessed": entity_data.get(
                        "last_accessed",
                        datetime.now(UTC).isoformat(),
                    ),
                    "file_reference_number": entity_data.get(
                        "file_reference_number",
                        "",
                    ),
                    "timestamp": datetime.now(UTC).isoformat(),
                    "last_activity": long_term_data_dict.get(
                        "last_activity",
                        datetime.now(UTC).isoformat(),
                    ),
                    "search_hits": long_term_data_dict.get("search_hits", 0),
                    "consolidation_date": datetime.now(UTC).isoformat(),
                    "memory_type": "archival",
                    # Extended lineage tracking
                    "memory_lineage": {
                        "origin": "sensory_memory",
                        "transitions": [
                            # Include existing transitions from long-term memory
                            *long_term_data_dict.get("memory_lineage", {}).get(
                                "transitions",
                                [],
                            ),
                            # Add new transition to archival memory
                            {
                                "from_tier": "long_term",
                                "to_tier": "archival",
                                "transition_date": datetime.now(
                                    UTC,
                                ).isoformat(),
                                "source_collection": self._long_term_collection_name,
                                "importance_at_transition": long_term_data_dict.get(
                                    "importance_score",
                                    0.0,
                                ),
                            },
                        ],
                        "long_term_id": long_term_data.get("_key", ""),
                        "source_activities": long_term_data_dict.get(
                            "source_activities",
                            [],
                        ),
                        "archival_reason": "high_importance",  # Default reason, could be enhanced
                        "preservation_level": "permanent",
                    },
                },
            },
        }

        # Add activity summary from long-term memory
        activity_summary = long_term_data_dict.get("activity_summary", {})
        document["Record"]["Data"]["activity_summary"] = activity_summary

        # Extract activity types into top-level field for easier querying
        activity_types = list(activity_summary.get("activity_types", {}).keys())
        document["Record"]["Data"]["activity_types"] = activity_types

        # Include W5H concepts from long-term memory
        w5h_concepts = long_term_data_dict.get("w5h_concepts", {})
        document["Record"]["Data"]["w5h_concepts"] = w5h_concepts
        document["Record"]["Data"]["semantic_concepts"] = long_term_data_dict.get(
            "semantic_concepts",
            [],
        )

        # Add extended ontology for archival memory
        ontology = self._enhance_ontology(w5h_concepts)
        document["Record"]["Data"]["ontology"] = ontology

        # Add activity patterns from long-term memory
        activity_patterns = long_term_data_dict.get("activity_patterns", {})
        document["Record"]["Data"]["activity_patterns"] = activity_patterns

        # Add reference to source activities
        document["Record"]["Data"]["source_activities"] = long_term_data_dict.get(
            "source_activities",
            [],
        )

        # Add importance score (slightly enhanced for archival memory)
        importance_score = min(
            1.0,
            long_term_data_dict.get("importance_score", 0.8) * 1.05,
        )
        document["Record"]["Data"]["importance_score"] = importance_score

        # Add enhanced historical context for archival memory
        document["Record"]["Data"]["historical_context"] = {
            "archival_date": datetime.now(UTC).isoformat(),
            "first_seen_date": long_term_data_dict.get("first_seen", ""),
            "activity_span_days": activity_summary.get("activity_span_days", 0),
            "total_activity_count": activity_summary.get("activity_count", 0),
            "preservation_reason": "high_importance",  # Default, could be enhanced with more logic
            "contextual_note": self._generate_contextual_note(
                long_term_data_dict,
                w5h_concepts,
            ),
        }

        # Add knowledge graph integration
        document["Record"]["Data"]["knowledge_graph"] = {
            "relationship_count": 0,  # Will be updated after relationships are created
            "centrality": 0.0,  # Will be calculated based on graph position
            "relationship_types": [],  # Will be populated with types of relationships
        }

        return document

    def _generate_contextual_note(self, entity_data: dict, w5h_concepts: dict) -> str:
        """
        Generate a contextual note about the entity.

        Args:
            entity_data: Entity data dictionary
            w5h_concepts: W5H concepts dictionary

        Returns:
            Contextual note string
        """
        # Extract basic information
        file_name = os.path.basename(entity_data.get("file_path", ""))
        file_path = entity_data.get("file_path", "")
        importance = entity_data.get("importance_score", 0.0)

        # Extract concepts
        what_concepts = w5h_concepts.get("what", [])
        why_concepts = w5h_concepts.get("why", [])
        how_concepts = w5h_concepts.get("how", [])

        # Determine file type description
        file_type = "file"
        for concept in what_concepts:
            if concept in ["document", "image", "video", "audio", "source_code"]:
                file_type = concept
                break

        # Determine importance description
        importance_desc = "significant"
        if importance > 0.9:
            importance_desc = "critical"
        elif importance > 0.8:
            importance_desc = "highly significant"

        # Determine usage pattern
        usage = ""
        for concept in how_concepts:
            if concept in ["frequently_modified", "frequently_accessed"]:
                usage = f"frequently {concept.split('_')[1]}"
                break

        # Determine purpose
        purpose = ""
        for concept in why_concepts:
            if concept in ["project_work", "work_related", "personal_use"]:
                if concept == "project_work":
                    purpose = "project work"
                else:
                    purpose = concept.replace("_", " ")
                break

        # Build contextual note
        note = (
            f"This {file_type} '{file_name}' has been preserved in archival memory due to its {importance_desc} nature"
        )

        if usage:
            note += f" and was {usage}"

        if purpose:
            note += f". It was used for {purpose}"

        note += "."

        # Add additional context if available
        project_indicators = [c for c in why_concepts if c.startswith("project:")]
        if project_indicators:
            project = project_indicators[0].split(":", 1)[1]
            note += f" Associated with the {project} project."

        return note

    def consolidate_from_long_term_memory(
        self,
        min_age_days: int = 90,
        min_importance: float = 0.0,
        entity_limit: int = 100,
    ) -> dict[str, int]:
        """
        Consolidate entities from long-term memory into archival memory.

        Args:
            min_age_days: Minimum age in days for entities to consolidate
            min_importance: Minimum importance score for entities to consolidate
            entity_limit: Maximum number of entities to process

        Returns:
            Dictionary with consolidation statistics
        """
        if not hasattr(self, "_db") or self._db is None:
            return {"error": "Not connected to database"}

        try:
            stats = {
                "entities_processed": 0,
                "entities_consolidated": 0,
                "already_in_archival": 0,
                "below_threshold": 0,
                "errors": 0,
            }

            self._logger.info(
                f"Consolidating entities from long-term memory (min age: {min_age_days} days, min importance: {min_importance})",
            )

            # Find eligible entities in long-term memory using the dedicated method
            from activity.recorders.storage.ntfs.memory.long_term.recorder import (
                NtfsLongTermMemoryRecorder,
            )

            # Try to instantiate a long-term memory recorder to use its methods
            try:
                long_term_recorder = NtfsLongTermMemoryRecorder(no_db=True)
                eligible_entities = long_term_recorder.get_entities_eligible_for_archival(
                    min_importance=self._importance_threshold,
                    min_age_days=min_age_days,
                    limit=entity_limit,
                )
                stats["entities_found"] = len(eligible_entities)
            except Exception as e:
                self._logger.error(
                    f"Error getting eligible entities from long-term memory: {e}",
                )
                # Fall back to direct query
                min_date = (datetime.now(UTC) - timedelta(days=min_age_days)).isoformat()

                query = """
                    FOR doc IN @@long_term_collection
                    FILTER doc.Record.Data.importance_score >= @min_importance
                    FILTER doc.Record.Data.consolidation_date <= @min_date
                    FILTER doc.Record.Data.archival_eligible == true
                    FILTER doc.Record.Data.consolidated_to_archival != true
                    SORT doc.Record.Data.importance_score DESC
                    LIMIT @entity_limit
                    RETURN doc
                """

                cursor = self._db._arangodb.aql.execute(
                    query,
                    bind_vars={
                        "@long_term_collection": self._long_term_collection_name,
                        "min_importance": min_importance,
                        "min_date": min_date,
                        "entity_limit": entity_limit,
                    },
                )

                eligible_entities = list(cursor)
                stats["entities_found"] = len(eligible_entities)

            # Process each eligible entity
            for long_term_entity in eligible_entities:
                entity_id = long_term_entity.get("_key")

                if not entity_id:
                    continue

                stats["entities_processed"] += 1

                try:
                    # Skip if already in archival memory
                    if self._is_in_archival_memory(uuid.UUID(entity_id)):
                        stats["already_in_archival"] += 1

                        # Update the long-term memory record to indicate it's been consolidated
                        self._mark_consolidated_in_long_term(uuid.UUID(entity_id))
                        continue

                    # Get entity information from entity collection
                    entity_data = self._get_entity_from_entity_collection(
                        uuid.UUID(entity_id),
                    )
                    if not entity_data:
                        continue

                    # Check if entity meets importance threshold for archival memory
                    importance_score = long_term_entity.get("Record", {}).get("Data", {}).get("importance_score", 0.0)
                    if importance_score < self._importance_threshold:
                        stats["below_threshold"] += 1
                        continue

                    # Build archival memory document
                    document = self._build_archival_memory_document(
                        uuid.UUID(entity_id),
                        entity_data,
                        long_term_entity,
                    )

                    # Insert into archival memory collection
                    self._collection.insert(document)

                    # Create knowledge graph relationships
                    relationships = self._build_knowledge_graph_relationships(
                        uuid.UUID(entity_id),
                        long_term_entity,
                    )

                    # Store relationships
                    if relationships:
                        knowledge_graph_collection = self._db.get_collection(
                            self._knowledge_graph_collection_name,
                        )

                        for relationship in relationships:
                            try:
                                knowledge_graph_collection.insert(relationship)
                            except Exception as e:
                                self._logger.error(f"Error storing relationship: {e}")

                        # Update relationship count in entity document
                        self._update_knowledge_graph_metadata(
                            uuid.UUID(entity_id),
                            len(relationships),
                            relationships,
                        )

                    # Mark as consolidated in long-term memory
                    self._mark_consolidated_in_long_term(uuid.UUID(entity_id))

                    stats["entities_consolidated"] += 1

                except Exception as e:
                    self._logger.error(f"Error consolidating entity {entity_id}: {e}")
                    stats["errors"] += 1

            self._logger.info(
                f"Consolidation complete: {stats['entities_consolidated']} entities consolidated",
            )

            return stats

        except Exception as e:
            self._logger.error(f"Error consolidating from long-term memory: {e}")
            return {"error": str(e)}

    def _is_in_archival_memory(self, entity_id: uuid.UUID) -> bool:
        """
        Check if an entity is already in archival memory.

        Args:
            entity_id: Entity UUID

        Returns:
            True if entity exists in archival memory
        """
        if not hasattr(self, "_db") or self._db is None:
            return False

        try:
            # Check if document exists
            return self._collection.has(str(entity_id))

        except Exception as e:
            self._logger.error(f"Error checking if entity is in archival memory: {e}")
            return False

    def _mark_consolidated_in_long_term(self, entity_id: uuid.UUID) -> bool:
        """
        Mark an entity as consolidated to archival memory in the long-term memory.

        Args:
            entity_id: Entity UUID

        Returns:
            True if successful
        """
        if not hasattr(self, "_db") or self._db is None:
            return False

        try:
            # Update the document
            query = """
                UPDATE @entity_id WITH {
                    Record: {
                        Data: {
                            consolidated_to_archival: true,
                            consolidation_to_archival_date: @timestamp
                        }
                    }
                } IN @@collection
                RETURN NEW
            """

            self._db._arangodb.aql.execute(
                query,
                bind_vars={
                    "@collection": self._long_term_collection_name,
                    "entity_id": str(entity_id),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            )

            return True

        except Exception as e:
            self._logger.error(
                f"Error marking entity as consolidated in long-term memory: {e}",
            )
            return False

    def _update_knowledge_graph_metadata(
        self,
        entity_id: uuid.UUID,
        count: int,
        relationships: list[dict],
    ) -> bool:
        """
        Update the knowledge graph metadata for an entity.

        Args:
            entity_id: Entity UUID
            count: Number of relationships
            relationships: List of relationship dictionaries

        Returns:
            True if successful
        """
        if not hasattr(self, "_db") or self._db is None:
            return False

        try:
            # Extract relationship types
            relationship_types = list(set(rel.get("type") for rel in relationships))

            # Calculate centrality (basic approximation)
            centrality = min(1.0, count / 20)

            # Update the document
            query = """
                UPDATE @entity_id WITH {
                    Record: {
                        Data: {
                            knowledge_graph: {
                                relationship_count: @count,
                                centrality: @centrality,
                                relationship_types: @relationship_types
                            }
                        }
                    }
                } IN @@collection
                RETURN NEW
            """

            self._db._arangodb.aql.execute(
                query,
                bind_vars={
                    "@collection": self._collection_name,
                    "entity_id": str(entity_id),
                    "count": count,
                    "centrality": centrality,
                    "relationship_types": relationship_types,
                },
            )

            return True

        except Exception as e:
            self._logger.error(f"Error updating knowledge graph metadata: {e}")
            return False

    def get_archival_memory_statistics(self) -> dict[str, Any]:
        """
        Get statistics about the archival memory.

        Returns:
            Dictionary of statistics
        """
        if not hasattr(self, "_db") or self._db is None:
            return {"error": "Not connected to database"}

        try:
            stats = {}

            # Get total count
            count_query = """
                RETURN LENGTH(@@collection)
            """

            count_cursor = self._db._arangodb.aql.execute(
                count_query,
                bind_vars={"@collection": self._collection_name},
            )

            for count in count_cursor:
                stats["total_count"] = count
                break

            # Get count by importance range
            importance_query = """
                FOR doc IN @@collection
                COLLECT importance = FLOOR(doc.Record.Data.importance_score * 10) / 10 WITH COUNT INTO count
                SORT importance ASC
                RETURN { importance, count }
            """

            importance_cursor = self._db._arangodb.aql.execute(
                importance_query,
                bind_vars={"@collection": self._collection_name},
            )

            stats["by_importance"] = {f"{item['importance']:.1f}": item["count"] for item in importance_cursor}

            # Get count by ontology concept
            concept_query = """
                FOR doc IN @@collection
                COLLECT WITH COUNT INTO total
                LET all_concepts = (
                    FOR d IN @@collection
                    FOR concept IN d.Record.Data.ontology.concepts || []
                    RETURN concept
                )
                LET concept_counts = (
                    FOR concept IN all_concepts
                    COLLECT c = concept WITH COUNT INTO count
                    SORT count DESC
                    LIMIT 10
                    RETURN { concept: c, count: count }
                )
                RETURN { total, concept_counts }
            """

            concept_cursor = self._db._arangodb.aql.execute(
                concept_query,
                bind_vars={"@collection": self._collection_name},
            )

            for result in concept_cursor:
                concept_counts = result.get("concept_counts", [])
                stats["by_concept"] = {item["concept"]: item["count"] for item in concept_counts}
                break

            # Get knowledge graph statistics
            knowledge_graph_query = """
                FOR doc IN @@collection
                RETURN AVERAGE(doc.Record.Data.knowledge_graph.relationship_count)
            """

            knowledge_graph_cursor = self._db._arangodb.aql.execute(
                knowledge_graph_query,
                bind_vars={"@collection": self._collection_name},
            )

            for avg_relationships in knowledge_graph_cursor:
                stats["avg_relationships_per_entity"] = avg_relationships
                break

            # Get historical context statistics
            age_query = """
                FOR doc IN @@collection
                LET age = DATE_DIFF(
                    doc.Record.Data.historical_context.archival_date,
                    doc.Record.Data.historical_context.first_seen_date,
                    "day"
                )
                RETURN AVERAGE(age)
            """

            age_cursor = self._db._arangodb.aql.execute(
                age_query,
                bind_vars={"@collection": self._collection_name},
            )

            for avg_age in age_cursor:
                stats["avg_entity_age_days"] = avg_age
                break

            # Get relationship statistics
            if self._db.collection_exists(self._knowledge_graph_collection_name):
                rel_count_query = """
                    RETURN LENGTH(@@collection)
                """

                rel_count_cursor = self._db._arangodb.aql.execute(
                    rel_count_query,
                    bind_vars={"@collection": self._knowledge_graph_collection_name},
                )

                for count in rel_count_cursor:
                    stats["total_relationships"] = count
                    break

                # Get counts by relationship type
                rel_type_query = """
                    FOR doc IN @@collection
                    COLLECT type = doc.type WITH COUNT INTO count
                    SORT count DESC
                    RETURN { type, count }
                """

                rel_type_cursor = self._db._arangodb.aql.execute(
                    rel_type_query,
                    bind_vars={"@collection": self._knowledge_graph_collection_name},
                )

                stats["relationships_by_type"] = {item["type"]: item["count"] for item in rel_type_cursor}

            # Add configuration information
            stats["collection_name"] = self._collection_name
            stats["recorder_id"] = str(self._recorder_id)
            stats["importance_threshold"] = self._importance_threshold

            return stats

        except Exception as e:
            self._logger.error(f"Error getting archival memory statistics: {e}")
            return {"error": str(e)}

    def search_archival_memory(
        self,
        query: str,
        concept_filter: list[str] | None = None,
        w5h_filter: dict[str, list[str]] | None = None,
        importance_min: float = 0.0,
        include_knowledge_graph: bool = False,
        limit: int = 10,
    ) -> list[dict]:
        """
        Search for entities in archival memory with W5H and ontology filtering.

        Args:
            query: Search query
            concept_filter: Optional list of concepts to filter by (legacy)
            w5h_filter: Optional W5H filter dictionary with dimensions as keys and concepts as values
            importance_min: Minimum importance score
            include_knowledge_graph: Whether to include knowledge graph relationships
            limit: Maximum number of results

        Returns:
            List of matching entities
        """
        if not hasattr(self, "_db") or self._db is None:
            return []

        try:
            # Build query based on parameters
            if w5h_filter:
                # Search with W5H model filtering
                filter_conditions = []
                w5h_bind_vars = {}

                # Build W5H filter conditions
                for i, (dimension, concepts) in enumerate(w5h_filter.items()):
                    if dimension in ["who", "what", "when", "where", "why", "how"] and concepts:
                        filter_conditions.append(
                            f"LENGTH(INTERSECTION(doc.Record.Data.w5h_concepts.{dimension}, @{dimension}_concepts)) > 0",
                        )
                        w5h_bind_vars[f"{dimension}_concepts"] = concepts

                # Build the complete query
                w5h_filter_str = " AND ".join(filter_conditions) if filter_conditions else "true"

                search_query = f"""
                    FOR doc IN @@collection
                    FILTER CONTAINS(LOWER(doc.Record.Data.file_path), LOWER(@query)) OR
                           CONTAINS(LOWER(doc.Record.Data.file_name), LOWER(@query))
                    FILTER doc.Record.Data.importance_score >= @importance_min
                    FILTER {w5h_filter_str}
                    SORT doc.Record.Data.importance_score DESC
                    LIMIT @limit
                    RETURN doc
                """

                # Combine all bind variables
                bind_vars = {
                    "@collection": self._collection_name,
                    "query": query.lower(),
                    "importance_min": importance_min,
                    "limit": limit,
                }
                bind_vars.update(w5h_bind_vars)

                cursor = self._db._arangodb.aql.execute(
                    search_query,
                    bind_vars=bind_vars,
                )

            elif concept_filter:
                # Search with concept filter (using ontology concepts for richer search)
                search_query = """
                    FOR doc IN @@collection
                    FILTER CONTAINS(LOWER(doc.Record.Data.file_path), LOWER(@query)) OR
                           CONTAINS(LOWER(doc.Record.Data.file_name), LOWER(@query))
                    FILTER doc.Record.Data.importance_score >= @importance_min
                    FILTER LENGTH(INTERSECTION(doc.Record.Data.ontology.concepts, @concepts)) > 0
                    SORT doc.Record.Data.importance_score DESC
                    LIMIT @limit
                    RETURN doc
                """

                cursor = self._db._arangodb.aql.execute(
                    search_query,
                    bind_vars={
                        "@collection": self._collection_name,
                        "query": query.lower(),
                        "importance_min": importance_min,
                        "concepts": concept_filter,
                        "limit": limit,
                    },
                )
            else:
                # Basic search without concept filter
                search_query = """
                    FOR doc IN @@collection
                    FILTER CONTAINS(LOWER(doc.Record.Data.file_path), LOWER(@query)) OR
                           CONTAINS(LOWER(doc.Record.Data.file_name), LOWER(@query))
                    FILTER doc.Record.Data.importance_score >= @importance_min
                    SORT doc.Record.Data.importance_score DESC
                    LIMIT @limit
                    RETURN doc
                """

                cursor = self._db._arangodb.aql.execute(
                    search_query,
                    bind_vars={
                        "@collection": self._collection_name,
                        "query": query.lower(),
                        "importance_min": importance_min,
                        "limit": limit,
                    },
                )

            # Get results
            results = []
            for doc in cursor:
                # If requested, include knowledge graph relationships
                if include_knowledge_graph:
                    doc["knowledge_graph_relationships"] = self.get_knowledge_graph_relationships(
                        uuid.UUID(doc["_key"]),
                        limit=5,
                    )

                results.append(doc)

            return results

        except Exception as e:
            self._logger.error(f"Error searching archival memory: {e}")
            return []

    def get_knowledge_graph_relationships(
        self,
        entity_id: uuid.UUID,
        relationship_type: str | None = None,
        semantic_type: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """
        Get knowledge graph relationships for the specified entity.

        Args:
            entity_id: Entity UUID
            relationship_type: Optional relationship type filter
            semantic_type: Optional semantic type filter
            limit: Maximum number of results

        Returns:
            List of relationships
        """
        if not hasattr(self, "_db") or self._db is None:
            return []

        try:
            # Build query based on parameters
            filter_conditions = [
                "rel._from == CONCAT(@collection, '/', @entity_id) OR rel._to == CONCAT(@collection, '/', @entity_id)",
            ]

            if relationship_type:
                filter_conditions.append("rel.type == @relationship_type")

            if semantic_type:
                filter_conditions.append("rel.semantic_type == @semantic_type")

            # Build the complete query
            filter_str = " AND ".join(filter_conditions)

            query = f"""
                FOR rel IN @@knowledge_graph_collection
                FILTER {filter_str}
                LET other_id = rel._from == CONCAT(@collection, "/", @entity_id) ?
                               SUBSTRING(rel._to, LENGTH(@collection) + 1) :
                               SUBSTRING(rel._from, LENGTH(@collection) + 1)
                LET other_entity = DOCUMENT(CONCAT(@collection, other_id))
                SORT rel.strength DESC
                LIMIT @limit
                RETURN {{
                    "entity": other_entity,
                    "relationship": rel
                }}
            """

            # Prepare bind variables
            bind_vars = {
                "@knowledge_graph_collection": self._knowledge_graph_collection_name,
                "@collection": self._collection_name,
                "entity_id": str(entity_id),
                "limit": limit,
            }

            if relationship_type:
                bind_vars["relationship_type"] = relationship_type

            if semantic_type:
                bind_vars["semantic_type"] = semantic_type

            cursor = self._db._arangodb.aql.execute(query, bind_vars=bind_vars)

            # Get results
            results = []
            for item in cursor:
                results.append(item)

            return results

        except Exception as e:
            self._logger.error(f"Error getting knowledge graph relationships: {e}")
            return []

    def get_recorder_name(self) -> str:
        """
        Get the name of the recorder.

        Returns:
            The recorder name
        """
        return self._name

    def get_recorder_id(self) -> uuid.UUID:
        """
        Get the ID of the recorder.

        Returns:
            The recorder UUID
        """
        return self._recorder_id

    def get_description(self) -> str:
        """
        Get a description of this recorder.

        Returns:
            The recorder description
        """
        return self._description

    def get_recorder_characteristics(self) -> list[ActivityDataCharacteristics]:
        """
        Get the characteristics of this recorder.

        Returns:
            List of activity data characteristics
        """
        result = [
            ActivityDataCharacteristics.ACTIVITY_DATA_SYSTEM_ACTIVITY,
            ActivityDataCharacteristics.ACTIVITY_DATA_FILE_ACTIVITY,
        ]

        # Add Windows-specific characteristic if available
        try:
            result.append(ActivityDataCharacteristics.ACTIVITY_DATA_WINDOWS_SPECIFIC)
        except AttributeError:
            # Windows-specific characteristic not defined, possibly using an older version
            self._logger.warning(
                "ACTIVITY_DATA_WINDOWS_SPECIFIC characteristic not available",
            )

        return result

    def get_collector_class_model(self) -> dict[str, type]:
        """
        Get the class models for the collector(s) used by this recorder.

        This method returns a dictionary mapping collector names to their types,
        which is used for type checking and serialization.

        Returns:
            Dictionary mapping collector names to types
        """
        # Import the necessary classes for the collector model
        from activity.collectors.storage.data_models.storage_activity_data_model import (
            NtfsStorageActivityData,
            StorageItemType,
            StorageProviderType,
        )
        from activity.collectors.storage.ntfs.ntfs_collector import (
            NtfsStorageActivityCollector,
        )
        from activity.collectors.storage.ntfs.ntfs_collector_v2 import (
            NtfsStorageActivityCollectorV2,
        )

        return {
            "NtfsStorageActivityCollector": NtfsStorageActivityCollector,
            "NtfsStorageActivityCollectorV2": NtfsStorageActivityCollectorV2,
            "NtfsStorageActivityData": NtfsStorageActivityData,
            "StorageActivityType": StorageActivityType,
            "StorageProviderType": StorageProviderType,
            "StorageItemType": StorageItemType,
        }

    def get_json_schema(self) -> dict:
        """
        Get the JSON schema for this recorder's data.

        Returns:
            The JSON schema
        """
        return NtfsStorageActivityData.model_json_schema()

    def cache_duration(self) -> timedelta:
        """
        Get the cache duration for this recorder's data.

        Archival memory data changes very infrequently, so we use a long cache duration.

        Returns:
            The cache duration
        """
        return timedelta(days=7)

    def get_cursor(self, activity_context: uuid.UUID) -> uuid.UUID:
        """
        Get a cursor for the provided activity context.

        This is used for tracking position in data streams.

        Args:
            activity_context: The activity context

        Returns:
            A cursor UUID
        """
        # Generate a deterministic cursor based on current time and context
        cursor_seed = f"{activity_context}:{int(time.time() / (3600 * 24 * 30))}"  # Changes monthly
        cursor_hash = hashlib.md5(cursor_seed.encode()).hexdigest()
        return uuid.UUID(cursor_hash)

    def get_latest_db_update(self) -> dict[str, Any]:
        """
        Get the latest data update information from the database.

        Returns:
            Information about the latest update
        """
        if not hasattr(self, "_db") or self._db is None:
            return {"error": "Not connected to database"}

        try:
            # Query for the most recent entity
            query = """
                FOR doc IN @@collection
                SORT doc.Record.Timestamp DESC
                LIMIT 1
                RETURN {
                    entity_id: doc._key,
                    file_path: doc.Record.Data.file_path,
                    consolidation_date: doc.Record.Data.consolidation_date,
                    importance_score: doc.Record.Data.importance_score,
                    relationship_count: doc.Record.Data.knowledge_graph.relationship_count,
                    historical_context: doc.Record.Data.historical_context
                }
            """

            cursor = self._db._arangodb.aql.execute(
                query,
                bind_vars={"@collection": self._collection_name},
            )

            # Return the first result, or empty dict if no results
            try:
                latest = next(cursor)

                # Add archival memory information
                latest["memory_type"] = "archival"

                return latest
            except StopIteration:
                return {
                    "memory_type": "archival",
                    "status": "empty",
                    "message": "No entities in archival memory",
                }

        except Exception as e:
            self._logger.error(f"Error getting latest update: {e}")
            return {"memory_type": "archival", "error": str(e)}


# Command-line interface
if __name__ == "__main__":
    import argparse
    import sys

    # Configure command-line interface
    parser = argparse.ArgumentParser(
        description="NTFS Archival Memory Recorder",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Add general arguments
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    # Add operation mode arguments
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--consolidate-from-long-term",
        action="store_true",
        help="Consolidate entities from long-term memory",
    )
    mode_group.add_argument(
        "--stats",
        action="store_true",
        help="Show statistics about archival memory",
    )
    mode_group.add_argument(
        "--search",
        type=str,
        help="Search for entities by name or path",
    )

    # Add consolidation options
    parser.add_argument(
        "--min-age-days",
        type=int,
        default=90,
        help="Minimum age in days for entities to consolidate",
    )
    parser.add_argument(
        "--min-importance",
        type=float,
        default=0.8,
        help="Minimum importance score for entities to consolidate",
    )
    parser.add_argument(
        "--entity-limit",
        type=int,
        default=100,
        help="Maximum number of entities to process",
    )

    # Add search options
    parser.add_argument(
        "--concept-filter",
        type=str,
        help="Comma-separated list of concepts to filter search results",
    )

    # Add database options
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Run without database connection",
    )
    parser.add_argument(
        "--db-config",
        type=str,
        default=None,
        help="Path to database configuration file",
    )

    # Parse arguments
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("NtfsArchivalMemoryRecorder")

    try:
        # Create recorder
        recorder = NtfsArchivalMemoryRecorder(
            debug=args.debug,
            no_db=args.no_db,
            db_config_path=args.db_config,
        )

        # Execute requested operation
        if args.consolidate_from_long_term:
            print("=== Consolidating from Long-Term Memory ===")
            result = recorder.consolidate_from_long_term_memory(
                min_age_days=args.min_age_days,
                min_importance=args.min_importance,
                entity_limit=args.entity_limit,
            )

            print("\nConsolidation Results:")
            for key, value in result.items():
                print(f"  {key}: {value}")

        elif args.stats:
            print("=== Archival Memory Statistics ===")
            stats = recorder.get_archival_memory_statistics()

            if "error" in stats:
                print(f"Error: {stats['error']}")
            else:
                print(f"  Total entities: {stats.get('total_count', 0)}")

                if "avg_relationships_per_entity" in stats:
                    print(
                        f"  Avg relationships per entity: {stats.get('avg_relationships_per_entity', 0):.1f}",
                    )

                if "avg_entity_age_days" in stats:
                    print(
                        f"  Avg entity age (days): {stats.get('avg_entity_age_days', 0):.1f}",
                    )

                if "by_importance" in stats:
                    print("\nEntities by importance score:")
                    for importance, count in stats["by_importance"].items():
                        print(f"  {importance}: {count}")

                if "by_concept" in stats:
                    print("\nTop ontology concepts:")
                    for concept, count in stats["by_concept"].items():
                        print(f"  {concept}: {count}")

                if "relationships_by_type" in stats:
                    print("\nRelationship types:")
                    for rel_type, count in stats["relationships_by_type"].items():
                        print(f"  {rel_type}: {count}")

                print("\nConfiguration:")
                print(f"  Collection name: {stats.get('collection_name', 'unknown')}")
                print(
                    f"  Importance threshold: {stats.get('importance_threshold', 'unknown')}",
                )

        elif args.search:
            concept_filter = args.concept_filter.split(",") if args.concept_filter else None

            print(f'=== Searching Archival Memory for "{args.search}" ===')
            if concept_filter:
                print(f"Filtering by concepts: {', '.join(concept_filter)}")

            results = recorder.search_archival_memory(
                args.search,
                concept_filter=concept_filter,
                importance_min=args.min_importance,
                include_knowledge_graph=True,
            )

            print(f"\nFound {len(results)} results:")
            for i, entity in enumerate(results):
                data = entity.get("Record", {}).get("Data", {})
                print(f"\nResult {i+1}:")
                print(f"  File: {data.get('file_name', 'Unknown')}")
                print(f"  Path: {data.get('file_path', 'Unknown')}")
                print(f"  Importance: {data.get('importance_score', 0.0):.2f}")

                # Show ontology concepts
                ontology = data.get("ontology", {})
                concepts = ontology.get("concepts", [])
                if concepts:
                    print(f"  Ontology concepts: {', '.join(concepts[:5])}")

                # Show inferences
                inferences = ontology.get("inferences", [])
                if inferences:
                    print(f"  Inferences: {', '.join(inferences)}")

                # Show historical context
                historical = data.get("historical_context", {})
                if historical:
                    print("  Historical context:")
                    print(
                        f"    First seen: {historical.get('first_seen_date', 'Unknown')}",
                    )
                    print(
                        f"    Activity span: {historical.get('activity_span_days', 0)} days",
                    )
                    print(f"    Note: {historical.get('contextual_note', '')}")

                # Show knowledge graph relationships if available
                if entity.get("knowledge_graph_relationships"):
                    print("  Related entities:")
                    for j, rel in enumerate(entity["knowledge_graph_relationships"]):
                        related_entity = rel.get("entity", {})
                        relationship = rel.get("relationship", {})
                        related_path = related_entity.get("Record", {}).get("Data", {}).get("file_path", "Unknown")

                        print(
                            f"    {j+1}. {os.path.basename(related_path)} ({relationship.get('type', 'related')})",
                        )

    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        print(f"Unhandled error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    print("\nDone.")
