#!/usr/bin/env python3
"""
Prompt Management System Database Setup

This script creates and configures the database collections, indices, and views
required by the Prompt Management System. It should be run once during initial setup
or when updating the schema.

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
from pathlib import Path

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from data_models.db_view import IndalekoViewDefinition
from db.collection import IndalekoCollection
from db.collection_view import IndalekoCollectionView
from db.db_collections import IndalekoDBCollections
from db.db_config import IndalekoDBConfig
from db.i_collections import IndalekoCollectionsBase
from query.utils.prompt_management.data_models.base import (
    PromptTemplate,
    PromptCacheEntry,
    PromptArchiveEntry,
    StabilityMetric,
)
# pylint: enable=wrong-import-position

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PromptManagementDatabaseSetup:
    """Setup class for Prompt Management System database components."""

    def __init__(self, db_config=None, force_recreate=False):
        """
        Initialize the setup manager.

        Args:
            db_config: Database configuration to use (None creates a new one)
            force_recreate: Whether to recreate collections even if they exist
        """
        self.db_config = db_config if db_config is not None else IndalekoDBConfig()
        self.db_config.start()
        self.force_recreate = force_recreate
        self.view_manager = IndalekoCollectionView(db_config=self.db_config)

    def get_collection_info(self, collection_name):
        """
        Get collection information including schema from db_collections.

        Args:
            collection_name: The name of the collection to get info for

        Returns:
            dict: Collection configuration or None if not found
        """
        # Get configuration from IndalekoDBCollections
        return IndalekoDBCollections.Collections.get(collection_name)

    def check_collection_exists(self, collection_name):
        """
        Check if a collection exists in the database.

        Args:
            collection_name: The name of the collection to check

        Returns:
            bool: True if the collection exists, False otherwise
        """
        # Check if collection exists in database
        db = self.db_config.get_arangodb()
        return db.has_collection(collection_name)

    def create_collection(self, collection_name):
        """
        Create a collection in the database.

        Args:
            collection_name: The name of the collection to create

        Returns:
            IndalekoCollection: The created collection object or None if failed
        """
        # Get collection configuration
        collection_info = self.get_collection_info(collection_name)
        if not collection_info:
            logger.error(f"Collection {collection_name} not found in configuration")
            return None

        # Check if collection exists
        if self.check_collection_exists(collection_name) and not self.force_recreate:
            logger.info(f"Collection {collection_name} already exists, skipping creation")
            # Return existing collection wrapped in IndalekoCollection
            collection = self.db_config.get_arangodb().collection(collection_name)
            return IndalekoCollection(ExistingCollection=collection, db=self.db_config)

        # Create the collection
        try:
            indaleko_collection = IndalekoCollection(
                name=collection_name,
                definition=collection_info,
                db=self.db_config,
                reset=self.force_recreate,
            )
            logger.info(f"Created collection {collection_name}")
            return indaleko_collection
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            return None

    def create_view(self, collection_name):
        """
        Create views for a collection.

        Args:
            collection_name: The name of the collection to create views for

        Returns:
            list: List of created view names or empty list if failed
        """
        # Get collection configuration
        collection_info = self.get_collection_info(collection_name)
        if not collection_info:
            logger.error(f"Collection {collection_name} not found in configuration")
            return []

        # Check if views are defined for the collection
        views = collection_info.get("views", [])
        if not views:
            logger.info(f"No views defined for collection {collection_name}")
            return []

        created_views = []
        for view_config in views:
            view_name = view_config.get("name")
            fields = view_config.get("fields")
            analyzers = view_config.get("analyzers", ["text_en"])
            include_all_fields = view_config.get("include_all_fields", False)
            stored_values = view_config.get("stored_values", [])

            # Create view definition
            view_def = IndalekoViewDefinition(
                name=view_name,
                collections=[collection_name],
                fields={collection_name: fields} if isinstance(fields, list) else fields,
                analyzers=analyzers,
                include_all_fields=include_all_fields,
                stored_values=stored_values,
            )

            # Create the view
            try:
                result = self.view_manager.create_view(view_def)
                if result:
                    logger.info(f"Created view {view_name} for collection {collection_name}")
                    created_views.append(view_name)
                else:
                    logger.warning(f"Failed to create view {view_name} for collection {collection_name}")
            except Exception as e:
                logger.error(f"Error creating view {view_name}: {e}")

        return created_views

    def setup_prompt_management_collections(self):
        """
        Set up all collections and views required by the Prompt Management System.

        Returns:
            dict: Summary of created collections and views
        """
        results = {"collections": [], "views": []}

        # Define the collections to create
        collections = [
            IndalekoDBCollections.Indaleko_Prompt_Templates_Collection,
            IndalekoDBCollections.Indaleko_Prompt_Cache_Recent_Collection,
            IndalekoDBCollections.Indaleko_Prompt_Cache_Archive_Collection,
            IndalekoDBCollections.Indaleko_Prompt_Stability_Metrics_Collection,
        ]

        # Create the collections
        for collection_name in collections:
            collection = self.create_collection(collection_name)
            if collection:
                results["collections"].append(collection_name)

                # Create views for the collection
                views = self.create_view(collection_name)
                results["views"].extend(views)

        return results


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Setup Prompt Management System database components")
    parser.add_argument("--force", action="store_true", help="Force recreation of existing collections")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    # Create setup manager
    setup_manager = PromptManagementDatabaseSetup(force_recreate=args.force)

    # Setup collections and views
    logger.info("Setting up Prompt Management System database components...")
    results = setup_manager.setup_prompt_management_collections()

    # Print results
    logger.info("Setup completed:")
    logger.info(f"Collections created: {len(results['collections'])}")
    for collection in results["collections"]:
        logger.info(f"  - {collection}")
    logger.info(f"Views created: {len(results['views'])}")
    for view in results["views"]:
        logger.info(f"  - {view}")


if __name__ == "__main__":
    main()
