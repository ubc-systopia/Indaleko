"""
Query execution tool for Indaleko.

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

from arango.cursor import Cursor
from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from db import IndalekoDBConfig
from query.search_execution.query_executor.aql_executor import AQLExecutor
from query.tools.base import (
    BaseTool,
    ToolDefinition,
    ToolInput,
    ToolOutput,
    ToolParameter,
)


class QueryExecutorTool(BaseTool):
    """Tool for executing AQL queries with optional EXPLAIN analysis."""

    def __init__(self) -> None:
        """Initialize the query executor tool."""
        super().__init__()
        self._db_config = None
        self._executor = AQLExecutor()

    @property
    def definition(self) -> ToolDefinition:
        """Get the tool definition."""
        return ToolDefinition(
            name="query_executor",
            description="Executes AQL queries against the database with optional EXPLAIN analysis.",
            parameters=[
                ToolParameter(
                    name="query",
                    description="The AQL query to execute",
                    type="string",
                    required=True,
                ),
                ToolParameter(
                    name="bind_vars",
                    description="Bind variables for the query",
                    type="object",
                    required=False,
                    default={},
                ),
                ToolParameter(
                    name="db_config_path",
                    description="Path to the database configuration file",
                    type="string",
                    required=False,
                ),
                ToolParameter(
                    name="explain_only",
                    description="Only return the query plan without executing the query",
                    type="boolean",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="include_plan",
                    description="Include the query plan in the results",
                    type="boolean",
                    required=False,
                    default=True,
                ),
                ToolParameter(
                    name="all_plans",
                    description="Include alternative query plans",
                    type="boolean",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="max_plans",
                    description="Maximum number of alternative plans to include",
                    type="integer",
                    required=False,
                    default=5,
                ),
                ToolParameter(
                    name="collect_performance",
                    description="Collect and include performance metrics",
                    type="boolean",
                    required=False,
                    default=True,
                ),
            ],
            returns={
                "results": "The query results (if query was executed)",
                "execution_plan": "The query execution plan",
                "performance": "Performance metrics (if collected)",
            },
            examples=[
                {
                    "parameters": {
                        "query": "FOR doc IN Objects FILTER doc.Label LIKE '%pdf' RETURN doc",
                        "include_plan": True,
                        "collect_performance": True,
                    },
                    "returns": {
                        "results": ["..."],
                        "execution_plan": {"...": "..."},
                        "performance": {"execution_time_seconds": 0.123},
                    },
                },
            ],
        )

    def _initialize_db_config(self, db_config_path: str | None = None) -> None:
        """
        Initialize the database configuration.

        Args:
            db_config_path (Optional[str]): Path to the database configuration file.
        """
        if db_config_path is None:
            config_dir = os.path.join(os.environ.get("INDALEKO_ROOT"), "config")
            db_config_path = os.path.join(config_dir, "indaleko-db-config.ini")

        self._db_config = IndalekoDBConfig(config_file=db_config_path)

    def execute(self, input_data: ToolInput) -> ToolOutput:
        """
        Execute the query executor tool.

        Args:
            input_data (ToolInput): The input data for the tool.

        Returns:
            ToolOutput: The result of the tool execution.
        """
        # Extract parameters
        query = input_data.parameters["query"]
        bind_vars = input_data.parameters.get("bind_vars", {})
        db_config_path = input_data.parameters.get("db_config_path")
        explain_only = input_data.parameters.get("explain_only", False)
        include_plan = input_data.parameters.get("include_plan", True)
        all_plans = input_data.parameters.get("all_plans", False)
        max_plans = input_data.parameters.get("max_plans", 5)
        collect_performance = input_data.parameters.get("collect_performance", True)

        # Initialize DB config if needed
        if self._db_config is None:
            self._initialize_db_config(db_config_path)

        ic(query)

        try:
            # Always get the execution plan
            execution_plan = None
            if include_plan or explain_only:
                execution_plan = self._executor.explain_query(
                    query=query,
                    data_connector=self._db_config,
                    bind_vars=bind_vars,
                    all_plans=all_plans,
                    max_plans=max_plans,
                )

            # Execute the query if not in explain-only mode
            results = None
            if not explain_only:
                results = self._executor.execute(
                    query=query,
                    data_connector=self._db_config,
                    bind_vars=bind_vars,
                    collect_performance=collect_performance,
                )

            # Extract performance metrics if present
            performance = None
            if results and isinstance(results, list) and len(results) > 0:
                for item in results:
                    if isinstance(item, dict) and "performance" in item:
                        performance = item["performance"]
                        # Remove the performance item from the results
                        results.remove(item)
                        break

            # Return the result
            result_data = {}

            # Make sure results is JSON serializable
            if results is not None:
                # Convert ArangoDB Cursor to list if needed
                if isinstance(results, Cursor):
                    # Convert cursor to list of documents
                    result_list = list(results)
                    result_data["results"] = result_list
                else:
                    result_data["results"] = results

            if execution_plan is not None:
                result_data["execution_plan"] = execution_plan
            if performance is not None:
                result_data["performance"] = performance

            return ToolOutput(
                tool_name=self.definition.name,
                success=True,
                result=result_data,
                elapsed_time=0.0,  # Will be filled by wrapper
            )

        except (GeneratorExit , RecursionError , MemoryError , NotImplementedError ) as e:
            ic(f"Error executing query: {e}")
            return ToolOutput(
                tool_name=self.definition.name,
                success=False,
                error=str(e),
                elapsed_time=0.0,  # Will be filled by wrapper
            )
