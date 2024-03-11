"""
IndalecoCollections.py - This module is used to manage the collections in the
Indaleko database.


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
"""

import argparse
import logging
import datetime
import os
from Indaleko import Indaleko
from IndalekoDBConfig import IndalekoDBConfig
class IndalekoCollectionIndex:
    '''Manages an index for an IndalekoCollection object.'''

    index_args = {
        'hash' : [
            'fields',
            'name',
            'unique',
            'sparse',
            'deduplicate',
            'in_background'
            ],
        'skip_list' : [
            'fields',
            'name',
            'unique',
            'sparse',
            'deduplicate',
            'in_background'
            ],
        'geo_index' : [
            'fields',
            'name',
            'geo_json',
            'in_background',
            'legacyPolygons'
            ],
        'fulltext' : [
            'fields',
            'name',
            'fields',
            'name',
            'min_length',
            'in_background'
            ],
        'persistent' : [
            'fields',
            'name',
            'unique',
            'sparse',
            'in_background',
            'storedValues',
            'cacheEnabled'
            ],
        'ttl' : [
            'fields',
            'name',
            'expiry_time',
            'in_background'
            ],
        'inverted' : [
            'fields',
            'name',
            'inBackground',
            'parallelism',
            'primarySort',
            'storedValues',
            'analyzer',
            'features',
            'includeAllFields',
            'trackListPositions',
            'searchField',
            'primaryKeyCache',
            'cache'],
        'zkd' : [
            'fields',
            'name',
            'field_value_types',
            'unique',
            'in_background'
            ],
        'mdi' : [
            'fields',
            'name',
            'field_value_types',
            'unique',
            'in_background'
            ]
    }


    def __init__(self,
                 **kwargs):
        """Parameters:
            This class is used to create indices for IndalekoCollection objects.

            collection: this points to the ArangoDB collection object to use for
                        this index.

            index_type: 'persistent' or 'hash'

            fields: list of fields to be indexed

            unique: if True, the index is unique
        """
        if 'collection' not in kwargs:
            raise ValueError('collection is a required parameter')
        self.collection = kwargs['collection']
        if 'fields' not in kwargs:
            raise ValueError('fields is a required parameter')
        if not isinstance(kwargs['fields'], list):
            raise ValueError('fields must be a list')
        self.fields = kwargs['fields']
        self.unique = None
        if 'unique' in kwargs:
            self.unique = kwargs['unique']
        if 'index_type' not in kwargs:
            raise ValueError('index_type is a required parameter')
        self.index_type = kwargs['index_type']
        self.sparse = None
        if 'sparse' in kwargs:
            self.sparse = kwargs['sparse']
        self.expiry_time = None
        if 'expiry_time' in kwargs:
            self.expiry_time = kwargs['expiry_time']
        self.name = None
        if 'name' in kwargs:
            self.name = kwargs['name']
        self.deduplicate = None
        if 'deduplicate' in kwargs:
            self.deduplicate = kwargs['deduplicate']
        if 'in_background' in kwargs:
            self.in_background = kwargs['in_background']
        # There are two parameters that are common to all index types:
        # fields (the fields being indexed) and name (the name of the index).
        args = {'fields' : self.fields}
        if self.name is not None:
            args['name'] = self.name
        if self.index_type == 'hash':
            if self.unique is not None:
                args['unique'] = self.unique
            if self.sparse is not None:
                args['sparse'] = self.sparse
            if self.deduplicate is not None:
                args['deduplicate'] = self.deduplicate
            if self.in_background is not None:
                args['in_background'] = self.in_background
            self.index = self.collection.add_hash_index(**args) # pylint: disable=unexpected-keyword-arg
        elif self.index_type == 'persistent':
            self.index = self.collection.add_persistent_index(fields=self.fields,
                                                              unique=self.unique)
        elif self.index_type == 'geo':
            self.index = self.collection.add_geo_index(fields=self.fields, unique=self.unique)
        elif self.index_type == 'fulltext':
            self.index = self.collection.add_fulltext_index(fields=self.fields,
                                                            unique=self.unique)
        elif self.index_type == 'skiplist':
            self.index = self.collection.add_skiplist_index(fields=self.fields,
                                                            unique=self.unique)
        elif self.index_type == 'ttl':
            self.index = self.collection.add_ttl_index(fields=self.fields,
                                                       unique=self.unique)
        else:
            raise ValueError('Invalid index type')


    def find_entries(self, **kwargs):
        """
        Given a list of keyword arguments, return a list of documents that
        match the criteria.
        """
        return [document for document in self.collection.find(kwargs)]


class IndalekoCollection:
    """
    An IndalekoCollection object is used to manage a collection of documents in the
    Indaleko database.
    """

    def __init__(self,
                 name : str,
                 definition : dict,
                 db : IndalekoDBConfig = None,
                 reset : bool = False) -> None:
        self.name = name
        self.definition = definition
        assert isinstance(definition, dict), 'Collection definition must be a dictionary'
        assert 'schema' in definition, 'Collection must have a schema'
        assert 'edge' in definition, 'Collection must have an edge flag'
        assert 'indices' in definition, 'Collection must have indices'
        assert db is None or isinstance(db, IndalekoDBConfig), \
            'db must be None or an IndalekoDBConfig object'
        if db is None:
            self.db_config = IndalekoDBConfig()
            self.db_config.start()
        else:
            self.db_config = db
        assert db is not None, 'db must be a valid IndalekoDBConfig object'
        self.collection_name = self.name
        self.indices = {}
        self.create_collection(self.collection_name, definition, reset=reset)

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

    def delete(self, key: str) -> 'IndalekoCollection':
        """Delete the document with the given key."""
        return self.collection.delete(key)


class IndalekoCollections:
    """
    This class is used to manage the collections in the Indaleko database.
    """
    def __init__(self, db_config: IndalekoDBConfig = None, reset: bool = False) -> None:
        if db_config is None:
            self.db_config = IndalekoDBConfig()
        else:
            self.db_config = db_config
        logging.debug('Starting database')
        self.db_config.start()
        self.collections = {}
        for name in Indaleko.Collections.items():
            name = name[0]
            logging.debug('Processing collection %s', name)
            self.collections[name] = IndalekoCollection(name,
                                                        Indaleko.Collections[name],
                                                        self.db_config, reset)

    def get_collection(self, name: str) -> IndalekoCollection:
        """Return the collection with the given name."""
        assert name in self.collections, f'Collection {name} does not exist.'
        return self.collections[name]


def main():
    """Test the IndalekoCollections class."""
    start_time = datetime.datetime.now(datetime.UTC).isoformat()
    parser = argparse.ArgumentParser()
    logfile = f'indalekocollections-test-{start_time.replace(":","-")}.log'
    parser = argparse.ArgumentParser(
        description='Set up and create the collections for the Indaleko database.')
    parser.add_argument('--reset',
                        '-r',
                        help='Reset the database', action='store_true')
    parser.add_argument('--config',
                        '-c',
                        help='Path to the config file', default='./config/indaleko-db-config.ini')
    parser.add_argument('--log',
                        '-l',
                        help='Log file to use', default=logfile)
    parser.add_argument('--logdir',
                        help='Log directory to use',
                        default='./logs')
    args = parser.parse_args()
    logging.basicConfig(filename=os.path.join(args.logdir, args.log),
                        level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info('Begin Indaleko Collections test at %s', start_time)
    collections = IndalekoCollections()
    end_time = datetime.datetime.now(datetime.UTC).isoformat()
    logging.info('End Indaleko Collections test at %s', end_time)
    assert collections is not None, 'Collections object should not be None'

if __name__ == "__main__":
    main()
