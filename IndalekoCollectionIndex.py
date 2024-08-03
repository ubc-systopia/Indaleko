'''IndalekoCollectionIndex ---
This module is used to manage index creation for IndalekoCollection objects.

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
from icecream import ic

from IndalekoSingleton import IndalekoSingleton

class IndalekoCollectionIndex:
    '''Manages an index for an IndalekoCollection object.'''

    index_args = {
        'hash' : {
            'fields' : str,
            'name' : str,
            'unique' : bool,
            'sparse' : bool,
            'deduplicate' : bool,
            'in_background' : bool
        },
        'skip_list' : {
            'fields' : str,
            'name' : str,
            'unique' : bool,
            'sparse' : bool,
            'deduplicate' : bool,
            'in_background' : bool
        },
        'geo_index' : {
            'fields' : str,
            'name' : str,
            'geo_json' : bool,
            'in_background' : bool,
            'legacyPolygons' : bool
    },
        'fulltext' : {
            'fields' : str,
            'name' : str,
            'min_length' : int,
            'in_background' : bool
        },
        'persistent' : {
            'fields' : str,
            'name' : str,
            'unique' : bool,
            'sparse' : bool,
            'in_background' : bool,
            'storedValues' : list,
            'cacheEnabled' : bool
        },
        'ttl' : {
            'fields' : str,
            'name' : str,
            'expiry_time' : int,
            'in_background' : bool
        },
        'inverted' : {
            'fields' : str,
            'name' : str,
            'inBackground' : bool,
            'parallelism' : int,
            'primarySort' : list,
            'storedValues' : list,
            'analyzer' : str,
            'features' : list,
            'includeAllFields' : bool,
            'trackListPositions' : bool,
            'searchField' : str,
            'primaryKeyCache' : bool,
            'cache' : bool
        },
        'zkd' : {
            'fields' : str,
            'name' : str,
            'field_value_types' : list,
            'unique' : bool,
            'in_background' : bool
        },
        'mdi' : {
            'fields' : str,
            'name' : str,
            'field_value_types' : list,
            'unique' : bool,
            'in_background' : bool
        }
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
        ic(f'Created index {self.index}')

def main():
    '''Test the IndalekoCollectionIndex class.'''
    print('IndalekoCollectionIndex: called.  No tests yet.')

if __name__ == '__main__':
    main()
