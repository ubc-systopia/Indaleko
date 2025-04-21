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

import os
import sys
import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Tuple

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.context.service import IndalekoActivityContextService
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
    
    def __init__(self, db_config=None, debug=False):
        """
        Initialize the QueryActivityProvider.
        
        Args:
            db_config: Optional database configuration
            debug: Whether to enable debug logging
        """
        # Set up logging
        self._logger = logging.getLogger("QueryActivityProvider")
        if debug:
            self._logger.setLevel(logging.DEBUG)
        
        # Initialize context service
        try:
            self._context_service = IndalekoActivityContextService(db_config=db_config)
            self._logger.info("Connected to Activity Context Service")
        except Exception as e:
            self._logger.error(f"Error connecting to Activity Context Service: {e}")
            self._context_service = None
            
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
        results: Optional[List[Any]] = None,
        execution_time: Optional[float] = None, 
        query_params: Optional[Dict[str, Any]] = None,
        relationship_type: Optional[str] = None,
        previous_query_id: Optional[uuid.UUID] = None
    ) -> Tuple[uuid.UUID, Optional[uuid.UUID]]:
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
                    self._last_query_text, query_text
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
                previous_query_id=previous_query_id
            )
            
            # Create summary for context
            summary = self._create_query_summary(query_text, results)
            
            # Update activity context with this query
            self._context_service.update_cursor(
                provider=self.QUERY_CONTEXT_PROVIDER_ID,
                provider_reference=query_id,
                provider_data=summary,
                provider_attributes=attributes
            )
            
            # Write updated context to database
            self._context_service.write_activity_context_to_database()
            
            # Update last query tracking
            self._last_query_id = query_id
            self._last_query_text = query_text
            
            self._logger.info(f"Recorded query: {query_text[:50]}...")
            return query_id, current_context_handle
            
        except Exception as e:
            self._logger.error(f"Error recording query activity: {e}")
            return uuid.uuid4(), None
    
    def _build_query_attributes(
        self,
        query_text: str,
        results: Optional[List[Any]],
        execution_time: Optional[float],
        query_params: Optional[Dict[str, Any]],
        context_handle: Optional[uuid.UUID],
        relationship_type: Optional[str],
        previous_query_id: Optional[uuid.UUID]
    ) -> Dict[str, Any]:
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
            Dictionary of attributes
        """
        attributes = {
            "query_text": query_text,
            "result_count": len(results) if results else 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if execution_time is not None:
            attributes["execution_time"] = execution_time
            
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
        results: Optional[List[Any]]
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
        if len(query_text) > 50:
            summary = f"Query: {query_text[:50]}..."
        else:
            summary = f"Query: {query_text}"
            
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
        elif current_query in previous_query and len(previous_query) > len(current_query):
            return "broadening"
            
        # Check for pivot (queries share significant words but have different focus)
        else:
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
    
    def get_query_by_id(self, query_id: uuid.UUID) -> Optional[Dict[str, Any]]:
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
            # Implement query retrieval from activity context system
            # This would require querying the database directly
            pass
        except Exception as e:
            self._logger.error(f"Error retrieving query: {e}")
            return None
    
    def get_recent_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
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
            # Implement recent query retrieval
            # This would require querying the database directly
            pass
        except Exception as e:
            self._logger.error(f"Error retrieving recent queries: {e}")
            return []


def main():
    """Test functionality of QueryActivityProvider."""
    logging.basicConfig(level=logging.DEBUG)
    
    # Create provider
    provider = QueryActivityProvider(debug=True)
    
    if not provider.is_context_available():
        print("Activity context service not available. Exiting.")
        return
    
    # Record a sequence of queries
    query1 = "Find documents about Indaleko"
    query2 = "Find PDF documents about Indaleko"
    query3 = "Show me the authors of Indaleko documents"
    
    # Record queries and check relationships
    q1_id, ctx1 = provider.record_query(query1)
    print(f"Recorded query 1: {q1_id}, context: {ctx1}")
    
    q2_id, ctx2 = provider.record_query(query2)
    print(f"Recorded query 2: {q2_id}, context: {ctx2}")
    print(f"Relationship: {provider._detect_relationship(query1, query2)}")
    
    q3_id, ctx3 = provider.record_query(query3)
    print(f"Recorded query 3: {q3_id}, context: {ctx3}")
    print(f"Relationship: {provider._detect_relationship(query2, query3)}")


if __name__ == "__main__":
    main()