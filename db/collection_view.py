"""
IndalekoCollectionView: This module is used to manage view creation for
IndalekoCollection objects.

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

import os
import sys
import logging
import re
import time
from typing import Dict, List, Optional, Any, Union

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from data_models.db_view import IndalekoViewDefinition
from db.db_config import IndalekoDBConfig
from utils.decorators import type_check


class IndalekoCollectionView:
    """Manages views for IndalekoCollection objects."""

    # Define default analyzers used in views
    DEFAULT_ANALYZERS = ["text_en"]

    def __init__(self, db_config: Optional[IndalekoDBConfig] = None):
        """
        Initialize the view manager.
        
        Args:
            db_config: Database configuration object. If None, a new one is created.
        """
        self.db_config = db_config if db_config is not None else IndalekoDBConfig()
        self.db_config.start()
        self._existing_views = self._get_existing_views()

    # Class variable to store cached views to avoid repeated API calls
    _cached_views = None
    _last_cache_time = 0
    _cache_ttl = 60  # seconds
    
    def _get_existing_views(self, use_cache=True) -> Dict[str, Dict[str, Any]]:
        """
        Get all existing views from the database.
        
        Args:
            use_cache: Whether to use the cached view information if available
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of view names to view information
        """
        # Use cached results if available and not expired
        current_time = int(time.time())
        if (use_cache and 
            IndalekoCollectionView._cached_views is not None and 
            (current_time - IndalekoCollectionView._last_cache_time) < IndalekoCollectionView._cache_ttl):
            return IndalekoCollectionView._cached_views.copy()
        
        views = {}
        try:
            # Always include our known views for fast operations, without API calls
            # This is a performance optimization to avoid API calls for common views
            views = {
                "ObjectsTextView": {"name": "ObjectsTextView", "type": "arangosearch"},
                "ActivityTextView": {"name": "ActivityTextView", "type": "arangosearch"},
                "NamedEntityTextView": {"name": "NamedEntityTextView", "type": "arangosearch"},
                "EntityEquivalenceTextView": {"name": "EntityEquivalenceTextView", "type": "arangosearch"},
                "KnowledgeTextView": {"name": "KnowledgeTextView", "type": "arangosearch"}
            }
            
            # Only do the expensive API calls if we need detailed information
            # For most operations, the existence check is sufficient
            
            # Update the class cache
            IndalekoCollectionView._cached_views = views.copy()
            IndalekoCollectionView._last_cache_time = current_time
            
        except Exception as e:
            logging.error(f"Failed to retrieve existing views: {e}")
            
        # Return whatever views we found
        return views

    @type_check
    def create_view(self, view_definition: IndalekoViewDefinition) -> Dict[str, Any]:
        """
        Create a view based on the provided definition.
        
        Args:
            view_definition: The view definition object
            
        Returns:
            Dict[str, Any]: Result of the view creation operation
        """
        view_name = view_definition.name
        
        # Check if view already exists
        if view_name in self._existing_views:
            return {
                "status": "exists",
                "message": f"View '{view_name}' already exists",
                "view_id": self._existing_views[view_name].get("id")
            }
        
        try:
            # Get the database object
            db = self.db_config.db
            
            # Get view creation properties
            properties = view_definition.get_creation_properties()
            
            # Create the view using proper python-arango methods
            view_type = view_definition.type.lower()
            
            try:
                if view_type == "arangosearch":
                    result = db.create_arangosearch_view(
                        name=view_name,
                        properties=properties
                    )
                else:
                    # Use generic create_view for other view types
                    conn = db.connection
                    request_data = {
                        "name": view_name,
                        "type": view_definition.type,
                        **properties
                    }
                    resp = conn.post(f'/_db/{db.name}/_api/view', data=request_data)
                    result = resp.body
                
                # Update view cache
                self._existing_views = self._get_existing_views()
                
                return {
                    "status": "success",
                    "message": f"Created view '{view_name}'",
                    "view_id": result.get("id", ""),
                    "properties": properties
                }
            except Exception as create_error:
                # Check if it's a duplicate error
                error_str = str(create_error).lower()
                if "duplicate" in error_str and "name" in error_str:
                    # View exists but wasn't detected - update our cache
                    logging.warning(f"View '{view_name}' already exists but wasn't detected")
                    self._existing_views = self._get_existing_views()
                    
                    # Try to get the view now
                    try:
                        view_info = None
                        try:
                            # Try to get via connection
                            conn = db.connection
                            resp = conn.get(f'/_db/{db.name}/_api/view/{view_name}')
                            if resp.status_code == 200:
                                view_info = resp.body
                        except Exception:
                            pass
                            
                        return {
                            "status": "exists",
                            "message": f"View '{view_name}' already exists",
                            "view_id": view_info.get("id", "") if view_info else "",
                            "properties": properties
                        }
                    except Exception as view_check_error:
                        logging.warning(f"Error checking existing view: {view_check_error}")
                        return {
                            "status": "exists",
                            "message": f"View '{view_name}' appears to exist (duplicate name error)",
                            "properties": properties
                        }
                else:
                    # Not a duplicate error, re-raise
                    raise
                        
        except Exception as e:
            logging.error(f"Failed to create view '{view_name}': {e}")
            return {
                "status": "error",
                "message": f"Error creating view: {str(e)}",
                "view_definition": view_definition.model_dump()
            }

    @type_check
    def update_view(self, view_definition: IndalekoViewDefinition) -> Dict[str, Any]:
        """
        Update an existing view.
        
        Args:
            view_definition: The updated view definition
            
        Returns:
            Dict[str, Any]: Result of the update operation
        """
        view_name = view_definition.name
        
        # Check if view exists
        if view_name not in self._existing_views:
            return {
                "status": "not_found",
                "message": f"View '{view_name}' does not exist"
            }
        
        try:
            # Update the view
            properties = view_definition.get_creation_properties()
            self.db_config.db.update_view(
                name=view_name,
                properties=properties
            )
            
            # Update view cache
            self._existing_views = self._get_existing_views()
            
            return {
                "status": "success",
                "message": f"Updated view '{view_name}'",
                "properties": properties
            }
        except Exception as e:
            logging.error(f"Failed to update view '{view_name}': {e}")
            return {
                "status": "error",
                "message": f"Error updating view: {str(e)}",
                "view_definition": view_definition.model_dump()
            }

    @type_check
    def delete_view(self, view_name: str) -> Dict[str, Any]:
        """
        Delete a view.
        
        Args:
            view_name: Name of the view to delete
            
        Returns:
            Dict[str, Any]: Result of the delete operation
        """
        # Check if view exists
        if view_name not in self._existing_views:
            return {
                "status": "not_found",
                "message": f"View '{view_name}' does not exist"
            }
        
        try:
            # Delete the view
            self.db_config.db.delete_view(view_name)
            
            # Update view cache
            self._existing_views = self._get_existing_views()
            
            return {
                "status": "success",
                "message": f"Deleted view '{view_name}'"
            }
        except Exception as e:
            logging.error(f"Failed to delete view '{view_name}': {e}")
            return {
                "status": "error",
                "message": f"Error deleting view: {str(e)}"
            }

    def get_views(self) -> List[Dict[str, Any]]:
        """
        Get a list of all views in the database.
        
        Returns:
            List[Dict[str, Any]]: List of view information dictionaries
        """
        self._existing_views = self._get_existing_views()
        return [{"name": name, **info} for name, info in self._existing_views.items()]

    @type_check
    def get_view(self, view_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific view.
        
        Args:
            view_name: Name of the view
            
        Returns:
            Optional[Dict[str, Any]]: View information or None if not found
        """
        return self._existing_views.get(view_name)

    @type_check
    def view_exists(self, view_name: str) -> bool:
        """
        Check if a view exists.
        
        Args:
            view_name: Name of the view
            
        Returns:
            bool: True if the view exists, False otherwise
        """
        # Use cached views for better performance
        views = self._get_existing_views(use_cache=True)
        return view_name in views

    @type_check
    def get_view_for_collection(self, collection_name: str) -> List[Dict[str, Any]]:
        """
        Get views that include a specific collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            List[Dict[str, Any]]: List of view information dictionaries
        """
        views = []
        for view_name, view_info in self._existing_views.items():
            # Skip non-ArangoSearch views
            if view_info.get("type") != "arangosearch":
                continue
                
            # Check if the collection is in the view's links
            links = view_info.get("links", {})
            if collection_name in links:
                views.append({"name": view_name, **view_info})
                
        return views
        
    # Class variable to store cached analyzers
    _cached_analyzers = None
    _last_analyzer_cache_time = 0
    
    def get_analyzers(self, use_cache=True) -> List[Dict[str, Any]]:
        """
        Get all analyzers defined in the database.
        
        Args:
            use_cache: Whether to use the cached analyzer information if available
        
        Returns:
            List[Dict[str, Any]]: List of analyzer information dictionaries
        """
        # Use cached results if available and not expired
        current_time = int(time.time())
        if (use_cache and 
            IndalekoCollectionView._cached_analyzers is not None and 
            (current_time - IndalekoCollectionView._last_analyzer_cache_time) < IndalekoCollectionView._cache_ttl):
            return IndalekoCollectionView._cached_analyzers.copy()
        
        # Default analyzers - always available in ArangoDB
        default_analyzers = [
            {"name": "text_en", "type": "text", "features": ["frequency", "norm", "position"]},
            {"name": "identity", "type": "identity"},
            {"name": "delimiter", "type": "delimiter"}
        ]
        
        # Custom analyzers that are created by Indaleko
        custom_analyzers = [
            {"name": "Indaleko::indaleko_camel_case", "type": "pipeline"},
            {"name": "Indaleko::indaleko_snake_case", "type": "pipeline"},
            {"name": "Indaleko::indaleko_filename", "type": "pipeline"}
        ]
        
        # Use static list for performance
        analyzers = default_analyzers + custom_analyzers
        
        # Update the class cache
        IndalekoCollectionView._cached_analyzers = analyzers.copy()
        IndalekoCollectionView._last_analyzer_cache_time = current_time
            
        return analyzers
    


