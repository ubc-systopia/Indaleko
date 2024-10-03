#!/usr/bin/env python3

from abc import ABC, abstractmethod
from typing import List, Dict, Any

class InterfaceBase(ABC):
    """
    Abstract base class for search tool interfaces.
    All concrete interface classes should inherit from this base class.
    """

    @abstractmethod
    def get_query(self) -> str:
        """
        Get a query from the user.

        Returns:
            str: The user's query
        """
        pass

    @abstractmethod
    def display_results(self, results: List[Dict[str, Any]], facets: List[str]) -> None:
        """
        Display search results and suggested facets to the user.

        Args:
            results (List[Dict[str, Any]]): The ranked search results
            facets (List[str]): Suggested facets for query refinement
        """
        pass

    @abstractmethod
    def continue_session(self) -> bool:
        """
        Ask the user if they want to continue the search session.

        Returns:
            bool: True if the user wants to continue, False otherwise
        """
        pass

    @abstractmethod
    def display_error(self, error_message: str) -> None:
        """
        Display an error message to the user.

        Args:
            error_message (str): The error message to display
        """
        pass

    @abstractmethod
    def get_result_selection(self, max_results: int) -> int:
        """
        Prompt the user to select a specific result for more details.

        Args:
            max_results (int): The number of results displayed

        Returns:
            int: The index of the selected result, or -1 if no selection
        """
        pass

    @abstractmethod
    def display_result_details(self, result: Dict[str, Any]) -> None:
        """
        Display detailed information about a specific result.

        Args:
            result (Dict[str, Any]): The result to display in detail
        """
        pass

    @abstractmethod
    def get_facet_selection(self, facets: List[str]) -> str:
        """
        Prompt the user to select a facet for query refinement.

        Args:
            facets (List[str]): The list of available facets

        Returns:
            str: The selected facet, or an empty string if no selection
        """
        pass

    @abstractmethod
    def initialize(self) -> None:
        """
        Perform any necessary initialization for the interface.
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """
        Perform any necessary cleanup when closing the interface.
        """
        pass
