"""
IndalekoCollectionView.

This module is used to manage view creation for
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
import time

from pathlib import Path
from typing import Any

import arango

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))


# pylint: disable=wrong-import-position
from data_models.db_view import IndalekoViewDefinition
from db.db_config import IndalekoDBConfig
from utils.decorators import type_check


# pylint: enable=wrong-import-position

class IndalekoCollectionView:
    """Manages views for IndalekoCollection objects."""

    # Define default analyzers used in views
    DEFAULT_ANALYZERS = ("text_en")

    def __init__(self, db_config: IndalekoDBConfig | None = None) -> None:
        """
        Initialize the view manager.

        Args:
            db_config: Database configuration object. If None, a new one is created.
        """
        self.db_config = db_config if db_config is not None else IndalekoDBConfig()
        self.db_config.start()


    @type_check
    def create_view(self, view_definition: IndalekoViewDefinition) -> dict[str, Any] | None:
        """
        Create a view based on the provided definition.

        Args:
            view_definition: The view definition object

        Returns:
            Dict[str, Any]: Result of the view creation operation
        """
        view_name = view_definition.name


        # Get the database object
        db = self.db_config.get_arangodb()

        # Get view creation properties
        properties = view_definition.get_creation_properties()

        # Create the view using proper python-arango methods
        view_type = view_definition.type.lower()

        result = None
        if view_type == "arangosearch":
            ic("Creating ArangoSearch view", view_name)
            try:
                db.view(name=view_name)
                ic("View already exists, updating properties")
                # If the view already exists, update its properties
                result = db.update_arangosearch_view(
                    name=view_name,
                    properties=properties,
                )
            except arango.exceptions.ViewGetError:
                result = db.create_arangosearch_view(
                    name=view_name,
                    properties=properties,
                )
        else:
            raise NotImplementedError(
                f"View type '{view_type}' is not supported yet",
            )
        return result

    @type_check
    def update_view(self, view_definition: IndalekoViewDefinition) -> dict[str, Any]:
        """
        Update an existing view.

        Args:
            view_definition: The updated view definition

        Returns:
            Dict[str, Any]: Result of the update operation
        """
        view_name = view_definition.name

        # Update the view
        try:
            properties = view_definition.get_creation_properties()
            self.db_config.get_arangodb().update_view(name=view_name, properties=properties)

        except arango.exceptions.ViewGetError as error:
            return {
                "status": "failure",
                "message": error,
                "properties": None,
            }

        return {
            "status": "success",
            "message": f"Updated view '{view_name}'",
            "properties": properties,
        }

    @type_check
    def delete_view(self, view_name: str) -> dict[str, Any]:
        """
        Delete a view.

        Args:
            view_name: Name of the view to delete

        Returns:
            Dict[str, Any]: Result of the delete operation
        """
        # Delete the view
        try:
            self.db_config.get_arangodb().delete_view(view_name)
        except arango.exceptions.ViewGetError as error:
            return {
                "status": "failure",
                "message": error,
                "properties": None,
            }

        return {
            "status":
            "success",
            "message":
            f"Deleted view '{view_name}'",
        }

    def get_views(self) -> list[dict[str, Any]]:
        """
        Get a list of all views in the database.

        Returns:
            List[Dict[str, Any]]: List of view information dictionaries
        """
        ic(self.db_config.get_arangodb().views())


    @type_check
    def get_view(self, view_name: str) -> dict[str, Any] | None:
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
        return view_name in (view["name"] for view in self.db_config.get_arangodb().views())

    def get_analyzers(self, use_cache: bool=True) -> list[dict[str, Any]]:  # noqa: FBT001, FBT002
        """
        Get all analyzers defined in the database.

        Args:
            use_cache: Whether to use the cached analyzer information if available

        Returns:
            List[Dict[str, Any]]: List of analyzer information dictionaries
        """
        # Use cached results if available and not expired
        current_time = int(time.time())
        if (
            use_cache
            and IndalekoCollectionView._cached_analyzers is not None
            and (current_time -
                 IndalekoCollectionView._last_analyzer_cache_time
                ) < IndalekoCollectionView._cache_ttl
        ):
            return IndalekoCollectionView._cached_analyzers.copy()

        # Default analyzers - always available in ArangoDB
        default_analyzers = [
            {
                "name": "text_en",
                "type": "text",
                "features": ["frequency", "norm", "position"],
            },
            {"name": "identity", "type": "identity"},
            {"name": "delimiter", "type": "delimiter"},
        ]

        # Custom analyzers that are created by Indaleko
        custom_analyzers = [
            {"name": "Indaleko::indaleko_camel_case", "type": "pipeline"},
            {"name": "Indaleko::indaleko_snake_case", "type": "pipeline"},
            {"name": "Indaleko::indaleko_filename", "type": "pipeline"},
        ]

        # Use static list for performance
        analyzers = default_analyzers + custom_analyzers

        # Update the class cache
        IndalekoCollectionView._cached_analyzers = analyzers.copy()
        IndalekoCollectionView._last_analyzer_cache_time = current_time

        return analyzers


def main() -> None:
    """Test the IndalekoCollectionView class."""
    # Create a view manager
    view_manager = IndalekoCollectionView()

    # Check available analyzers
    analyzers = view_manager.get_analyzers()
    for analyzer in analyzers:
        analyzer.get("name", "unknown")
        analyzer.get("type", "unknown")

    # List existing views
    views = view_manager.get_views()
    for _view in views:
        ic(_view)

    # Create a test view definition with standard analyzers
    view_def = IndalekoViewDefinition(
        name="TestObjectsView",
        collections=["Objects"],
        fields={"Objects": ["Label", "description"]},
        analyzers=["text_en"],
        include_all_fields=False,
        stored_values=["_key", "Label"],
    )

    # Create the view
    if view_def.name not in views:
        ic("Creating test view:", view_def)
        view_manager.create_view(view_def)

    # Check if the view exists
    exists = view_manager.view_exists("TestObjectsView")

    # Get view details
    if exists:
        view_info = view_manager.get_view("TestObjectsView")

        # Check if we can see analyzers in the view
        links = view_info.get("links", {})
        for link_info in links.values():
            if "analyzers" in link_info:
                pass

    # Get views for a collection
    view_manager.get_view_for_collection("Objects")

    # Ask to delete
    if exists:
        delete = input("\nDelete test view? (y/n): ")
        if delete.lower() == "y":
            view_manager.delete_view("TestObjectsView")


if __name__ == "__main__":
    main()
