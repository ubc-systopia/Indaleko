"""
Evaluate AQL query performance and log slow queries.

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

import json
import logging
import os
import sys
import time

from logging import getLogger
from pathlib import Path
from typing import Any

from arango import ArangoClient
from arango.cursor import Cursor
from arango.exceptions import AQLQueryExecuteError
from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from db.db_config import IndalekoDBConfig


# pylint: enable=wrong-import-position


# Configure logger
logger = getLogger("QueryPerformanceLogger")


class TimedAQLExecute:
    """Handle a timed AQL query execution."""

    def __init__(
            self,
            *,
            db: IndalekoDBConfig | None = IndalekoDBConfig(),
            description: str | None = None,
            query: str | None = None,
            bind_vars: dict[str, Any] | None = None,
            threshold: float = 5.0,
            capture_explain: bool = True,
    ) -> None:
        """
        Initialize the timed AQL execution.

        Args:
            db: An ArangoDB database instance or client
            query: The AQL query string to execute
            count_query: The AQL count query string to execute
            bind_vars: Variables to bind to the query
            threshold: Time threshold in seconds to trigger logging (default: 5.0)
            capture_explain: Whether to capture EXPLAIN data for slow queries (default: True)
        """
        if not isinstance(db, IndalekoDBConfig):
            raise TypeError("db must be an instance of IndalekoDBConfig")
        self._arango_client : ArangoClient = db.get_arangodb()
        self._description = description or "Timed AQL Execute"
        self._query = query
        self._bind_vars = bind_vars
        self._threshold = threshold
        self._capture_explain = capture_explain
        self._log_data = {}
        self.execute()

    def execute(self) -> None:
        """
        Execute the AQL query and log performance metrics for slow queries.

        Returns:
            The query cursor result
        """
        if self._arango_client is None:
            raise RuntimeError("Database connection is not established.")

        # Get the execute method - works with both Database and Client objects
        execute_method = self._arango_client.aql.execute
        explain_method = self._arango_client.aql.explain

        # Start timing
        start_time = time.time()

        # Execute the query
        try:
            self._cursor = execute_method(self._query, bind_vars=self._bind_vars)
        except AQLQueryExecuteError as error:
            print(f"Error {error} executing AQL query: {self._query} with bind variables: {self._bind_vars}")
            raise

        # Calculate execution time
        query_time = time.time() - start_time

        # Redact any potentially sensitive bind variables
        sanitized_bind_vars = {}
        if self._bind_vars:
            for k, v in self._bind_vars.items():
                # Redact potential passwords or tokens
                if any(sensitive in k.lower() for sensitive in ["pass", "secret", "token", "key"]):
                    sanitized_bind_vars[k] = "***REDACTED***"
                else:
                    sanitized_bind_vars[k] = v

            self._log_data = {
                "bind_vars": sanitized_bind_vars,
                "cursor": self._cursor,
                "description": self._description,
                "query_time": query_time,
                "query": self._query,
            }

            # Capture EXPLAIN data for slow queries if requested
            if self._capture_explain:
                explain_data = explain_method(
                    self._query,
                    bind_vars=self._bind_vars,
                )

                # Add important metrics from explain
                if explain_data:
                    self._log_data["explain"] = explain_data


    def get_cursor(self) -> Cursor:
        """Return the cursor for the executed query."""
        return self._cursor

    def get_data(self) -> dict[str, Any]:
        """Return the log data for the executed query."""
        return self._log_data

    def get_query_time(self) -> float:
        """Return the query time for the executed query."""
        return self._log_data["query_time"]

    def get_explain(self) -> dict[str, Any]:
        """Return the explain data for the executed query."""
        return self._log_data.get("explain", {})


def timed_aql_execute(
    query: str,
    bind_vars: dict[str, Any] | None = None,
    threshold: float = 5.0,
    capture_explain: bool = True,  # noqa: FBT001 FBT002
    log_level: int = logging.WARNING,
    **kwargs: dict,
) -> Cursor:
    """
    Execute an AQL query and log performance metrics for slow queries.

    Args:
        db: An ArangoDB database instance or client
        query: The AQL query string to execute
        bind_vars: Variables to bind to the query
        threshold: Time threshold in seconds to trigger logging (default: 5.0)
        capture_explain: Whether to capture EXPLAIN data for slow queries (default: True)
        log_level: Logging level to use for slow query reports (default: WARNING)
        **kwargs: Additional arguments to pass to the execute method

    Returns:
        The query cursor result

    This function wraps the standard ArangoDB AQL execute function with timing
    instrumentation. If a query exceeds the specified threshold (default 5 seconds),
    it will:

    1. Log the slow query with timing information
    2. Optionally capture EXPLAIN data to help diagnose performance issues
    3. Include bind variables (with sensitive data redacted) in the log

    Usage example:
    ```python
    from db.utils import timed_aql_execute

    # Simple usage with default threshold (5 seconds)
    cursor = timed_aql_execute(
        db,
        "FOR doc IN @@collection FILTER doc.LocalIdentifier == @frn RETURN doc",
        bind_vars={"@collection": "Objects", "frn": "12345"}
    )

    # With custom threshold and disabled EXPLAIN capture
    cursor = timed_aql_execute(
        db,
        "FOR doc IN @@collection FILTER doc.LocalIdentifier == @frn RETURN doc",
        bind_vars={"@collection": "Objects", "frn": "12345"},
        threshold=1.0,
        capture_explain=False
    )
    ```
    """
    log_data = TimedAQLExecute(
        db=IndalekoDBConfig(),
        query=query,
        bind_vars=bind_vars,
        threshold=threshold,
        capture_explain=capture_explain,
    ).get_data()

    if log_data["query_time"] > threshold:
        # Log the slow query with appropriate level
        logger.log(
            log_level,
            "Slow AQL query detected (%.2fs): %s",
            log_data["query_time"],
            json.dumps(log_data, indent=2),
        )

        # Log the slow query with appropriate level
        logger.log(
            log_level,
            "Slow AQL query detected (%.2fs): %s",
            log_data["query_time"],
            json.dumps(log_data, indent=2),
        )

    return log_data["cursor"]
