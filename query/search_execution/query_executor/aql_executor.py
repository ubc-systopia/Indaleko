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
from typing import Any

from arango.exceptions import AQLQueryExecuteError
from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from db import IndalekoDBConfig
from perf.perf_collector import IndalekoPerformanceDataCollector
from query.result_analysis.result_formatter import FormattedResults, deduplicate_results
from query.search_execution.query_executor.executor_base import ExecutorBase

# pylint: enable=wrong-import-position


class AQLExecutor(ExecutorBase):
    """
    Executor for AQL (ArangoDB Query Language) queries.
    """

    @staticmethod
    def execute(
        query: str,
        data_connector: Any,
        bind_vars: dict[str, Any] | None = None,
        explain: bool = False,
        collect_performance: bool = False,
        deduplicate: bool = False,
        similarity_threshold: float = 0.85,
    ) -> list[dict[str, Any]] | dict[str, Any] | FormattedResults:
        """
        Execute an AQL query using the provided data connector.

        Args:
            query (str): The AQL query to execute
            data_connector (Any): The connector to the ArangoDB data source
            bind_vars (Optional[Dict[str, Any]]): Bind variables for the query
            explain (bool): Whether to return the query plan instead of executing
            collect_performance (bool): Whether to collect performance metrics
            deduplicate (bool): Whether to deduplicate similar results
            similarity_threshold (float): Threshold for considering items as duplicates (when deduplicate=True)

        Returns:
            Union[List[Dict[str, Any]], Dict[str, Any], FormattedResults]:
                - The query results (when explain=False, deduplicate=False)
                - The query execution plan (when explain=True)
                - A FormattedResults object with deduplicated results (when explain=False, deduplicate=True)
        """
        assert isinstance(
            data_connector, IndalekoDBConfig,
        ), "Data connector must be an instance of IndalekoDBConfig"

        # Initialize bind variables if not provided
        if bind_vars is None:
            bind_vars = {}

        ic(query)

        # If explain mode is requested, return the query plan
        if explain:
            return AQLExecutor.explain_query(query, data_connector, bind_vars)

        # Set up performance collection if requested
        perf_collector = None
        if collect_performance:
            perf_collector = IndalekoPerformanceDataCollector()
            perf_collector.start()
            start_time = time.time()

        try:
            # Execute the AQL query
            raw_results = data_connector._arangodb.aql.execute(
                query, bind_vars=bind_vars,
            )

            # If collecting performance metrics, prepare performance info
            performance_info = None
            if collect_performance and perf_collector:
                perf_collector.stop()
                execution_time = time.time() - start_time
                perf_data = perf_collector.get_performance_data()

                # Create performance metadata entry
                performance_info = {
                    "performance": {
                        "execution_time_seconds": execution_time,
                        "cpu": {
                            "user_time": perf_data.user_time,
                            "system_time": perf_data.system_time,
                        },
                        "memory": {"rss": perf_data.rss, "vms": perf_data.vms},
                        "io": {
                            "read_count": perf_data.io_read_count,
                            "write_count": perf_data.io_write_count,
                            "read_bytes": perf_data.io_read_bytes,
                            "write_bytes": perf_data.io_write_bytes,
                        },
                        "threads": perf_data.num_threads,
                        "query_length": len(query),
                    },
                }

            # Format the results with or without deduplication
            formatted_results = AQLExecutor.format_results(
                raw_results,
                deduplicate=deduplicate,
                similarity_threshold=similarity_threshold,
            )

            # Add performance info if available and not deduplicating
            if performance_info and not deduplicate:
                formatted_results.append(performance_info)

            return formatted_results

        except TimeoutError as e:
            ic(
                f"The query execution has timed out:\n\tquery: {query}\n\tException: {e}",
            )
            ic("Terminating")
            sys.exit(1)
        except AQLQueryExecuteError as e:
            ic(
                f"An error occurred while executing the AQL query:\n\tquery: {query}\n\tException: {e}",
            )
            return [{"result": f"Exception: {e!s}"}]
        finally:
            # Ensure performance collection is stopped if we have an exception
            if collect_performance and perf_collector:
                perf_collector.stop()

    @staticmethod
    def explain_query(
        query: str,
        data_connector: Any,
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
            data_connector, IndalekoDBConfig,
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
                    if param.lower() in ["size", "filesize", "minsize"]:
                        bind_vars[param] = 1000000
                    elif param.lower() in ["timestamp", "date", "time"]:
                        bind_vars[param] = "2024-01-01"
                    elif param.lower() in [
                        "path",
                        "file",
                        "filename",
                        "filename",
                        "fname",
                        "filepath",
                    ]:
                        bind_vars[param] = "test.pdf"
                    elif param.lower() in ["name", "label", "title"]:
                        bind_vars[param] = "example_name"
                    elif param.lower() in ["limit", "max", "count"]:
                        bind_vars[param] = 10
                    else:
                        # Default to a string for unknown parameters that preserves the parameter name
                        bind_vars[param] = f"sample_value_for_{param}"

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
            explain_result = data_connector._arangodb.aql.explain(query, **kwargs)

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
                "error": str(e),
                "query": query,
                "bind_vars": bind_vars,
                "analysis": {
                    "warnings": [str(e)],
                    "recommendations": [
                        "Check query syntax and ensure bind variables are provided for all parameters",
                    ],
                },
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
            analysis["summary"].update(
                {
                    "estimated_cost": plan.get("estimatedCost", 0),
                    "collections_used": len(plan.get("collections", [])),
                    "operations": len(plan.get("nodes", [])),
                    "cacheable": explain_result.get("cacheable", False),
                },
            )

            # Extract plan details
            nodes = plan.get("nodes", [])
            collection_scans = [
                n for n in nodes if n.get("type") == "EnumerateCollectionNode"
            ]
            index_nodes = [n for n in nodes if n.get("type") == "IndexNode"]

            # Add warnings for full collection scans
            if collection_scans:
                scan_collections = [
                    n.get("collection", "unknown") for n in collection_scans
                ]
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
            analysis["warnings"].append(
                "Received list result instead of expected plan structure",
            )
            analysis["recommendations"].append(
                "Check query syntax and database configuration",
            )

        elif isinstance(explain_result, str):
            # If the result is a string, it's probably an error message
            analysis["warnings"].append(f"Explain returned message: {explain_result}")

        else:
            # Unknown result type
            analysis["warnings"].append(
                f"Unexpected explain result type: {type(explain_result)}",
            )

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
        raw_results: Any, deduplicate: bool = False, similarity_threshold: float = 0.85,
    ) -> list[dict[str, Any]] | FormattedResults:
        """
        Format the raw AQL query results into a standardized format.

        Args:
            raw_results (Any): The raw results from the AQL query execution
            deduplicate (bool): Whether to deduplicate similar results
            similarity_threshold (float): Threshold for considering items as duplicates (when deduplicate=True)

        Returns:
            Union[List[Dict[str, Any]], FormattedResults]:
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
                formatted_results, similarity_threshold=similarity_threshold,
            )

            # Add performance info if available
            if performance_info and "performance" in performance_info:
                if "execution_time_seconds" in performance_info["performance"]:
                    deduped_results.query_time = performance_info["performance"][
                        "execution_time_seconds"
                    ]

            return deduped_results

        return formatted_results
