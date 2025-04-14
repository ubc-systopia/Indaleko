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
import os
import sys
import logging
from typing import Dict, List, Any

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from db.collection_view import IndalekoCollectionView
from data_models.db_view import IndalekoViewDefinition
from db.db_collections import IndalekoDBCollections
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
    # Check if test view already exists
    test_view_name = "TestSearchView"
    if view_manager.view_exists(test_view_name):
        print(f"\nTest view '{test_view_name}' already exists.")
        return
    
    # Create test view definition
    test_view = IndalekoViewDefinition(
        name=test_view_name,
        collections=["Objects"],
        fields={
            "Objects": ["Label", "Record.Attributes.URI", "Record.Attributes.Description"]
        },
        analyzers=["text_en"],
        include_all_fields=False,
        stored_values=["_key", "Label"]
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
    if confirm.lower() != 'y':
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


def execute_test_query(view_manager, query):
    """Execute a test query using a view."""
    print(f"\nExecuting search query: '{query}'")
    
    # Get database connection
    from db.db_config import IndalekoDBConfig
    db_config = IndalekoDBConfig()
    db_config.start()
    db = db_config.db
    
    # Set up AQL query for each view
    views = view_manager.get_views()
    
    for view in views:
        view_name = view["name"]
        
        # Skip views that aren't ArangoSearch views
        if view.get("type") != "arangosearch":
            continue
        
        print(f"\nSearching in view '{view_name}':")
        
        # Construct AQL query
        aql_query = f"""
        FOR doc IN {view_name}
        SEARCH ANALYZER(LIKE(doc.Label, @query) OR 
                       LIKE(doc.Record.Attributes.Description, @query) OR 
                       LIKE(doc.Record.Attributes.URI, @query), "text_en")
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
                bind_vars={"query": f"%{query}%"},
                count=True
            )
            
            results = list(cursor)
            
            # Print results
            total = cursor.count() if cursor.has_more() else len(results)
            print(f"Found {total} results:")
            
            for i, result in enumerate(results):
                print(f"  {i+1}. {result.get('label', '[No Label]')} (key: {result.get('key')})")
                if result.get('score'):
                    print(f"     Score: {result.get('score')}")
                    
            if not results:
                print("  No matching results found")
                
        except Exception as e:
            print(f"  ❌ Error executing query: {str(e)}")


def main():
    """Main function for the test script."""
    parser = argparse.ArgumentParser(description="Test ArangoSearch views for Indaleko")
    parser.add_argument('--list', action='store_true', help='List existing views')
    parser.add_argument('--create-test', action='store_true', help='Create a test view')
    parser.add_argument('--delete-test', action='store_true', help='Delete the test view')
    parser.add_argument('--ensure', action='store_true', help='Create/update all defined views')
    parser.add_argument('--clear', action='store_true', help='Clear all existing views before creating new ones')
    parser.add_argument('--query', type=str, help='Execute a test query using the views')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    IndalekoLogging(
        service_name="test_views",
        log_level=log_level
    )
    
    # Create the view manager
    view_manager = IndalekoCollectionView()
    
    # Process commands
    if args.list:
        list_views(view_manager)
    
    if args.create_test:
        create_test_view(view_manager)
    
    if args.delete_test:
        delete_test_view(view_manager)
    
    if args.ensure:
        ensure_views(args.clear)
    
    if args.query:
        execute_test_query(view_manager, args.query)
    
    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()


if __name__ == "__main__":
    main()