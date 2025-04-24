"""
Indaleko Search CLI

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

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

from typing import Any

from icecream import ic


class CLI:
    def __init__(self):
        """
        This implements a simple command-line interface for the user to
        interact with Indaleko.
        """
        self.prompt = "Indaleko Search> "

    def initialize(self) -> None:
        """
        Initializes the CLI interface.
        """

    def get_query(self) -> str:
        """
        Prompts the user for a query and returns it.

        Returns:
            str: The user's query
        """
        return input(self.prompt).strip()

    def display_results(self, results: list[dict[str, Any]], facets: list[str]) -> None:
        """
        Displays the search results and suggested facets to the user.

        Args:
            results (List[Dict[str, Any]]): The ranked search results
            facets (List[str]): Suggested facets for query refinement
        """
        if not results:
            print("No results found.")
            return

        print("\nSearch Results:")
        ic(len(results))
        if len(results) < 10:
            for i, result in enumerate(results, 1):
                doc = result["original"]["result"]
                ic(doc["Record"]["Attributes"]["Path"])

        if facets:
            print("Suggested refinements:")
            for facet in facets:
                print(f"- {facet}")

    def continue_session(self) -> bool:
        """
        Asks the user if they want to continue the search session.

        Returns:
            bool: True if the user wants to continue, False otherwise
        """
        response = input("Do you want to perform another search? (y/n): ").strip().lower()
        return response == "y"

    def display_error(self, error_message: str) -> None:
        """
        Displays an error message to the user.

        Args:
            error_message (str): The error message to display
        """
        print(f"Error: {error_message}")

    def get_result_selection(self, max_results: int) -> int:
        """
        Prompts the user to select a specific result for more details.

        Args:
            max_results (int): The number of results displayed

        Returns:
            int: The index of the selected result, or -1 if no selection
        """
        while True:
            try:
                selection = input(
                    "Enter the number of a result to see more details (or press Enter to skip): ",
                )
                if not selection:
                    return -1
                selection = int(selection)
                if 1 <= selection <= max_results:
                    return selection - 1
                else:
                    print(f"Please enter a number between 1 and {max_results}")
            except ValueError:
                print("Please enter a valid number")

    def display_result_details(self, result: dict[str, Any]) -> None:
        """
        Displays detailed information about a specific result.

        Args:
            result (Dict[str, Any]): The result to display in detail
        """
        print("\nDetailed Result:")
        for key, value in result.items():
            print(f"{key.capitalize()}: {value}")

    def get_facet_selection(self, facets: list[str]) -> str:
        """
        Prompts the user to select a facet for query refinement.

        Args:
            facets (List[str]): The list of available facets

        Returns:
            str: The selected facet, or an empty string if no selection
        """
        if not facets:
            return ""

        print("\nAvailable facets for refinement:")
        for i, facet in enumerate(facets, 1):
            print(f"{i}. {facet}")

        while True:
            try:
                selection = input(
                    "Enter the number of a facet to refine your search (or press Enter to skip): ",
                )
                if not selection:
                    return ""
                selection = int(selection)
                if 1 <= selection <= len(facets):
                    return facets[selection - 1]
                else:
                    print(f"Please enter a number between 1 and {len(facets)}")
            except ValueError:
                print("Please enter a valid number")
