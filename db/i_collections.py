"""
IndalecoCollections.py - This module is used to manage the collections in the
Indaleko database.


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
import json
import logging
import os
import sys

import arango

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
# from Indaleko import Indaleko
from data_models.db_view import IndalekoViewDefinition
from db.analyzer_manager import IndalekoAnalyzerManager
from db.collection import IndalekoCollection
from db.collection_index import IndalekoCollectionIndex
from db.collection_view import IndalekoCollectionView
from db.db_collections import IndalekoDBCollections
from db.db_config import IndalekoDBConfig
from utils.singleton import IndalekoSingleton

# pylint: enable=wrong-import-position


class IndalekoCollections(IndalekoSingleton):
    """
    This class is used to manage the collections in the Indaleko database.
    """

    def __init__(self, **kwargs) -> None:
        # db_config: IndalekoDBConfig = None, reset: bool = False) -> None:
        self.db_config = kwargs.get("db_config", IndalekoDBConfig())
        if self.db_config is None:
            self.db_config = IndalekoDBConfig()
        self.reset = kwargs.get("reset", False)

        # Skip view creation if specified (for performance optimization)
        self.skip_views = kwargs.get("skip_views", False)

        logging.debug("Starting database")
        self.db_config.start()
        self.collections = {}

        # Create or update collections
        for name in IndalekoDBCollections.Collections.items():
            name = name[0]
            logging.debug("Processing collection %s", name)
            try:
                self.collections[name] = IndalekoCollection(
                    name=name,
                    definition=IndalekoDBCollections.Collections[name],
                    db=self.db_config,
                    reset=self.reset,
                )
            except (
                arango.exceptions.CollectionConfigureError
            ) as error:  # pylint: disable=no-member
                logging.exception("Failed to configure collection %s", name)
                print(f"Failed to configure collection {name}")
                print(error)
                if IndalekoDBCollections.Collections[name]["schema"] is not None:
                    print("Schema:")
                    print(
                        json.dumps(
                            IndalekoDBCollections.Collections[name]["schema"], indent=2,
                        ),
                    )
                raise error

        # Create or update views (unless skipped)
        if not self.skip_views:
            self._create_views()
        else:
            logging.debug("Skipping view creation (skip_views=True)")

    def _ensure_custom_analyzers(self) -> None:
        """Ensure custom analyzers are created before setting up views."""
        logging.debug("Ensuring custom analyzers exist...")

        # Use lazy import to avoid circular dependency

        analyzer_manager = IndalekoAnalyzerManager(db_config=self.db_config)

        # Create all custom analyzers
        results = analyzer_manager.create_all_analyzers()

        # Log results
        for analyzer, success in results.items():
            if success:
                logging.debug(f"Analyzer {analyzer} is available")
            else:
                logging.warning(f"Failed to create analyzer {analyzer}")

        # Verify all required analyzers are available
        required_analyzers = [
            analyzer_manager.CAMEL_CASE_ANALYZER,
            analyzer_manager.SNAKE_CASE_ANALYZER,
            analyzer_manager.FILENAME_ANALYZER,
        ]

        # Get list of existing analyzers for verification
        available_analyzers = [
            a.get("name", "") for a in analyzer_manager.list_analyzers()
        ]

        # Log any missing analyzers
        for analyzer in required_analyzers:
            if analyzer not in available_analyzers:
                logging.warning(f"Required analyzer {analyzer} is not available")

    def _create_views(self) -> None:
        """Create or update views for collections that have view definitions."""
        # First ensure custom analyzers are created
        self._ensure_custom_analyzers()

        # Now create/update views
        view_manager = IndalekoCollectionView(db_config=self.db_config)
        created_views = []

        # Process views for each collection
        for (
            collection_name,
            collection_def,
        ) in IndalekoDBCollections.Collections.items():
            # Skip collections without view definitions
            if "views" not in collection_def:
                continue

            # Process each view definition for this collection
            for view_def in collection_def["views"]:
                view_name = view_def["name"]
                logging.debug(
                    f"Processing view {view_name} for collection {collection_name}",
                )

                # Skip if already processed
                if view_name in created_views:
                    continue

                # Create the view definition
                fields_dict = {collection_name: view_def["fields"]}

                # Handle the case where fields are defined with specific analyzers per field
                # Format: {"Field1": ["analyzer1", "analyzer2"], "Field2": ["analyzer3"]}

                # Ensure we use the default analyzers if not specified
                analyzers = view_def.get("analyzers", ["text_en"])

                # For collections that deal with file objects, ensure we include our custom analyzers
                if collection_name.lower() in ["objects"]:
                    # Add our custom analyzers if not already included
                    custom_analyzers = [
                        "Indaleko::indaleko_camel_case",
                        "Indaleko::indaleko_snake_case",
                        "Indaleko::indaleko_filename",
                    ]
                    for analyzer in custom_analyzers:
                        if analyzer not in analyzers:
                            analyzers.append(analyzer)

                view_definition = IndalekoViewDefinition(
                    name=view_name,
                    collections=[collection_name],
                    fields=fields_dict,
                    analyzers=analyzers,
                    include_all_fields=view_def.get("include_all_fields", False),
                    stored_values=view_def.get("stored_values"),
                )

                # Create or update the view
                if view_manager.view_exists(view_name):
                    result = view_manager.update_view(view_definition)
                    logging.debug(f"Updated view {view_name}: {result['status']}")
                else:
                    result = view_manager.create_view(view_definition)
                    logging.debug(f"Created view {view_name}: {result['status']}")

                # Add to processed list
                created_views.append(view_name)

    @staticmethod
    def get_collection(name: str, skip_views=False) -> IndalekoCollection:
        """
        Return the collection with the given name.

        Args:
            name: The name of the collection to retrieve
            skip_views: If True, skip view creation for performance
        """
        # Special case for MachineConfig collection, always skip views for performance
        # This is particularly important for the machine_config.py script
        if name == IndalekoDBCollections.Indaleko_MachineConfig_Collection:
            skip_views = True

        # Check environment variable for global view skipping (useful for scripts)
        if os.environ.get("INDALEKO_SKIP_VIEWS", "0") == "1":
            skip_views = True

        collections = IndalekoCollections(skip_views=skip_views)
        collection = None
        if name not in collections.collections:
            # Look for it by the specific name (activity data providers do this)
            if not collections.db_config._arangodb.has_collection(name):
                collection = IndalekoCollection(name=name, db=collections.db_config)
            else:
                collection = IndalekoCollection(
                    ExistingCollection=collections.db_config._arangodb.collection(name),
                )
        else:
            collection = collections.collections[name]
        return collection

    @staticmethod
    def get_view(name: str) -> dict:
        """Return the view with the given name."""
        collections = IndalekoCollections()
        view_manager = IndalekoCollectionView(db_config=collections.db_config)
        return view_manager.get_view(name)


def extract_params() -> tuple:
    """Extract the common parameters from the given keyword arguments."""
    common_params = set(IndalekoCollectionIndex.index_args["hash"].keys())
    for params in IndalekoCollectionIndex.index_args.values():
        common_params = common_params.intersection(params)
        common_params.intersection_update(params)
    unique_params_by_index = {
        index: list(set(params) - common_params)
        for index, params in IndalekoCollectionIndex.index_args.items()
    }
    return common_params, unique_params_by_index


def main():
    """Test the IndalekoCollections class."""
    # start_time = datetime.datetime.now(datetime.UTC).isoformat()
    IndalekoCollections()
    common_params, unique_params_by_index = extract_params()
    print(common_params)
    print(unique_params_by_index)
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument(
        "--collection",
        type=str,
        help="Name of the collection to which the index will be added",
        required=True,
    )
    pre_parser.add_argument(
        "--type",
        type=str,
        help="Type of index to create",
        choices=IndalekoCollectionIndex.index_args.keys(),
        default="persistent",
    )
    for common_arg in common_params:
        arg_type = IndalekoCollectionIndex.index_args["hash"][common_arg]
        print(f"Adding argument {common_arg} with type {arg_type}")
        pre_parser.add_argument(
            f"--{common_arg}",
            type=IndalekoCollectionIndex.index_args["hash"][common_arg],
            required=True,
            help=f"Value for {common_arg}",
        )
    pre_args, _ = pre_parser.parse_known_args()
    parser = argparse.ArgumentParser(
        description="Create an index for an IndalekoCollection", parents=[pre_parser],
    )
    for index_args in unique_params_by_index[pre_args.type]:
        arg_type = IndalekoCollectionIndex.index_args[pre_args.type][index_args]
        if arg_type is bool:
            parser.add_argument(
                f"--{index_args}",
                action="store_true",
                default=None,
                help=f"Value for {index_args}",
            )
        else:
            parser.add_argument(
                f"--{index_args}",
                type=IndalekoCollectionIndex.index_args[pre_args.type][index_args],
                default=None,
                help=f"Value for {index_args}",
            )
    args = parser.parse_args()
    if hasattr(args, "fields"):
        args.fields = [field.strip() for field in pre_args.fields.split(",")]
    print(args)
    index_args = {"collection": args.collection}
    for index_arg in common_params:
        if getattr(args, index_arg) is not None:
            index_args[index_arg] = getattr(args, index_arg)
    for index_arg in unique_params_by_index[pre_args.type]:
        if getattr(args, index_arg) is not None:
            index_args[index_arg] = getattr(args, index_arg)
    print(index_args)
    print("TODO: add tests for the various type of indices")


if __name__ == "__main__":
    main()
