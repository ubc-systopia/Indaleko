'''
IndalekoActivityDataProvider --- this module provides
the data for the mechanisms for the activity data provider class.

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
import argparse
import datetime
import logging
import json

from Indaleko import Indaleko
from IndalekoLogging import IndalekoLogging
from IndalekoActivityDataProviderRegistration import IndalekoActivityDataProviderRegistrationService, IndalekoActivityDataProviderRegistration

class IndalekoActivityDataProvider():
    '''This class is used to provide the data for the
    mechanisms for the activity data provider class.'''

    class ActivityTimestamp():

        def __init__(self, **kwargs):
            '''Create an instance of the ActivityTimestamp class.'''
            self.Label = kwargs.get('Label', None)
            self.Value = kwargs.get('Value', None)
            self.Description = kwargs.get('Description', None)


        def to_dict(self) -> dict:
            '''Return the object as a dictionary.'''
            return {
                'Label' : self.Label,
                'Value' : self.Value,
                'Description' : self.Description
            }

    def __init__(self, **kwargs):
        '''Create an instance of the IndalekoActivityDataProvider class.'''
        self.last_activity_data_identifier = None # this is the UUID of the last activity data.
        self.activity_provider_identifier = None # this is the UUID of THIS activity provider.
        self.activity_timestamps = [] # This is a list of timestamps with UUID-based semantic meanings associated with this object.
        self.activity_type = [] # This is the UUID identifying the type of activity.
        self.activity_data_version = None # This is the version of the activity data.
        self.entities = [] # This is a list of users associated with this object.
        self.active = True # This is a boolean indicating if the activity data provider is active.
        self.last_activity_data_generated = None # This is the last activity data generated.

    @staticmethod
    def create_activity_data(**kwargs):
        '''Create an activity data element.'''
        if 'ActivityDataIdentifier' in kwargs:
            Indaleko.validate_uuid_string(kwargs['ActivityDataIdentifier'])
        if 'ActivityProviderIdentifier' not in kwargs:
            raise ValueError('ActivityProviderIdentifier is required')
        if 'ActivityType' not in kwargs:
            raise ValueError('ActivityType is required')
        data = {
            'ActivityDataIdentifier' : kwargs.get('ActivityDataIdentifier', str(uuid.uuid4())),
            'ActivityProviderIdentifier' : kwargs['ActivityProviderIdentifier'],
            'ActivityType' : kwargs['ActivityType'],
            'Active' : kwargs.get('Active', True)
        }
        if 'DataVersion' in kwargs:
            data['DataVersion'] = kwargs['DataVersion']
        if 'Timestamps' in kwargs and len(kwargs['Timestamps']) > 0:
            data['Timestamps'] = kwargs['Timestamps']
        if 'Entities' in kwargs and len(kwargs['Entities']) > 0:
            data['Entities'] = kwargs['Entities']
        return data

    def generate_activity_data(self, **kwargs) -> dict:
        '''This method is used to generate an activity data element.'''
        new_data = IndalekoActivityDataProvider.create_activity_data(**kwargs)
        updated = True
        if len(self.last_activity_data_generated) == len(new_data):
            for key, value in new_data.items():
                if key == 'ActivityDataIdentifier':
                    continue # skip the UUID
                if value != self.last_activity_data_generated[key]:
                    updated = False
                    break
        if updated:
            if new_data['ActivityDataIdentifier'] == self.last_activity_data_identifier:
                self.last_activity_data_identifier = str(uuid.uuid4()) # need a new UUID
                new_data['ActivityDataIdentifier'] = self.last_activity_data_identifier
            self.last_activity_data_generated = new_data
        return self.last_activity_data_generated

    def to_dict(self) -> dict:
        '''Return activity provider information as a dictionary.'''
        return {
            'ActivityDataIdentifier' : self.last_activity_data_identifier,
            'ActivityProviderIdentifier' : self.activity_provider_identifier,
            'Timestamps' : [ts.to_dict() for ts in self.activity_timestamps],
            'ActivityType' : self.activity_type,
            'DataVersion' : self.activity_data_version,
            'Entities' : self.entities,
            'Active' : self.active
        }

class IndalekoActivityDataProviderTest(IndalekoActivityDataProvider):
    '''This class is used to test the IndalekoActivityDataProvider class.'''

    UUID_str = 'e6705d60-678e-4aae-ae75-e0d4f8f00469'
    Name = 'IndalekoActivityDataProviderTest'
    Version = '1.0'
    Description = 'Indaleko Activity Data Provider Test'

    def __init__(self, **kwargs):
        '''Create an instance of the IndalekoActivityDataProviderTest class.'''
        # Remove the following line
        # super().__init__(**kwargs)
        self.provider_registration = \
            IndalekoActivityDataProviderRegistrationService().\
                lookup_provider_by_identifier(self.UUID_str)
        if self.provider_registration is None or len(self.provider_registration) == 0:
            self.provider_registration = \
                IndalekoActivityDataProviderRegistrationService().\
                    register_provider(
                        Identifier = self.UUID_str,
                        Version = self.Version,
                        Description = self.Description,
                        Name = self.Name
                    )


    def generate_test_activity_data(self, **kwargs) -> dict:
        '''Generate a test activity data element.'''
        activity_data = IndalekoActivityDataProvider.create_activity_data(**kwargs)
        # Now add it to the relevant collection and return the identifier for
        # it.
        return activity_data['ActivityDataIdentifier']

def old_main():
    """Main function for the IndalekoActivityDataProvider class."""
    test_provider_uuid = '29872b82-af11-4b3a-bcb1-1ff2b6090d05'
    # backup_uuid = 'ddecdf14-ef7d-4537-abdb-da777dbe32fb'
    print("Welcome to Indaleko Activity Data Provider")
    registration = IndalekoActivityDataProviderRegistrationService()
    print(f'registration = {registration}')
    provider = registration.lookup_provider_by_identifier(test_provider_uuid)
    if len(provider) == 0:
        print(f'provider {test_provider_uuid} not found, creating')
        provider = registration.register_provider(
            Identifier = test_provider_uuid,
            Version = '1.0',
            Description = 'Test Activity Data Provider',
            Name = "Test Activity Data"
        )
    print(f'provider {provider}')
    print("Goodbye from Indaleko Activity Data Provider")

def show_command(args: argparse.Namespace) -> None:
    '''Show the command line arguments.'''
    print('Show Command')
    print(f'args = {args}')
    provider_list = IndalekoActivityDataProviderRegistrationService().get_provider_list()
    for provider in provider_list:
        registration = IndalekoActivityDataProviderRegistration.create_from_db_entry(provider)
        print (f'provider = {json.dumps(provider, indent=4)}')
        print (f'registration = {registration.to_json()}')
        registration_dict = registration.to_dict()
        assert provider['_key'] == registration_dict['Identifier'], \
            'provider and registration do not match'
        assert provider['Record'] == registration_dict['Record'], \
            'provider and registration do not match'
        assert provider['ActivityProvider'] == registration_dict['ActivityProvider'], \
            'provider and registration do not match'
        assert provider['ActivityCollection'] == registration_dict['ActivityCollection'], \
            'provider and registration do not match'

def check_command(args: argparse.Namespace) -> None:
    '''Check the activity data provider setup.'''
    print('Check Command')
    print(f'args = {args}')

def test_command(args: argparse.Namespace) -> None:
    '''Test the activity data provider.'''
    print('Test Command')
    print(f'args = {args}')

def delete_command(args: argparse.Namespace) -> None:
    '''Delete the test activity data provider.'''
    print('Delete Command')
    print(f'args = {args}')

def create_command(args: argparse.Namespace) -> None:
    '''Create the test activity data provider.'''
    print('Create Command')
    print(f'args = {args}')
    existing_provider = \
        IndalekoActivityDataProviderRegistrationService.\
            lookup_provider_by_identifier(IndalekoActivityDataProviderTest.UUID_str)
    if existing_provider is not None and len(existing_provider) > 0:
        print('Provider already exists')
        return
    print(f'Creating provider {IndalekoActivityDataProviderTest.UUID_str}')
    provider = IndalekoActivityDataProviderTest()
    print(f'provider = {provider}')

def main():
    '''Test the IndalekoActivityDataProvider class.'''
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp=now.isoformat()

    print('Starting Indaleko Activity Data Provider Test')
    parser = argparse.ArgumentParser(description='Indaleko Activity Data Provider Management.')
    parser.add_argument('--logdir' , type=str, default=Indaleko.default_log_dir, help='Log directory')
    parser.add_argument('--log', type=str, default=None, help='Log file name')
    parser.add_argument('--loglevel', type=int, default=logging.DEBUG, choices=IndalekoLogging.get_logging_levels(), help='Log level')
    command_subparser = parser.add_subparsers(dest='command')
    parser_check = command_subparser.add_parser('check', help='Check the activity data provider setup')
    parser_check.set_defaults(func=check_command)
    parser_show = command_subparser.add_parser('show', help='Show the activity data provider setup')
    parser_show.set_defaults(func=show_command)
    parser_test = command_subparser.add_parser('test', help='Test the activity data provider')
    parser_test.set_defaults(func=test_command)
    parser_delete = command_subparser.add_parser('delete', help='Delete the test activity data provider')
    parser_delete.set_defaults(func=delete_command)
    parser_create = command_subparser.add_parser('create', help='Create the test activity data provider')
    parser_create.set_defaults(func=create_command)
    parser.set_defaults(func=show_command)
    args = parser.parse_args()
    if args.log is None:
        args.log = Indaleko.generate_file_name(
            suffix='log',
            service='IndalekoActivityDataProvider',
            timestamp=timestamp
        )
    indaleko_logging = IndalekoLogging(
        service_name='IndalekoActivityDataProvider',
        log_level=args.loglevel,
        log_file=args.log,
        log_dir=args.logdir
    )
    if indaleko_logging is None:
        print('Could not create logging object')
        exit(1)
    logging.info('Starting IndalekoDBConfig')
    logging.debug(args)
    args.func(args)
    logging.info('IndalekoDBConfig: done processing.')



if __name__ == "__main__":
    main()
