"""
This module provides a CLI based interface for editin collection metadata for Indaleko.

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
import json
import tempfile
import subprocess
import sys

from icecream import ic
from typing import Union

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from data_models.collection_metadata_data_model import IndalekoCollectionMetadataDataModel  # noqa: E402
from db import IndalekoDBConfig  # noqa: E402
from db.db_collection_metadata import IndalekoDBCollectionsMetadata  # noqa: E402
from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
# pylint: enable=wrong-import-position


class CollectionMetadataEditor:
    """
    Allows interactive editing of CollectionMetadata using a user's default text editor.
    """

    def __init__(self, db: IndalekoDBConfig = IndalekoDBConfig()):
        """Initialize the editor with database connection."""
        self.db_metadata = IndalekoDBCollectionsMetadata(db)

    def export_metadata(self) -> dict:
        """Fetch and return all collection metadata as a dictionary."""
        return {name: meta.serialize() for name, meta in self.db_metadata.collections_metadata.items()}

    def edit_metadata(self, collection_name: str):
        """
        Opens the metadata for a collection in the system's default editor.
        Args:
            collection_name (str): The collection to edit.
        """
        if collection_name not in self.db_metadata.collections_metadata:
            print(f"Error: Collection '{collection_name}' not found.")
            return

        # Fetch metadata for editing
        metadata = self.db_metadata.collections_metadata[collection_name].serialize()

        # Write to a temp file
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmp_file:
            json.dump(metadata, tmp_file, indent=4)
            tmp_file.flush()  # Ensure all data is written
            tmp_file_path = tmp_file.name

        editor_options = []
        if os.environ.get("EDITOR"):
            editor_options.append(os.environ.get("EDITOR"))
        if os.environ.get("VISUAL"):
            editor_options.append(os.environ.get("VISUAL"))
        editor_options += ["code", "nano", "vim", "vi", "emacs", "subl", "notepad"]

        found = False
        for editor in editor_options:
            try:
                subprocess.run([editor, tmp_file_path])
                found = True
                break
            except FileNotFoundError:
                continue

        if not found:
            print("Error: No text editor found. Please set the EDITOR environment variable.")
            return

        edit_ok = False
        while not edit_ok:
            # Reload edited file
            with open(tmp_file_path, "r") as f:
                edited_data = json.load(f)

            # Validate and save changes
            try:
                self.apply_changes(collection_name, edited_data)
                edit_ok = True
            except Exception as e:
                print(f"Edited file raised an exception: {e}")
                retry = input("Retry editing? (y/n): ").strip().lower()
                if retry != "y":
                    break

        # Cleanup temp file
        os.remove(tmp_file_path)

    def apply_changes(self, collection_name: str, edited_data: dict):
        """
        Validates and updates collection metadata in the database.
        Args:
            collection_name (str): The collection being edited.
            edited_data (dict): The modified metadata.
        """
        try:
            # Deserialize into Pydantic model (ensures valid format)
            updated_metadata = IndalekoCollectionMetadataDataModel.deserialize(edited_data)

            # Update in the database
            db_collection = self.db_metadata.db_config.db.collection("CollectionMetadata")
            ic(updated_metadata.serialize())
            db_collection.insert(updated_metadata.serialize(), overwrite=True)

            print(f"Successfully updated metadata for '{collection_name}'.")

        except Exception as e:
            print(f"Error: Failed to update collection metadata - {e}")


def old_main():
    '''A CLI tool for editing Indaleko collection metadata.'''
    editor = CollectionMetadataEditor(IndalekoDBConfig())

    # List available collections
    collections = editor.export_metadata()
    print("\nAvailable collections:")
    for col in collections.keys():
        print(f"- {col}")

    # Prompt user for a collection to edit
    collection_name = input("\nEnter collection name to edit: ").strip()
    if collection_name:
        editor.edit_metadata(collection_name)


class IndalekoCollectorMetadataCLI(IndalekoBaseCLI):
    '''This class is used to define the command-line interface for the Indaleko collector metadata.'''

    service_name = 'collector_metadata_util'

    def __init__(self):
        '''Create an instance of the IndalekoCollectorMetadataCLI class.'''
        cli_data = IndalekoBaseCliDataModel(
            Service=IndalekoCollectorMetadataCLI.service_name,
        )
        handler_mixin = self.local_handler_mixin
        features = IndalekoBaseCLI.cli_features(
            machine_config=False,
            input=False,
            output=True,
            offline=False,
            logging=True,
            performance=False,
            platform=False,
        )
        super().__init__(cli_data, handler_mixin, features)
        config_data = self.get_config_data()
        config_file_path = os.path.join(config_data['ConfigDirectory'], config_data['DBConfigFile'])
        self.db_config = IndalekoDBConfig(config_file=config_file_path, start=True)

    def run(self):
        '''Run the command-line interface.'''
        ic('Running the IndalekoCollectorMetadataCLI')
        ic(self.config_data)
        args = self.get_args()
        ic(args)
        if hasattr(self, args.func):
            getattr(self, args.func)()

    def edit(self):
        '''Edit the metadata for the specified collection.'''
        ic('edit called')

    def backup(self):
        '''Backup the metadata for the specified collection.'''
        ic('backup called')

    def restore(self, collection_name: str):
        '''Restore the metadata for the specified collection.'''
        ic('restore called')

    class CollectorMetadataCLIHandlerMixin(IndalekoBaseCLI.default_handler_mixin):
        '''This class is used to provide callback processing for the IndalekoCollectorMetadataCLI class.'''

        @staticmethod
        def get_pre_parser() -> Union[argparse.Namespace, None]:
            '''
            This method is used to get the pre-parser.  Callers can
            set up switches/parameters before we add the common ones.

            Note the default implementation here does not add any additional parameters.
            '''
            ic('Getting the pre-parser')
            pre_parser = IndalekoBaseCLI.default_handler_mixin.get_pre_parser()
            command_subparser = pre_parser.add_subparsers(dest='command', help='Command to execute')
            edit_subparser = command_subparser.add_parser('edit', help='Edit the metadata for a collection')
            edit_subparser.set_defaults(func='edit')
            backup_subparser = command_subparser.add_parser('backup', help='Backup the metadata for a collection')
            backup_subparser.set_defaults(func='backup')
            restore_subparser = command_subparser.add_parser('restore', help='Restore the metadata for a collection')
            restore_subparser.set_defaults(func='restore')
            pre_parser.set_defaults(func='edit')
            return pre_parser

    local_handler_mixin = CollectorMetadataCLIHandlerMixin


def main():
    '''This is a CLI tool for managing the Indaleko collection metadata.'''
    cli = IndalekoCollectorMetadataCLI()
    cli.run()


if __name__ == "__main__":
    main()
