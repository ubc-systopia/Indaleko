"""
Database tools for data generation agents.

This module provides tools for interacting with the ArangoDB database,
including querying, inserting, and validating data.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from db.db_config import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections

from ..core.tools import Tool


class DatabaseQueryTool(Tool):
    """Tool for querying the database."""

    def __init__(self, db_config: IndalekoDBConfig):
        """Initialize the database query tool.

        Args:
            db_config: Database configuration
        """
        super().__init__(
            name="database_query",
            description="Query the database using AQL"
        )
        self.db_config = db_config

    def execute(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute the tool with provided parameters.

        Args:
            parameters: Tool parameters
                - query: AQL query string
                - bind_vars: Optional query parameters

        Returns:
            Query results
        """
        query = parameters.get("query")
        if not query:
            raise ValueError("Query parameter is required")

        bind_vars = parameters.get("bind_vars", {})

        self.logger.debug(f"Executing query: {query}")
        try:
            cursor = self.db_config.db.aql.execute(query, bind_vars=bind_vars)
            results = list(cursor)
            self.logger.debug(f"Query returned {len(results)} results")
            return results
        except Exception as e:
            self.logger.error(f"Error executing query: {str(e)}")
            raise

    def get_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for this tool.

        Returns:
            Tool schema description
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "AQL query string"
                        },
                        "bind_vars": {
                            "type": "object",
                            "description": "Query parameters"
                        }
                    },
                    "required": ["query"]
                }
            }
        }


class DatabaseInsertTool(Tool):
    """Tool for inserting documents into the database."""

    def __init__(self, db_config: IndalekoDBConfig):
        """Initialize the database insert tool.

        Args:
            db_config: Database configuration
        """
        super().__init__(
            name="database_insert",
            description="Insert documents into a database collection"
        )
        self.db_config = db_config

    def execute(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute the tool with provided parameters.

        Args:
            parameters: Tool parameters
                - collection: Collection name
                - documents: Documents to insert
                - overwrite: Whether to overwrite existing documents

        Returns:
            Insertion results
        """
        collection_name = parameters.get("collection")
        if not collection_name:
            raise ValueError("Collection parameter is required")

        documents = parameters.get("documents", [])
        if not documents:
            return []

        overwrite = parameters.get("overwrite", False)

        self.logger.debug(f"Inserting {len(documents)} documents into {collection_name}")

        # Ensure the collection exists
        if not self.db_config.db.has_collection(collection_name):
            edge = parameters.get("edge", False)
            self.logger.info(f"Requesting collection {collection_name} (edge={edge})")
            # Use the proper method to get collections via IndalekoDBCollections
            IndalekoDBCollections.get_collection(self.db_config.db, collection_name, edge=edge)

        collection = self.db_config.db.collection(collection_name)
        results = []

        for doc in documents:
            try:
                if overwrite and "_key" in doc and collection.has(doc["_key"]):
                    result = collection.replace(doc["_key"], doc)
                else:
                    result = collection.insert(doc)

                results.append({
                    "success": True,
                    "key": result["_key"],
                    "id": result["_id"]
                })
            except Exception as e:
                self.logger.error(f"Error inserting document: {str(e)}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "document": doc.get("_key", "unknown")
                })

        self.logger.info(f"Inserted {sum(1 for r in results if r.get('success', False))} documents")
        return results

    def get_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for this tool.

        Returns:
            Tool schema description
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "collection": {
                            "type": "string",
                            "description": "Collection name"
                        },
                        "documents": {
                            "type": "array",
                            "description": "Documents to insert",
                            "items": {
                                "type": "object"
                            }
                        },
                        "overwrite": {
                            "type": "boolean",
                            "description": "Whether to overwrite existing documents"
                        },
                        "edge": {
                            "type": "boolean",
                            "description": "Whether the collection is an edge collection (only for creation)"
                        }
                    },
                    "required": ["collection", "documents"]
                }
            }
        }


class DatabaseBulkInsertTool(Tool):
    """Tool for bulk inserting documents into the database."""

    def __init__(self, db_config: IndalekoDBConfig):
        """Initialize the database bulk insert tool.

        Args:
            db_config: Database configuration
        """
        super().__init__(
            name="database_bulk_insert",
            description="Bulk insert documents into a database collection"
        )
        self.db_config = db_config

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with provided parameters.

        Args:
            parameters: Tool parameters
                - collection: Collection name
                - documents: Documents to insert
                - batch_size: Number of documents to insert in each batch

        Returns:
            Insertion results
        """
        collection_name = parameters.get("collection")
        if not collection_name:
            raise ValueError("Collection parameter is required")

        documents = parameters.get("documents", [])
        if not documents:
            return {"inserted": 0, "errors": 0}

        batch_size = parameters.get("batch_size", 1000)

        self.logger.debug(f"Bulk inserting {len(documents)} documents into {collection_name}")

        # Ensure the collection exists
        if not self.db_config.db.has_collection(collection_name):
            edge = parameters.get("edge", False)
            self.logger.info(f"Requesting collection {collection_name} (edge={edge})")
            # Use the proper method to get collections via IndalekoDBCollections
            IndalekoDBCollections.get_collection(self.db_config.db, collection_name, edge=edge)

        collection = self.db_config.db.collection(collection_name)

        # Split documents into batches
        batches = [documents[i:i + batch_size] for i in range(0, len(documents), batch_size)]

        inserted = 0
        errors = 0

        for batch in batches:
            try:
                result = collection.insert_many(batch)
                inserted += len(result)
            except Exception as e:
                self.logger.error(f"Error batch inserting documents: {str(e)}")
                # Fall back to inserting one by one
                for doc in batch:
                    try:
                        collection.insert(doc)
                        inserted += 1
                    except Exception as inner_e:
                        self.logger.error(f"Error inserting document: {str(inner_e)}")
                        errors += 1

        self.logger.info(f"Inserted {inserted} documents with {errors} errors")
        return {
            "inserted": inserted,
            "errors": errors,
            "total": len(documents)
        }

    def get_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for this tool.

        Returns:
            Tool schema description
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "collection": {
                            "type": "string",
                            "description": "Collection name"
                        },
                        "documents": {
                            "type": "array",
                            "description": "Documents to insert",
                            "items": {
                                "type": "object"
                            }
                        },
                        "batch_size": {
                            "type": "integer",
                            "description": "Number of documents to insert in each batch"
                        },
                        "edge": {
                            "type": "boolean",
                            "description": "Whether the collection is an edge collection (only for creation)"
                        }
                    },
                    "required": ["collection", "documents"]
                }
            }
        }


