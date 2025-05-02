"""
Define translator base class for query processing.

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

import os
import sys

from abc import ABC, abstractmethod
from pathlib import Path


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))


# pylint: disable=wrong-import-position
from query.query_processing.data_models.translator_input import TranslatorInput
from query.query_processing.data_models.translator_response import TranslatorOutput


# pylint: enable=wrong-import-position


class TranslatorBase(ABC):
    """Abstract base class for query translators."""

    @abstractmethod
    def translate(
        self: "TranslatorBase",
        input_data: TranslatorInput,
    ) -> TranslatorOutput:
        """
        Translate a parsed query into a specific query language.

        Args:
            input_data (TranslatorInput): The input data containing the parsed query
                and any additional parameters.

        Returns:
            str: The translated query string
        """

    @abstractmethod
    def validate_query(self, query: str) -> bool:
        """
        Validate the translated query.

        Args:
            query (str): The translated query

        Returns:
            bool: True if the query is valid, False otherwise
        """

    @abstractmethod
    def optimize_query(self, query: str) -> str:
        """
        Optimize the translated query for better performance.

        Args:
            query (str): The translated query

        Returns:
            str: The optimized query
        """
