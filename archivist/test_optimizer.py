"""
Test script for the database optimizer component.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason and contributors

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

from datetime import timedelta


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from archivist.database_optimizer import DatabaseOptimizer
from db import IndalekoDBConfig
from query.memory.archivist_memory import ArchivistMemory
from query.query_processing.query_history import QueryHistory


# pylint: enable=wrong-import-position


def main():
    """Run tests for the database optimizer."""

    # Connect to the database
    db_config = IndalekoDBConfig()

    # Initialize components
    archivist_memory = ArchivistMemory(db_config)
    query_history = QueryHistory()

    optimizer = DatabaseOptimizer(db_config._arangodb, archivist_memory, query_history)

    # Analyze query patterns
    analysis = optimizer.analyze_query_patterns(timedelta(days=30))

    # Print summary

    # Print index recommendations
    index_recs = analysis.get("index_recommendations", [])
    if index_recs:
        for _i, _rec in enumerate(index_recs[:5], 1):
            pass
    else:
        pass

    # Print view recommendations
    view_recs = analysis.get("view_recommendations", [])
    if view_recs:
        for _i, _rec in enumerate(view_recs[:3], 1):
            pass
    else:
        pass

    # Print query optimizations
    query_opts = analysis.get("query_optimizations", [])
    if query_opts:
        for _i, _opt in enumerate(query_opts[:3], 1):
            pass
    else:
        pass



if __name__ == "__main__":
    main()
