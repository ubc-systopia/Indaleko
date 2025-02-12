"""
This module provides a CLI based interface for querying Indaleko.

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

# from icecream import ic
from typing import Any

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.utils.llm_connector.openai_connector import OpenAIConnector
# pylint: enable=wrong-import-position


class NLParser:
    """
    Natural Language Parser for processing user queries.
    """

    def __init__(self, llm_connector: OpenAIConnector):
        # Initialize any necessary components or models
        self.llm_connector = llm_connector

    def parse(self, query: str, schema: dict) -> dict[str, Any]:
        """
        Parse the natural language query into a structured format.

        Args:
            query (str): The user's natural language query

        Returns:
            dict[str, Any]: A structured representation of the query
        """
        assert isinstance(schema, dict), "Schema must be a dictionary"
        # The schema can be used to infer categories, which may be useful
        # for pre-processing the user prompt, which may help improve the
        # efficiency of query generation.

        # Placeholder implementation
        parsed_query = {
            "original_query": query,
            "intent": self._detect_intent(query),
            "entities": self._extract_entities(query),
            "filters": self._extract_filters(query),
            "schema": schema
        }
        return parsed_query

    def _detect_intent(self, query: str) -> str:
        """
        Detect the primary intent of the query.

        Args:
            query (str): The user's query

        Returns:
            str: The detected intent
        """
        # Implement intent detection logic
        assert isinstance(query, str), "Query must be a string"
        return "search"  # Placeholder

    def _extract_entities(self, query: str) -> dict[str, Any]:
        """
        Extract named entities from the query.

        Args:
            query (str): The user's query

        Returns:
            dict[str, Any]: Extracted entities
        """
        # Implement entity extraction logic
        assert isinstance(query, str), "Query must be a string"
        return {}  # Placeholder

    def _extract_filters(self, query: str) -> dict[str, Any]:
        """
        Extract any filters or constraints from the query.

        Args:
            query (str): The user's query

        Returns:
            dict[str, Any]: Extracted filters
        """
        # Implement filter extraction logic
        assert isinstance(query, str), "Query must be a string"
        return {}  # Placeholder
