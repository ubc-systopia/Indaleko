\n+# fmt: on
"""
# fmt: off
Example AQL query for entity relationships. Formatting disabled.
"""
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
import time
from typing import Dict, List, Optional, Tuple, Union

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

class EntityLookupService:
    """
    Demonstrates how to retrofit the existing entity lookup code with the new
    timed_aql_execute function.

    This is a simplified version of the entity lookup service in the hot tier recorder.
    """

    def __init__(self, db_config: IndalekoDBConfig):
        """Initialize the entity lookup service."""
        self._db = db_config
        self._entity_collection_name = IndalekoDBCollections.Indaleko_Object_Collection
        self.connection_valid = True

    def find_entity_by_identifiers(self,
                                  frn: str,
                                  volume: str,
                                  local_path: Optional[str] = None) -> Optional[Dict]:
        """
        Find an entity using the LocalIdentifier (file reference number) and Volume fields.

        Original implementation:
        ```python
        query = """
            FOR doc IN @@collection
            FILTER doc.LocalIdentifier == @frn AND doc.Volume == @volume
            LIMIT 1
            RETURN doc
        """

        cursor = self._db._arangodb.aql.execute(
            query,
            bind_vars={
                "@collection": self._entity_collection_name,
                "frn": frn,
                "volume": volume,
            },
        )
        ```

        Retrofitted implementation using timed_aql_execute:
        """
        query = """
            FOR doc IN @@collection
            FILTER doc.LocalIdentifier == @frn AND doc.Volume == @volume
            LIMIT 1
            RETURN doc
        """

        bind_vars = {
            "@collection": self._entity_collection_name,
            "frn": frn,
            "volume": volume,
        }

        # Use timed_aql_execute instead of direct execute
        cursor = timed_aql_execute(
            self._db,
            query,
            bind_vars=bind_vars,
            threshold=0.5,  # 500ms threshold for logging
        )

        entity = next(cursor, None)

        # If entity not found and we have a local_path, try a fallback query
        if entity is None and local_path:
            return self.find_entity_by_path(local_path, volume)

        return entity

    def find_entity_by_path(self, path: str, volume: str) -> Optional[Dict]:
        """
        Fallback query to find an entity by its path.

        This demonstrates using timed_aql_execute with a more complex query.
        """
        query = """
            FOR doc IN @@collection
            FILTER doc.LocalPath == @path AND doc.Volume == @volume
            LIMIT 1
            RETURN doc
        """

        bind_vars = {
            "@collection": self._entity_collection_name,
            "path": path,
            "volume": volume,
        }

        # Use timed_aql_execute with capture_explain=True to get more details on slow queries
        cursor = timed_aql_execute(
            self._db,
            query,
            bind_vars=bind_vars,
            threshold=0.5,  # 500ms threshold for logging
            capture_explain=True,
        )

        return next(cursor, None)

def main():
    """Main function to demonstrate the retrofitted entity lookup service."""
    parser = argparse.ArgumentParser(description="Demonstrate timed_aql_execute with entity lookups")

    parser.add_argument(
        "--frn",
        type=str,
        default="123456",
        help="File reference number to lookup",
    )

    parser.add_argument(
        "--volume",
        type=str,
        default="00000000-0000-0000-0000-000000000000",
        help="Volume GUID to lookup",
    )

    parser.add_argument(
        "--path",
        type=str,
        default="C:\\example\\file.txt",
        help="File path to use as fallback",
    )

    args = parser.parse_args()

    # Connect to database
    db_config = IndalekoDBConfig()
    if not db_config.started:
        logger.error("Failed to connect to database")
        return

    # Create entity lookup service
    lookup_service = EntityLookupService(db_config)

    # Try to find entity
    entity = lookup_service.find_entity_by_identifiers(args.frn, args.volume, args.path)

    if entity:
        logger.info(f"Found entity with ID: {entity.get('_key', 'unknown')}")
    else:
        logger.info(f"No entity found for FRN: {args.frn}, Volume: {args.volume}")

        # Try fallback query directly
        fallback_entity = lookup_service.find_entity_by_path(args.path, args.volume)
        if fallback_entity:
            logger.info(f"Found entity by path with ID: {fallback_entity.get('_key', 'unknown')}")

if __name__ == "__main__":
    main()
