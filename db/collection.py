'''
This module is used to manage specific collection objects in Indaleko.

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

import arango
import json
import os
import sys

import arango.collection
from icecream import ic
from typing import Any, Dict, Sequence, Union

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from utils.decorators import type_check
# pylint: enable=wrong-import-position


from db.db_config import IndalekoDBConfig
from db.collection_index import IndalekoCollectionIndex

class IndalekoCollection():
    """
    An IndalekoCollection object is used to manage a collection of documents in the
    Indaleko database.
    """

    def __init__(self, **kwargs):
        if 'ExistingCollection' in kwargs:
            self.collection = kwargs['ExistingCollection']
            assert isinstance(self.collection, arango.collection.StandardCollection), \
                f'self.collection is unexpected type {type(self.collection)}'
            self.name = self.collection.name
            self.definition = self.collection.properties()
            self.db_config = kwargs.get('db', IndalekoDBConfig())
            self.collection_name = self.name
            self.indices = {}
            return
        if 'name' not in kwargs:
            raise ValueError('name is a required parameter')
        self.name = kwargs['name']
        self.definition = kwargs.get('definition', None)
        self.db_config = kwargs.get('db', None)
        self.db_config.start()
        self.reset = kwargs.get('reset', False)
        self.max_chunk_size = kwargs.get('max_chunk_size', 1000)
        self.collection_name = self.name
        self.indices = {}
        if self.definition is None:
            raise ValueError('Dynamic collection does not exist')
        assert isinstance(self.definition, dict), 'Collection definition must be a dictionary'
        assert 'schema' in self.definition, 'Collection must have a schema'
        assert 'edge' in self.definition, 'Collection must have an edge flag'
        assert 'indices' in self.definition, 'Collection must have indices'
        assert isinstance(self.db_config, IndalekoDBConfig), \
            'db must be None or an IndalekoDBConfig object'
        self.create_collection(self.collection_name, self.definition, reset=self.reset)

    @type_check
    def create_collection(self,
                          name : str,
                          config : dict,
                          reset : bool = False) -> 'IndalekoCollection':
        """
        Create a collection in the database. If the collection already exists,
        return the existing collection. If reset is True, delete the existing
        collection and create a new one.
        """
        if self.db_config.db.has_collection(name):
            if not reset:
                self.collection = self.db_config.db.collection(name)
            else:
                raise NotImplementedError('delete existing collection not implemented')
        else:
            self.collection = self.db_config.db.create_collection(name, edge=config['edge'])
            if 'schema' in config:
                try:
                    self.collection.configure(schema=config['schema'])
                except arango.exceptions.CollectionConfigureError as error: # pylint: disable=no-member
                    print(f'Failed to configure collection {name}')
                    print(error)
                    print('Schema:')
                    print(json.dumps(config['schema'], indent=2))
                    raise error
            if 'indices' in config:
                for index in config['indices']:
                    self.create_index(index,
                                      config['indices'][index]['type'],
                                      config['indices'][index]['fields'],
                                      config['indices'][index]['unique'])
        assert isinstance(self.collection, arango.collection.StandardCollection), \
            f'self.collection is unexpected type {type(self.collection)}'
        return IndalekoCollection(ExistingCollection=self.collection)

    @type_check
    def delete_collection(self, name: str) -> bool:
        '''Delete the collection with the given name.'''
        if not self.db_config.db.has_collection(name):
            print(f'Collection {name} does not exist **')
            return False
        self.db_config.db.delete_collection(name)
        print(f'Collection {name} does exists, requesting deletion **')
        return True

    @type_check
    def create_index(self,
                     name: str,
                     index_type: str,
                     fields: list,
                     unique: bool) -> 'IndalekoCollection':
        """Create an index for the given collection."""
        self.indices[name] = IndalekoCollectionIndex(
            collection=self.collection,
            name=name,
            index_type=index_type,
            fields=fields,
            unique=unique)
        return self

    def find_entries(self, **kwargs):
        """Given a list of keyword arguments, return a list of documents that match the criteria."""
        return [document for document in self.collection.find(kwargs)]

    def insert(self, document: dict, overwrite : bool = False) -> Union[dict,bool]:
        """
        Insert a document into the collection.

        Inputs:
            document (dict): The document to insert.
            overwrite (bool): If True, overwrite the document if it already exists.

        Returns:
            dict: The document that was inserted.
            None: If the document could not be inserted.

        Note: the python-arango library docs are ambiguous about the return type, suggesting
        Union[dict,None] and Union[dict,bool] in different places.  The way we use it here,
        this should return dict or None
        """
        try:
            return self.collection.insert(document, overwrite=overwrite)
        except arango.exceptions.DocumentInsertError as e:
            ic(f'Insert failure for document into collection {self.name}')
            ic(document)
            print(json.dumps(document, indent=2))
            ic(e)
            return None


    @type_check
    def bulk_insert(self, documents: Sequence[Dict[str, Any]]) -> Union[None, list[Dict[str, Any]]]:
        '''Insert a list of documents into the collection in batches.'''
        errors = []
        for i in range(0, len(documents), self.max_chunk_size):
            batch = documents[i:i + self.max_chunk_size]
            try:
                result = self.collection.insert_many(batch)
                batch_errors = [doc for doc in result if doc.get('error')]
                errors.extend(batch_errors)
            except arango.exceptions.DocumentInsertError as e:
                ic(f'Bulk insert failure for documents into collection {self.name}')
                ic(batch)
                print(json.dumps(batch, indent=2))
                ic(e)
                raise e
        return errors if errors else None

    def add_schema(self, schema: dict) -> 'IndalekoCollection':
        """Add a schema to the collection."""
        self.collection.configure(schema=schema)
        return self

    def get_schema(self) -> dict:
        """Return the schema for the collection."""
        return self.collection.properties().get('schema', {})

    def delete(self, key: str) -> 'IndalekoCollection':
        """Delete the document with the given key."""
        return self.collection.delete(key)

def main():
    '''Test the IndalekoCollection class.'''
    print('IndalekoCollection: called.  No tests yet.')

if __name__ == '__main__':
    main()
