'''
This module is used to define the metadata for the collections.  This
is used to define how the collections are indexed and queried, which
is important for interfacing with the LLM.

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
'''
import os
import sys

from typing import Union
from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db import IndalekoDBConfig, IndalekoDBCollections
from data_models.collection_metadata_data_model import IndalekoCollectionMetadataDataModel, IndexMetadata
from utils import IndalekoSingleton
from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
# pylint: enable=wrong-import-position


class IndalekoDBCollectionsMetadata(IndalekoSingleton):
    '''
    This class is used to manage the metadata for the collections in the
    Indaleko database.
    '''

    def __init__(self,
                 db_config: IndalekoDBConfig = IndalekoDBConfig()):
        '''Initialize the object.'''
        self.collections = {}
        self.db_config = db_config
        self.collections = self.db_config.db.collections()
        self.collections_metadata = {}
        for collection in self.collections:
            if 'name' in collection and not collection['name'].startswith('_'):
                self.collections_metadata[collection['name']] = self.get_collection_metadata(collection['name'])

    def generate_new_collection_metadata(self, name: str) -> IndalekoCollectionMetadataDataModel:
        '''Generate a new collection metadata object.'''
        return IndalekoCollectionMetadataDataModel(
            key=name,
            Description=None,
            RelevantQueries=None,
            PrimaryKeys=None,
            IndexedFields=None,
            QueryGuidelines=None,
        )

        return IndalekoCollectionMetadataDataModel()

    def get_collection_metadata(self, collection_name: str) -> Union[IndalekoCollectionMetadataDataModel, None]:
        '''Get the metadata for the specified collection.'''
        db_collection = self.db_config.db.collection(IndalekoDBCollections.Indaleko_Collection_Metadata)
        assert db_collection is not None, \
            f'Failed to get collection {IndalekoDBCollections.Indaleko_Collection_Metadata}'
        entry = db_collection.get(collection_name)
        if not entry:
            return self.generate_new_collection_metadata(collection_name)
        return IndalekoCollectionMetadataDataModel.deserialize(**entry)


class IndalekoCollectorMetadataCLI(IndalekoBaseCLI):
    '''This class is used to define the command-line interface for the Indaleko collector metadata.'''

    service_name = 'IndalekoCollectorMetadataCLI'

    def __init__(self):
        '''Create an instance of the IndalekoCollectorMetadataCLI class.'''
        cli_data = IndalekoBaseCliDataModel()
        handler_mixin = IndalekoBaseCLI.default_handler_mixin
        features = IndalekoBaseCLI.cli_features(
            machine_config=False,
            input=False,
            output=False,
            offline=False,
            logging=False,
            performance=False,
            platform=False,
        )
        super().__init__(cli_data, handler_mixin, features)
        config_data = self.get_config_data()
        config_file_path = os.path.join(config_data['ConfigDirectory'], config_data['DBConfigFile'])
        self.db_config = IndalekoDBConfig(config_file=config_file_path, start=True)
        self.collections_metadata = IndalekoDBCollectionsMetadata()

    def get_db_collections_metadata(self, collection_name: str):
        '''Get the metadata for the specified collection.'''

    def run(self):
        '''Run the command-line interface.'''
        ic('Running the IndalekoCollectorMetadataCLI')


def main():
    ''''Main entry point for the program.'''
    ic('Hello, World!')
    IndalekoCollectorMetadataCLI().run()



if __name__ == "__main__":
    main()
