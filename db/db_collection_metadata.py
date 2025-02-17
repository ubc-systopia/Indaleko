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
from activity.activity_metadata import ActivityCollectionMetadata
from activity.recorders.registration_service import IndalekoActivityDataRegistrationService
from db import IndalekoDBConfig, IndalekoDBCollections
from data_models.collection_info import CollectionInfo
from data_models.collection_metadata_data_model import IndalekoCollectionMetadataDataModel
from data_models.db_index import IndalekoCollectionIndexDataModel
from platforms.machine_config_metadata import MachineConfigCollectionMetadata
from storage.object_metadata import ObjectCollectionMetadata
from storage.relationship_metadata import RelationshipCollectionMetadata
from utils import IndalekoSingleton
from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
# pylint: enable=wrong-import-position


class IndalekoDBCollectionsMetadata(IndalekoSingleton):
    '''
    This class is used to manage the metadata for the collections in the
    Indaleko database.
    '''

    default_collection_metadata = {
        IndalekoDBCollections.Indaleko_Object_Collection: ObjectCollectionMetadata.default_metadata,
        IndalekoDBCollections.Indaleko_Relationship_Collection: RelationshipCollectionMetadata.default_metadata,
        IndalekoDBCollections.Indaleko_MachineConfig_Collection: MachineConfigCollectionMetadata.default_metadata,
        'ActivityData': ActivityCollectionMetadata.default_metadata,
    }

    def __init__(self,
                 db_config: IndalekoDBConfig = IndalekoDBConfig()):
        '''Initialize the object.'''
        if self._initialized:
            return
        self.collections = {}
        self.db_config = db_config
        self.collections = self.db_config.db.collections()
        self.collections_metadata = {}
        self.collections_additional_data = {}
        self._initialized = True
        for collection in self.collections:
            if 'name' not in collection:
                continue
            if collection['name'] not in IndalekoDBCollections.Collections:
                continue
            if 'internal' not in IndalekoDBCollections.Collections[collection['name']] or \
                    not IndalekoDBCollections.Collections[collection['name']]['internal']:
                # Only gather metadata for external collections
                self.collections_metadata[collection['name']] = self.get_collection_metadata(collection['name'])
            if collection['name'] not in self._collection_handlers:  # handlers can add more information
                continue  # Done with this collection
            ic(f'Processing additional data for collection {collection["name"]}')
            assert collection['name'] in self._collection_handlers, \
                f'Failed to find handler for collection {collection["name"]}'
            self._collection_handlers[collection['name']](self)

    def generate_new_collection_metadata(self, name: str) -> IndalekoCollectionMetadataDataModel:
        '''Generate a new collection metadata object.'''
        if self.default_collection_metadata.get(name):
            return self.default_collection_metadata[name]
        db_collection = self.db_config.db.collection(name)
        assert db_collection is not None, f'Failed to get collection {name}'
        description = db_collection.properties().get('description', "No description available")
        query_guidelines = [db_collection.properties().get('query_guidelines', "No guidelines provided")]
        schema = db_collection.properties().get('schema', {})
        if not schema:
            schema = {}
        if 'rule' in schema:
            schema = schema['rule']
        return IndalekoCollectionMetadataDataModel(
            key=name,
            Description=description,
            QueryGuidelines=query_guidelines,
            Schema=schema,
        )

    def get_collection_metadata(self, collection_name: str) -> Union[IndalekoCollectionMetadataDataModel, None]:
        '''Get the metadata for the specified collection.'''
        db_collection = self.db_config.db.collection(IndalekoDBCollections.Indaleko_Collection_Metadata)
        assert db_collection is not None, \
            f'Failed to get collection {IndalekoDBCollections.Indaleko_Collection_Metadata}'
        ic(collection_name)
        entry = db_collection.get(collection_name)
        if not entry:
            return self.generate_new_collection_metadata(collection_name)
        if 'Schema' not in entry:
            entry['Schema'] = {}
        return IndalekoCollectionMetadataDataModel.deserialize(entry)

    def get_all_collections_metadata(self) -> dict[str, IndalekoCollectionMetadataDataModel]:
        '''
        Get the metadata for all collections.

        Note: this does not cache data, callers may wish to do so.
        '''
        collection_data = {}
        for name, data in self.collections_metadata.items():
            collection = self.db_config.db.collection(name)
            if collection is None:
                ic(f'Failed to get collection {name}')
                continue
            indices = [
                IndalekoCollectionIndexDataModel(
                    Name=index.get('name'),
                    Type=index.get('type'),
                    Fields=index.get('fields'),
                    Unique=index.get('unique'),
                    Sparse=index.get('sparse'),
                    Deduplicate=index.get('deduplicate'),
                )
                for index in collection.indexes()
            ]
            collection_data[name] = CollectionInfo(
                Name=name,
                Description=data.Description,
                Indices=indices,
                Schema=data.Schema,
                QueryGuidelines=data.QueryGuidelines,
            )
        return collection_data

    def __activity_data_provider_collection_handler(self) -> None:
        '''Handle the activity data provider collection.'''
        collection_data = {}
        collections_metadata = IndalekoDBCollectionsMetadata()
        for provider in IndalekoActivityDataRegistrationService.get_provider_list():
            collection = IndalekoActivityDataRegistrationService.\
                lookup_activity_provider_collection(provider['Identifier'])
            collection_metadata = collections_metadata.get_collection_metadata(collection.name)
            self.collections_metadata[collection.name] = collection_metadata
        return collection_data

    _collection_handlers = {
        IndalekoDBCollections.Indaleko_ActivityDataProvider_Collection: __activity_data_provider_collection_handler,
    }


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
        ic(self.collections_metadata.collections_metadata)
        ic(self.collections_metadata.collections_additional_data)


def main():
    ''''Main entry point for the program.'''
    IndalekoCollectorMetadataCLI().run()


if __name__ == "__main__":
    main()
