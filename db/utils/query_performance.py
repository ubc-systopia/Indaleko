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
from arango.database import Database


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
    db = IndalekoDBConfig().get_arangodb()

    if db is None:
        raise ValueError("Database connection is not established.")

    # Get the execute method - works with both Database and Client objects
    execute_method = db.aql.execute

    # Start timing
    start_time = time.time()

    # Execute the query
    cursor = execute_method(query, bind_vars=bind_vars, **kwargs)

    # Calculate execution time
    query_time = time.time() - start_time

    # Log slow queries
    if query_time > threshold:
        # Redact any potentially sensitive bind variables
        sanitized_bind_vars = {}
        if bind_vars:
            for k, v in bind_vars.items():
                # Redact potential passwords or tokens
                if any(sensitive in k.lower() for sensitive in ["pass", "secret", "token", "key"]):
                    sanitized_bind_vars[k] = "***REDACTED***"
                else:
                    sanitized_bind_vars[k] = v

        # Base log message
        log_data = {
            "query_time": f"{query_time:.2f}s",
            "query": query,
            "bind_vars": sanitized_bind_vars,
        }

        # Capture EXPLAIN data for slow queries if requested
        if capture_explain:
            try:
                explain_cursor = execute_method(
                    f"EXPLAIN {query}",
                    bind_vars=bind_vars,
                    **{k: v for k, v in kwargs.items() if k != "count"},
                )
                explain_data = list(explain_cursor)

                # Add important metrics from explain
                if explain_data:
                    explain = explain_data[0]
                    log_data["explain"] = {
                        "estimatedCost": explain.get("estimatedCost", "unknown"),
                        "estimatedNrItems": explain.get("estimatedNrItems", "unknown"),
                        "rules": explain.get("rules", []),
                        "collections": [col.get("name") for col in explain.get("collections", [])],
                        "indexes": [idx.get("name") for idx in explain.get("indexes", [])],
                    }

                    # Flag missing index usage
                    if not explain.get("indexes"):
                        log_data["warning"] = "No indexes are being used for this query!"
            except ValueError as e:
                log_data["explain_error"] = str(e)

        # Log the slow query with appropriate level
        logger.log(
            log_level,
            "Slow AQL query detected (%.2fs): %s",
            query_time,
            json.dumps(log_data, indent=2),
        )

    return cursor
