'''
This module defines the data model for location services.

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
from uuid import uuid4

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db import IndalekoDBConfig, IndalekoDBCollections
from data_models.named_entity import IndalekoNamedEntityDataModel
import asyncio
# pylint: enable=wrong-import-position


class IndalekoNamedEntity:
    '''
    This class handles the named entities for Indaleko.
    '''
    def __init__(self, db_config: IndalekoDBConfig = IndalekoDBConfig()):
        '''
        Initialize the named entity handler.
        '''
        self.named_entities = {}
        self.db_config = db_config
        self.collection = self.db_config.db.collection(
            IndalekoDBCollections.Indaleko_Named_Entity_Collection
        )
        assert self.collection is not None, 'Failed to get the named entity collection'
        self.named_entities = self.get_named_entities()

    def add_named_entity(
            self,
            named_entity: IndalekoNamedEntityDataModel
    ) -> bool:
        '''
        Add a named entity to the handler and database.

        Args:
            named_entity (NamedEntity): The named entity to add

        Returns:
            bool: True if the named entity was added successfully, False otherwise
        '''
        assert isinstance(named_entity, IndalekoNamedEntityDataModel), \
            f'named_entity must be a NamedEntity, not {type(named_entity)}'

        self.named_entities[named_entity.name] = named_entity

        # Serialize the named entity to JSON
        entity_json = named_entity.serialize()

        # Insert the named entity into the database
        self.collection.insert(entity_json)
        return True

    def get_named_entity(self, name: str) -> IndalekoNamedEntityDataModel:
        '''
        Get a named entity from the handler.

        Args:
            name (str): The name of the named entity to retrieve

        Returns:
            NamedEntity: The named entity
        '''
        # In future, we may want to cache individual entities and/or
        # negative lookups to speed things up as a performance
        # optimization.
        return self.named_entities.get(name, None)

    def get_named_entities(self, allow_cached: bool = False) -> dict[str, IndalekoNamedEntityDataModel]:
        '''
        Get all named entities from the handler.

        Returns:
            Dict[str, NamedEntity]: The named entities
        '''

        if allow_cached and self.named_entities:
            return self.named_entities

        ic('Fetching all named entities')

        cursor = self.collection.all()
        ic(dir(cursor))
        while True:
            if cursor.count():
                entity = cursor.next()
                ic(entity)
                self.named_entities[entity['name']] = IndalekoNamedEntityDataModel(**entity)
            if not cursor.has_more():
                break
        return self.named_entities

    def remove_named_entity(self, name: str) -> bool:
        '''
        Remove a named entity from the handler.

        Args:
            name (str): The name of the named entity to remove
        '''
        named_entity = self.named_entities.get(name, None)
        if not named_entity:
            return False

        # Remove the named entity from the collection
        result = self.collection.delete({'name': name})

        if result.acknowledged:
            # Remove the named entity from the handler
            self.named_entities.pop(name, None)

        return result.acknowledged

    def update_named_entity(self, name: str):
        '''
        Update a named entity in the handler.

        Args:
            name (str): The name of the named entity to update
        '''
        named_entity = self.named_entities.get(name, None)
        if named_entity:
            # Serialize the named entity to JSON
            entity_json = named_entity.serialize()

            # Update the named entity in the database
            result = self.collection.update(
                {'name': name},
                {'$set': entity_json}
            )

            if result.acknowledged:
                # update the named entity in the handler
                self.named_entities[name] = named_entity

            return result.acknowledged

        return False

    def clear_named_entities(self) -> bool:
        '''
        Clear all named entities from the handler.
        '''
        # Truncate the collection in the database
        result = self.collection.truncate()

        ic(result)

        # Clear the local cached copy of the named entities
        if result:
            self.named_entities.clear()


def main():
    '''
    Main function for the named entity module.
    '''
    named_entity = IndalekoNamedEntity()
    print(named_entity)
    named_entities = named_entity.get_named_entities()
    ic(named_entities)
    if len(named_entities) > 0:
        named_entity.clear_named_entities()
    named_entity_1 = IndalekoNamedEntityDataModel(
        name='Home',
        category='place',
        gis_location={
            'source': 'GPS',
            'timestamp': '2025-01-01T00:00:00Z',
            'latitude': -122.084,
            'longitude': 37.422,
        },
        device_id=uuid4()
    )
    assert named_entity.add_named_entity(named_entity_1)


if __name__ == '__main__':
    main()
