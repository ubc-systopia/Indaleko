"""
Query Navigation for Indaleko.

This module provides the QueryNavigator class, which enables navigation
between related queries based on their shared contexts and relationships.

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
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union, Set, Tuple

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.context.service import IndalekoActivityContextService
from query.context.activity_provider import QueryActivityProvider
from Indaleko import Indaleko
# pylint: enable=wrong-import-position


class QueryNavigator:
    """
    Provides navigation between related queries based on shared context.
    
    This class enables exploration of query relationships, including:
    - Finding related queries that share a context
    - Reconstructing query paths (sequences of queries)
    - Identifying exploration branches (divergent paths)
    """
    
    def __init__(self, db_config=None, debug=False):
        """
        Initialize the QueryNavigator.
        
        Args:
            db_config: Optional database configuration
            debug: Whether to enable debug logging
        """
        # Set up logging
        self._logger = logging.getLogger("QueryNavigator")
        if debug:
            self._logger.setLevel(logging.DEBUG)
        
        # Initialize context service and other dependencies
        try:
            self._context_service = IndalekoActivityContextService(db_config=db_config)
            self._activity_provider = QueryActivityProvider(db_config=db_config)
            self._db_config = db_config
            self._logger.info("Initialized QueryNavigator")
        except Exception as e:
            self._logger.error(f"Error initializing QueryNavigator: {e}")
            self._context_service = None
            self._activity_provider = None
        
        # Track whether navigation is available
        self._nav_available = (self._context_service is not None and 
                              self._activity_provider is not None)
        
        # Initialize database connection if available
        try:
            from db import IndalekoDBConfig, IndalekoCollections
            self._db = IndalekoDBConfig.get_db()
            self._logger.debug("Connected to database")
        except Exception as e:
            self._logger.error(f"Error connecting to database: {e}")
            self._db = None
    
    def is_navigation_available(self) -> bool:
        """Check if query navigation is available."""
        return self._nav_available and self._db is not None
    
    def get_query_by_id(self, query_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Retrieve a query by its ID.
        
        Args:
            query_id: The query ID
            
        Returns:
            Dictionary of query attributes or None if not found
        """
        if not self.is_navigation_available():
            return None
            
        try:
            # Query the database to find the activity cursor with this ID
            query = """
            FOR ctx IN ActivityContext
            FOR cursor IN ctx.Cursors
            FILTER cursor.Provider == @provider_id
            FILTER cursor.ProviderReference == @query_id
            RETURN {
                query_id: cursor.ProviderReference,
                query_text: cursor.ProviderAttributes.query_text,
                result_count: cursor.ProviderAttributes.result_count,
                execution_time: cursor.ProviderAttributes.execution_time,
                context_handle: ctx.Handle,
                relationship_type: cursor.ProviderAttributes.relationship_type,
                previous_query_id: cursor.ProviderAttributes.previous_query_id,
                timestamp: cursor.ProviderAttributes.timestamp
            }
            """
            
            cursor = self._db.aql.execute(
                query,
                bind_vars={
                    "provider_id": str(QueryActivityProvider.QUERY_CONTEXT_PROVIDER_ID),
                    "query_id": str(query_id)
                }
            )
            
            results = [doc for doc in cursor]
            
            if not results:
                return None
                
            return results[0]
            
        except Exception as e:
            self._logger.error(f"Error retrieving query: {e}")
            return None
    
    def get_related_queries(
        self, 
        query_id: Optional[uuid.UUID] = None,
        context_handle: Optional[uuid.UUID] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get queries related to the specified query or context.
        
        This method finds queries that share a context with the specified
        query or are directly associated with the specified context handle.
        
        Args:
            query_id: Optional query ID to find related queries for
            context_handle: Optional context handle to find queries for
            limit: Maximum number of queries to return
            
        Returns:
            List of related query dictionaries
        """
        if not self.is_navigation_available():
            return []
            
        try:
            # If query_id is provided, get its context handle
            if query_id is not None and context_handle is None:
                query_data = self.get_query_by_id(query_id)
                if query_data and "context_handle" in query_data:
                    context_handle = uuid.UUID(query_data["context_handle"])
            
            if context_handle is None:
                self._logger.warning("No context handle available")
                return []
                
            # Query for activities with this context handle
            query = """
            FOR ctx IN ActivityContext
            FILTER ctx.Handle == @context_handle
            FOR cursor IN ctx.Cursors
            FILTER cursor.Provider == @provider_id
            SORT cursor.ProviderAttributes.timestamp DESC
            LIMIT @limit
            RETURN {
                query_id: cursor.ProviderReference,
                query_text: cursor.ProviderAttributes.query_text,
                result_count: cursor.ProviderAttributes.result_count,
                execution_time: cursor.ProviderAttributes.execution_time,
                context_handle: ctx.Handle,
                relationship_type: cursor.ProviderAttributes.relationship_type,
                previous_query_id: cursor.ProviderAttributes.previous_query_id,
                timestamp: cursor.ProviderAttributes.timestamp
            }
            """
            
            cursor = self._db.aql.execute(
                query,
                bind_vars={
                    "context_handle": str(context_handle),
                    "provider_id": str(QueryActivityProvider.QUERY_CONTEXT_PROVIDER_ID),
                    "limit": limit
                }
            )
            
            return [doc for doc in cursor]
            
        except Exception as e:
            self._logger.error(f"Error getting related queries: {e}")
            return []
    
    def get_query_path(self, query_id: uuid.UUID, max_depth: int = 10) -> List[Dict[str, Any]]:
        """
        Get the sequence of queries leading to the specified query.
        
        This method reconstructs the query exploration path by following
        the chain of previous_query_id references.
        
        Args:
            query_id: Query ID to find the path for
            max_depth: Maximum path depth to explore
            
        Returns:
            List of query dictionaries in the path (oldest to newest)
        """
        if not self.is_navigation_available():
            return []
            
        try:
            path = []
            current_id = query_id
            depth = 0
            
            # Follow the chain of previous_query_id references
            while current_id is not None and depth < max_depth:
                query_data = self.get_query_by_id(current_id)
                
                if not query_data:
                    break
                    
                path.append(query_data)
                
                # Move to the previous query in the chain
                if "previous_query_id" in query_data and query_data["previous_query_id"]:
                    current_id = uuid.UUID(query_data["previous_query_id"])
                else:
                    current_id = None
                    
                depth += 1
            
            # Reverse to get oldest-to-newest order
            return list(reversed(path))
            
        except Exception as e:
            self._logger.error(f"Error getting query path: {e}")
            return []
    
    def get_exploration_branches(
        self, 
        query_id: uuid.UUID,
        max_branches: int = 5,
        max_queries_per_branch: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get different exploration branches from a common query point.
        
        This method identifies divergent query paths that branch from
        the specified query.
        
        Args:
            query_id: Query ID to find branches from
            max_branches: Maximum number of branches to return
            max_queries_per_branch: Maximum queries per branch
            
        Returns:
            Dictionary mapping branch IDs to lists of query dictionaries
        """
        if not self.is_navigation_available():
            return {}
            
        try:
            # First, find queries that have this query as their previous_query_id
            query = """
            FOR ctx IN ActivityContext
            FOR cursor IN ctx.Cursors
            FILTER cursor.Provider == @provider_id
            FILTER cursor.ProviderAttributes.previous_query_id == @query_id
            SORT cursor.ProviderAttributes.timestamp DESC
            LIMIT @max_branches
            RETURN {
                query_id: cursor.ProviderReference,
                query_text: cursor.ProviderAttributes.query_text,
                result_count: cursor.ProviderAttributes.result_count,
                execution_time: cursor.ProviderAttributes.execution_time,
                context_handle: ctx.Handle,
                relationship_type: cursor.ProviderAttributes.relationship_type,
                previous_query_id: cursor.ProviderAttributes.previous_query_id,
                timestamp: cursor.ProviderAttributes.timestamp
            }
            """
            
            cursor = self._db.aql.execute(
                query,
                bind_vars={
                    "provider_id": str(QueryActivityProvider.QUERY_CONTEXT_PROVIDER_ID),
                    "query_id": str(query_id),
                    "max_branches": max_branches
                }
            )
            
            branches = {}
            for branch_start in cursor:
                branch_id = branch_start["query_id"]
                
                # For each branch start, follow its path
                branch_path = [branch_start]
                current_id = uuid.UUID(branch_id)
                
                # Follow the forward path (queries that have this as previous_query_id)
                for _ in range(max_queries_per_branch - 1):
                    next_queries = self._get_next_queries(current_id, limit=1)
                    
                    if not next_queries:
                        break
                        
                    branch_path.append(next_queries[0])
                    current_id = uuid.UUID(next_queries[0]["query_id"])
                
                branches[branch_id] = branch_path
                
            return branches
            
        except Exception as e:
            self._logger.error(f"Error getting exploration branches: {e}")
            return {}
    
    def _get_next_queries(
        self, 
        query_id: uuid.UUID,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get queries that have the specified query as their previous_query_id.
        
        Args:
            query_id: Query ID to find next queries for
            limit: Maximum number of queries to return
            
        Returns:
            List of query dictionaries
        """
        if not self.is_navigation_available():
            return []
            
        try:
            query = """
            FOR ctx IN ActivityContext
            FOR cursor IN ctx.Cursors
            FILTER cursor.Provider == @provider_id
            FILTER cursor.ProviderAttributes.previous_query_id == @query_id
            SORT cursor.ProviderAttributes.timestamp ASC
            LIMIT @limit
            RETURN {
                query_id: cursor.ProviderReference,
                query_text: cursor.ProviderAttributes.query_text,
                result_count: cursor.ProviderAttributes.result_count,
                execution_time: cursor.ProviderAttributes.execution_time,
                context_handle: ctx.Handle,
                relationship_type: cursor.ProviderAttributes.relationship_type,
                previous_query_id: cursor.ProviderAttributes.previous_query_id,
                timestamp: cursor.ProviderAttributes.timestamp
            }
            """
            
            cursor = self._db.aql.execute(
                query,
                bind_vars={
                    "provider_id": str(QueryActivityProvider.QUERY_CONTEXT_PROVIDER_ID),
                    "query_id": str(query_id),
                    "limit": limit
                }
            )
            
            return [doc for doc in cursor]
            
        except Exception as e:
            self._logger.error(f"Error getting next queries: {e}")
            return []
    
    def get_recent_queries(
        self, 
        hours: int = 24,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent queries within the specified time window.
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of queries to return
            
        Returns:
            List of query dictionaries
        """
        if not self.is_navigation_available():
            return []
            
        try:
            # Calculate time range
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=hours)
            
            query = """
            FOR ctx IN ActivityContext
            FILTER ctx.Timestamp >= @start_time AND ctx.Timestamp <= @end_time
            FOR cursor IN ctx.Cursors
            FILTER cursor.Provider == @provider_id
            SORT cursor.ProviderAttributes.timestamp DESC
            LIMIT @limit
            RETURN {
                query_id: cursor.ProviderReference,
                query_text: cursor.ProviderAttributes.query_text,
                result_count: cursor.ProviderAttributes.result_count,
                execution_time: cursor.ProviderAttributes.execution_time,
                context_handle: ctx.Handle,
                relationship_type: cursor.ProviderAttributes.relationship_type,
                previous_query_id: cursor.ProviderAttributes.previous_query_id,
                timestamp: cursor.ProviderAttributes.timestamp
            }
            """
            
            cursor = self._db.aql.execute(
                query,
                bind_vars={
                    "provider_id": str(QueryActivityProvider.QUERY_CONTEXT_PROVIDER_ID),
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "limit": limit
                }
            )
            
            return [doc for doc in cursor]
            
        except Exception as e:
            self._logger.error(f"Error getting recent queries: {e}")
            return []

    def get_query_history(
        self,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get the query history.
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List of query dictionaries
        """
        if not self.is_navigation_available():
            return []
            
        try:
            query = """
            FOR ctx IN ActivityContext
            FOR cursor IN ctx.Cursors
            FILTER cursor.Provider == @provider_id
            SORT cursor.ProviderAttributes.timestamp DESC
            LIMIT @limit
            RETURN {
                query_id: cursor.ProviderReference,
                query_text: cursor.ProviderAttributes.query_text,
                result_count: cursor.ProviderAttributes.result_count,
                execution_time: cursor.ProviderAttributes.execution_time,
                context_handle: ctx.Handle,
                relationship_type: cursor.ProviderAttributes.relationship_type,
                previous_query_id: cursor.ProviderAttributes.previous_query_id,
                timestamp: cursor.ProviderAttributes.timestamp
            }
            """
            
            cursor = self._db.aql.execute(
                query,
                bind_vars={
                    "provider_id": str(QueryActivityProvider.QUERY_CONTEXT_PROVIDER_ID),
                    "limit": limit
                }
            )
            
            return [doc for doc in cursor]
            
        except Exception as e:
            self._logger.error(f"Error getting query history: {e}")
            return []


def main():
    """Test functionality of QueryNavigator."""
    logging.basicConfig(level=logging.DEBUG)
    
    # Create navigator
    navigator = QueryNavigator(debug=True)
    
    if not navigator.is_navigation_available():
        print("Query navigation not available. Exiting.")
        return
    
    # Test query history retrieval
    print("\nQuery History:")
    history = navigator.get_query_history(limit=5)
    
    if not history:
        print("No query history found. Create some queries first.")
        
        # Create some test queries
        provider = QueryActivityProvider(debug=True)
        
        # Record a sequence of related queries
        query1 = "Find documents about Indaleko"
        query2 = "Find PDF documents about Indaleko"
        query3 = "Show me the authors of Indaleko documents"
        
        # Record queries
        print("\nCreating test queries...")
        q1_id, _ = provider.record_query(query1)
        print(f"Recorded query 1: {query1}")
        
        q2_id, _ = provider.record_query(query2, previous_query_id=q1_id)
        print(f"Recorded query 2: {query2}")
        
        q3_id, _ = provider.record_query(query3, previous_query_id=q2_id)
        print(f"Recorded query 3: {query3}")
        
        # Try again to get history
        print("\nQuery History (after creating test queries):")
        history = navigator.get_query_history(limit=5)
    
    for i, query in enumerate(history):
        print(f"{i+1}. {query['query_text']} (ID: {query['query_id']})")
        print(f"   Context: {query['context_handle']}")
        print(f"   Previous: {query['previous_query_id']}")
        print(f"   Relationship: {query['relationship_type']}")
    
    if history:
        # Use the most recent query for testing
        test_query_id = uuid.UUID(history[0]["query_id"])
        
        # Test get_query_path
        print("\nQuery Path:")
        path = navigator.get_query_path(test_query_id)
        
        for i, query in enumerate(path):
            print(f"{i+1}. {query['query_text']} (ID: {query['query_id']})")
            
        # Test get_related_queries
        print("\nRelated Queries:")
        related = navigator.get_related_queries(test_query_id)
        
        for i, query in enumerate(related):
            print(f"{i+1}. {query['query_text']} (ID: {query['query_id']})")
            
        # Test get_exploration_branches
        print("\nExploration Branches:")
        branches = navigator.get_exploration_branches(test_query_id)
        
        for branch_id, branch_path in branches.items():
            print(f"Branch starting with {branch_id}:")
            for i, query in enumerate(branch_path):
                print(f"  {i+1}. {query['query_text']} (ID: {query['query_id']})")


if __name__ == "__main__":
    main()