'''
IndalekoActivityRegistrationService is the class that implements the
registration service for activity data providers.

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
import json
import os
import sys
import uuid

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from Indaleko import Indaleko
from IndalekoDBConfig import IndalekoDBConfig
from IndalekoSingleton import IndalekoSingleton
from IndalekoService import IndalekoService
from IndalekoServiceManager import IndalekoServiceManager
from IndalekoCollection import IndalekoCollection
from IndalekoCollections import IndalekoCollections
from IndalekoRecordDataModel import IndalekoRecordDataModel
from provider_registration import IndalekoActivityDataProviderRegistration
from data_models.activity_data_provider_registration \
    import IndalekoActivityDataProviderRegistrationDataModel
# pylint: enable=wrong-import-position

class IndalekoActivityDataProviderRegistrationService(IndalekoSingleton):
    '''
    This class is used to implement and access the Indaleko Activity Data
    Provider Registration Service.
    '''
    service_uuid_str = '5ef4125d-4e46-4e35-bea5-f23a9fcb3f63'
    Version = '1.0'
    Description = 'Indaleko Activity Data Provider Registration Service'
    Name = 'IndalekoActivityDataProviderRegistrationService'

    def __init__(self):
        '''
        Create an instance of the registration service.
        '''
        if self._initialized:
            return
        self.service = IndalekoServiceManager().register_service(
            service_name = Indaleko.Indaleko_ActivityDataProviders,
            service_description = self.Description,
            service_version = self.Version,
            service_type = IndalekoServiceManager.service_type_activity_data_registrar,
            service_id = self.service_uuid_str,
        )
        self.activity_providers = IndalekoCollections().get_collection(
            Indaleko.Indaleko_ActivityDataProviders
        )
        assert self.activity_providers is not None, 'Activity provider collection must exist'
        self._initialized = True

    @staticmethod
    def deserialize(data : dict) -> 'IndalekoActivityDataProviderRegistrationService':
        '''
        Deserialize the registration service from a dictionary.
        '''
        return IndalekoActivityDataProviderRegistrationService(**data)

    def serialize(self) -> dict:
        '''
        Serialize the registration service to a dictionary.
        '''
        serialized_data = IndalekoService.serialize(self.service)
        if isinstance(serialized_data, tuple):
            assert len(serialized_data) == 1, 'Serialized data is a multi-entry tuple.'
            serialized_data = serialized_data[0]
        if isinstance(serialized_data, dict):
            serialized_data['_key'] = self.service_uuid_str
        return serialized_data

    def to_json(self) -> dict:
        return json.dumps(self.serialize(), indent=4)

    @staticmethod
    def lookup_provider_by_name(name : str) -> dict:
        '''Return the provider with the given name.'''
        providers = IndalekoActivityDataProviderRegistrationService().\
            activity_providers.find_entries(name=name)
        return providers

    @staticmethod
    def get_provider_list() -> list:
        '''Return a list of providers.'''
        aql_query = f'''
            FOR provider IN {Indaleko.Indaleko_ActivityDataProviders}
            RETURN provider
        '''
        cursor = IndalekoDBConfig().db.aql.execute(aql_query)
        return [document for document in cursor]


    def get_provider(self, **kwargs) -> dict:
        '''Return a provider.'''
        if 'identifier' in kwargs:
            provider = self.lookup_provider_by_identifier(kwargs['identifier'])
        elif 'name' in kwargs:
            provider = self.lookup_provider_by_name(kwargs['name'])
        else:
            raise ValueError('Must specify either identifier or name.')
        if provider is None:
            provider = self.register_provider(**kwargs)
        return provider

    @staticmethod
    def create_activity_provider_collection(identifier : str, reset : bool = False) -> IndalekoCollection:
        '''Create an activity provider collection.'''
        assert Indaleko.validate_uuid_string(identifier), 'Identifier must be a valid UUID'
        activity_provider_collection_name = \
            IndalekoActivityDataProviderRegistration.\
                generate_activity_data_provider_collection_name(identifier)
        existing_collection = None
        try:
            existing_collection = IndalekoCollections.get_collection(activity_provider_collection_name)
        except ValueError:
            pass # this is the "doesn't exist" path
        if existing_collection is not None:
            return existing_collection
        activity_data_collection = IndalekoCollections\
            .get_collection(Indaleko.Indaleko_ActivityDataProviders)\
            .create_collection(
                name = activity_provider_collection_name,
                config = {
                    'schema' : IndalekoActivityDataSchema().get_json_schema(),
                    'edge' : False,
                    'indices' : {
                    },
                },
                reset = reset
            )
        return activity_data_collection

    @staticmethod
    def delete_activity_provider_collection(identifier : str, delete_data_collection : bool = True) -> bool:
        '''Delete an activity provider collection.'''
        if identifier.startswith(
            IndalekoActivityDataProviderRegistration.ActivityProviderDataCollectionPrefix):
            identifier = identifier[len(IndalekoActivityDataProviderRegistration.\
                               ActivityProviderDataCollectionPrefix):]
        assert Indaleko.validate_uuid_string(identifier), 'Identifier must be a valid UUID'
        activity_provider_collection_name = \
            IndalekoActivityDataProviderRegistration.\
                generate_activity_data_provider_collection_name(identifier)
        existing_collection = None
        try:
            existing_collection = IndalekoCollections.\
                get_collection(activity_provider_collection_name)
            if existing_collection is not None:
                logging.info('Collection %s exists, deleting', activity_provider_collection_name)
                existing_collection.delete_collection(activity_provider_collection_name)
            else:
                logging.info('Collection %s does not exist', activity_provider_collection_name)
                return False
        except ValueError:
            pass
        return True

    def delete_provider(self, identifier : str) -> bool:
        '''Delete an activity data provider.'''
        existing_provider = self.lookup_provider_by_identifier(identifier)
        if existing_provider is None:
            return False
        logging.info('Deleting provider %s', identifier)
        self.activity_providers.delete(identifier)
        return False

    def register_provider(self, **kwargs) -> tuple:
        '''Register an activity data provider.'''
        assert 'Identifier' in kwargs, 'Identifier must be in kwargs'
        # print('Registering provider: ', kwargs)
        existing_provider = self.lookup_provider_by_identifier(kwargs['Identifier'])
        if existing_provider is not None and len(existing_provider) > 0:
            raise NotImplementedError('Provider already exists, not updating.')
        activity_registration = IndalekoActivityDataProviderRegistration(**kwargs)
        self.activity_providers.insert(activity_registration.to_dict())
        activity_provider_collection = None
        create_collection = kwargs.get('CreateCollection', True)
        if create_collection:
            activity_provider_collection = self.create_activity_provider_collection(
                activity_registration.get_activity_collection_uuid()
            )
        existing_provider = self.lookup_provider_by_identifier(kwargs['Identifier'])
        assert existing_provider is not None, 'Provider creation failed'
        print(f"Registered Provider {kwargs['Identifier']}")
        return activity_registration, activity_provider_collection

    def deactivate_provider(self, identifier : str) -> bool:
        '''Deactivate an activity data provider.'''
        existing_provider = self.lookup_provider_by_identifier(identifier)
        if existing_provider is None:
            return False
        print('TODO: mark as inactive')
        return False

def main():
    '''Test the IndalekoActivityDataProviderRegistrationService.'''
    service = IndalekoActivityDataProviderRegistrationService()

    print(service.to_json())
    print(service.get_provider_list())

if __name__ == '__main__':
    main()

