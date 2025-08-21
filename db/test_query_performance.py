"""
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

import argparse
import logging
import os
import sys


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db import IndalekoDBConfig, timed_aql_execute
from db.db_collections import IndalekoDBCollections
from utils.i_logging import get_logger


# Configure logger
logger = get_logger(__name__)


def test_fast_query(db_config: IndalekoDBConfig, collection_name: str) -> None:
    """Test a fast query that should execute quickly."""
    logger.info("Testing fast query with timed_aql_execute")

    query = f"FOR doc IN {collection_name} LIMIT 5 RETURN doc"

    # Use the timed_aql_execute function with a very low threshold
    # to ensure we get logging output even for fast queries
    cursor = timed_aql_execute(
        db_config._arangodb,
        query,
        threshold=0.001,  # 1ms threshold to ensure we log
        log_level=logging.INFO,  # Use INFO level instead of WARNING
    )

    # Fetch results
    results = list(cursor)
    logger.info(f"Found {len(results)} documents in fast query")


def test_slow_query(db_config: IndalekoDBConfig, collection_name: str) -> None:
    """Test a slow query that should trigger performance logging."""
    logger.info("Testing slow query with timed_aql_execute")

    # This query should be slow due to lack of index usage and the sleep
    query = f"""
    FOR doc IN {collection_name}
    LET sleep = SLEEP(0.2)  // Force this query to be slow
    SORT doc._key
    LIMIT 5
    RETURN doc
    """

    # Use the timed_aql_execute function with standard threshold
    cursor = timed_aql_execute(db_config._arangodb, query, threshold=0.1, capture_explain=True)  # 100ms threshold

    # Fetch results
    results = list(cursor)
    logger.info(f"Found {len(results)} documents in slow query")


def main():
    """Main function to run the test."""
    parser = argparse.ArgumentParser(description="Test timed_aql_execute function")

    parser.add_argument(
        "--collection",
        type=str,
        default=IndalekoDBCollections.Indaleko_Object_Collection,
        help="Collection to query for testing",
    )

    parser.add_argument(
        "--fast-only",
        action="store_true",
        help="Only run the fast query test",
    )

    parser.add_argument(
        "--slow-only",
        action="store_true",
        help="Only run the slow query test",
    )

    args = parser.parse_args()

    # Connect to database
    db_config = IndalekoDBConfig()
    if not db_config.started:
        logger.error("Failed to connect to database")
        return

    # Determine which tests to run
    run_fast = not args.slow_only
    run_slow = not args.fast_only

    if run_fast:
        test_fast_query(db_config, args.collection)

    if run_slow:
        test_slow_query(db_config, args.collection)

    logger.info("Test completed successfully")


if __name__ == "__main__":
    main()
