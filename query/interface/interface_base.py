from abc import ABC, abstractmethod
from typing import Any


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

    @abstractmethod
    def display_results(self, results: list[dict[str, Any]], facets: list[str]) -> None:
        """
        Display search results and suggested facets to the user.

        Args:
            results (List[Dict[str, Any]]): The ranked search results
            facets (List[str]): Suggested facets for query refinement
        """

    @abstractmethod
    def continue_session(self) -> bool:
        """
        Ask the user if they want to continue the search session.

        Returns:
            bool: True if the user wants to continue, False otherwise
        """

    @abstractmethod
    def display_error(self, error_message: str) -> None:
        """
        Display an error message to the user.

        Args:
            error_message (str): The error message to display
        """

    @abstractmethod
    def get_result_selection(self, max_results: int) -> int:
        """
        Prompt the user to select a specific result for more details.

        Args:
            max_results (int): The number of results displayed

        Returns:
            int: The index of the selected result, or -1 if no selection
        """

    @abstractmethod
    def display_result_details(self, result: dict[str, Any]) -> None:
        """
        Display detailed information about a specific result.

        Args:
            result (Dict[str, Any]): The result to display in detail
        """

    @abstractmethod
    def get_facet_selection(self, facets: list[str]) -> str:
        """
        Prompt the user to select a facet for query refinement.

        Args:
            facets (List[str]): The list of available facets

        Returns:
            str: The selected facet, or an empty string if no selection
        """

    @abstractmethod
    def initialize(self) -> None:
        """Perform any necessary initialization for the interface."""

    @abstractmethod
    def cleanup(self) -> None:
        """Perform any necessary cleanup when closing the interface."""
