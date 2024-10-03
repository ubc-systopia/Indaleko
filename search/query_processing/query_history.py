#!/usr/bin/env python3

from typing import List, Dict, Any
from collections import deque

class QueryHistory:
    """
    Manages the history of user queries and their results.
    """

    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.history = deque(maxlen=max_history)

    def add(self, query: str, results: List[Dict[str, Any]]) -> None:
        """
        Add a query and its results to the history.

        Args:
            query (str): The user's query
            results (List[Dict[str, Any]]): The search results for the query
        """
        self.history.append({"query": query, "results": results})

    def get_recent_queries(self, n: int = 5) -> List[str]:
        """
        Get the n most recent queries.

        Args:
            n (int): Number of recent queries to retrieve

        Returns:
            List[str]: List of recent queries
        """
        return [item["query"] for item in list(self.history)[-n:]]

    def get_last_query(self) -> Dict[str, Any]:
        """
        Get the most recent query and its results.

        Returns:
            Dict[str, Any]: The last query and its results, or None if history is empty
        """
        return self.history[-1] if self.history else None

    def clear(self) -> None:
        """
        Clear the query history.
        """
        self.history.clear()

    def get_full_history(self) -> List[Dict[str, Any]]:
        """
        Get the full query history.

        Returns:
            List[Dict[str, Any]]: The full query history
        """
        return list(self.history)

    def find_similar_queries(self, query: str) -> List[Dict[str, Any]]:
        """
        Find queries in the history that are similar to the given query.

        Args:
            query (str): The query to compare against

        Returns:
            List[Dict[str, Any]]: Similar queries and their results
        """
        # Implement similarity comparison logic
        # This is a placeholder implementation
        return [item for item in self.history if query.lower() in item["query"].lower()]
