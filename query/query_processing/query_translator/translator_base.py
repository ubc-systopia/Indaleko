"""
This module defines the translator framework for queries
to use with an LLM.

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

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.query_processing.data_models.translator_input import TranslatorInput
from query.query_processing.data_models.translator_response import TranslatorOutput

# pylint: enable=wrong-import-position


class TranslatorBase(ABC):
    """
    Abstract base class for query translators.
    """

    @abstractmethod
    def translate(
        self: "TranslatorBase",
        input_data: TranslatorInput,
    ) -> TranslatorOutput:
        """
        Translate a parsed query into a specific query language.

        Args:
            parsed_query (Dict[str, Any]): The parsed query from NLParser
            llm_connector (Any): Connector to the LLM service

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
