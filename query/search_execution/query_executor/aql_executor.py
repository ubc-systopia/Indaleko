"""
This module implements an execution mechanism for AQL queries.

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
from arango.exceptions import AQLQueryExecuteError
import sys

from typing import Any

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from db import IndalekoDBConfig
from query.search_execution.query_executor.executor_base import ExecutorBase

# pylint: enable=wrong-import-position


class AQLExecutor(ExecutorBase):
    """
    Executor for AQL (ArangoDB Query Language) queries.
    """

    @staticmethod
    def execute(query: str, data_connector: Any) -> list[dict[str, Any]]:
        """
        Execute an AQL query using the provided data connector.

        Args:
            query (str): The AQL query to execute
            data_connector (Any): The connector to the ArangoDB data source

        Returns:
            List[Dict[str, Any]]: The query results
        """
        assert isinstance(
            data_connector, IndalekoDBConfig
        ), "Data connector must be an instance of IndalekoDBConfig"
        ic(query)
        try:
            raw_results = data_connector.db.aql.execute(query)
            return AQLExecutor.format_results(raw_results)
        except TimeoutError as e:
            ic(
                f"The query execution has timed out:\n\tquery: {query}\n\tException: {e}"
            )
            ic("Terminating")
            sys.exit(1)
        except AQLQueryExecuteError as e:
            ic(
                f"An error occurred while executing the AQL query:\n\tquery: {query}\n\tException: {e}"
            )
            raw_results = [{'result': f'Exception: {str(e)}'}]

    @staticmethod
    def validate_query(query: str) -> bool:
        """
        Validate the AQL query before execution.

        Args:
            query (str): The AQL query to validate

        Returns:
            bool: True if the query is valid, False otherwise
        """
        # Implement AQL query validation logic
        # This is a placeholder implementation
        return "FOR" in query and "RETURN" in query

    @staticmethod
    def format_results(raw_results: Any) -> list[dict[str, Any]]:
        """
        Format the raw AQL query results into a standardized format.

        Args:
            raw_results (Any): The raw results from the AQL query execution

        Returns:
            List[Dict[str, Any]]: The formatted results
        """
        # Implement result formatting logic
        # This is a placeholder implementation
        return [{"result": item} for item in raw_results]
