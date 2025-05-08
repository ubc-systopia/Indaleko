"""
Entity manager for the ablation study framework.

This module provides functionality for managing named entities
in the synthetic data generation process, ensuring consistent
entity references across queries and metadata.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Union

try:
    from db.db_config import IndalekoDBConfig
except ImportError:
    # Mock implementation for standalone testing
    class IndalekoDBConfig:
        """Mock DB config for standalone testing."""

        def get_arangodb(self):
            """Get a mock ArangoDB connection."""
            return MockArangoDB()

class MockArangoDB:
    """Mock ArangoDB for standalone testing."""

    def __init__(self):
        """Initialize the mock database."""
        self.collections = {}
        self.aql = self

    def execute(self, query, bind_vars=None):
        """Execute a mock AQL query."""
        return []

    def create_collection(self, name):
        """Create a mock collection."""
        self.collections[name] = []
        return {"name": name}

    def collection(self, name):
        """Get a mock collection."""
        if name not in self.collections:
            self.collections[name] = []
        return MockCollection(self.collections[name])

class MockCollection:
    """Mock collection for standalone testing."""

    def __init__(self, data):
        """Initialize the mock collection."""
        self.data = data

    def insert(self, document):
        """Insert a document into the mock collection."""
        self.data.append(document)
        return {"_id": str(uuid.uuid4())}

    def update(self, document_key, document):
        """Update a document in the mock collection."""
        for i, doc in enumerate(self.data):
            if doc.get("_key") == document_key:
                self.data[i].update(document)
                return {"_id": doc.get("_id")}
        return None


class EntityManager:
    """Manager for named entities.

    This class manages named entities in the synthetic data generation process,
    ensuring consistent entity references across queries and metadata.
    """

    def __init__(self, collection_name: str = "AblationNamedEntities"):
        """Initialize the entity manager.

        Args:
            collection_name: Name of the collection to store entities in
        """
        self.collection_name = collection_name
        self.logger = logging.getLogger(__name__)

        try:
            self.db_config = IndalekoDBConfig()
            self.db = self.db_config.get_arangodb()

            # Create the entity collection if it doesn't exist
            collections = self.db.collections()
            collection_names = [c["name"] for c in collections]

            if self.collection_name not in collection_names:
                self.db.create_collection(self.collection_name)
        except Exception as e:
            self.logger.error(f"Error connecting to database: {e}")
            self.db = None

        # In-memory cache for entities
        self.entity_cache = {}

    def get_entity(self, name: str, entity_type: str) -> Optional[Dict[str, Any]]:
        """Get a named entity by name and type.

        Args:
            name: The name of the entity
            entity_type: The type of the entity

        Returns:
            Entity dictionary if found, None otherwise
        """
        # Check cache first
        cache_key = f"{name}:{entity_type}"
        if cache_key in self.entity_cache:
            return self.entity_cache[cache_key]

        try:
            if self.db:
                query = f"""
                FOR doc IN {self.collection_name}
                FILTER doc.name == @name AND doc.entity_type == @entity_type
                LIMIT 1
                RETURN doc
                """

                cursor = self.db.aql.execute(query, bind_vars={
                    "name": name,
                    "entity_type": entity_type
                })

                results = list(cursor)

                if results:
                    # Cache the result
                    self.entity_cache[cache_key] = results[0]
                    return results[0]

            return None
        except Exception as e:
            self.logger.error(f"Error getting entity: {e}")
            return None

    def add_entity(self, name: str, entity_type: str,
                  attributes: Dict[str, Any]) -> str:
        """Add a new named entity.

        Args:
            name: The name of the entity
            entity_type: The type of the entity
            attributes: Dictionary of entity attributes

        Returns:
            Identifier for the added entity
        """
        # Check if the entity already exists
        existing_entity = self.get_entity(name, entity_type)
        if existing_entity:
            return existing_entity["_id"]

        # Generate a unique ID
        entity_id = str(uuid.uuid4())

        entity_record = {
            "_key": entity_id,
            "id": entity_id,
            "name": name,
            "entity_type": entity_type,
            "attributes": attributes,
            "references": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        try:
            if self.db:
                collection = self.db.collection(self.collection_name)
                result = collection.insert(entity_record)

                # Cache the entity
                cache_key = f"{name}:{entity_type}"
                self.entity_cache[cache_key] = entity_record
                self.entity_cache[cache_key]["_id"] = result["_id"]

                return result["_id"]
            else:
                self.logger.warning("Database not available, entity not added")
                return entity_id
        except Exception as e:
            self.logger.error(f"Error adding entity: {e}")
            return entity_id

    def update_entity(self, entity_id: str,
                     attributes: Dict[str, Any]) -> bool:
        """Update an existing entity.

        Args:
            entity_id: The identifier for the entity
            attributes: Dictionary of updated attributes

        Returns:
            True if the update succeeded, False otherwise
        """
        try:
            if self.db:
                query = f"""
                FOR doc IN {self.collection_name}
                FILTER doc._key == @entity_id
                LIMIT 1
                RETURN doc
                """

                cursor = self.db.aql.execute(query, bind_vars={
                    "entity_id": entity_id
                })

                results = list(cursor)

                if results:
                    entity = results[0]
                    entity["attributes"].update(attributes)
                    entity["updated_at"] = datetime.now(timezone.utc).isoformat()

                    collection = self.db.collection(self.collection_name)
                    collection.update(entity["_key"], {
                        "attributes": entity["attributes"],
                        "updated_at": entity["updated_at"]
                    })

                    # Update cache
                    cache_key = f"{entity['name']}:{entity['entity_type']}"
                    if cache_key in self.entity_cache:
                        self.entity_cache[cache_key] = entity

                    return True

                return False
            else:
                self.logger.warning("Database not available, entity not updated")
                return False
        except Exception as e:
            self.logger.error(f"Error updating entity: {e}")
            return False

    def add_reference(self, entity_id: str, reference_id: str) -> bool:
        """Add a reference to an entity.

        Args:
            entity_id: The identifier for the entity
            reference_id: The identifier for the reference

        Returns:
            True if the reference was added, False otherwise
        """
        try:
            if self.db:
                query = f"""
                FOR doc IN {self.collection_name}
                FILTER doc._key == @entity_id
                LIMIT 1
                RETURN doc
                """

                cursor = self.db.aql.execute(query, bind_vars={
                    "entity_id": entity_id
                })

                results = list(cursor)

                if results:
                    entity = results[0]

                    # Add reference if it doesn't exist
                    references = entity.get("references", [])
                    if reference_id not in references:
                        references.append(reference_id)

                        collection = self.db.collection(self.collection_name)
                        collection.update(entity["_key"], {
                            "references": references,
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        })

                        # Update cache
                        cache_key = f"{entity['name']}:{entity['entity_type']}"
                        if cache_key in self.entity_cache:
                            self.entity_cache[cache_key]["references"] = references

                    return True

                return False
            else:
                self.logger.warning("Database not available, reference not added")
                return False
        except Exception as e:
            self.logger.error(f"Error adding reference: {e}")
            return False

    def get_entities_by_type(self, entity_type: str) -> List[Dict[str, Any]]:
        """Get all entities of a specific type.

        Args:
            entity_type: The type of entities to retrieve

        Returns:
            List of entity dictionaries
        """
        try:
            if self.db:
                query = f"""
                FOR doc IN {self.collection_name}
                FILTER doc.entity_type == @entity_type
                RETURN doc
                """

                cursor = self.db.aql.execute(query, bind_vars={
                    "entity_type": entity_type
                })

                return list(cursor)
            else:
                self.logger.warning("Database not available, entities not retrieved")
                return []
        except Exception as e:
            self.logger.error(f"Error getting entities by type: {e}")
            return []

    def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity.

        Args:
            entity_id: The identifier for the entity to delete

        Returns:
            True if the deletion succeeded, False otherwise
        """
        try:
            if self.db:
                query = f"""
                FOR doc IN {self.collection_name}
                FILTER doc._key == @entity_id
                REMOVE doc IN {self.collection_name}
                RETURN OLD
                """

                cursor = self.db.aql.execute(query, bind_vars={
                    "entity_id": entity_id
                })

                results = list(cursor)

                if results:
                    # Remove from cache
                    entity = results[0]
                    cache_key = f"{entity['name']}:{entity['entity_type']}"
                    if cache_key in self.entity_cache:
                        del self.entity_cache[cache_key]

                    return True

                return False
            else:
                self.logger.warning("Database not available, entity not deleted")
                return False
        except Exception as e:
            self.logger.error(f"Error deleting entity: {e}")
            return False

    def get_or_create_entity(self, name: str, entity_type: str,
                            attributes: Dict[str, Any]) -> str:
        """Get an entity by name and type, or create it if it doesn't exist.

        Args:
            name: The name of the entity
            entity_type: The type of the entity
            attributes: Dictionary of entity attributes

        Returns:
            Identifier for the entity
        """
        entity = self.get_entity(name, entity_type)

        if entity:
            # Update attributes if provided
            if attributes:
                self.update_entity(entity["_key"], attributes)

            return entity["_id"]
        else:
            return self.add_entity(name, entity_type, attributes)

    def save_entities(self, output_path: Path) -> None:
        """Save all entities to a file.

        Args:
            output_path: Path to save the entities to
        """
        try:
            if self.db:
                query = f"""
                FOR doc IN {self.collection_name}
                RETURN doc
                """

                cursor = self.db.aql.execute(query)
                results = list(cursor)

                with open(output_path, 'w') as f:
                    json.dump(results, f, indent=2)
            else:
                self.logger.warning("Database not available, entities not saved")
        except Exception as e:
            self.logger.error(f"Error saving entities: {e}")

    def load_entities(self, input_path: Path) -> None:
        """Load entities from a file.

        Args:
            input_path: Path to load the entities from
        """
        try:
            if self.db:
                with open(input_path, 'r') as f:
                    entities = json.load(f)

                collection = self.db.collection(self.collection_name)

                for entity in entities:
                    # Convert _key to string if it's not already
                    if "_key" in entity and not isinstance(entity["_key"], str):
                        entity["_key"] = str(entity["_key"])

                    try:
                        collection.insert(entity)

                        # Update cache
                        cache_key = f"{entity['name']}:{entity['entity_type']}"
                        self.entity_cache[cache_key] = entity
                    except Exception as e:
                        self.logger.error(f"Error inserting entity: {e}")
            else:
                self.logger.warning("Database not available, entities not loaded")
        except Exception as e:
            self.logger.error(f"Error loading entities: {e}")

    def clear_entities(self) -> None:
        """Clear all entities from the collection."""
        try:
            if self.db:
                query = f"""
                FOR doc IN {self.collection_name}
                REMOVE doc IN {self.collection_name}
                """

                self.db.aql.execute(query)

                # Clear cache
                self.entity_cache = {}
            else:
                self.logger.warning("Database not available, entities not cleared")
        except Exception as e:
            self.logger.error(f"Error clearing entities: {e}")

    def get_entity_count(self) -> int:
        """Get the number of entities in the collection.

        Returns:
            Number of entities
        """
        try:
            if self.db:
                query = f"""
                RETURN LENGTH({self.collection_name})
                """

                cursor = self.db.aql.execute(query)
                results = list(cursor)

                if results:
                    return results[0]

                return 0
            else:
                self.logger.warning("Database not available, entity count not available")
                return 0
        except Exception as e:
            self.logger.error(f"Error getting entity count: {e}")
            return 0
