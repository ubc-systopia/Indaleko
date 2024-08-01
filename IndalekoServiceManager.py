"""
The purpose of this package is to create a common class structure for managing
Indaleko Services.

We have multiple sources of information that can be indexed by Indaleko.  Thus,
this provides a "registration mechanism" that allows a service to create a
registration endpoint and get back an object that it can use for interacting
with its service information.

The types of services envisioned here are:

* Indexers - these are component that gather data from storage locations.
* Ingesters - these are components that convert raw indexed information into a
  common format that is used when storing the actual data.

I expect there will be other kinds of services in the future, but that's the
list for now.

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
import uuid
import datetime

from icecream import ic
from IndalekoDBConfig import IndalekoDBConfig
from IndalekoCollections import IndalekoCollection
from Indaleko import Indaleko
from IndalekoSingleton import IndalekoSingleton
from IndalekoServiceSchema import IndalekoServiceSchema
from IndalekoService import IndalekoService
from IndalekoRecordDataModel import IndalekoRecordDataModel
from IndalekoDataModel import IndalekoDataModel

class IndalekoServiceManager(IndalekoSingleton):
    '''
    This class defines the service model for Indaleko.
    '''

    Schema = IndalekoServiceSchema().get_json_schema()

    service_manager_uuid_str = 'c3e03488-660c-42f5-8277-1c8073fb2144'
    service_manager_version = '1.1'

    indaleko_services = 'Services'
    assert indaleko_services in Indaleko.Collections, \
        f'{indaleko_services} must be in Indaleko_Collections'

    service_type_test = 'Test'
    service_type_machine_configuration = "Machine Configuration"
    service_type_indexer = 'Indexer'
    service_type_ingester = 'Ingester'
    service_type_semantic_transducer = 'Semantic Transducer'
    service_type_activity_context_generator = 'Activity Context Generator'
    service_type_activity_data_collector = 'Activity Data Collector'
    service_type_activity_data_registrar = 'Activity Data Registrar'

    service_types = (
        service_type_test,
        service_type_machine_configuration,
        service_type_indexer,
        service_type_ingester,
        service_type_semantic_transducer,
        service_type_activity_context_generator,
        service_type_activity_data_collector,
        service_type_activity_data_registrar
    )

    CollectionDefinition = {
        'schema' : Schema,
        'edge' : False,
        'indices' : {
            'name' : {
                'fields' : ['name'],
                'unique' : True,
                'type' : 'persistent'
            },
        },
    }

    def __init__(self, reset: bool = False) -> None:
        self.db_config = IndalekoDBConfig()
        self.db_config.start()
        self.service_collection = IndalekoCollection(
            name=self.indaleko_services,
            definition=self.CollectionDefinition,
            db=self.db_config,
            reset=reset)


    def create_indaleko_services_collection(self) -> IndalekoCollection:
        """
        This method creates the IndalekoServices collection in the database.
        """
        assert not self.db_config.db.has_collection(self.indaleko_services), \
         f'{self.indaleko_services} collection already exists, cannot create it.'
        self.service_collection = IndalekoCollection(
            name=self.indaleko_services,
            definition=self.CollectionDefinition,
            db=self.db_config.db
        )
        self.service_collection.add_schema(IndalekoServiceManager.Schema)
        self.service_collection.create_index('name', 'persistent', ['name'], unique=True)
        return self.service_collection

    def lookup_service_by_name(self, name: str) -> dict:
        """
        This method is used to lookup a service by name.
        """
        ic(name)
        entries = self.service_collection.find_entries(Name =  name)
        ic(entries)
        assert len(entries) < 2, f'Multiple entries found for service {name}, not handled.'
        if len(entries) == 0:
            return None
        else:
            ic(entries[0])
            return IndalekoService.deserialize(entries[0])

    def lookup_service_by_identifier(self, service_identifier: str) -> dict:
        """
        This method is used to lookup a service by name.
        """
        if not Indaleko.validate_uuid_string(service_identifier):
            raise ValueError(f'{service_identifier} is not a valid UUID.')
        entries = self.service_collection.find_entries(identifier =  service_identifier)
        assert len(entries) < 2, \
            f'Multiple entries found for service {service_identifier}, not handled.'
        if len(entries) == 0:
            return None
        else:
            return IndalekoService.deserialize(entries[0])


    def register_service(self,
                         name: str,
                         description: str,
                         version: str,
                         service_type : str = 'Indexer',
                         service_id : str  = None) -> IndalekoService:
        """
        This method registers a service with the given name, description, and
        version in the database.
        """
        assert service_type in IndalekoServiceManager.service_types, \
            f'Invalid service type {service_type} specified.'
        if service_id is None:
            service_id = str(uuid.uuid4())
        new_service = IndalekoService(
            record = IndalekoRecordDataModel.IndalekoRecord(
                SourceIdentifier = IndalekoDataModel.SourceIdentifier(
                    Identifier = IndalekoServiceManager.service_manager_uuid_str,
                    Version = IndalekoServiceManager.service_manager_version,
                    Description = 'Indaleko Service Manager'
                ),
                Timestamp = datetime.datetime.now(datetime.UTC),
                Attributes = {},
                Data = Indaleko.encode_binary_data(b'{}')
            ),
            service_name=name,
            service_description=description,
            service_version=version,
            service_type=service_type,
            service_identifier=service_id
        )
        ic(new_service.serialize())
        self.service_collection.insert(new_service.serialize())
        # return self.lookup_service_by_name(name)
        return new_service

def old_main():
    """Test the IndalekoServices class."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--identifier', type=str, default='4debd7e6-c71a-4830-a0a1-8b4e599faea6', help='The identifier of the service to look up.')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('--reset', action='store_true', help='Reset the service collection.')
    args = parser.parse_args()
    service = IndalekoService(service_name='test',
                              service_identifier=args.identifier,
                              service_description='This is a test service.',
                              service_version='1.0',
                              service_type='Test')
    print('Dump record after the lookup by name test:')
    print(service.to_json())
    service = IndalekoService(service_identifier='4debd7e6-c71a-4830-a0a1-8b4e599faea6')
    print('Dump record after the lookup by identifier test:')
    print(service.to_json())

def main():
    '''Test code for IndalekoServiceManager.'''
    service_manager = IndalekoServiceManager()
    print('service manager created successfully')
    existing_service = service_manager.lookup_service_by_name('Test Service')
    if existing_service is not None:
        print('Found existing service:')
        print(existing_service.to_json())
    else:
        print('No existing service found.')
        new_service = service_manager.register_service(
            name='Test Service',
            description='This is a test service.',
            version='1.0.0',
            service_type='Test'
        )


if __name__ == "__main__":
    main()
