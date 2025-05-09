"""Media activity recorder for ablation testing."""

import logging
import sys
from typing import Any

from db.db_collections import IndalekoDBCollections

from ..models.media_activity import MediaActivity, MediaType
from .base import BaseActivityRecorder


class MediaActivityRecorder(BaseActivityRecorder):
    """Synthetic recorder for media activity data.

    This recorder writes media activity data to the ArangoDB database
    and manages the ablation test collections.
    """

    # Collection name for media activity
    COLLECTION_NAME = IndalekoDBCollections.Indaleko_Ablation_Media_Activity_Collection

    # Collection name for truth data
    TRUTH_COLLECTION = IndalekoDBCollections.Indaleko_Ablation_Query_Truth_Collection

    # Activity model class
    ActivityClass = MediaActivity

    def __init__(self):
        """Initialize the media activity recorder."""
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def get_records_by_query(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get media activity records that match a query.

        This is a semantic search implementation that looks for matches
        in media titles, types, platforms, and creators.

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
            LOWER(doc.title) LIKE @query OR
            LOWER(doc.media_type) LIKE @query OR
            LOWER(doc.platform) LIKE @query OR
            (doc.creator != null AND LOWER(doc.creator) LIKE @query)
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

    def get_records_by_media_type(self, media_type: MediaType | str, limit: int = 10) -> list[dict[str, Any]]:
        """Get media activity records by media type.

        Args:
            media_type: The media type to search for.
            limit: The maximum number of records to return.

        Returns:
            List[Dict[str, Any]]: The matching records.
        """
        if not self.db:
            self.logger.critical("No database connection available")
            sys.exit(1)

        # Convert media_type to string if it's an enum
        if isinstance(media_type, MediaType):
            media_type = media_type.value

        # Execute AQL query to search for matching documents
        result_cursor = self.db.aql.execute(
            f"""
            FOR doc IN {self.COLLECTION_NAME}
            FILTER doc.media_type == @media_type
            LIMIT @limit
            RETURN doc
            """,
            bind_vars={"media_type": media_type, "limit": limit},
        )

        # Convert cursor to list
        results = [doc for doc in result_cursor]

        return results

    def get_records_by_platform(self, platform: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get media activity records by platform.

        Args:
            platform: The platform to search for.
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
            FILTER doc.platform == @platform
            LIMIT @limit
            RETURN doc
            """,
            bind_vars={"platform": platform, "limit": limit},
        )

        # Convert cursor to list
        results = [doc for doc in result_cursor]

        return results

    def get_records_by_creator(self, creator: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get media activity records by creator.

        Args:
            creator: The creator to search for.
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
            FILTER doc.creator == @creator
            LIMIT @limit
            RETURN doc
            """,
            bind_vars={"creator": creator, "limit": limit},
        )

        # Convert cursor to list
        results = [doc for doc in result_cursor]

        return results

    def get_records_by_title(self, title_fragment: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get media activity records by title fragment.

        Args:
            title_fragment: The title fragment to search for.
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
            FILTER LIKE(doc.title, @title_fragment, true)
            LIMIT @limit
            RETURN doc
            """,
            bind_vars={"title_fragment": f"%{title_fragment}%", "limit": limit},
        )

        # Convert cursor to list
        results = [doc for doc in result_cursor]

        return results
