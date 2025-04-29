"""
Test script for Indaleko ArangoSearch views

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

from data_models.db_view import IndalekoViewDefinition
from db.collection_view import IndalekoCollectionView
from db.i_collections import IndalekoCollections
from utils import IndalekoLogging


def list_views(view_manager):
    """List all views in the database."""
    views = view_manager.get_views()
    print(f"\nFound {len(views)} views:")
    for view in views:
        view_name = view["name"]
        view_type = view.get("type", "unknown")
        collections = list(view.get("links", {}).keys())
        print(f"  - {view_name} (type: {view_type})")
        print(f"    Collections: {', '.join(collections)}")


def create_test_view(view_manager):
    """Create a test view for demonstration purposes."""
    # Use a unique timestamped name to avoid conflicts
    import time

    test_view_name = f"TestSearchView_{int(time.time())}"
    print(f"\nCreating view with unique name: '{test_view_name}'")

    # Create test view definition with field-specific analyzers
    test_view = IndalekoViewDefinition(
        name=test_view_name,
        collections=["Objects"],
        fields={
            "Objects": {
                "Label": [
                    "text_en",
                    "indaleko_camel_case",
                    "indaleko_snake_case",
                    "indaleko_filename",
                ],
                "Record.Attributes.URI": ["text_en"],
                "Record.Attributes.Description": ["text_en"],
            },
        },
        include_all_fields=False,
        stored_values=["_key", "Label"],
    )

    # Create the view
    print(f"\nCreating test view '{test_view_name}'...")
    result = view_manager.create_view(test_view)

    if result["status"] == "success":
        print(f"✅ Successfully created view '{test_view_name}'")
    else:
        print(f"❌ Failed to create view: {result['message']}")


def delete_test_view(view_manager):
    """Delete the test view if it exists."""
    test_view_name = "TestSearchView"
    if not view_manager.view_exists(test_view_name):
        print(f"\nTest view '{test_view_name}' does not exist.")
        return

    # Ask for confirmation
    confirm = input(f"\nConfirm deletion of test view '{test_view_name}'? (y/n): ")
    if confirm.lower() != "y":
        print("Deletion cancelled.")
        return

    # Delete the view
    print(f"Deleting test view '{test_view_name}'...")
    result = view_manager.delete_view(test_view_name)

    if result["status"] == "success":
        print(f"✅ Successfully deleted view '{test_view_name}'")
    else:
        print(f"❌ Failed to delete view: {result['message']}")


def ensure_views(clear_existing=False):
    """Create or update all views defined in IndalekoDBCollections."""
    print("\nCreating/updating views defined in IndalekoDBCollections...")

    # Get the view manager
    view_manager = IndalekoCollectionView()

    # Optionally clear existing views first
    if clear_existing:
        views = view_manager.get_views()
        for view in views:
            view_name = view["name"]
            print(f"Deleting existing view '{view_name}'...")
            result = view_manager.delete_view(view_name)
            if result["status"] == "success":
                print(f"  ✅ Deleted view '{view_name}'")
            else:
                print(f"  ❌ Failed to delete view: {result['message']}")

    # Create collections, which will also create the views
    collections = IndalekoCollections()

    # Verify views were created
    views = view_manager.get_views()
    print(f"\nVerified {len(views)} views after initialization:")
    for view in views:
        view_name = view["name"]
        collections = list(view.get("links", {}).keys())
        print(f"  - {view_name} (collections: {', '.join(collections)})")


def execute_test_query(view_manager, query, analyzer=None):
    """
    Execute a test query using a view.

    Args:
        view_manager: The view manager instance
        query: The query string to search for
        analyzer: Optional analyzer name to use (if None, tests multiple analyzers)
    """
    print(f"\nExecuting search query: '{query}'")

    # Get database connection
    from db.db_config import IndalekoDBConfig

    db_config = IndalekoDBConfig()
    db_config.start()
    db = db_config._arangodb

    # Set up AQL query for each view
    views = view_manager.get_views()

    # List of analyzers to test if none specified
    analyzers_to_test = (
        [analyzer]
        if analyzer
        else [
            "text_en",
            "indaleko_filename",
            "indaleko_camel_case",
            "indaleko_snake_case",
        ]
    )

    for view in views:
        view_name = view["name"]

        # Skip views that aren't ArangoSearch views
        if view.get("type") != "arangosearch":
            continue

        print(f"\nSearching in view '{view_name}':")

        for current_analyzer in analyzers_to_test:
            print(f"\n  Using analyzer: {current_analyzer}")

            # Construct AQL query with the current analyzer
            aql_query = f"""
            FOR doc IN {view_name}
            SEARCH ANALYZER(
                LIKE(doc.Label, @query),
                @analyzer
            )
            LIMIT 10
            RETURN DISTINCT {{
                "key": doc._key,
                "label": doc.Label,
                "score": BM25(doc)
            }}
            """

            # Execute query
            try:
                cursor = db.aql.execute(
                    aql_query,
                    bind_vars={"query": f"%{query}%", "analyzer": current_analyzer},
                    count=True,
                )

                results = list(cursor)

                # Print results
                total = cursor.count() if cursor.has_more() else len(results)
                print(f"  Found {total} results:")

                for i, result in enumerate(results):
                    print(
                        f"    {i+1}. {result.get('label', '[No Label]')} (key: {result.get('key')})",
                    )
                    if result.get("score"):
                        print(f"       Score: {result.get('score')}")

                if not results:
                    print("    No matching results found")

            except Exception as e:
                print(f"    ❌ Error executing query: {e!s}")


def test_tokenized_search(view_manager):
    """Test search with tokenized fields."""
    from storage.recorders.tokenization import tokenize_filename

    print("\n=== Testing tokenized search ===")

    # Define test filenames
    test_filenames = [
        "IndalekoObjectDataModel.py",
        "indaleko_object_data_model.py",
        "CamelCaseExample123.txt",
        "snake_case_example_123.txt",
    ]

    # Tokenize and show the results
    for filename in test_filenames:
        print(f"\nTokenizing: {filename}")
        tokens = tokenize_filename(filename)
        print(f"  Original filename: {filename}")
        print(f"  CamelCase tokenized: {tokens['CamelCaseTokenizedName']}")
        print(f"  snake_case tokenized: {tokens['SnakeCaseTokenizedName']}")
        print(f"  Search tokenized: {tokens['SearchTokenizedName']}")

    # Test search queries for different tokenization patterns
    test_queries = ["Indaleko", "Object", "Data", "Model", "Example", "snake", "case"]

    for query in test_queries:
        execute_test_query(view_manager, query)


def list_analyzers(view_manager):
    """List all analyzers in the database."""
    analyzers = view_manager.get_analyzers()
    print(f"\nFound {len(analyzers)} analyzers:")
    for analyzer in analyzers:
        name = analyzer.get("name", "unknown")
        type = analyzer.get("type", "unknown")
        print(f"  - {name} (type: {type})")

    return len(analyzers) > 0


def main():
    """Main function for the test script."""
    parser = argparse.ArgumentParser(description="Test ArangoSearch views for Indaleko")
    parser.add_argument("--list", action="store_true", help="List existing views")
    parser.add_argument(
        "--list-analyzers",
        action="store_true",
        help="List all analyzers",
    )
    parser.add_argument("--create-test", action="store_true", help="Create a test view")
    parser.add_argument(
        "--delete-test",
        action="store_true",
        help="Delete the test view",
    )
    parser.add_argument(
        "--ensure",
        action="store_true",
        help="Create/update all defined views",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all existing views before creating new ones",
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Execute a test query using the views",
    )
    parser.add_argument(
        "--analyzer",
        type=str,
        help="Specify analyzer to use with query (tests all analyzers if not specified)",
    )
    parser.add_argument(
        "--test-tokenization",
        action="store_true",
        help="Test tokenized search functionality",
    )
    parser.add_argument(
        "--test-camel-case",
        action="store_true",
        help="Test with CamelCase filenames",
    )
    parser.add_argument(
        "--test-snake-case",
        action="store_true",
        help="Test with snake_case filenames",
    )
    parser.add_argument(
        "--test-complex",
        action="store_true",
        help="Test with complex filenames (mixed separators)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    IndalekoLogging(service_name="test_views", log_level=log_level)

    # Create the view manager
    view_manager = IndalekoCollectionView()

    # Process commands
    if args.list:
        list_views(view_manager)

    if args.list_analyzers:
        list_analyzers(view_manager)

    if args.create_test:
        create_test_view(view_manager)

    if args.delete_test:
        delete_test_view(view_manager)

    if args.ensure:
        ensure_views(args.clear)

    if args.query:
        execute_test_query(view_manager, args.query, args.analyzer)

    if args.test_tokenization:
        test_tokenized_search(view_manager)

    if args.test_camel_case:
        print("\n=== Testing CamelCase filenames ===")
        camel_queries = [
            "Indaleko",
            "Object",
            "IndalekoObject",
            "indalekoObject",
            "indaleko",
        ]
        for query in camel_queries:
            execute_test_query(view_manager, query, "indaleko_camel_case")

    if args.test_snake_case:
        print("\n=== Testing snake_case filenames ===")
        snake_queries = ["indaleko", "object", "indaleko_object", "data_model"]
        for query in snake_queries:
            execute_test_query(view_manager, query, "indaleko_snake_case")

    if args.test_complex:
        print("\n=== Testing complex filenames ===")
        complex_queries = ["this-is", "the_file", "%2efor", "Claude"]
        for query in complex_queries:
            execute_test_query(view_manager, query, "indaleko_filename")

    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()


if __name__ == "__main__":
    main()