class DatabaseSchemaValidationTool(Tool):
    """Tool for validating database schema."""

    def __init__(self, db_config: IndalekoDBConfig):
        """Initialize the database schema validation tool.

        Args:
            db_config: Database configuration
        """
        super().__init__(
            name="database_schema_validation",
            description="Validate documents against collection schema"
        )
        self.db_config = db_config

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with provided parameters.

        Args:
            parameters: Tool parameters
                - collection: Collection name
                - documents: Documents to validate

        Returns:
            Validation results
        """
        collection_name = parameters.get("collection")
        if not collection_name:
            raise ValueError("Collection parameter is required")

        documents = parameters.get("documents", [])
        if not documents:
            return {"valid": 0, "invalid": 0, "issues": []}

        self.logger.debug(f"Validating {len(documents)} documents against {collection_name} schema")

        # Get the collection schema
        schema = None
        try:
            schema_query = "RETURN SCHEMA_GET(@collection)"
            cursor = self.db_config.db.aql.execute(
                schema_query,
                bind_vars={"collection": collection_name}
            )
            schema_result = list(cursor)
            if schema_result and schema_result[0]:
                schema = schema_result[0]
        except Exception as e:
            self.logger.warning(f"Error getting schema for {collection_name}: {str(e)}")
            return {
                "valid": 0,
                "invalid": 0,
                "issues": [{"error": f"Error getting schema: {str(e)}"}]
            }

        if not schema:
            self.logger.info(f"No schema found for {collection_name}")
            return {"valid": len(documents), "invalid": 0, "issues": []}

        # Validate each document against the schema
        valid = 0
        invalid = 0
        issues = []

        for i, doc in enumerate(documents):
            try:
                validation_query = """
                RETURN SCHEMA_VALIDATE(
                    @collection,
                    @document,
                    {withDefaults: false}
                )
                """
                cursor = self.db_config.db.aql.execute(
                    validation_query,
                    bind_vars={
                        "collection": collection_name,
                        "document": doc
                    }
                )
                result = list(cursor)

                if result and result[0] and result[0].get("valid", False):
                    valid += 1
                else:
                    invalid += 1
                    issues.append({
                        "index": i,
                        "key": doc.get("_key", "unknown"),
                        "issues": result[0].get("errors", ["Unknown validation error"])
                    })
            except Exception as e:
                self.logger.error(f"Error validating document: {str(e)}")
                invalid += 1
                issues.append({
                    "index": i,
                    "key": doc.get("_key", "unknown"),
                    "error": str(e)
                })

        self.logger.info(f"Validated {valid} valid documents, {invalid} invalid")
        return {
            "valid": valid,
            "invalid": invalid,
            "issues": issues
        }

    def get_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for this tool.

        Returns:
            Tool schema description
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "collection": {
                            "type": "string",
                            "description": "Collection name"
                        },
                        "documents": {
                            "type": "array",
                            "description": "Documents to validate",
                            "items": {
                                "type": "object"
                            }
                        }
                    },
                    "required": ["collection", "documents"]
                }
            }
        }
