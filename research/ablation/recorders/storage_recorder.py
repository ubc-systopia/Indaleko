"""Storage activity recorder for ablation testing."""

import logging
import sys
from typing import Any

from db.db_collections import IndalekoDBCollections

from ..models.storage_activity import StorageActivity, StorageOperationType
from .base import BaseActivityRecorder


class StorageActivityRecorder(BaseActivityRecorder):
    """Synthetic recorder for storage activity data.

    This recorder writes storage activity data to the ArangoDB database
    and manages the ablation test collections.
    """

    # Collection name for storage activity
    COLLECTION_NAME = IndalekoDBCollections.Indaleko_Ablation_Storage_Activity_Collection

    # Collection name for truth data
    TRUTH_COLLECTION = IndalekoDBCollections.Indaleko_Ablation_Query_Truth_Collection

    # Activity model class
    ActivityClass = StorageActivity

    def __init__(self):
        """Initialize the storage activity recorder."""
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def get_records_by_query(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get storage activity records that match a query.

        This is a semantic search implementation that looks for matches
        in file paths, types, operations, and sources.

        Args:
            query: The query string to search for.
            limit: The maximum number of records to return.

        Returns:
            List[Dict[str, Any]]: The matching records.
        """
        if not self.db:
            self.logger.critical("No database connection available")
            sys.exit(1)

        # Convert query to lowercase for case-insensitive search
        query_lower = query.lower()

        # Execute AQL query to search for matching documents
        aql_query = f"""
        FOR doc IN {self.COLLECTION_NAME}
        FILTER
            LOWER(doc.path) LIKE @query OR
            LOWER(doc.file_type) LIKE @query OR
            LOWER(doc.operation) LIKE @query OR
            LOWER(doc.source) LIKE @query
        LIMIT @limit
        RETURN doc
        """

        result_cursor = self.db.aql.execute(
            aql_query,
            bind_vars={"query": f"%{query_lower}%", "limit": limit},
        )

        # Convert cursor to list
        results = [doc for doc in result_cursor]

        return results

    def get_records_by_file_type(self, file_type: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get storage activity records by file type.

        Args:
            file_type: The file type to search for.
            limit: The maximum number of records to return.

        Returns:
            List[Dict[str, Any]]: The matching records.
        """
        if not self.db:
            self.logger.critical("No database connection available")
            sys.exit(1)

        # Execute AQL query to search for matching documents
        result_cursor = self.db.aql.execute(
            f"""
            FOR doc IN {self.COLLECTION_NAME}
            FILTER doc.file_type == @file_type
            LIMIT @limit
            RETURN doc
            """,
            bind_vars={"file_type": file_type, "limit": limit},
        )

        # Convert cursor to list
        results = [doc for doc in result_cursor]

        return results

    def get_records_by_operation(self, operation: StorageOperationType | str, limit: int = 10) -> list[dict[str, Any]]:
        """Get storage activity records by operation type.

        Args:
            operation: The operation type to search for.
            limit: The maximum number of records to return.

        Returns:
            List[Dict[str, Any]]: The matching records.
        """
        if not self.db:
            self.logger.critical("No database connection available")
            sys.exit(1)

        # Convert operation to string if it's an enum
        if isinstance(operation, StorageOperationType):
            operation = operation.value

        # Execute AQL query to search for matching documents
        result_cursor = self.db.aql.execute(
            f"""
            FOR doc IN {self.COLLECTION_NAME}
            FILTER doc.operation == @operation
            LIMIT @limit
            RETURN doc
            """,
            bind_vars={"operation": operation, "limit": limit},
        )

        # Convert cursor to list
        results = [doc for doc in result_cursor]

        return results

    def get_records_by_path(self, path_fragment: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get storage activity records by path fragment.

        Args:
            path_fragment: The path fragment to search for.
            limit: The maximum number of records to return.

        Returns:
            List[Dict[str, Any]]: The matching records.
        """
        if not self.db:
            self.logger.critical("No database connection available")
            sys.exit(1)

        # Execute AQL query to search for matching documents
        result_cursor = self.db.aql.execute(
            f"""
            FOR doc IN {self.COLLECTION_NAME}
            FILTER LIKE(doc.path, @path_fragment, true) OR
                   (doc.related_path != null AND LIKE(doc.related_path, @path_fragment, true))
            LIMIT @limit
            RETURN doc
            """,
            bind_vars={"path_fragment": f"%{path_fragment}%", "limit": limit},
        )

        # Convert cursor to list
        results = [doc for doc in result_cursor]

        return results
