"""
Schema extraction module for the Indaleko database.

This module provides functions to extract collection and relationship
information from the ArangoDB database used by Indaleko.

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

import logging
import os
import sys

from pathlib import Path
from typing import Any


# Add the root directory to the path to ensure imports work correctly
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from db.db_config import IndalekoDBConfig


# pylint: enable=wrong-import-position

# Collection type constants
DOCUMENT_COLLECTION = "document"
EDGE_COLLECTION = "edge"

# Collection descriptions - to be expanded
COLLECTION_DESCRIPTIONS = {
    "Objects": "Core storage for file and object metadata",
    "SemanticData": "Semantic enrichment metadata for objects",
    "NamedEntities": "Named entity storage for identity resolution",
    "Relationships": "Edge collection linking related objects",
    "ActivityContext": "Activity context data for user actions",
    "TempActivityContext": "Temperature-related activity context",
    "GeoActivityContext": "Geographic location activity context",
    "MusicActivityContext": "Music listening activity context",
    "EntityEquivalenceGroups": "Groups of equivalent entity identifiers",
    "EntityEquivalenceNodes": "Individual entity equivalence nodes",
    "EntityEquivalenceRelations": "Relationships between equivalent entities",
    "QueryHistory": "History of user queries to the system",
    "ActivityDataProviders": "Data providers for activity information",
    "Services": "Service definitions and metadata",
    "MachineConfig": "Machine configuration information",
    "Users": "User information and settings",
    "IdentityDomains": "Domain definitions for identities",
    "CollectionMetadata": "Metadata about database collections",
    "PerformanceData": "System performance measurements",
    "FeedbackRecords": "User feedback and ratings",
    "LearningEvents": "System learning event records",
    "KnowledgePatterns": "Learned knowledge patterns",
    "ArchivistMemory": "Archivist conversation and memory data",
}


def extract_collections() -> list[dict[str, Any]]:
    """
    Extract collection information from the ArangoDB database.

    Returns:
        A list of dictionaries containing collection information, with
        each dictionary having the following keys:
        - name: The name of the collection
        - type: The type of collection (document or edge)
        - description: A description of the collection's purpose
        - indexes: A list of indexes defined for the collection
        - count: The number of documents in the collection
    """
    logging.info("Connecting to ArangoDB...")
    try:
        db_config = IndalekoDBConfig()
        db = db_config.get_arangodb()
    except Exception as e:
        logging.exception(f"Failed to connect to ArangoDB: {e}")
        return []

    collections_info = []

    try:
        # Get all collections from ArangoDB
        logging.debug("Retrieving collections from ArangoDB...")
        collections = db.collections()

        # Filter out system collections
        user_collections = [c for c in collections if not c["name"].startswith("_")]

        for collection in user_collections:
            collection_name = collection["name"]
            logging.debug(f"Processing collection: {collection_name}")

            # Determine collection type
            collection_type = EDGE_COLLECTION if collection["type"] == 3 else DOCUMENT_COLLECTION

            # Get collection information
            collection_obj = db.collection(collection_name)

            # Get indexes
            try:
                indexes = collection_obj.indexes()
            except Exception as e:
                logging.warning(f"Failed to get indexes for {collection_name}: {e}")
                indexes = []

            # Get document count
            try:
                count = collection_obj.count()
            except Exception as e:
                logging.warning(f"Failed to get document count for {collection_name}: {e}")
                count = 0

            # Get description
            description = COLLECTION_DESCRIPTIONS.get(
                collection_name,
                f"{collection_type.capitalize()} collection",
            )

            # If it's an ActivityProviderData collection with UUID, use a generic description
            if collection_name.startswith("ActivityProviderData_"):
                description = "Activity data for a specific provider"

            collections_info.append({
                "name": collection_name,
                "type": collection_type,
                "description": description,
                "indexes": indexes,
                "count": count,
            })

        logging.info(f"Extracted information for {len(collections_info)} collections")
        return collections_info

    except Exception as e:
        logging.exception(f"Error extracting collections: {e}")
        return []


def extract_relationships(collections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Extract relationships between collections.

    Args:
        collections: List of collection information as returned by extract_collections()

    Returns:
        A list of dictionaries representing relationships, with each dictionary
        having the following keys:
        - from: The source collection name
        - to: The target collection name
        - type: The type of relationship (e.g., "contains", "references")
        - description: A description of the relationship
    """
    logging.info("Extracting relationships between collections...")
    relationships = []

    try:
        db_config = IndalekoDBConfig()
        db_config.get_arangodb()
    except Exception as e:
        logging.exception(f"Failed to connect to ArangoDB: {e}")
        return []

    # Find edge collections
    edge_collections = [c for c in collections if c["type"] == EDGE_COLLECTION]

    # Extract relationships from edge collections
    for edge_collection in edge_collections:
        collection_name = edge_collection["name"]
        logging.debug(f"Processing edge collection: {collection_name}")

        try:
            # For most edge collections, we would examine a sample of documents to find
            # the _from and _to collections, but we'll use predefined relationships for now
            if collection_name == "Relationships":
                # Core relationships
                relationships.extend([
                    {
                        "from": "Relationships",
                        "to": "Objects",
                        "type": "contains",
                        "description": "Relationship contains or links objects",
                    },
                    {
                        "from": "Relationships",
                        "to": "NamedEntities",
                        "type": "references",
                        "description": "Relationship references named entities",
                    },
                ])
            elif collection_name == "EntityEquivalenceRelations":
                # Entity equivalence relationships
                relationships.extend([
                    {
                        "from": "EntityEquivalenceGroups",
                        "to": "EntityEquivalenceRelations",
                        "type": "connects",
                        "description": "Group connects through relations",
                    },
                    {
                        "from": "EntityEquivalenceNodes",
                        "to": "EntityEquivalenceRelations",
                        "type": "connects",
                        "description": "Node connects through relations",
                    },
                ])
        except Exception as e:
            logging.warning(f"Failed to process relationships for {collection_name}: {e}")

    # Add known semantic relationships that aren't strictly edge-based
    semantic_relationships = [
        {
            "from": "SemanticData",
            "to": "Objects",
            "type": "enriches",
            "description": "Semantic data enriches objects",
        },
        {
            "from": "ActivityContext",
            "to": "Objects",
            "type": "contextualizes",
            "description": "Activity context provides context for objects",
        },
        {
            "from": "ActivityContext",
            "to": "TempActivityContext",
            "type": "specializes",
            "description": "Temperature activity extends base activity",
        },
        {
            "from": "ActivityContext",
            "to": "GeoActivityContext",
            "type": "specializes",
            "description": "Geographic activity extends base activity",
        },
        {
            "from": "ActivityContext",
            "to": "MusicActivityContext",
            "type": "specializes",
            "description": "Music activity extends base activity",
        },
        {
            "from": "NamedEntities",
            "to": "EntityEquivalenceGroups",
            "type": "groups",
            "description": "Entities are grouped by equivalence",
        },
        {
            "from": "ActivityDataProviders",
            "to": "ActivityContext",
            "type": "provides",
            "description": "Providers supply activity context data",
        },
        {
            "from": "QueryHistory",
            "to": "PerformanceData",
            "type": "generates",
            "description": "Queries generate performance data",
        },
        {
            "from": "QueryHistory",
            "to": "LearningEvents",
            "type": "triggers",
            "description": "Queries trigger learning events",
        },
        {
            "from": "Users",
            "to": "IdentityDomains",
            "type": "belongs-to",
            "description": "Users belong to identity domains",
        },
        {
            "from": "Users",
            "to": "FeedbackRecords",
            "type": "provides",
            "description": "Users provide feedback records",
        },
        {
            "from": "LearningEvents",
            "to": "KnowledgePatterns",
            "type": "creates",
            "description": "Learning events create knowledge patterns",
        },
        {
            "from": "ArchivistMemory",
            "to": "QueryHistory",
            "type": "enhances",
            "description": "Archivist memory enhances query history",
        },
    ]
    relationships.extend(semantic_relationships)

    logging.info(f"Extracted {len(relationships)} relationships between collections")
    return relationships


