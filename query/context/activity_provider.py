"""
Query Activity Provider for Indaleko.

This module provides the QueryActivityProvider class, which is responsible for
recording queries as activities in the Indaleko Activity Context system.

Project Indaleko
Copyright (C) 2025 Tony Mason

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

import json
import logging
import os
import sys
import uuid

from datetime import UTC, datetime
from typing import Any


# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.context.service import IndalekoActivityContextService
from db.db_collections import IndalekoDBCollections
from query.context.data_models.query_activity import QueryActivityData


# pylint: enable=wrong-import-position


class QueryActivityProvider:
    """
    Provides query activities to the Activity Context system.

    This class is responsible for recording queries as activities in the
    Indaleko Activity Context system, allowing them to be connected to
    other activities and to each other.
    """

    # Provider ID for query activity context
    QUERY_CONTEXT_PROVIDER_ID = uuid.UUID("a7b4c3d2-e5f6-4708-b9a1-f2e3d4c5b6a7")

    def __init__(self, db_config=None, debug=False) -> None:
        """
        Initialize the QueryActivityProvider.

        Args:
            db_config: Optional database configuration3
            debug: Whether to enable debug logging
        """
        # Set up logging
        self._logger = logging.getLogger("QueryActivityProvider")
        if debug:
            self._logger.setLevel(logging.DEBUG)

        # Initialize context service
        self._context_service = IndalekoActivityContextService(db_config=db_config)
        self._logger.info("Connected to Activity Context Service")

        # Track whether context is available
        self._context_available = self._context_service is not None

        # Track the most recent query ID for relationship building
        self._last_query_id = None
        self._last_query_text = None

    def is_context_available(self) -> bool:
        """Check if activity context service is available."""
        return self._context_available and self._context_service is not None

    def record_query(
        self,
        query_text: str,
        results: list[Any] | None = None,
        execution_time: float | None = None,
        query_params: dict[str, Any] | None = None,
        relationship_type: str | None = None,
        previous_query_id: uuid.UUID | None = None,
    ) -> tuple[uuid.UUID, uuid.UUID | None]:
        """
        Record a query as an activity and associate it with current context.

        Args:
            query_text: The text of the query
            results: Optional results returned by the query
            execution_time: Optional execution time in milliseconds
            query_params: Optional query parameters
            relationship_type: Optional relationship to previous query
            previous_query_id: Optional ID of the previous query

        Returns:
            Tuple of (query_id, context_handle)
        """
        if not self.is_context_available():
            self._logger.warning("Activity context service not available")
            return uuid.uuid4(), None

        try:
            # Get current activity context
            current_context_handle = self._context_service.get_activity_handle()

            # Create query ID
            query_id = uuid.uuid4()

            # Determine relationship with previous query if not specified
            if relationship_type is None and self._last_query_id is not None:
                relationship_type = self._detect_relationship(
                    self._last_query_text,
                    query_text,
                )
                previous_query_id = self._last_query_id

            # Build attributes dictionary
            attributes = self._build_query_attributes(
                query_text=query_text,
                results=results,
                execution_time=execution_time,
                query_params=query_params,
                context_handle=current_context_handle,
                relationship_type=relationship_type,
                previous_query_id=previous_query_id,
            )

            # Create summary for context
            summary = self._create_query_summary(query_text, results)

            # Update activity context with this query
            self._context_service.update_cursor(
                provider=self.QUERY_CONTEXT_PROVIDER_ID,
                provider_reference=query_id,
                provider_data=summary,
                provider_attributes=attributes,
            )

            # Write updated context to database
            self._context_service.write_activity_context_to_database()

            # Update last query tracking
            self._last_query_id = query_id
            self._last_query_text = query_text

            self._logger.info(f"Recorded query: {query_text[:50]}...")
            return query_id, current_context_handle

        except Exception as e:
            self._logger.exception(f"Error recording query activity: {e}")
            return uuid.uuid4(), None

    def _build_query_attributes(
        self,
        query_text: str,
        results: list[Any] | None,
        execution_time: float | None,
        query_params: dict[str, Any] | None,
        context_handle: uuid.UUID | None,
        relationship_type: str | None,
        previous_query_id: uuid.UUID | None,
    ) -> dict[str, str]:
        """
        Build the attributes dictionary for the query activity.

        Args:
            query_text: The text of the query
            results: Results returned by the query
            execution_time: Execution time in milliseconds
            query_params: Query parameters
            context_handle: Activity context handle
            relationship_type: Relationship to previous query
            previous_query_id: ID of the previous query

        Returns:
            Dictionary of attributes (all values must be strings)
        """
        attributes = {
            "query_text": query_text,
            "result_count": str(len(results) if results else 0),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        if execution_time is not None:
            attributes["execution_time"] = str(execution_time)

        if query_params is not None:
            try:
                attributes["query_params"] = json.dumps(query_params)
            except (TypeError, json.JSONDecodeError):
                # Handle non-serializable objects
                self._logger.warning("Could not serialize query parameters")
                attributes["query_params"] = str(query_params)

        if context_handle is not None:
            attributes["context_handle"] = str(context_handle)

        if relationship_type is not None:
            attributes["relationship_type"] = relationship_type

        if previous_query_id is not None:
            attributes["previous_query_id"] = str(previous_query_id)

        return attributes

    def _create_query_summary(
        self,
        query_text: str,
        results: list[Any] | None,
    ) -> str:
        """
        Create a summary of the query for the context.

        Args:
            query_text: The text of the query
            results: Results returned by the query

        Returns:
            Summary string
        """
        # Truncate long queries
        summary = f"Query: {query_text[:50]}..." if len(query_text) > 50 else f"Query: {query_text}"

        # Add result count if available
        if results is not None:
            summary += f" ({len(results)} results)"

        return summary

    def _detect_relationship(self, previous_query: str, current_query: str) -> str:
        """
        Detect the relationship between two queries.

        Args:
            previous_query: The previous query text
            current_query: The current query text

        Returns:
            Relationship type: "refinement", "broadening", "pivot", or "unrelated"
        """
        # Simple heuristic detection - a more sophisticated version would use
        # NLP or LLM-based analysis

        # Check for refinement (current query includes previous query and adds constraints)
        if previous_query in current_query and len(current_query) > len(previous_query):
            return "refinement"

        # Check for broadening (previous query includes current query and adds constraints)
        if current_query in previous_query and len(previous_query) > len(
            current_query,
        ):
            return "broadening"

        # Check for pivot (queries share significant words but have different focus)
        # Simple word overlap calculation
        prev_words = set(previous_query.lower().split())
        curr_words = set(current_query.lower().split())

        # Calculate Jaccard similarity
        overlap = len(prev_words.intersection(curr_words))
        union = len(prev_words.union(curr_words))

        similarity = overlap / union if union > 0 else 0

        if similarity > 0.5:
            return "pivot"

        return "unrelated"

    def get_query_by_id(self, query_id: uuid.UUID) -> dict[str, Any] | None:
        """
        Retrieve a query by its ID.

        Args:
            query_id: The query ID

        Returns:
            Dictionary of query attributes or None if not found
        """
        if not self.is_context_available():
            return None

        try:
            # Get the query activity object
            activity = self.get_query_activity(query_id)

            # Convert to dictionary if found
            if activity:
                return {
                    "query_id": str(activity.query_id),
                    "query_text": activity.query_text,
                    "execution_time": activity.execution_time,
                    "result_count": activity.result_count,
                    "context_handle": (str(activity.context_handle) if activity.context_handle else None),
                    "relationship_type": activity.relationship_type,
                    "previous_query_id": (str(activity.previous_query_id) if activity.previous_query_id else None),
                    "timestamp": (activity.timestamp.isoformat() if activity.timestamp else None),
                }

            return None
        except Exception as e:
            self._logger.exception(f"Error retrieving query: {e}")
            return None

    def get_recent_queries(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get the most recent queries.

        Args:
            limit: Maximum number of queries to return

        Returns:
            List of query dictionaries
        """
        if not self.is_context_available():
            return []

        try:
            # Get recent query activities
            activities = self.get_recent_query_activities(limit)

            # Convert to dictionaries
            queries = []
            for activity in activities:
                queries.append(
                    {
                        "query_id": str(activity.query_id),
                        "query_text": activity.query_text,
                        "execution_time": activity.execution_time,
                        "result_count": activity.result_count,
                        "context_handle": (str(activity.context_handle) if activity.context_handle else None),
                        "relationship_type": activity.relationship_type,
                        "previous_query_id": (str(activity.previous_query_id) if activity.previous_query_id else None),
                        "timestamp": (activity.timestamp.isoformat() if activity.timestamp else None),
                    },
                )

            return queries
        except Exception as e:
            self._logger.exception(f"Error retrieving recent queries: {e}")
            return []

    def get_recent_query_activities(self, limit: int = 10) -> list[Any]:
        """
        Get the most recent query activities.

        Args:
            limit: Maximum number of activities to return

        Returns:
            List of query activity objects
        """
        if not self.is_context_available():
            return []

        try:
            self._logger.info(f"Getting recent query activities (limit: {limit})")

            # Query the database for activity context entries that have query activity data
            query = """
            FOR doc IN @@collection
            FILTER doc.Cursors != null
            LET query_cursors = (
                FOR cursor IN doc.Cursors
                FILTER cursor.Provider == @provider_id
                RETURN cursor
            )
            FILTER LENGTH(query_cursors) > 0
            SORT doc.Timestamp DESC
            LIMIT @limit
            RETURN {
                query_id: FIRST(query_cursors).ProviderReference,
                context_handle: doc.Handle,
                timestamp: doc.Timestamp,
                attributes: FIRST(query_cursors).ProviderAttributes,
                data: FIRST(query_cursors).ProviderData
            }
            """

            bind_vars = {
                "@collection": IndalekoDBCollections.Indaleko_ActivityContext_Collection,
                "provider_id": str(self.QUERY_CONTEXT_PROVIDER_ID),
                "limit": limit,
            }

            try:
                # Execute the query
                results = self._context_service.db_config._arangodb.aql.execute(
                    query,
                    bind_vars=bind_vars,
                )

                # Convert results to query activity objects
                activities = []
                for result in results:
                    if result and "attributes" in result and result["attributes"]:
                        attributes = result["attributes"]
                        activity = QueryActivityData(
                            query_id=uuid.UUID(str(result["query_id"])),
                            query_text=attributes.get("query_text", ""),
                            execution_time=(
                                float(attributes.get("execution_time", "0")) if "execution_time" in attributes else None
                            ),
                            result_count=(
                                int(attributes.get("result_count", "0")) if "result_count" in attributes else None
                            ),
                            context_handle=(
                                uuid.UUID(str(result["context_handle"])) if result["context_handle"] else None
                            ),
                            relationship_type=attributes.get("relationship_type"),
                            previous_query_id=(
                                uuid.UUID(attributes.get("previous_query_id"))
                                if "previous_query_id" in attributes and attributes.get("previous_query_id")
                                else None
                            ),
                            timestamp=(
                                datetime.fromisoformat(attributes.get("timestamp"))
                                if "timestamp" in attributes
                                else datetime.fromisoformat(result["timestamp"])
                            ),
                        )
                        activities.append(activity)

                self._logger.debug(f"Found {len(activities)} query activities")
                return activities

            except Exception as e:
                self._logger.exception(f"Error executing query for recent activities: {e}")
                return []

        except Exception as e:
            self._logger.exception(f"Error retrieving recent query activities: {e}")
            return []

    def get_query_activity(self, query_id: uuid.UUID) -> Any | None:
        """
        Get a query activity by ID.

        Args:
            query_id: The query ID

        Returns:
            Query activity object or None if not found
        """
        if not self.is_context_available():
            return None

        try:
            self._logger.info(f"Getting query activity for ID: {query_id}")

            # Query the database for activity context entries that have this specific query ID
            query = """
            FOR doc IN @@collection
            FILTER doc.Cursors != null
            LET query_cursors = (
                FOR cursor IN doc.Cursors
                FILTER cursor.Provider == @provider_id
                FILTER cursor.ProviderReference == @query_id
                RETURN cursor
            )
            FILTER LENGTH(query_cursors) > 0
            RETURN {
                query_id: FIRST(query_cursors).ProviderReference,
                context_handle: doc.Handle,
                timestamp: doc.Timestamp,
                attributes: FIRST(query_cursors).ProviderAttributes,
                data: FIRST(query_cursors).ProviderData
            }
            """

            bind_vars = {
                "@collection": IndalekoDBCollections.Indaleko_ActivityContext_Collection,
                "provider_id": str(self.QUERY_CONTEXT_PROVIDER_ID),
                "query_id": str(query_id),
            }

            try:
                # Execute the query
                results = self._context_service.db_config._arangodb.aql.execute(
                    query,
                    bind_vars=bind_vars,
                )

                # Get the first result (should be only one or none)
                result = None
                for r in results:
                    result = r
                    break

                if not result:
                    self._logger.debug(f"No query activity found for ID: {query_id}")
                    return None

                # Convert result to query activity object
                if result and "attributes" in result and result["attributes"]:
                    attributes = result["attributes"]
                    return QueryActivityData(
                        query_id=uuid.UUID(str(result["query_id"])),
                        query_text=attributes.get("query_text", ""),
                        execution_time=(
                            float(attributes.get("execution_time", "0")) if "execution_time" in attributes else None
                        ),
                        result_count=(
                            int(attributes.get("result_count", "0")) if "result_count" in attributes else None
                        ),
                        context_handle=(uuid.UUID(str(result["context_handle"])) if result["context_handle"] else None),
                        relationship_type=attributes.get("relationship_type"),
                        previous_query_id=(
                            uuid.UUID(attributes.get("previous_query_id"))
                            if "previous_query_id" in attributes and attributes.get("previous_query_id")
                            else None
                        ),
                        timestamp=(
                            datetime.fromisoformat(attributes.get("timestamp"))
                            if "timestamp" in attributes
                            else datetime.fromisoformat(result["timestamp"])
                        ),
                    )

                return None

            except Exception as e:
                self._logger.exception(f"Error executing query for activity: {e}")
                return None

        except Exception as e:
            self._logger.exception(f"Error retrieving query activity: {e}")
            return None


def main() -> None:
    """Test functionality of QueryActivityProvider."""
    logging.basicConfig(level=logging.DEBUG)

    # Create provider
    provider = QueryActivityProvider(debug=True)

    if not provider.is_context_available():
        return

    # Record a sequence of queries
    query1 = "Find documents about Indaleko"
    query2 = "Find PDF documents about Indaleko"
    query3 = "Show me the authors of Indaleko documents"

    # Record queries and check relationships
    q1_id, ctx1 = provider.record_query(query1)

    q2_id, ctx2 = provider.record_query(query2)

    q3_id, ctx3 = provider.record_query(query3)


if __name__ == "__main__":
    main()
