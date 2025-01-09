'''
IndalekoActivityRegistration is a class used to register activity data
providers for the Indaleko system.

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
import json
import os
import sys
import uuid

from typing import Any, Dict, Union

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from Indaleko import Indaleko
from IndalekoCollection import IndalekoCollection
from data_models.activity_data_registration \
    import IndalekoActivityDataRegistrationDataModel
# pylint: enable=wrong-import-position

class IndalekoActivityDataRegistration:
    '''
    This class defines the activity data provider registration for the Indaleko
    system.
    '''
    identifier = uuid.UUID('6c65350c-1dd5-4675-b17a-4dd409349a40')
    version = '1.0.0'
    description = 'Activity Data Provider Registration'
    name = 'Activity Data Provider Registration'
    provider_prefix = 'ActivityProviderData_'

    def __init__(self,
                registration_data : Union[Dict[str, Any], IndalekoActivityDataRegistrationDataModel]):
        '''Initialize an activity data provider registration.'''
        self.registration_data = registration_data
        ic(registration_data)
        if isinstance(registration_data, dict):
            ic(registration_data)
            self.registration_object = \
                IndalekoActivityDataRegistrationDataModel(**registration_data)
        elif isinstance(registration_data, IndalekoActivityDataRegistrationDataModel):
            self.registration_object = registration_data
        else:
            raise ValueError('Invalid registration data type')
        ic(self.registration_object.Identifier)
        self.activity_collection_name = \
            IndalekoActivityDataRegistration.generate_activity_data_provider_collection_name(
                str(self.registration_object.Identifier)
            )

    @staticmethod
    def generate_activity_data_provider_collection_name(identifier : str) -> str:
        '''Return the name of the collection for the activity provider.'''
        assert isinstance(identifier, str), \
            f'Identifier {identifier} must be a string is {type(identifier)}'
        assert Indaleko.validate_uuid_string(identifier), \
            f'Identifier {identifier} must be a valid UUID'
        prefix = IndalekoActivityDataRegistration.provider_prefix
        return f'{prefix}{identifier}'

    def get_activity_data_collection(self) -> IndalekoCollection:
        '''Return the collection for the activity provider.'''
        raise NotImplementedError('Not implemented yet')

    def get_activity_collection_uuid(self) -> str:
        '''Return the UUID for the activity collection.'''
        return self.registration_object.Identifier

    def get_activity_collection_name(self) -> str:
        '''Return the name of the activity collection.'''
        return self.activity_collection_name

    def model_dump(self) -> dict:
        '''Return the model dump for the object.'''
        return self.registration_object.model_dump()
    
    def model_dump_json(self) -> dict:
        '''Return a JSON compatible dictionary.'''
        data = self.registration_object.model_dump_json()
        assert isinstance(data, str)
        doc = json.loads(data)
        assert isinstance(doc, dict)
        return doc


def main():
    '''Test the activity data provider registration.'''
    IndalekoActivityDataRegistrationDataModel.test_model_main()


if __name__ == '__main__':
    main()
