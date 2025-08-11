#!/usr/bin/env python
"""
Test script for Query Context Integration.

This script tests the integration between queries and the
Indaleko Activity Context system.

Project Indaleko
Copyright (C) 2025 Tony Mason

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
import uuid


# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.context.activity_provider import QueryActivityProvider
from query.context.navigation import QueryNavigator
from query.context.relationship import QueryRelationshipDetector, RelationshipType
from query.context.visualization import QueryPathVisualizer


# pylint: enable=wrong-import-position


def create_test_queries(
    provider: QueryActivityProvider,
    count: int = 5,
) -> list[uuid.UUID]:
    """Create a sequence of test queries for testing."""
    query_ids = []

    # Define a sequence of test queries that show different relationships
    test_queries = [
        "Find documents about Indaleko",  # Starting point
        "Find PDF documents about Indaleko",  # Refinement
        "Find PDF documents about Indaleko created last week",  # Refinement
        "Show me all documents about Indaleko",  # Broadening
        "Who authored Indaleko documents?",  # Pivot
        "Find documents about Indaleko",  # Backtrack
        "Find documents about Fire Circle",  # Unrelated
        "Show me the relationship between Indaleko and Fire Circle",  # Pivot
        "What is the status of the Knowledge Base implementation?",  # Unrelated
        "List all files modified in the last 24 hours",  # Unrelated
    ]

    # Create as many queries as requested (up to the limit)
    for i in range(min(count, len(test_queries))):
        query_text = test_queries[i]

        # For queries after the first, use the previous query as the previous_query_id
        previous_id = query_ids[-1] if query_ids else None

        # Record the query
        query_id, _ = provider.record_query(
            query_text=query_text,
            results=[{"id": j, "name": f"Result {j}"} for j in range(3)],
            execution_time=123.45,
            previous_query_id=previous_id,
        )

        query_ids.append(query_id)

        # Pause briefly to ensure timestamps are different
        time.sleep(0.1)

    return query_ids


def test_activity_provider(args: argparse.Namespace) -> None:
    """Test the QueryActivityProvider functionality."""

    # Create provider
    provider = QueryActivityProvider(debug=args.debug)

    if not provider.is_context_available():
        return

    # Create test queries
    query_ids = create_test_queries(provider, count=args.count)

    # Test relationship detection
    for i in range(len(query_ids) - 1):
        provider._detect_relationship(f"Query {i}", f"Query {i+1}")


def test_navigation(args: argparse.Namespace) -> None:
    """Test the QueryNavigator functionality."""

    # Create navigator
    navigator = QueryNavigator(debug=args.debug)

    if not navigator.is_navigation_available():
        return

    # Get query history
    history = navigator.get_query_history(limit=args.count)

    if not history:

        # Create test queries
        provider = QueryActivityProvider(debug=args.debug)
        create_test_queries(provider, count=args.count)

        # Try again
        history = navigator.get_query_history(limit=args.count)
        if not history:
            return

    # Print query history
    for _i, _query in enumerate(history):
        pass

    # Use the most recent query for further testing
    test_query_id = uuid.UUID(history[0]["query_id"])

    # Test get_query_path
    path = navigator.get_query_path(test_query_id)

    for _i, _query in enumerate(path):
        pass

    # Test get_related_queries
    related = navigator.get_related_queries(test_query_id)

    for _i, _query in enumerate(related):
        pass

    # Test get_exploration_branches
    branches = navigator.get_exploration_branches(test_query_id)

    for branch_path in branches.values():
        for _i, _query in enumerate(branch_path):
            pass


def test_relationship_detection(args: argparse.Namespace) -> None:
    """Test the QueryRelationshipDetector functionality."""

    # Create detector
    detector = QueryRelationshipDetector(debug=args.debug)

    # Define test query pairs that demonstrate different relationships
    test_pairs = [
        ("Find documents about Indaleko", "Find PDF documents about Indaleko"),
        ("Find PDF documents about Indaleko", "Find documents about Indaleko"),
        ("Find documents about Indaleko", "Show me the authors of Indaleko documents"),
        ("Find documents about Indaleko", "Find documents about Windows"),
        ("Find documents about Indaleko", "Find documents about Indaleko"),
    ]

    # Expected relationship types
    expected_types = [
        RelationshipType.REFINEMENT,
        RelationshipType.BROADENING,
        RelationshipType.PIVOT,
        RelationshipType.UNRELATED,
        RelationshipType.BACKTRACK,
    ]

    # Test each pair

    success_count = 0
    for i, (q1, q2) in enumerate(test_pairs):
        rel_type, confidence = detector.detect_relationship(q1, q2)
        expected = expected_types[i]
        success = rel_type == expected

        if success:
            success_count += 1


    # Report accuracy
    success_count / len(test_pairs)

    # Test analyzing a sequence
    navigator = QueryNavigator(debug=args.debug)
    history = navigator.get_query_history(limit=1)

    if history:
        test_query_id = uuid.UUID(history[0]["query_id"])

        analysis = detector.analyze_query_sequence(test_query_id)


        for i, _rel in enumerate(analysis.get("relationships", [])):
            pass


def test_visualization(args: argparse.Namespace) -> None:
    """Test the QueryPathVisualizer functionality."""

    # Create visualizer
    visualizer = QueryPathVisualizer(debug=args.debug)

    # Get query history
    navigator = QueryNavigator(debug=args.debug)
    history = navigator.get_query_history(limit=args.count)

    if not history:

        # Create test queries
        provider = QueryActivityProvider(debug=args.debug)
        create_test_queries(provider, count=args.count)

        # Try again
        history = navigator.get_query_history(limit=args.count)
        if not history:
            return

    # Use the most recent query for testing
    test_query_id = uuid.UUID(history[0]["query_id"])

    # Generate the graph
    graph = visualizer.generate_path_graph(test_query_id, include_branches=True)

    if not graph:
        return

    # Display graph info

    # Export the graph
    try:
        output_path = visualizer.export_graph(show=args.show)

        if output_path:
            pass
        else:
            pass
    except Exception:
        pass

    # Generate report
    visualizer.generate_report(test_query_id)



def test_integration(args: argparse.Namespace) -> None:
    """Test the full Query Context Integration workflow."""

    # Create components
    provider = QueryActivityProvider(debug=args.debug)
    navigator = QueryNavigator(debug=args.debug)
    QueryRelationshipDetector(debug=args.debug)
    visualizer = QueryPathVisualizer(debug=args.debug)

    if not provider.is_context_available():
        return

    # Create test queries with explicit relationships

    # Define test queries that form a coherent exploration path
    test_queries = [
        "Find documents about Indaleko",
        "Find PDF documents about Indaleko",
        "Find PDF documents about Indaleko created last week",
        "Who authored Indaleko documents last week?",
        "Show documents authored by Tony Mason",
        "Show all documents authored by Tony Mason",
    ]

    # Define explicit relationships between queries
    relationships = [
        None,  # First query has no relationship
        RelationshipType.REFINEMENT.value,
        RelationshipType.REFINEMENT.value,
        RelationshipType.PIVOT.value,
        RelationshipType.PIVOT.value,
        RelationshipType.BROADENING.value,
    ]

    # Record the queries
    query_ids = []
    contexts = []

    for i, query_text in enumerate(test_queries):
        # For queries after the first, use the previous query as the previous_query_id
        previous_id = query_ids[-1] if query_ids else None
        relationship = relationships[i]

        # Record the query with explicit relationship
        query_id, context = provider.record_query(
            query_text=query_text,
            results=[{"id": j, "name": f"Result {j}"} for j in range(i + 1)],
            execution_time=100 + i * 10,
            previous_query_id=previous_id,
            relationship_type=relationship,
        )

        query_ids.append(query_id)
        contexts.append(context)


        # Pause briefly to ensure timestamps are different
        time.sleep(0.1)

    # Verify query path
    path = navigator.get_query_path(query_ids[-1])

    if len(path) == len(query_ids):
        pass
    else:
        pass

    # Compare paths
    for i, (query, query_id) in enumerate(zip(path, query_ids, strict=False)):
        path_id = uuid.UUID(query["query_id"])
        if path_id == query_id:
            pass
        else:
            pass

    # Verify relationships
    for i in range(1, len(path)):
        rel_from_path = path[i].get("relationship_type")
        expected_rel = relationships[i]

        if rel_from_path == expected_rel:
            pass
        else:
            pass

    # Generate and save visualization
    graph = visualizer.generate_path_graph(query_ids[-1])

    if graph:

        # Export the graph
        output_path = visualizer.export_graph(
            file_path="query_context_test.png",
            show=args.show,
        )

        if output_path:
            pass
    else:
        pass

    # Generate report
    visualizer.generate_report(query_ids[-1])




def main():
    """Test functionality of Query Context Integration."""
    parser = argparse.ArgumentParser(description="Test Query Context Integration")
    parser.add_argument(
        "--provider",
        action="store_true",
        help="Test activity provider",
    )
    parser.add_argument("--navigation", action="store_true", help="Test navigation")
    parser.add_argument(
        "--relationship",
        action="store_true",
        help="Test relationship detection",
    )
    parser.add_argument(
        "--visualization",
        action="store_true",
        help="Test visualization",
    )
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Test full integration",
    )
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of queries to create/use",
    )
    parser.add_argument("--show", action="store_true", help="Show visualizations")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # If no specific tests specified, run all
    if not (
        args.provider or args.navigation or args.relationship or args.visualization or args.integration or args.all
    ):
        args.all = True

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Print banner

    # Run tests
    try:
        if args.all or args.provider:
            test_activity_provider(args)

        if args.all or args.navigation:
            test_navigation(args)

        if args.all or args.relationship:
            test_relationship_detection(args)

        if args.all or args.visualization:
            test_visualization(args)

        if args.all or args.integration:
            test_integration(args)
    except Exception as e:
        logging.exception(f"Error during testing: {e}")
        import traceback

        traceback.print_exc()

    # Summary


if __name__ == "__main__":
    main()
