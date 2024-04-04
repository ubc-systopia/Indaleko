'''Indaleko Acivity Data Provider: Location'''

import argparse
import datetime
import json
import logging
import os
import platform
import requests
import uuid

if platform.system() == 'Windows':
    import asyncio
    import winsdk.windows.devices.geolocation as wdg

from IndalekoActivityDataProvider import IndalekoActivityDataProvider
from Indaleko import Indaleko
from IndalekoLogging import IndalekoLogging
from IndalekoRecord import IndalekoRecord
from IndalekoDBConfig import IndalekoDBConfig
from IndalekoActivityDataProviderRegistration import IndalekoActivityDataProviderRegistrationService


class IADPLocation(IndalekoActivityDataProvider):
    '''Indaleko Acivity Data Provider for location information'''

    indaleko_activity_provider_location_name = 'IADPLocation'
    indaleko_activity_provider_location_source_uuid = '04c82f31-07d8-409c-9dd3-cbc661b7756d'
    indaleko_activity_provider_location_source = {
        'Identifier' : indaleko_activity_provider_location_source_uuid,
        'Version' : '1.0',
        'Description' : 'Indaleko Activity Data Provider for Location',
        'Name' : indaleko_activity_provider_location_name,
    }
    indaleko_location_cache_time = 60 * 60 # 1 hour in seconds

    class IndalekoLocationData(IndalekoRecord):
        '''
        This defines the format of the Indaleko Location Data.
        Note: at the present time it is just returning latitude and longitude,
        even though we are gathering more metadata than that.  We can look at
        using more in the future.
        '''

        def __init__(self, **kwargs):
            args = {key : value for key, value in kwargs.items()}
            assert '_key' not in args, '_key is a reserved parameter'
            assert 'Data' not in args, 'Data is a reserved parameter'
            self.raw_data = args.get('raw_data', b'')
            self.provider = args.get('provider',
                                     IADPLocation.indaleko_activity_provider_location_source_uuid)
            self.attributes = None
            self._key = str(uuid.uuid4())
            if 'Attributes' in args:
                self.attributes = args['Attributes']
                del args['Attributes']
            self.args = args
            if self.attributes is None:
                self.attributes = {
                    'latitude' : self.args.get('latitude', None),
                    'longitude' : self.args.get('longitude', None),
                }
            super().__init__(
                raw_data=self.raw_data,
                provider=self.provider,
                source=IADPLocation.indaleko_activity_provider_location_source,
                attributes=self.attributes,
            )
            if os.path.exists('config/ipstack-com-api-key.json'):
                with open('config/ipstack-com-api-key.json', 'r') as file:
                    data = json.load(file)
                    self.api_key = data['api_key']
            else:
                self.api_key = None
                logging.error('config/ipstack-com-api-key.json not found, no IP to location service available.')

        def get_latitude(self):
            '''Get the latitude of the device'''
            return self.attributes['latitude']

        def get_longitude(self):
            '''Get the longitude of the device'''
            return self.attributes['longitude']

        def to_dict(self):
            location_data = {}
            location_data['Record'] = super().to_dict()
            location_data['_key'] = str(uuid.uuid4())


    def __init__(self, **kwargs):
        '''
        Create an instance of the IADPLocation class.
        Note: you can provide a capture_location function to override the
        default.  This is useful for systems where there is hardware GPS or
        specialized libraries.
        '''
        self.location_capture = kwargs.get('capture_location', IADPLocation.capture_location)
        self.source = kwargs.get('source',
                                 IADPLocation.indaleko_activity_provider_location_source)
        assert IndalekoRecord.validate_source(self.source), \
            f'source is not valid: {self.source}'
        self.provider_registration = \
            IndalekoActivityDataProviderRegistrationService()\
            .lookup_provider_by_identifier(self.source['Identifier'])
        if self.provider_registration is None or len(self.provider_registration) == 0:
            logging.info('Start Registration for location service %s', \
                         self.source['Identifier'])
            self.provider_registration = IndalekoActivityDataProviderRegistrationService()\
                .register_provider(
                    Identifier=self.source['Identifier'],
                    Version=self.source['Version'],
                    Description = self.source.get('Description', None),
                    Name = self.source.get('Name', None)
            )
        self.public_ip_address = None
        self.last_ip_address_update = None
        self.location = self.IndalekoLocationData()
        super().__init__()

    @staticmethod
    def is_provider_registered() -> bool:
        '''Check if the provider is registered'''
        provider_registration = IndalekoActivityDataProviderRegistrationService()\
            .lookup_provider_by_identifier(IADPLocation.indaleko_activity_provider_location_source_uuid)
        return provider_registration is not None and len(provider_registration) > 0

    @staticmethod
    def remove_provider_registration() -> None:
        '''Remove the provider registration'''
        existing_provider = IndalekoActivityDataProviderRegistrationService()\
            .lookup_provider_by_identifier(IADPLocation.indaleko_activity_provider_location_source_uuid)
        if existing_provider is None or len(existing_provider) == 0:
            logging.info('Provider %s not found', IADPLocation.indaleko_activity_provider_location_source_uuid)
            return
        assert len(existing_provider) == 1, 'Multiple providers found'
        existing_provider = existing_provider[0]
        logging.info('Removing provider %s', existing_provider.to_json())
        IndalekoActivityDataProviderRegistrationService()\
            .delete_activity_provider_collection(existing_provider.get_activity_collection_name())
        IndalekoActivityDataProviderRegistrationService()\
            .delete_provider(IADPLocation.indaleko_activity_provider_location_source_uuid)

    def lookup_ip_location_in_db(self, ipaddr):
        '''Lookup the IP address in the database'''
        raise NotImplementedError('lookup_ip_location_in_db not implemented')

    def get_public_ip_address(self):
        '''Get the public IP address of the device'''
        if self.public_ip_address is not None:
            if self.last_ip_address_update is not None:
                now = datetime.datetime.now()
                if now - self.last_ip_address_update < \
                    datetime.timedelta(seconds=self.indaleko_location_cache_time):
                    return self.public_ip_address
        # otherwise we need to update the IP address
        public_ip = IADPLocation.IndalekoLocationData.capture_public_ip_address()
        if public_ip is not None:
            logging.info('Updated public IP address to %s', public_ip)
            self.public_ip_address = public_ip
            self.last_ip_address_update = datetime.datetime.now()
        return self.public_ip_address

    def get_last_location(self):
        '''Get the last location of the device'''
        raise NotImplementedError('get_last_location not implemented')

    def get_location(self):
        '''Get the location of the device.'''
        raise NotImplementedError('get_location not implemented')

    @staticmethod
    def capture_public_ip_address(timeout : int = 10) -> str:
        '''Capture the public IP address of the device'''
        url = 'https://api.ipify.org?format=json'
        response = requests.get(url, timeout=10)
        data = response.json()
        public_ip = data.get('ip', None)
        return public_ip

    @staticmethod
    async def retrieve_windows_location(ip_addr : str = None) -> dict:
        '''Capture the location of the device on Windows'''
        locator = wdg.Geolocator()
        pos = await locator.get_geoposition_async()
        data = {}
        skipped = {}
        for field in dir(pos.coordinate):
            if field.startswith('_'):
                continue
            value = getattr(pos.coordinate, field)
            if isinstance(value, (int, float, str, bool)) or value is None:
                data[field] = getattr(pos.coordinate, field)
            elif isinstance(value, datetime.datetime):
                data[field] = value.isoformat()
            else:
                skipped[field] = getattr(pos.coordinate, field)
        if ip_addr is not None:
            for field in IADPLocation.get_loc_from_ip(ip_addr):
                if field not in data:
                    data[field] = IADPLocation.get_loc_from_ip(ip_addr)[field]
        return data

    @staticmethod
    def capture_windows_location(ip_addr : str = None) -> dict:
        '''Capture the location of the device on Windows'''
        if platform.system() != 'Windows':
            raise NotImplementedError('capture_windows_location not implemented for non-Windows')
        return asyncio.run(IADPLocation.retrieve_windows_location(ip_addr))

    @staticmethod
    def get_loc_from_ip(ip_addr : str) -> dict:
        '''Get the location from the IP address'''
        assert ip_addr is not None, 'IP address is required'
        url = f'http://ip-api.com/json/{ip_addr}'
        response = requests.get(url, timeout=10)
        data = response.json()
        if data['status'] == 'success':
            return data
        return {}

    @staticmethod
    def capture_location(ip_addr : str = None) -> dict:
        '''Capture the current location of the device'''
        if ip_addr is None:
            ip_addr = IADPLocation.capture_public_ip_address()
        if platform.system() == 'Windows':
            return IADPLocation.capture_windows_location(ip_addr)
        return IADPLocation.get_loc_from_ip(ip_addr)

