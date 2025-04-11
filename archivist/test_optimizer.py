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
from query.memory.archivist_memory import ArchivistMemory
from query.query_processing.query_history import QueryHistory
from db import IndalekoDBConfig
# pylint: enable=wrong-import-position


def main():
    """Run tests for the database optimizer."""
    print("Indaleko Database Optimizer Test")
    print("================================")
    
    # Connect to the database
    print("\nConnecting to ArangoDB...")
    db_config = IndalekoDBConfig()
    
    # Initialize components
    archivist_memory = ArchivistMemory(db_config)
    query_history = QueryHistory()
    
    print("Initializing database optimizer...")
    optimizer = DatabaseOptimizer(db_config.db, archivist_memory, query_history)
    
    # Analyze query patterns
    print("\nAnalyzing query patterns (last 30 days)...")
    analysis = optimizer.analyze_query_patterns(timedelta(days=30))
    
    # Print summary
    print(f"\nAnalyzed {analysis.get('analyzed_queries', 0)} queries.")
    print(f"Found {len(analysis.get('slow_queries', []))} slow queries.")
    
    # Print index recommendations
    index_recs = analysis.get("index_recommendations", [])
    if index_recs:
        print(f"\nIndex Recommendations ({len(index_recs)}):")
        for i, rec in enumerate(index_recs[:5], 1):
            print(f"{i}. {rec.short_description()}")
            print(f"   Impact: {rec.estimated_impact:.2f}")
            print(f"   Explanation: {rec.explanation}")
    else:
        print("\nNo index recommendations.")
    
    # Print view recommendations
    view_recs = analysis.get("view_recommendations", [])
    if view_recs:
        print(f"\nView Recommendations ({len(view_recs)}):")
        for i, rec in enumerate(view_recs[:3], 1):
            print(f"{i}. {rec.short_description()}")
            print(f"   Impact: {rec.estimated_impact:.2f}")
            print(f"   Explanation: {rec.explanation}")
    else:
        print("\nNo view recommendations.")
    
    # Print query optimizations
    query_opts = analysis.get("query_optimizations", [])
    if query_opts:
        print(f"\nQuery Optimization Recommendations ({len(query_opts)}):")
        for i, opt in enumerate(query_opts[:3], 1):
            print(f"{i}. {opt.short_description()}")
            print(f"   Speedup: {opt.estimated_speedup:.2f}x")
            print(f"   Explanation: {opt.explanation}")
    else:
        print("\nNo query optimization recommendations.")
    
    print("\nTest complete!")


if __name__ == "__main__":
    main()