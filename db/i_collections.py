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
import logging
import os
import json
import sys

import arango

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
# from Indaleko import Indaleko
from db.db_config import IndalekoDBConfig
from db.collection_index import IndalekoCollectionIndex
from db.collection import IndalekoCollection
from db.db_collections import IndalekoDBCollections
from utils.singleton import IndalekoSingleton
# pylint: enable=wrong-import-position


class IndalekoCollections(IndalekoSingleton):
    """
    This class is used to manage the collections in the Indaleko database.
    """

    def __init__(self, **kwargs) -> None:
        # db_config: IndalekoDBConfig = None, reset: bool = False) -> None:
        self.db_config = kwargs.get('db_config', IndalekoDBConfig())
        if self.db_config is None:
            self.db_config = IndalekoDBConfig()
        self.reset = kwargs.get('reset', False)
        logging.debug('Starting database')
        self.db_config.start()
        self.collections = {}
        for name in IndalekoDBCollections.Collections.items():
            name = name[0]
            logging.debug('Processing collection %s', name)
            try:
                self.collections[name] = IndalekoCollection(name=name,
                                                            definition=IndalekoDBCollections.Collections[name],
                                                            db=self.db_config,
                                                            reset=self.reset)
            except arango.exceptions.CollectionConfigureError as error:  # pylint: disable=no-member
                logging.error('Failed to configure collection %s', name)
                print(f'Failed to configure collection {name}')
                print(error)
                if IndalekoDBCollections.Collections[name]['schema'] is not None:
                    print('Schema:')
                    print(json.dumps(IndalekoDBCollections.Collections[name]['schema'], indent=2))
                raise error

    @staticmethod
    def get_collection(name: str) -> IndalekoCollection:
        """Return the collection with the given name."""
        collections = IndalekoCollections()
        collection = None
        if name not in collections.collections:
            # Look for it by the specific name (activity data providers do this)
            if not collections.db_config.db.has_collection(name):
                collection = IndalekoCollection(name=name, db=collections.db_config)
            else:
                collection = \
                    IndalekoCollection(ExistingCollection=collections.db_config.db.collection(name))
        else:
            collection = collections.collections[name]
        return collection


def extract_params() -> tuple:
    '''Extract the common parameters from the given keyword arguments.'''
    common_params = set(IndalekoCollectionIndex.index_args['hash'].keys())
    for params in IndalekoCollectionIndex.index_args.values():
        common_params = common_params.intersection(params)
        common_params.intersection_update(params)
    unique_params_by_index = {
        index: list(set(params) - common_params) for index, params in IndalekoCollectionIndex.index_args.items()
    }
    return common_params, unique_params_by_index


def main():
    '''Test the IndalekoCollections class.'''
    # start_time = datetime.datetime.now(datetime.UTC).isoformat()
    common_params, unique_params_by_index = extract_params()
    print(common_params)
    print(unique_params_by_index)
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--collection',
                            type=str,
                            help='Name of the collection to which the index will be added',
                            required=True)
    pre_parser.add_argument('--type',
                            type=str,
                            help='Type of index to create',
                            choices=IndalekoCollectionIndex.index_args.keys(),
                            default='persistent')
    for common_arg in common_params:
        arg_type = IndalekoCollectionIndex.index_args['hash'][common_arg]
        print(f'Adding argument {common_arg} with type {arg_type}')
        pre_parser.add_argument(f'--{common_arg}',
                                type=IndalekoCollectionIndex.index_args['hash'][common_arg],
                                required=True,
                                help=f'Value for {common_arg}')
    pre_args, _ = pre_parser.parse_known_args()
    parser = argparse.ArgumentParser(description='Create an index for an IndalekoCollection', parents=[pre_parser])
    for index_args in unique_params_by_index[pre_args.type]:
        arg_type = IndalekoCollectionIndex.index_args[pre_args.type][index_args]
        if arg_type is bool:
            parser.add_argument(f'--{index_args}',
                                action='store_true',
                                default=None,
                                help=f'Value for {index_args}')
        else:
            parser.add_argument(f'--{index_args}',
                                type=IndalekoCollectionIndex.index_args[pre_args.type][index_args],
                                default=None,
                                help=f'Value for {index_args}')
    args = parser.parse_args()
    if hasattr(args, 'fields'):
        args.fields = [field.strip() for field in pre_args.fields.split(',')]
    print(args)
    index_args = {'collection': args.collection}
    for index_arg in common_params:
        if getattr(args, index_arg) is not None:
            index_args[index_arg] = getattr(args, index_arg)
    for index_arg in unique_params_by_index[pre_args.type]:
        if getattr(args, index_arg) is not None:
            index_args[index_arg] = getattr(args, index_arg)
    print(index_args)
    print('TODO: add tests for the various type of indices')


if __name__ == "__main__":
    main()