def check_command(args: argparse.Namespace) -> None:
    '''Check the activity data provider setup'''
    logging.info('Checking the activity data provider setup')

def show_command(args: argparse.Namespace) -> None:
    '''Show the activity data provider setup'''
    logging.info('Showing the activity data provider setup')

def test_command(args: argparse.Namespace) -> None:
    '''Test the activity data provider'''
    logging.info('Testing the activity data provider')
    print('Testing the activity data provider')
    #location_provider = IADPLocation()
    #print(location_provider.get_last_location())
    print(IADPLocation.capture_location())

def delete_command(args: argparse.Namespace) -> None:
    '''Delete the test activity data provider'''
    logging.info('Deleting the test activity data provider')
    if not IADPLocation.is_provider_registered():
        print('Location provider does not exist.')
        return
    IADPLocation.remove_provider_registration()
    print('Location provider was deleted.')


def create_command(args: argparse.Namespace) -> None:
    '''Create the test activity data provider'''
    logging.info('Creating the test activity data provider')
    if IADPLocation.is_provider_registered():
        print('Location provider already exists.')
        return
    location_provider = IADPLocation()
    assert location_provider.is_provider_registered(), \
        'Location provider registration failed.'
    print('Location provider was created.')

def main() -> None:
    '''Main function'''
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp = now.isoformat()

    print('Starting Indaleko Activity Data Provider for Location')
    parser = argparse.ArgumentParser()
    parser.add_argument('--logdir' ,
                        type=str,
                        default=Indaleko.default_log_dir,
                        help='Log directory')
    parser.add_argument('--log',
                        type=str,
                        default=None,
                        help='Log file name')
    parser.add_argument('--loglevel',
                        type=int,
                        default=logging.DEBUG,
                        choices=IndalekoLogging.get_logging_levels(),
                        help='Log level')
    command_subparser = parser.add_subparsers(dest='command')
    parser_check = command_subparser.add_parser('check',
                                                help='Check the activity data provider setup')
    parser_check.set_defaults(func=check_command)
    parser_show = command_subparser.add_parser('show', help='Show the activity data provider setup')
    parser_show.add_argument('--inactive', action='store_true', help='Show inactive providers')
    parser_show.set_defaults(func=show_command)
    parser_test = command_subparser.add_parser('test', help='Test the activity data provider')
    parser_test.set_defaults(func=test_command)
    parser_create = command_subparser.add_parser('create',
                                                 help='Create the test activity data provider')
    parser_create.set_defaults(func=create_command)
    parser_delete = command_subparser.add_parser('delete',
                                                 help='Delete the test activity data provider')
    parser_delete.set_defaults(func=delete_command)
    parser.set_defaults(func=show_command)
    args = parser.parse_args()
    if args.log is None:
        args.log = Indaleko.generate_file_name(
            suffix='log',
            service='IADPLocation',
            timestamp=timestamp
        )
    indaleko_logging = IndalekoLogging(
        service_name='IADPLocation',
        log_level=args.loglevel,
        log_file=args.log,
        log_dir=args.logdir
    )
    if indaleko_logging is None:
        print('Could not create logging object')
        exit(1)
    logging.info('Starting IADPLocation: Location activity data provider.')
    logging.debug(args)
    args.func(args)
    logging.info('IADPLocation: done processing.')



if __name__ == '__main__':
    main()
