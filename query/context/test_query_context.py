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
    provider: QueryActivityProvider, count: int = 5,
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
    print("\n=== Testing QueryActivityProvider ===")

    # Create provider
    provider = QueryActivityProvider(debug=args.debug)

    if not provider.is_context_available():
        print("Activity context service not available. Exiting test.")
        return

    # Create test queries
    print("\nCreating test queries...")
    query_ids = create_test_queries(provider, count=args.count)
    print(f"Created {len(query_ids)} test queries")

    # Test relationship detection
    print("\nTesting relationship detection:")
    for i in range(len(query_ids) - 1):
        rel_type = provider._detect_relationship(f"Query {i}", f"Query {i+1}")
        print(f"  Relationship {i} → {i+1}: {rel_type}")


def test_navigation(args: argparse.Namespace) -> None:
    """Test the QueryNavigator functionality."""
    print("\n=== Testing QueryNavigator ===")

    # Create navigator
    navigator = QueryNavigator(debug=args.debug)

    if not navigator.is_navigation_available():
        print("Query navigation not available. Exiting test.")
        return

    # Get query history
    print("\nQuery History:")
    history = navigator.get_query_history(limit=args.count)

    if not history:
        print("No query history found.")

        # Create test queries
        provider = QueryActivityProvider(debug=args.debug)
        query_ids = create_test_queries(provider, count=args.count)

        # Try again
        history = navigator.get_query_history(limit=args.count)
        if not history:
            print("Still no query history found. Exiting test.")
            return

    # Print query history
    for i, query in enumerate(history):
        print(f"{i+1}. {query['query_text']} (ID: {query['query_id']})")

    # Use the most recent query for further testing
    test_query_id = uuid.UUID(history[0]["query_id"])

    # Test get_query_path
    print(f"\nQuery Path for {history[0]['query_text']}:")
    path = navigator.get_query_path(test_query_id)

    for i, query in enumerate(path):
        print(f"{i+1}. {query['query_text']} (ID: {query['query_id']})")

    # Test get_related_queries
    print(f"\nRelated Queries for {history[0]['query_text']}:")
    related = navigator.get_related_queries(test_query_id)

    for i, query in enumerate(related):
        print(f"{i+1}. {query['query_text']} (ID: {query['query_id']})")

    # Test get_exploration_branches
    print(f"\nExploration Branches from {history[0]['query_text']}:")
    branches = navigator.get_exploration_branches(test_query_id)

    for branch_id, branch_path in branches.items():
        print(f"\nBranch starting with {branch_id}:")
        for i, query in enumerate(branch_path):
            print(f"  {i+1}. {query['query_text']} (ID: {query['query_id']})")


def test_relationship_detection(args: argparse.Namespace) -> None:
    """Test the QueryRelationshipDetector functionality."""
    print("\n=== Testing QueryRelationshipDetector ===")

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
    print("\nTesting rule-based relationship detection:")

    success_count = 0
    for i, (q1, q2) in enumerate(test_pairs):
        rel_type, confidence = detector.detect_relationship(q1, q2)
        expected = expected_types[i]
        result = "✓" if rel_type == expected else "✗"
        success = rel_type == expected

        if success:
            success_count += 1

        print(f"{result} Pair {i+1}: {q1} → {q2}")
        print(f"   Detected: {rel_type} (Confidence: {confidence:.2f})")
        print(f"   Expected: {expected}")

    # Report accuracy
    accuracy = success_count / len(test_pairs)
    print(f"\nAccuracy: {success_count}/{len(test_pairs)} ({accuracy:.0%})")

    # Test analyzing a sequence
    navigator = QueryNavigator(debug=args.debug)
    history = navigator.get_query_history(limit=1)

    if history:
        test_query_id = uuid.UUID(history[0]["query_id"])

        print(f"\nAnalyzing sequence for query: {history[0]['query_text']}")
        analysis = detector.analyze_query_sequence(test_query_id)

        print(f"  Path Length: {analysis['path_length']}")
        print(f"  Exploration Pattern: {analysis['exploration_pattern']}")
        print(f"  Focus Shifts: {analysis['focus_shifts']}")

        print("\nRelationships:")
        for i, rel in enumerate(analysis.get("relationships", [])):
            print(f"  {i+1}. {rel['from_query']} → {rel['to_query']}")
            print(f"     {rel['relationship']} (Confidence: {rel['confidence']:.2f})")


