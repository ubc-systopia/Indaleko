'''
This module is used to manage specific collection objects in Indaleko.

Project Indaleko
Copyright (C) 2024 Tony Mason

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

from IndalekoDBConfig import IndalekoDBConfig
from IndalekoCollectionIndex import IndalekoCollectionIndex

class IndalekoCollection():
    """
    An IndalekoCollection object is used to manage a collection of documents in the
    Indaleko database.
    """

    def __init__(self, **kwargs):
        if 'ExistingCollection' in kwargs:
            self.collection = kwargs['ExistingCollection']
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

    def create_collection(self,
                          name : str,
                          config : dict,
                          reset : bool = False) -> 'IndalekoCollection':
        """
        Create a collection in the database. If the collection already exists,
        return the existing collection. If reset is True, delete the existing
        collection and create a new one.
        """
        if self.db_config.db.has_collection(name) and not reset:
            self.collection = self.db_config.db.collection(name)
        else:
            self.collection = self.db_config.db.create_collection(name, edge=config['edge'])
            if 'schema' in config:
                self.collection.configure(schema=config['schema'])
            if 'indices' in config:
                for index in config['indices']:
                    self.create_index(index,
                                      config['indices'][index]['type'],
                                      config['indices'][index]['fields'],
                                      config['indices'][index]['unique'])
        return self.collection

    def delete_collection(self, name: str) -> bool:
        '''Delete the collection with the given name.'''
        if not self.db_config.db.has_collection(name):
            print(f'Collection {name} does not exist **')
            return False
        self.db_config.db.delete_collection(name)
        print(f'Collection {name} does exists, requesting deletion **')
        return True

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

    def insert(self, document: dict, overwrite : bool = False) -> 'IndalekoCollection':
        """Insert a document into the collection."""
        return self.collection.insert(document, overwrite=overwrite)

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
