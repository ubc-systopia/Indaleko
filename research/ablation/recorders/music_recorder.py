"""Music activity recorder for ablation testing."""

import logging
from typing import Any
from uuid import UUID

from db.db_collections import IndalekoDBCollections

from ..base import ISyntheticRecorder
from ..models.music_activity import MusicActivity
from .base import BaseActivityRecorder


class MusicActivityRecorder(BaseActivityRecorder):
    """Synthetic recorder for music activity data.

    This recorder writes music activity data to the ArangoDB database
    and manages the ablation test collections.
    """

    # Collection name for music activity
    COLLECTION_NAME = IndalekoDBCollections.Indaleko_Ablation_Music_Activity_Collection

    # Collection name for truth data
    TRUTH_COLLECTION = IndalekoDBCollections.Indaleko_Ablation_Query_Truth_Collection

    # Activity model class
    ActivityClass = MusicActivity

    def __init__(self):
        """Initialize the music activity recorder."""
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def get_records_by_query(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get music activity records that match a query.

        This is a simplified implementation that uses AQL to search
        for music activities based on a keyword query.

        Args:
            query: The query string to search for.
            limit: The maximum number of records to return.

        Returns:
            List[Dict[str, Any]]: The matching records.
        """
        if not self.db:
            self.logger.critical("No database connection available")
            import sys
            sys.exit(1)

        # Convert query to lowercase for case-insensitive search
        query_lower = query.lower()

        # Execute AQL query to search for matching documents
        result_cursor = self.db.aql.execute(
            f"""
            FOR doc IN {self.COLLECTION_NAME}
            FILTER LOWER(doc.artist) LIKE @query OR
                   LOWER(doc.track) LIKE @query OR
                   (doc.album != NULL AND LOWER(doc.album) LIKE @query) OR
                   (doc.genre != NULL AND LOWER(doc.genre) LIKE @query) OR
                   LOWER(doc.platform) LIKE @query
            LIMIT @limit
            RETURN doc
            """,
            bind_vars={"query": f"%{query_lower}%", "limit": limit},
        )

        # Convert cursor to list
        results = [doc for doc in result_cursor]

        return results