def extract_collection_schema(collection_name: str) -> dict[str, Any]:
    """
    Extract schema information for a specific collection.

    Args:
        collection_name: The name of the collection to extract schema for

    Returns:
        A dictionary containing schema information, with fields and their types
    """
    logging.info(f"Extracting schema for collection: {collection_name}")

    try:
        db_config = IndalekoDBConfig()
        db = db_config.get_arangodb()

        # Get a sample document from the collection
        query = f"FOR doc IN {collection_name} LIMIT 1 RETURN doc"
        cursor = db.aql.execute(query)

        # Extract schema from the sample document
        schema = {}

        for document in cursor:
            _extract_schema_from_document(document, schema)
            break  # Only process the first document

        return schema

    except Exception as e:
        logging.exception(f"Failed to extract schema for {collection_name}: {e}")
        return {}


def _extract_schema_from_document(document: dict[str, Any], schema: dict[str, Any], prefix: str = "") -> None:
    """
    Helper function to recursively extract schema from a document.

    Args:
        document: The document to extract schema from
        schema: The schema dictionary to update
        prefix: Prefix for nested fields
    """
    for key, value in document.items():
        # Skip internal ArangoDB fields
        if key.startswith("_"):
            continue

        field_name = f"{prefix}{key}" if prefix else key

        if isinstance(value, dict):
            schema[field_name] = "object"
            _extract_schema_from_document(value, schema, f"{field_name}.")
        elif isinstance(value, list):
            if value and all(isinstance(item, dict) for item in value):
                schema[field_name] = "array[object]"
                # Process the first item to get schema of array items
                _extract_schema_from_document(value[0], schema, f"{field_name}[].")
            else:
                schema[field_name] = "array"
        else:
            schema[field_name] = type(value).__name__