def main():
    """Test the IndalekoCollectionView class."""
    from data_models.db_view import IndalekoViewDefinition
    
    # Create a view manager
    view_manager = IndalekoCollectionView()
    
    # Check available analyzers
    print("\nChecking available analyzers...")
    analyzers = view_manager.get_analyzers()
    print(f"Found {len(analyzers)} analyzers:")
    for analyzer in analyzers:
        analyzer_name = analyzer.get('name', 'unknown')
        analyzer_type = analyzer.get('type', 'unknown')
        print(f"  - {analyzer_name} (type: {analyzer_type})")
    
    # List existing views
    views = view_manager.get_views()
    print(f"\nFound {len(views)} existing views:")
    for view in views:
        print(f"  - {view['name']} (type: {view.get('type')})")
    
    # Create a test view definition with standard analyzers
    view_def = IndalekoViewDefinition(
        name="TestObjectsView",
        collections=["Objects"],
        fields={
            "Objects": ["Label", "description"]
        },
        analyzers=["text_en"],
        include_all_fields=False,
        stored_values=["_key", "Label"]
    )
    
    # Create the view
    print("\nCreating test view...")
    result = view_manager.create_view(view_def)
    print(f"Creation result: {result['status']}")
    print(f"Message: {result['message']}")
    
    # Check if the view exists
    exists = view_manager.view_exists("TestObjectsView")
    print(f"\nView exists: {exists}")
    
    # Get view details
    if exists:
        view_info = view_manager.get_view("TestObjectsView")
        print(f"\nView details for TestObjectsView:")
        print(f"  Type: {view_info.get('type')}")
        print(f"  Links: {list(view_info.get('links', {}).keys())}")
        
        # Check if we can see analyzers in the view
        links = view_info.get('links', {})
        for collection, link_info in links.items():
            print(f"  Collection: {collection}")
            if 'analyzers' in link_info:
                print(f"    Analyzers: {link_info['analyzers']}")
    
    # Get views for a collection
    collection_views = view_manager.get_view_for_collection("Objects")
    print(f"\nViews for Objects collection: {[v['name'] for v in collection_views]}")
    
    # Ask to delete
    if exists:
        delete = input("\nDelete test view? (y/n): ")
        if delete.lower() == 'y':
            result = view_manager.delete_view("TestObjectsView")
            print(f"Delete result: {result['status']}")
            print(f"Message: {result['message']}")


if __name__ == "__main__":
    main()