def test_visualization(args: argparse.Namespace) -> None:
    """Test the QueryPathVisualizer functionality."""
    print("\n=== Testing QueryPathVisualizer ===")

    # Create visualizer
    visualizer = QueryPathVisualizer(debug=args.debug)

    # Get query history
    navigator = QueryNavigator(debug=args.debug)
    history = navigator.get_query_history(limit=args.count)

    if not history:
        print("No query history found. Creating test queries...")

        # Create test queries
        provider = QueryActivityProvider(debug=args.debug)
        query_ids = create_test_queries(provider, count=args.count)

        # Try again
        history = navigator.get_query_history(limit=args.count)
        if not history:
            print("Still no query history found. Exiting test.")
            return

    # Use the most recent query for testing
    test_query_id = uuid.UUID(history[0]["query_id"])
    print(f"Generating visualization for query: {history[0]['query_text']}")

    # Generate the graph
    graph = visualizer.generate_path_graph(test_query_id, include_branches=True)

    if not graph:
        print("Failed to generate graph.")
        return

    # Display graph info
    print(f"\nGraph has {len(graph.nodes)} nodes and {len(graph.edges)} edges")

    # Export the graph
    try:
        output_path = visualizer.export_graph(show=args.show)

        if output_path:
            print(f"\nGraph exported to: {output_path}")
        else:
            print("\nFailed to export graph.")
    except Exception as e:
        print(f"\nError exporting graph: {e}")

    # Generate report
    report = visualizer.generate_report(test_query_id)

    print("\nQuery Exploration Report:")
    print(f"  Path Length: {report['path_length']}")
    print(f"  Query: {report['query_text']}")
    print(f"  Exploration Pattern: {report.get('exploration_pattern', 'unknown')}")
    print(f"  Focus Shifts: {report.get('focus_shifts', 0)}")
    print(f"  Summary: {report['exploration_summary']}")


def test_integration(args: argparse.Namespace) -> None:
    """Test the full Query Context Integration workflow."""
    print("\n=== Testing Full Integration ===")

    # Create components
    provider = QueryActivityProvider(debug=args.debug)
    navigator = QueryNavigator(debug=args.debug)
    detector = QueryRelationshipDetector(debug=args.debug)
    visualizer = QueryPathVisualizer(debug=args.debug)

    if not provider.is_context_available():
        print("Activity context service not available. Exiting test.")
        return

    # Create test queries with explicit relationships
    print("\nCreating test queries with explicit relationships...")

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

        print(f"  {i+1}. {query_text}")
        print(f"     ID: {query_id}")
        print(f"     Context: {context}")
        print(f"     Relationship: {relationship or 'None'}")

        # Pause briefly to ensure timestamps are different
        time.sleep(0.1)

    # Verify query path
    print("\nVerifying query path...")
    path = navigator.get_query_path(query_ids[-1])

    if len(path) == len(query_ids):
        print("✓ Path length matches number of queries")
    else:
        print(f"✗ Path length mismatch: {len(path)} != {len(query_ids)}")

    # Compare paths
    for i, (query, query_id) in enumerate(zip(path, query_ids, strict=False)):
        path_id = uuid.UUID(query["query_id"])
        if path_id == query_id:
            print(f"✓ Path query {i+1} matches recorded query")
        else:
            print(f"✗ Path query {i+1} mismatch: {path_id} != {query_id}")

    # Verify relationships
    print("\nVerifying relationships...")
    for i in range(1, len(path)):
        rel_from_path = path[i].get("relationship_type")
        expected_rel = relationships[i]

        if rel_from_path == expected_rel:
            print(f"✓ Relationship {i} matches expected: {rel_from_path}")
        else:
            print(f"✗ Relationship {i} mismatch: {rel_from_path} != {expected_rel}")

    # Generate and save visualization
    print("\nGenerating visualization...")
    graph = visualizer.generate_path_graph(query_ids[-1])

    if graph:
        print(
            f"✓ Generated graph with {len(graph.nodes)} nodes and {len(graph.edges)} edges",
        )

        # Export the graph
        output_path = visualizer.export_graph(
            file_path="query_context_test.png", show=args.show,
        )

        if output_path:
            print(f"✓ Exported graph to: {output_path}")
    else:
        print("✗ Failed to generate graph")

    # Generate report
    report = visualizer.generate_report(query_ids[-1])

    print("\nExploration Summary:")
    print(report["exploration_summary"])

    print("\nIntegration test completed successfully!")


def main():
    """Test functionality of Query Context Integration."""
    parser = argparse.ArgumentParser(description="Test Query Context Integration")
    parser.add_argument(
        "--provider", action="store_true", help="Test activity provider",
    )
    parser.add_argument("--navigation", action="store_true", help="Test navigation")
    parser.add_argument(
        "--relationship", action="store_true", help="Test relationship detection",
    )
    parser.add_argument(
        "--visualization", action="store_true", help="Test visualization",
    )
    parser.add_argument(
        "--integration", action="store_true", help="Test full integration",
    )
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument(
        "--count", type=int, default=5, help="Number of queries to create/use",
    )
    parser.add_argument("--show", action="store_true", help="Show visualizations")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # If no specific tests specified, run all
    if not (
        args.provider
        or args.navigation
        or args.relationship
        or args.visualization
        or args.integration
        or args.all
    ):
        args.all = True

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Print banner
    print("=" * 70)
    print("Query Context Integration Test")
    print("=" * 70)

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
    print("\nTests completed")


if __name__ == "__main__":
    main()
