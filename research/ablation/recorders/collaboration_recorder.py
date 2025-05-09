"""Collaboration activity recorder for ablation testing."""

import logging
from typing import Any
from uuid import UUID

from db.db_collections import IndalekoDBCollections

from ..models.collaboration_activity import CollaborationActivity
from .base import BaseActivityRecorder


class CollaborationActivityRecorder(BaseActivityRecorder):
    """Synthetic recorder for collaboration activity data.

    This recorder writes collaboration activity data to the ArangoDB database
    and manages the ablation test collections.
    """

    # Collection name for collaboration activity
    COLLECTION_NAME = IndalekoDBCollections.Indaleko_Ablation_Collaboration_Activity_Collection

    # Collection name for truth data
    TRUTH_COLLECTION = IndalekoDBCollections.Indaleko_Ablation_Query_Truth_Collection

    # Activity model class
    ActivityClass = CollaborationActivity

    def __init__(self):
        """Initialize the collaboration activity recorder."""
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def get_records_by_query(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get collaboration activity records that match a query.

        This is a simplified implementation that uses AQL to search
        for collaboration activities based on a keyword query.

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

        try:
            # Convert query to lowercase for case-insensitive search
            query_lower = query.lower()

            # Execute AQL query to search for matching documents
            result_cursor = self.db.aql.execute(
                f"""
                FOR doc IN {self.COLLECTION_NAME}
                FILTER LOWER(doc.platform) LIKE @query OR
                       LOWER(doc.event_type) LIKE @query OR
                       (doc.content != NULL AND LOWER(doc.content) LIKE @query) OR
                       LOWER(doc.source) LIKE @query OR
                       (
                           FOR participant IN doc.participants
                           FILTER
                               LOWER(participant.name) LIKE @query OR
                               (participant.email != NULL AND LOWER(participant.email) LIKE @query)
                           RETURN true
                       )[0] == true
                LIMIT @limit
                RETURN doc
                """,
                bind_vars={"query": f"%{query_lower}%", "limit": limit},
            )

            # Convert cursor to list
            results = [doc for doc in result_cursor]

            return results
        except Exception as e:
            self.logger.error(f"Failed to get records by query: {e}")
            import sys
            sys.exit(1)  # Fail-stop approach
