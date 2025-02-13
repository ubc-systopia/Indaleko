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

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db import IndalekoDBConfig
from data_models.named_entity import IndalekoNamedEntityDataModel
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

    def add_named_entity(self, named_entity: IndalekoNamedEntityDataModel):
        '''
        Add a named entity to the handler.

        Args:
            named_entity (NamedEntity): The named entity to add
        '''
        assert isinstance(named_entity, IndalekoNamedEntityDataModel), f'named_entity must be a NamedEntity, not {type(named_entity)}'
        self.named_entities[named_entity.name] = named_entity

    def get_named_entity(self, name: str) -> IndalekoNamedEntityDataModel:
        '''
        Get a named entity from the handler.

        Args:
            name (str): The name of the named entity to retrieve

        Returns:
            NamedEntity: The named entity
        '''
        return self.named_entities.get(name, None)

    def get_named_entities(self) -> dict[str, IndalekoNamedEntityDataModel]:
        '''
        Get all named entities from the handler.

        Returns:
            Dict[str, NamedEntity]: The named entities
        '''
        return self.named_entities

    def remove_named_entity(self, name: str):
        '''
        Remove a named entity from the handler.

        Args:
            name (str): The name of the named entity to remove
        '''
        self.named_entities.pop(name, None)

    def clear_named_entities(self):
        '''
        Clear all named entities from the handler.
        '''
        self.named_entities.clear()

    def __str__(self) -> str:
        '''
        Return a string representation of the named entities.

        Returns:
            str: The string representation
        '''
        return str(self.named_entities)

    def __get_named_entities_from_db(self) -> dict[str, IndalekoNamedEntityDataModel]:
        '''
        Get named entities from the database.

        Returns:
            Dict[str, NamedEntity]: The named entities
        '''
        return {}  # Placeholder

    def __save_named_entities_to_db(self, named_entities: dict[str, IndalekoNamedEntityDataModel]) -> bool:
        '''
        Save named entities to the database.
        '''
        return False  # Placeholder

    def __update_named_entity_in_db(self, named_entity: IndalekoNamedEntityDataModel) -> bool:
        '''
        Update a named entity in the database.
        '''
        return False  # Placeholder
