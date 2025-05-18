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
import sys
import time

from pathlib import Path
from typing import Any

from arango.exceptions import AQLQueryExecuteError
from arango.cursor import Cursor
from arango.result import Result
from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))


# pylint: disable=wrong-import-position
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from db import IndalekoDBConfig
from perf.perf_collector import IndalekoPerformanceDataCollector
from query.result_analysis.result_formatter import FormattedResults, deduplicate_results
from query.search_execution.query_executor.executor_base import ExecutorBase
from query.utils.llm_connector.llm_base import LLMBase


# pylint: enable=wrong-import-position

# ruff: noqa: S101,S311,FBT001,FBT002,G004
# pylint: disable=W1203

class AQLExecutor(ExecutorBase):
    """Executor for AQL (ArangoDB Query Language) queries."""

    @staticmethod
    def execute(
        query: str,
        data_connector: LLMBase,
        **kwargs: dict[str, Any],
    ) -> list[dict[str, Any]] | dict[str, Any] | FormattedResults:
        """
        Execute an AQL query using the provided data connector.

        Args:
            query (str): The AQL query to execute
            data_connector (Any): The connector to the ArangoDB data source
            **kwargs: Additional arguments for query execution
            Note: these values (via kwargs) are used by the AQL executor:
                bind_vars (Optional[Dict[str, Any]]): Bind variables for the query
                explain (bool): Whether to return the query plan instead of executing
                collect_performance (bool): Whether to collect performance metrics
                deduplicate (bool): Whether to deduplicate similar results
                similarity_threshold (float): Threshold for considering items
                    as duplicates (when deduplicate=True)

        Returns:
            list[dict[str, Any]], dict[str, Any] | FormattedResults
                - The query results (when explain=False, deduplicate=False)
                - The query execution plan (when explain=True)
                - A FormattedResults object with deduplicated
                  results (when explain=False, deduplicate=True)
        """
        assert isinstance(
            data_connector,
            IndalekoDBConfig,
        ), "Data connector must be an instance of IndalekoDBConfig"

        bind_vars = kwargs.get("bind_vars")
        explain = kwargs.get("explain", False)
        collect_performance = kwargs.get("collect_performance", False)
        deduplicate = kwargs.get("deduplicate", False)
        similarity_threshold = kwargs.get("similarity_threshold", 0.85)

        # Initialize bind variables if not provided
        if bind_vars is None:
            bind_vars = {}

        # If explain mode is requested, return the query plan
        if explain:
            return AQLExecutor.explain_query(query, data_connector, bind_vars)

        try:
            # Execute the AQL query
            class LocalExecutor:
                """A local executor class to handle query execution."""
                def __init__(self, query: str, bind_vars: dict[str, Any] | None = None) -> None:
                    self.query = query
                    self.bind_vars = bind_vars or {}
                    self.retry_query = False

                def execute_query(self, **_kwargs: dict | None) -> Result[Cursor]:
                    """Execute the AQL query."""
                    result = data_connector.db.aql.execute(
                        self.query,
                        bind_vars=self.bind_vars,
                    )
                    _result = [doc for doc in result if "ERR 1551" in str(doc)]
                    if len(_result) > 0:
                        ic(f"**** Query result: {_result}")
                    if not self.retry_query:
                        return result
                    if (
                        result["original"].get("result") is not None and
                        "ERR 1551" in result["original"]["result"]
                    ):
                        ic('Rewriting query to avoid "ERR 1551" error')
                        revised_query = self.query
                        for key, value in self.bind_vars.items():
                            bind_key = f"@{key}"
                            bind_value = f'"{value}"'
                            revised_query = revised_query.replace(bind_key, bind_value)
                        result = data_connector.db.aql.execute(revised_query)
                    return result

            executor = LocalExecutor(query, bind_vars)

            def process_query_response(**kwargs: dict | None) -> dict:
                result = kwargs.get("result")
                if not isinstance(result, Cursor):
                    raise TypeError("Expected a Cursor object")
                return {"query response": result}

            # If collecting performance metrics, prepare performance info
            performance_info = None
            if collect_performance:
                perf_data = IndalekoPerformanceDataCollector.measure_performance(
                    task_func=executor.execute_query,
                    source=IndalekoSourceIdentifierDataModel(
                        Identifier="6b2c9343-d6f5-4360-b43c-39094f83170f",
                        Version="1.0,0",
                        Description="AQL execution",
                    ),
                    description="Executing AQL query",
                    MachineIdentifier=None,
                    query=query,
                    bind_vars=bind_vars,
                    process_results_func=process_query_response,
                )

                # Create performance metadata entry
                performance_info = {
                    "performance": {
                        "execution_time_seconds": perf_data.ElapsedTime,
                        "cpu": {
                            "user_time": perf_data.UserCPUTime,
                            "system_time": perf_data.SystemCPUTime,
                        },
                        "memory": {"vms": perf_data.PeakMemoryUsage},
                        "io": {
                            "read_bytes": perf_data.IoReadBytes,
                            "write_bytes": perf_data.IoWriteBytes,
                        },
                        "threads": perf_data.ThreadCount,
                        "query_length": len(query),
                    },
                }
                query_result = perf_data.AdditionalData["query response"]
            else:
                query_result = executor.execute_query()

            # Format the results with or without deduplication
            formatted_results = AQLExecutor.format_results(
                query_result,
                deduplicate=deduplicate,
                similarity_threshold=similarity_threshold,
            )

            # Add performance info if available and not deduplicating
            if performance_info and not deduplicate:
                formatted_results.append(performance_info)

        except TimeoutError as e:
            ic(
                f"The query execution has timed out:\n\tquery: {query}\n\tException: {e}",
            )
            ic("Terminating")
            sys.exit(1)
        except AQLQueryExecuteError as e:
            ic(
                f"""An error occurred while executing the AQL query:\n
                \tquery: {query}\n\tException: {e}""",
            )
            return [{"result": f"Exception: {e!s}"}]
        return formatted_results

    @staticmethod
    def explain_query(
        query: str,
        data_connector: LLMBase,
        bind_vars: dict[str, Any] | None = None,
        all_plans: bool = False,
        max_plans: int = 5,
    ) -> dict[str, Any]:
        """
        Get the execution plan for an AQL query without executing it.

        Args:
            query (str): The AQL query to explain
            data_connector (Any): The connector to the ArangoDB data source
            bind_vars (Optional[Dict[str, Any]]): Bind variables for the query
            all_plans (bool): Whether to return all possible execution plans
            max_plans (int): Maximum number of plans to return when all_plans is True

        Returns:
            Dict[str, Any]: The query execution plan(s) with analysis
        """
        assert isinstance(
            data_connector,
            IndalekoDBConfig,
        ), "Data connector must be an instance of IndalekoDBConfig"

        # Initialize bind variables if not provided
        if bind_vars is None:
            bind_vars = {}

        try:
            # Check if we have parameters in the query for which we don't have bind values
            import re

            param_pattern = r"@([a-zA-Z0-9_]+)"
            params_in_query = set(re.findall(param_pattern, query))

            # Log parameters found in query
            ic(f"Parameters found in query: {params_in_query}")
            ic(f"Bind variables provided: {bind_vars.keys()}")

            # Add some sample values for common parameters if they're missing
            for param in params_in_query:
                if param not in bind_vars:
                    if param.lower() in ['size', 'filesize', 'minsize']:
                        bind_vars[param] = 1000000
                    elif param.lower() in ['timestamp', 'date', 'time']:
                        bind_vars[param] = "2024-01-01"
                    elif param.lower() in ['path', 'file', 'filename']:
                        bind_vars[param] = "test.pdf"
                    elif param.lower() in ['limit', 'max', 'count']:
                        bind_vars[param] = 10
                    else:
                        # Default to a string for unknown parameters
                        bind_vars[param] = "sample_value"

            # Log the final set of bind variables
            ic(f"Final bind variables: {bind_vars}")

            # Build explain options - pass directly as kwargs
            # Create the options for explain
            kwargs = {}
            if bind_vars:
                kwargs["bind_vars"] = bind_vars

            # Add all_plans parameter if it's True
            if all_plans:
                kwargs["all_plans"] = all_plans
                kwargs["max_plans"] = max_plans

            # Call ArangoDB's explain method
            ic(f"Calling ArangoDB explain with kwargs: {kwargs}")
            explain_result = data_connector.db.aql.explain(query, **kwargs)

            # Enhance the explain result with additional analysis
            enhanced_result = AQLExecutor._enhance_explain_result(explain_result, query)

            # Add the bind variables used to the result
            enhanced_result["bind_vars"] = bind_vars

            return enhanced_result

        except AQLQueryExecuteError as e:
            ic(
                f"An error occurred while explaining the AQL query:\n\tquery: {query}\n\tException: {e}",
            )
            return {
                'error': str(e),
                'query': query,
                'bind_vars': bind_vars,
                'analysis': {
                    'warnings': [str(e)],
                    'recommendations': ["Check query syntax and ensure bind variables are provided for all parameters"]
                }
            }

    @staticmethod
    def _enhance_explain_result(explain_result: Any, query: str) -> dict[str, Any]:
        """
        Enhance the ArangoDB explain result with additional analysis.

        Args:
            explain_result (Any): The raw explain result from ArangoDB
            query (str): The original query string

        Returns:
            Dict[str, Any]: Enhanced explain result with additional analysis
        """
        # Create an enhanced result dictionary
        enhanced = {"query": query, "raw_result": explain_result}

        # Initialize analysis section with default values
        analysis = {
            "summary": {
                "estimated_cost": 0,
                "collections_used": 0,
                "operations": 0,
                "cacheable": False,
            },
            "warnings": [],
            "recommendations": [],
        }

        # Process the explain result based on its type
        if isinstance(explain_result, dict):
            # Standard dictionary result - extract plan data
            plan = explain_result.get("plan", {})

            # Update analysis with plan data
            analysis["summary"].update({
                "estimated_cost": plan.get("estimatedCost", 0),
                "collections_used": len(plan.get("collections", [])),
                "operations": len(plan.get("nodes", [])),
                "cacheable": explain_result.get("cacheable", False)
            })

            # Extract plan details
            nodes = plan.get("nodes", [])
            collection_scans = [n for n in nodes if n.get("type") == "EnumerateCollectionNode"]
            index_nodes = [n for n in nodes if n.get("type") == "IndexNode"]

            # Add warnings for full collection scans
            if collection_scans:
                scan_collections = [n.get("collection", "unknown") for n in collection_scans]
                analysis["warnings"].append(
                    f"Full collection scan(s) detected on: {', '.join(scan_collections)}",
                )
                analysis["recommendations"].append(
                    "Consider adding indexes to collections that are being full-scanned",
                )

            # Add info about indexes being used
            if index_nodes:
                index_info = []
                for node in index_nodes:
                    collection = node.get("collection", "unknown")
                    index_type = node.get("indexes", [{}])[0].get("type", "unknown")
                    index_info.append(f"{collection} ({index_type})")

                analysis["summary"]["indexes_used"] = index_info
            else:
                analysis["warnings"].append("No indexes are being used in this query")
                analysis["recommendations"].append(
                    "Review your query and consider adding appropriate indexes",
                )

            # Check for very high estimated cost
            if plan.get("estimatedCost", 0) > 1000:
                analysis["warnings"].append(
                    f"High estimated cost: {plan.get('estimatedCost')}",
                )
                analysis["recommendations"].append(
                    "Query may be inefficient and could benefit from optimization",
                )

            # Add any warnings from ArangoDB itself
            for warning in explain_result.get("warnings", []):
                if isinstance(warning, dict):
                    analysis["warnings"].append(warning.get("message", str(warning)))
                else:
                    analysis["warnings"].append(str(warning))

            # Copy relevant parts from explain_result to enhanced
            for key in ["plan", "plans", "stats", "cacheable", "warnings"]:
                if key in explain_result:
                    enhanced[key] = explain_result[key]

        elif isinstance(explain_result, list):
            # If the result is a list, it could be an array of plans or an error
            analysis["warnings"].append("Received list result instead of expected plan structure")
            analysis["recommendations"].append("Check query syntax and database configuration")

        elif isinstance(explain_result, str):
            # If the result is a string, it's probably an error message
            analysis["warnings"].append(f"Explain returned message: {explain_result}")

        else:
            # Unknown result type
            analysis["warnings"].append(f"Unexpected explain result type: {type(explain_result)}")

        # Add analysis to the enhanced result
        enhanced["analysis"] = analysis

        return enhanced

    @staticmethod
    def validate_query(query: str) -> bool:
        """
        Validate the AQL query before execution.

        Args:
            query (str): The AQL query to validate

        Returns:
            bool: True if the query is valid, False otherwise
        """
        # Basic validation - check for FOR and RETURN keywords
        if "FOR" not in query or "RETURN" not in query:
            return False

        # Check for balanced parentheses, brackets, and braces
        parens_stack = []
        for char in query:
            if char in "({[":
                parens_stack.append(char)
            elif char in ")}]":
                if not parens_stack:
                    return False
                last_open = parens_stack.pop()
                if (
                    (char == ")" and last_open != "(")
                    or (char == "}" and last_open != "{")
                    or (char == "]" and last_open != "[")
                ):
                    return False

        # Check if all parentheses were closed
        if parens_stack:
            return False

        return True

    @staticmethod
    def format_results(
        raw_results: Any,
        deduplicate: bool = False,
        similarity_threshold: float = 0.85,
    ) -> list[dict[str, Any]] | FormattedResults:
        """
        Format the raw AQL query results into a standardized format.

        Args:
            raw_results (Any): The raw results from the AQL query execution
            deduplicate (bool): Whether to deduplicate similar results
            similarity_threshold (float): Threshold for considering items as
                duplicates (when deduplicate=True)

        Returns:
            list[dict[str, Any]] | FormattedResults:
                - A list of formatted results (when deduplicate=False)
                - A FormattedResults object with deduplicated results (when deduplicate=True)
        """
        formatted_results = []

        # Extract any performance information before processing
        performance_info = None
        if isinstance(raw_results, list):
            for item in raw_results:
                if isinstance(item, dict) and "performance" in item:
                    performance_info = item
                    break

        # Handle case when raw_results is already a list
        if isinstance(raw_results, list):
            for item in raw_results:
                # Skip performance info for deduplication
                if isinstance(item, dict) and "performance" in item:
                    if not deduplicate:
                        formatted_results.append(item)
                    continue

                if isinstance(item, dict):
                    formatted_results.append(item)
                else:
                    formatted_results.append({"result": item})
        else:
            # Handle case when raw_results is a cursor or other iterable
            try:
                for item in raw_results:
                    if isinstance(item, dict) and "performance" in item:
                        if not deduplicate:
                            formatted_results.append(item)
                        continue

                    if isinstance(item, dict):
                        formatted_results.append(item)
                    else:
                        formatted_results.append({"result": item})
            except TypeError:
                # If raw_results is not iterable, wrap it in a single result
                formatted_results.append({"result": raw_results})

        # Apply deduplication if requested
        if deduplicate:
            deduped_results = deduplicate_results(
                formatted_results,
                similarity_threshold=similarity_threshold,
            )

            # Add performance info if available
            if (performance_info and
                "performance" in performance_info and
                "execution_time_seconds" in performance_info["performance"]
            ):
                deduped_results.query_time = performance_info["performance"]["execution_time_seconds"]

            return deduped_results

        return formatted_results
