"""
This implements the base class for semantic data collectors.

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

# standard imports
import os
import sys

from abc import ABC, abstractmethod

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Indaleko imports
# pylint: disable=wrong-import-position
from semantic.characteristics import SemanticDataCharacteristics


# pylint: enable=wrong-import-position


class SemanticCollector(ABC):
    """
    Base class for semantic data collectors.

    This class defines the common interface for semantic data collectors.
    """

    def __init__(self, **kwargs) -> None:
        """Initialize the semantic data collector."""

    @abstractmethod
    def get_collector_characteristics(self) -> list[SemanticDataCharacteristics]:
        """
        This call returns the characteristics of the semantic data provider.  This is
        intended to be used to help users understand the data provider and to
        help the system understand how to interact with the data provider.

        Returns:
            Dict: A dictionary containing the characteristics of the provider.
        """

    @abstractmethod
    def get_collector_name(self) -> str:
        """Get the name of the collector."""

    @abstractmethod
    def get_collector_id(self) -> str:
        """Get the UUID for the collector."""

    @abstractmethod
    def retrieve_data(self, data_id: str) -> dict:
        """
        This call retrieves the data associated with the provided data_id.

        Args:
            data_id (str): The data_id to retrieve

        Returns:
            Dict: The data associated with the data_id
        """

    @abstractmethod
    def get_collector_description(self) -> str:
        """Get the description of the collector."""

    @abstractmethod
    def get_json_schema(self) -> dict:
        """Get the JSON schema for the collector."""


def main() -> None:
    """This is a test interface for the semantic collector base."""
    ic("SemanticCollector test interface")


if __name__ == "__main__":
    main()
