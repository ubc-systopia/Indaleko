"""Database utilities for the ablation framework."""

import logging
from typing import Any

from arango.collection import StandardCollection
from arango.cursor import Cursor
from arango.exceptions import DocumentInsertError, DocumentUpdateError

from db.db_config import IndalekoDBConfig
from db.i_collections import IndalekoCollections
from research.ablation.db.collections import get_default_collection_schemas

logger = logging.getLogger(__name__)


class AblationDatabase:
    """Database utility class for the ablation framework.

    This class provides a wrapper around the ArangoDB connection
    with specialized methods for the ablation framework.
    """

    def __init__(self) -> None:
        """Initialize the database connection."""
        self._db_config = IndalekoDBConfig()
        self._db = self._db_config.get_arangodb()

    @property
    def db(self):
        """Get the ArangoDB database instance.

        Returns:
            The ArangoDB database instance.
        """
        return self._db

    def ensure_collections(self) -> bool:
        """Ensure all required collections exist.

        This method verifies all required collections exist for the
        ablation framework, following the Indaleko collection naming
        conventions. Since collections are defined in IndalekoDBCollections,
        missing collections are treated as a fatal error (fail-stop condition).

        Returns:
            bool: True if all collections are available, False otherwise.
        """
        schemas = get_default_collection_schemas()
        success = True

        for schema in schemas:
            try:
                # Use the proper Indaleko pattern to get collections
                # This will create the collection if it doesn't exist yet
                # but only if it's properly defined in IndalekoDBCollections
                collection = IndalekoCollections.get_collection(schema.name)
                if collection is None:
                    logger.error("Collection %s does not exist and is not defined in IndalekoDBCollections", 
                                schema.name)
                    success = False
                    continue

                logger.info("Collection %s exists", schema.name)

                # Ensure indexes exist
                for index_def in schema.indexes:
                    index_dict = index_def.copy()
                    fields = index_dict.pop("fields")
                    index_type = index_dict.pop("type", "persistent")

                    # Get the ArangoDB collection object
                    arango_collection = collection._arangodb_collection

                    if index_type == "hash":
                        arango_collection.add_hash_index(fields, **index_dict)
                    elif index_type == "fulltext":
                        arango_collection.add_fulltext_index(fields, **index_dict)
                    elif index_type == "geo":
                        arango_collection.add_geo_index(fields, **index_dict)
                    else:
                        arango_collection.add_persistent_index(fields, **index_dict)

            except Exception as e:
                logger.exception("Failed to verify collection %s: %s", schema.name, e)
                success = False

        if not success:
            logger.error("FATAL: Some required collections are missing. Cannot proceed with ablation testing.")

        return success

    def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists.

        Args:
            collection_name: The name of the collection to check.

        Returns:
            bool: True if the collection exists, False otherwise.
        """
        try:
            # Use the proper Indaleko pattern to check if a collection exists
            # Without trying to create it if it doesn't
            indaleko_collection = IndalekoCollections.get_collection(collection_name)
            return indaleko_collection is not None
        except Exception as e:
            logger.exception("Failed to check if collection %s exists: %s", collection_name, e)
            return False

    def get_collection(self, collection_name: str) -> StandardCollection | None:
        """Get a collection by name.

        Args:
            collection_name: The name of the collection.

        Returns:
            Optional[StandardCollection]: The collection or None if it doesn't exist.
        """
        try:
            # Use the proper Indaleko pattern to get collections
            indaleko_collection = IndalekoCollections.get_collection(collection_name)
            if indaleko_collection is None:
                logger.error("Collection %s does not exist", collection_name)
                return None
            return indaleko_collection._arangodb_collection
        except Exception as e:
            logger.exception("Failed to get collection %s: %s", collection_name, e)
            return None

    def aql_query(
        self, query: str, bind_vars: dict[str, Any] | None = None, batch_size: int = 100,
    ) -> Cursor | list[dict[str, Any]]:
        """Execute an AQL query.

        Args:
            query: The AQL query to execute.
            bind_vars: The bind variables to use.
            batch_size: The batch size for cursor fetching.

        Returns:
            Union[Cursor, List[Dict]]: The query results as a cursor or list.
        """
        try:
            bind_vars = bind_vars or {}
            return self._db.aql.execute(query, bind_vars=bind_vars, batch_size=batch_size)
        except Exception as e:
            logger.exception("Failed to execute AQL query: %s", e)
            return []

    def insert_document(self, collection_name: str, document: dict[str, Any]) -> str | None:
        """Insert a document into a collection.

        Args:
            collection_name: The name of the collection.
            document: The document to insert.

        Returns:
            Optional[str]: The _key of the inserted document or None if failed.
        """
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                logger.error("Collection %s does not exist", collection_name)
                return None

            result = collection.insert(document)
            return result["_key"] if "_key" in result else None
        except DocumentInsertError as e:
            logger.exception("Failed to insert document into %s: %s", collection_name, e)
            return None
        except Exception as e:
            logger.exception("Failed to insert document into %s: %s", collection_name, e)
            return None

    def insert_batch(self, collection_name: str, documents: list[dict[str, Any]]) -> list[str]:
        """Insert multiple documents into a collection.

        Args:
            collection_name: The name of the collection.
            documents: The documents to insert.

        Returns:
            List[str]: The _keys of the inserted documents.
        """
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                logger.error("Collection %s does not exist", collection_name)
                return []

            # Insert documents one by one to handle errors gracefully
            keys = []
            for doc_data in documents:
                try:
                    result = collection.insert(doc_data)
                    keys.append(result["_key"])
                except Exception as e:
                    logger.exception("Failed to insert document: %s", e)

            return keys
        except Exception as e:
            logger.exception("Failed to batch insert documents into %s: %s", collection_name, e)
            return []

    def get_document(self, collection_name: str, key: str) -> dict[str, Any] | None:
        """Get a document by key.

        Args:
            collection_name: The name of the collection.
            key: The document key.

        Returns:
            Optional[Dict]: The document or None if not found.
        """
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                logger.error("Collection %s does not exist", collection_name)
                return None

            return collection.get(key)
        except Exception as e:
            logger.exception("Failed to get document %s from %s: %s", key, collection_name, e)
            return None

    def update_document(self, collection_name: str, key: str, update_data: dict[str, Any]) -> bool:
        """Update a document by key.

        Args:
            collection_name: The name of the collection.
            key: The document key.
            update_data: The data to update.

        Returns:
            bool: True if updated successfully, False otherwise.
        """
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                logger.error("Collection %s does not exist", collection_name)
                return False

            collection.update(key, update_data)
            return True
        except DocumentUpdateError:
            logger.error("Document %s not found in collection %s", key, collection_name)
            return False
        except Exception as e:
            logger.exception("Failed to update document %s in %s: %s", key, collection_name, e)
            return False

    def delete_document(self, collection_name: str, key: str) -> bool:
        """Delete a document by key.

        Args:
            collection_name: The name of the collection.
            key: The document key.

        Returns:
            bool: True if deleted successfully, False otherwise.
        """
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                logger.error("Collection %s does not exist", collection_name)
                return False

            collection.delete(key)
            return True
        except Exception as e:
            logger.exception("Failed to delete document %s from %s: %s", key, collection_name, e)
            return False

    def clear_collection(self, collection_name: str) -> bool:
        """Clear all documents from a collection.

        Args:
            collection_name: The name of the collection.

        Returns:
            bool: True if cleared successfully, False otherwise.
        """
        try:
            query = f"FOR doc IN {collection_name} REMOVE doc IN {collection_name}"
            self.aql_query(query)
            return True
        except Exception as e:
            logger.exception("Failed to clear collection %s: %s", collection_name, e)
            return False

    def count_documents(self, collection_name: str) -> int:
        """Count the number of documents in a collection.

        Args:
            collection_name: The name of the collection.

        Returns:
            int: The number of documents in the collection.
        """
        try:
            query = f"RETURN LENGTH({collection_name})"
            cursor = self.aql_query(query)
            return next(cursor) if cursor else 0
        except Exception as e:
            logger.exception("Failed to count documents in %s: %s", collection_name, e)
            return 0


class AblationDatabaseManager:
    """Manager for handling ablation-specific database operations.

    This class provides specialized methods for ablation testing, such as
    temporarily ablating collections and calculating metrics.
    """

    def __init__(self) -> None:
        """Initialize the database manager."""
        self.db = AblationDatabase()
        self._ablated_collections: dict[str, bool] = {}

    def ensure_collections(self) -> bool:
        """Ensure all required collections exist.

        Returns:
            bool: True if all collections are available, False otherwise.
        """
        return self.db.ensure_collections()

    def ablate_collection(self, collection_name: str) -> bool:
        """Temporarily hide a collection from queries.

        This is done by renaming the collection to add a "_ABLATED" suffix.
        The original collection can be restored with restore_collection().

        Args:
            collection_name: The name of the collection to ablate.

        Returns:
            bool: True if ablated successfully, False otherwise.
        """
        # Define ablated collection name
        ablated_name = f"{collection_name}_ABLATED"

        try:
            # Check if collection exists
            if not self.db.collection_exists(collection_name):
                logger.error("Cannot ablate: collection %s does not exist", collection_name)
                return False

            # Check if already ablated
            if collection_name in self._ablated_collections:
                logger.warning("Collection %s is already ablated", collection_name)
                return True

            # Check if ablated collection already exists (from a previous failed ablation)
            if self.db.collection_exists(ablated_name):
                logger.warning("Ablated collection %s already exists, dropping it first", ablated_name)
                # Get the database directly for operations not supported through IndalekoCollections
                self.db.db.delete_collection(ablated_name)

            # Rename collection to ablated name - this requires direct db access
            # as IndalekoCollections doesn't support renaming
            self.db.db.rename_collection(collection_name, ablated_name)
            self._ablated_collections[collection_name] = True

            logger.info("Successfully ablated collection %s", collection_name)
            return True

        except Exception as e:
            logger.exception("Failed to ablate collection %s: %s", collection_name, e)
            return False

    def restore_collection(self, collection_name: str) -> bool:
        """Restore a previously ablated collection.

        Args:
            collection_name: The original name of the collection.

        Returns:
            bool: True if restored successfully, False otherwise.
        """
        # Define ablated collection name
        ablated_name = f"{collection_name}_ABLATED"

        try:
            # Check if collection is ablated
            if collection_name not in self._ablated_collections:
                logger.warning("Collection %s is not ablated", collection_name)
                # If the original collection exists, consider it already restored
                if self.db.collection_exists(collection_name):
                    return True

            # Check if ablated collection exists
            if not self.db.collection_exists(ablated_name):
                logger.error("Cannot restore: ablated collection %s does not exist", ablated_name)
                return False

            # Check if original collection exists (should not)
            if self.db.collection_exists(collection_name):
                logger.warning("Original collection %s already exists, dropping it first", collection_name)
                # Get the database directly for operations not supported through IndalekoCollections
                self.db.db.delete_collection(collection_name)

            # Rename ablated collection back to original name - this requires direct db access
            # as IndalekoCollections doesn't support renaming
            self.db.db.rename_collection(ablated_name, collection_name)
            self._ablated_collections.pop(collection_name, None)

            logger.info("Successfully restored collection %s", collection_name)
            return True

        except Exception as e:
            logger.exception("Failed to restore collection %s: %s", collection_name, e)
            return False

    def restore_all_collections(self) -> bool:
        """Restore all ablated collections.

        Returns:
            bool: True if all collections were restored successfully.
        """
        success = True
        # Create a copy of the keys to avoid modifying dictionary during iteration
        ablated_collections = list(self._ablated_collections.keys())

        for collection_name in ablated_collections:
            if not self.restore_collection(collection_name):
                success = False

        return success

    def get_current_ablated_collections(self) -> list[str]:
        """Get list of currently ablated collections.

        Returns:
            List[str]: List of ablated collection names.
        """
        return list(self._ablated_collections.keys())

    def is_collection_ablated(self, collection_name: str) -> bool:
        """Check if a collection is currently ablated.

        Args:
            collection_name: The name of the collection to check.

        Returns:
            bool: True if the collection is ablated, False otherwise.
        """
        return collection_name in self._ablated_collections
