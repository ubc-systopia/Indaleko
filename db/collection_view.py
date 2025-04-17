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

    def __init__(self, db_config: Optional[IndalekoDBConfig] = None):
        """
        Initialize the view manager.
        
        Args:
            db_config: Database configuration object. If None, a new one is created.
        """
        self.db_config = db_config if db_config is not None else IndalekoDBConfig()
        self.db_config.start()
        self._existing_views = self._get_existing_views()

    def _get_existing_views(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all existing views from the database.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of view names to view information
        """
        views = {}
        try:
            # Properly access the database object from ArangoDB
            db = self.db_config.db
            
            # Get list of views using the proper ArangoDB Python driver method
            try:
                # Get all views (safer approach)
                cursor = db.aql.execute("FOR v IN _views RETURN v")
                view_data = [doc for doc in cursor]
                
                # Process each view
                for view_info in view_data:
                    if "name" in view_info:
                        view_name = view_info["name"]
                        views[view_name] = view_info
                
                logging.info(f"Retrieved {len(views)} views from ArangoDB")
            except Exception as view_error:
                logging.warning(f"Error retrieving views with AQL: {view_error}")
                
                # If the above failed, try another approach
                try:
                    # Get direct access to ArangoDB connection
                    conn = db.connection
                    
                    # Use low-level API to get views
                    resp = conn.get(f'/_db/{db.name}/_api/view')
                    if resp.status_code == 200:
                        result = resp.body.get('result', [])
                        for view_info in result:
                            if "name" in view_info:
                                view_name = view_info["name"]
                                views[view_name] = view_info
                    else:
                        logging.warning(f"Failed to get views using API: {resp.error_message}")
                except Exception as api_error:
                    logging.warning(f"Error using connection API: {api_error}")
                    
                    # One last attempt - try each view individually if we have a list
                    try:
                        # Try to get known view names
                        known_views = [
                            "ObjectsTextView", 
                            "ActivityTextView", 
                            "NamedEntityTextView", 
                            "EntityEquivalenceTextView",
                            "KnowledgeTextView"
                        ]
                        
                        for view_name in known_views:
                            try:
                                # Try to get view info
                                view_resp = conn.get(f'/_db/{db.name}/_api/view/{view_name}')
                                if view_resp.status_code == 200:
                                    views[view_name] = view_resp.body
                            except Exception:
                                # Ignore errors for individual views
                                pass
                    except Exception as known_view_error:
                        logging.warning(f"Error retrieving known views: {known_view_error}")
                
        except Exception as e:
            logging.error(f"Failed to retrieve existing views: {e}")
            
        # Return whatever views we found - will be empty dict if none were found
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
        return view_name in self._existing_views

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


def main():
    """Test the IndalekoCollectionView class."""
    from data_models.db_view import IndalekoViewDefinition
    
    # Create a view manager
    view_manager = IndalekoCollectionView()
    
    # List existing views
    views = view_manager.get_views()
    print(f"Found {len(views)} existing views:")
    for view in views:
        print(f"  - {view['name']} (type: {view.get('type')})")
    
    # Create a test view definition
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
    
    # Get views for a collection
    collection_views = view_manager.get_view_for_collection("Objects")
    print(f"\nViews for Objects collection: {[v['name'] for v in collection_views]}")
    
    # Update the view
    if exists:
        print("\nUpdating test view...")
        view_def.fields["Objects"].append("URI")
        result = view_manager.update_view(view_def)
        print(f"Update result: {result['status']}")
        print(f"Message: {result['message']}")
    
    # Ask to delete
    if exists:
        delete = input("\nDelete test view? (y/n): ")
        if delete.lower() == 'y':
            result = view_manager.delete_view("TestObjectsView")
            print(f"Delete result: {result['status']}")
            print(f"Message: {result['message']}")


if __name__ == "__main__":
    main()