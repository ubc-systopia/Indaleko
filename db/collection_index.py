'''
IndalekoCollectionIndex: This module is used to manage index creation for
IndalekoCollection objects.

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

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
# pylint: enable=wrong-import-position


class IndalekoCollectionIndex:
    '''Manages an index for an IndalekoCollection object.'''

    index_args = {
        'hash': {
            'fields': str,
            'name': str,
            'unique': bool,
            'sparse': bool,
            'deduplicate': bool,
            'in_background': bool
        },
        'skip_list': {
            'fields': str,
            'name': str,
            'unique': bool,
            'sparse': bool,
            'deduplicate': bool,
            'in_background': bool
        },
        'geo_index': {
            'fields': str,
            'name': str,
            'geo_json': bool,
            'in_background': bool,
            'legacyPolygons': bool
        },
        'fulltext': {
            'fields': str,
            'name': str,
            'min_length': int,
            'in_background': bool
        },
        'persistent': {
            'fields': str,
            'name': str,
            'unique': bool,
            'sparse': bool,
            'in_background': bool,
            'storedValues': list,
            'cacheEnabled': bool
        },
        'ttl': {
            'fields': str,
            'name': str,
            'expiry_time': int,
            'in_background': bool
        },
        'inverted': {
            'fields': str,
            'name': str,
            'inBackground': bool,
            'parallelism': int,
            'primarySort': list,
            'storedValues': list,
            'analyzer': str,
            'features': list,
            'includeAllFields': bool,
            'trackListPositions': bool,
            'searchField': str,
            'primaryKeyCache': bool,
            'cache': bool
        },
        'zkd': {
            'fields': str,
            'name': str,
            'field_value_types': list,
            'unique': bool,
            'in_background': bool
        },
        'mdi': {
            'fields': str,
            'name': str,
            'field_value_types': list,
            'unique': bool,
            'in_background': bool
        }
    }

    @staticmethod
    def create_index_from_args(
        collection: str,
        index_type: str,
        **kwargs: dict[str, str]
    ) -> 'IndalekoCollectionIndex':
        '''Create an index for the given collection.'''
        if index_type not in IndalekoCollectionIndex.index_args:
            raise ValueError('Invalid index type')
        assert index_type != 'primary', 'Primary index is not supported'
        args = {}
        for key in IndalekoCollectionIndex.index_args[index_type]:
            if key in kwargs:
                args[key] = kwargs[key]
        return IndalekoCollectionIndex(
            collection=collection,
            index_type=index_type,
            **args
        )

    def __init__(self,
                 collection,
                 **kwargs):
        """Parameters:
            This class is used to create indices for IndalekoCollection objects.

            collection: this points to the ArangoDB collection object to use for
                        this index.

            index_type: 'persistent' or 'hash'

            fields: list of fields to be indexed

            unique: if True, the index is unique
        """
        self.collection = collection
        ic(kwargs)
        assert kwargs.get('type') is not None, 'type is a required parameter'
        assert kwargs.get('fields') is not None, 'fields is a required parameter'
        self.index = self.collection.add_index(data=kwargs, formatter=False)
        ic(f'Created index for collection {self.collection}: {self.index}')


def main():
    '''Test the IndalekoCollectionIndex class.'''
    print('IndalekoCollectionIndex: called.  No tests yet.')


if __name__ == '__main__':
    main()
