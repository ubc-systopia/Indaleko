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
import argparse
import datetime
import logging

from Indaleko import Indaleko
from IndalekoRecord import IndalekoRecord
from IndalekoLogging import IndalekoLogging
from IndalekoDBConfig import IndalekoDBConfig
from IndalekoCollections import IndalekoCollection, IndalekoCollections
from IndalekoActivityDataProviderRegistrationSchema \
    import IndalekoActivityDataProviderRegistrationSchema
from IndalekoServices import IndalekoService
class IndalekoActivityDataProviderRegistration(IndalekoRecord):
    '''This class is used to manage Indaleko Activity Data Provider Registration.'''

    Schema = IndalekoActivityDataProviderRegistrationSchema.get_schema()
    ActivityDataProviderRegistration_UUID = '6c65350c-1dd5-4675-b17a-4dd409349a40'
    ActivityDataProviderRegistration_Version = '1.0'
    ActivityDataProviderRegistration_Description = 'Activity Data Provider Registration'

    def __init__(self, **kwargs):
        '''Create an instance of the IndalekoActivityRegistration class.'''
        assert isinstance(kwargs, dict), 'kwargs must be a dict'
        assert 'Identifier' in kwargs, 'Identifier must be in kwargs'
        self.identifier = self.get_identifier(
            kwargs['Identifier'],
            kwargs.get('Version', None),
            kwargs.get('Description', None)
        )
        db_config = kwargs.get('DBConfig', None)
        self.db_config = IndalekoDBConfig() if db_config is None else db_config
        self.collections = IndalekoCollections(db_config=self.db_config)
        self.activity_registration_service = IndalekoService(
            service_name = Indaleko.Indaleko_ActivityDataProviders,
            service_identifier = self.identifier,
            service_version = self.version,
            service_type='Activity Data Collector'
        )
        self.activity_registration_collection = kwargs.get('ActivityCollection', \
                                              self.get_activity_registration_collection())
        self.activity_registration = self.activity_registration_collection.find_entries(_key=self.identifier)
        if self.activity_registration is None:
            logging.debug('Creating new activity registration')
            self.activity_registration = \
                self.create_activity_registration(**kwargs)
        if 'raw_data' not in kwargs:
            kwargs['raw_data'] = b''
        if 'source' not in kwargs:
            kwargs['source'] = {
                'Identifier' : self.identifier,
                'Version' : self.version,
                'Description' : self.description,
            }
        super().__init__(**kwargs)


    def get_activity_registration_service(self) -> Indaleko:
        '''Return the activity registration service.'''

    def get_identifier(self, identifier : str, version : str = None, description : str = None) -> str:
        '''Return the identifier for the activity provider.'''
        assert isinstance(identifier, str), 'identifier must be a string'
        assert Indaleko.validate_uuid_string(identifier), 'identifier must be a valid UUID'
        self.identifier = identifier
        if version is not None:
            assert isinstance(version, str), 'version must be a string'
            self.version = version
        else:
            self.version = '1.0'
        if description is not None:
            assert isinstance(description, str), 'description must be a string'
            self.description = description
        else:
            self.description = f'Activity Provider {self.identifier} version {self.version}'
        return self.identifier

    def get_activity_registration_collection(self) -> IndalekoCollection:
        '''Return the activity registration collection.'''
        if not hasattr(self, 'activity_registration_collection'):
            self.activity_registration_collection = self.collections.get_collection(Indaleko.Indaleko_ActivityDataProviders)
        return self.activity_registration_collection

    def create_activity_registration(self, **kwargs) -> dict:
        '''Create the activity registration entry.'''
        assert isinstance(kwargs, dict), 'kwargs must be a dict'
        activity_registration = {
            'ActivityProvider' : {
                'Identifier' : self.identifier,
                'Version' : self.version,
                'Description' : self.description,
            },
            'ActivityCollection' : self.activity_registration_collection,
        }
        print(activity_registration)
        # Need to insert the activity registration into the collection
        # return activity_registration
        return {}


def check_command(args : argparse.Namespace) -> None:
    '''Check the database connection.'''
    logging.debug('check_command invoked')
    print('Checking Database connection')
    db_config = IndalekoDBConfig()
    if db_config is None:
        print('Could not create IndalekoDBConfig object')
        exit(1)
    started = db_config.start(timeout=args.timeout)
    if not started:
        print('Could not start IndalekoDBConfig object')
        exit(1)
    print('Database connection successful')

def create_collection(args : argparse.Namespace) -> None:
    '''Create the collection in the database if it doesn't exist.'''
    assert args is not None
    activity_registration = IndalekoActivityDataProviderRegistration(
        Identifier=args.uuid,
        Version=args.version,
        Description=args.description
    )
    print(activity_registration)
    return

def delete_collection(args : argparse.Namespace) -> None:
    '''Delete the collection from the database if it exists.'''
    assert args is not None
    return



def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp = now.isoformat()
    parser = argparse.ArgumentParser(description='Indaleko Activity Registration')
    parser.add_argument('--logdir' , type=str, default=Indaleko.default_log_dir, help='Log directory')
    parser.add_argument('--log', type=str, default=None, help='Log file name')
    parser.add_argument('--loglevel', type=int, default=logging.DEBUG, choices=IndalekoLogging.get_logging_levels(),
                        help='Log level')
    parser.add_argument('--timeout', type=int, default=10, help='Timeout for database connection in seconds')
    command_subparser = parser.add_subparsers(dest='command', help='Command')
    parser_check = command_subparser.add_parser('check', help='Check the database connection')
    parser_check.add_argument('--ipaddr', type=str, default=None, help='IP address for database')
    parser_check.set_defaults(func=check_command)
    parser_create = command_subparser.add_parser('create', help='Create a sample activity registration')
    parser_create.add_argument('--uuid', type=str, default='8cf76ad4-22e7-46bc-b162-e77a552438f9', help='UUID for the activity provider')
    parser_create.add_argument('--version', type=str, default='1.0', help='Version for the activity provider')
    parser_create.add_argument('--description', type=str, default='Test Activity Provider', help='Description for the activity provider')
    parser_create.set_defaults(func=create_collection)
    parser.set_defaults(func=check_command)
    args = parser.parse_args()
    args=parser.parse_args()
    if args.log is None:
        args.log=Indaleko.generate_file_name(
            suffix='log',
            service='IndalekoActivityRegistration',
            timestamp=timestamp
        )
    indaleko_logging = IndalekoLogging(
        service_name='IndalekoActivityRegistration',
        log_level=args.loglevel,
        log_file=args.log,
        log_dir=args.logdir
    )
    if indaleko_logging is None:
        print('Could not create logging object')
        exit(1)
    logging.info('Starting IndalekoActivityRegistration')
    logging.debug(args)
    args.func(args)
    logging.info('IndalekoActivityRegistration: done processing.')

if __name__ == '__main__':
    main()
