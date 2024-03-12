'''
IndalekoActivityRegistration is a class used to register activity data
providers for the Indaleko system.

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
import uuid

from Indaleko import Indaleko
from IndalekoDBConfig import IndalekoDBConfig
from IndalekoServices import IndalekoService, IndalekoServices
from IndalekoSingleton import IndalekoSingleton
from Indaleko import Indaleko
from IndalekoCollections import IndalekoCollections

class IndalekoActivityDataProviderRegistrationService(IndalekoSingleton):

    '''This class is used to implement and access
    the Indaleko Activity Data Provider Registration Service.'''

    UUID = '5ef4125d-4e46-4e35-bea5-f23a9fcb3f63'
    Version = '1.0'
    Description = 'Indaleko Activity Data Provider Registration Service'
    Name = 'IndalekoActivityDataProviderRegistrationService'

    activity_registration_service = IndalekoService.create_service_data(
        service_name = Name,
        service_description = Description,
        service_version = Version,
        service_type = IndalekoServices.service_type_activity_data_registrar,
        service_identifier = UUID
    )

    def __init__(self, **kwargs):
        '''Create an instance of the
        IndalekoActivityDataProviderRegistrationService class.'''
        if self._initialized:
            return
        if 'db_config' in kwargs:
            self.db_config = kwargs['db_config']
        else:
            self.db_config = IndalekoDBConfig()
        self.service = IndalekoService(
            service_name = Indaleko.Indaleko_ActivityDataProviders,
            service_description = self.Description,
            service_version = self.Version,
            service_type=IndalekoServices.service_type_activity_data_registrar,
            service_identifier = self.UUID
        )
        self.activity_providers = IndalekoCollections.get_collection(
            Indaleko.Indaleko_ActivityDataProviders
        )
        self._initialized = True

    def to_json(self) -> dict:
        '''Return the service as a JSON object.'''
        return self.service.to_json()

    def lookup_provider_by_identifier(self, identifier : str) -> dict:
        '''Return the provider with the given identifier.'''
        providers = self.activity_providers.find_entries(_key=identifier)
        print(providers)
        return {}

    def lookup_provider_by_name(self, name : str) -> dict:
        '''Return the provider with the given name.'''
        providers = self.activity_providers.find_entries(name=name)
        print(providers)
        return {}

    def get_provider_list(self) -> list:
        '''Return a list of providers.'''
        aql_query = f'''
            FOR provider IN {Indaleko.Indaleko_ActivityDataProviders}
            RETURN provider
        '''
        cursor = self.db_config.db.aql.execute(aql_query)
        return [document for document in cursor]


    def get_provider(self, **kwargs) -> dict:
        '''Return a provider.'''
        if 'identifier' in kwargs:
            provider = self.lookup_provider_by_identifier(kwargs['identifier'])
            print('found provider by identifier')
        elif 'name' in kwargs:
            provider = self.lookup_provider_by_name(kwargs['name'])
            print('found provider by name')
        else:
            raise ValueError('Must specify either identifier or name.')
        if provider is None:
            provider = self.register_provider(**kwargs)
            print('registered provider')
        return provider

    def register_provider(self, **kwargs) -> None:
        '''Register an activity data provider.'''
        activity_registration = {'ActivityProvider' : {}}
        assert 'Identifier' in kwargs, 'Identifier must be in kwargs'
        activity_registration['ActivityProvider']['Identifier'] = kwargs['Identifier']
        activity_registration['ActivityProvider']['Version'] = kwargs.get('Version', '1.0')
        if 'Description' in kwargs:
            activity_registration['ActivityProvider']['Description'] = kwargs['Description']
        if 'Name' in kwargs:
            activity_registration['ActivityProvider']['Name'] = kwargs['Name']
        activity_registration['ActivityCollection'] = kwargs.get('ActivityCollection', str(uuid.uuid4()))
        # TODO: need to create the the activity collection if it does not exist
        # self.activity_providers.insert() # now to create the activity provider registration

        return {}

def main():
    '''Test the IndalekoActivityRegistration class.'''
    service = IndalekoActivityDataProviderRegistrationService()
    print(service.to_json())
    print(service.get_provider_list())


if __name__ == '__main__':
    main()
