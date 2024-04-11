'''Indaleko Acivity Data Provider: Location'''

import argparse
import base64
import datetime
from icecream import ic
from itertools import cycle
import json
import logging
import math
import msgpack
import os
import platform
import requests

if platform.system() == 'Windows':
    import asyncio
    import winsdk.windows.devices.geolocation as wdg

from IndalekoActivityDataProvider import IndalekoActivityDataProvider
from Indaleko import Indaleko
from IndalekoLogging import IndalekoLogging
from IndalekoDBConfig import IndalekoDBConfig
from IndalekoActivityDataProviderRegistration import IndalekoActivityDataProviderRegistrationService
from IADPLocationData import IADPLocationData
from IndalekoRecord import IndalekoRecord
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
    indaleko_location_distance_change_required_in_meters = 1000
    location_services = {
        'ipstack' : [lambda ip, api_key, timeout=2:
                     requests.get(f'http://api.ipstack.com/{ip}?access_key={api_key}',
                                  timeout=timeout).json()],
        'abstract' : [lambda ip, api_key, timeout=2:
                           requests.get(f'https://ipgeolocation.abstractapi.com/v1/?api_key={api_key}&ip_address={ip}',
                                        timeout=timeout).json()],
        'ipapi' : [lambda ip, api_key, timeout=2:
                    requests.get(f'http://ip-api.com/json/{ip}',
                                 timeout=timeout).json()],
    }
    indaleko_location_activity_type = ['Location']

    def __init__(self, **kwargs):
        '''
        Create an instance of the IADPLocation class.
        Note: you can provide a capture_location function to override the
        default.  This is useful for systems where there is hardware GPS or
        specialized libraries.
        '''
        assert 'raw_data' not in kwargs, 'raw_data is a reserved parameter'
        # allows overriding the capture_location function
        self.location_capture = kwargs.get('capture_location', IADPLocation.capture_location)
        self.source = kwargs.get('source',
                                 IADPLocation.indaleko_activity_provider_location_source)
        assert IndalekoRecord.validate_source(self.source), \
            f'source is not valid: {self.source}'
        registration_data = IndalekoActivityDataProviderRegistrationService()\
            .lookup_provider_by_identifier(self.source['Identifier'])
        if registration_data is None or len(registration_data) == 0:
            logging.info('Start Registration for location service %s', \
                         self.source['Identifier'])
            registration_data = IndalekoActivityDataProviderRegistrationService()\
                .register_provider(
                    Identifier=self.source['Identifier'],
                    Version=self.source['Version'],
                    Description = self.source.get('Description', None),
                    Name = self.source.get('Name', None),
                    CreateCollection=True,
            )
        if len(registration_data) == 0:
            raise ValueError('Provider registration failed')
        elif len(registration_data) == 2:
            self.provider_registration = registration_data[0]
            self.activity_data_collection = registration_data[1]
        else:
            ic('Invalid data returned')
            ic(len(registration_data))
            assert False
        self.cache_time = kwargs.get('cache_time', IADPLocation.indaleko_location_cache_time)
        self.distance_change_required = kwargs.get(
            'distance_change_required', \
            IADPLocation.indaleko_location_distance_change_required_in_meters)
        self.public_ip_address = IADPLocation.capture_public_ip_address()
        self.last_ip_address_update = None
        self.last_location_update = None
        self.location_services = IADPLocation.load_location_services()
        self.location = self.get_location()
        if 'activity type' not in kwargs:
            kwargs['activity type'] = IADPLocation.indaleko_location_activity_type
        super().__init__(**kwargs)

    def get_activity_collection_name(self) -> str:
        '''Get the activity collection name'''
        return self.activity_data_collection.collection_name

    @staticmethod
    def load_location_services(config_dir : str = './config', location_services : dict = None):
        '''Load the location services'''
        if location_services is None:
            location_services = IADPLocation.location_services
        ic(location_services)
        assert os.path.exists(config_dir), f'Config directory {config_dir} does not exist'
        location_services_file = os.path.join(config_dir, 'location_services.json')
        if not os.path.exists(location_services_file):
            raise FileNotFoundError(f'Location services file {location_services_file} not found')
        location_service_data = {}
        data = {}
        with open(location_services_file, 'r', encoding='utf-8') as fd:
            data = json.load(fd)
        ic(data)
        for service, api_key in data.items():
            ic(service)
            ic(api_key)
            if service in location_services:
                ic(location_services[service])
                location_service_data[service] = [location_services[service],api_key]
                ic(location_service_data[service])
                assert len(location_service_data[service]) <= 2, \
                    ic(f'Too many entries {location_service_data[service]}')
        return ic(location_service_data)


    @staticmethod
    def is_provider_registered() -> bool:
        '''Check if the provider is registered'''
        provider_registration = IndalekoActivityDataProviderRegistrationService()\
            .lookup_provider_by_identifier(
                IADPLocation.indaleko_activity_provider_location_source_uuid)
        return provider_registration is not None and len(provider_registration) > 0

    @staticmethod
    def remove_provider_registration() -> None:
        '''Remove the provider registration'''
        existing_provider = \
            IndalekoActivityDataProviderRegistrationService()\
            .lookup_provider_by_identifier(
                IADPLocation.indaleko_activity_provider_location_source_uuid)
        if existing_provider is None or len(existing_provider) == 0:
            logging.info('Provider %s not found',
                         IADPLocation.indaleko_activity_provider_location_source_uuid)
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
        public_ip = IADPLocation.capture_public_ip_address()
        if public_ip is not None:
            logging.info('Updated public IP address to %s', public_ip)
            self.public_ip_address = public_ip
            self.last_ip_address_update = datetime.datetime.now()
        return self.public_ip_address

    def get_location(self) -> dict:
        '''Get the location of the device.'''
        if self.last_location_update is not None and \
           self.location is not None and \
            datetime.datetime.now() - self.last_location_update < \
            datetime.timedelta(seconds=self.indaleko_location_cache_time):
            return self.location
        data = IADPLocation.capture_location()
        raw_data = base64.b64encode(msgpack.packb(bytes(json.dumps(data).encode('utf-8'))))
        self.location_data = IADPLocationData(
            location=data,
            raw_data=raw_data,
            attributes=data,
            source=self.source,
        )
        self.last_location_update = datetime.datetime.now()
        self.location = self.location_data
        self.update_location()
        return self.location

    @staticmethod
    def compute_distance(location1 : tuple, location2 : tuple) -> float:
        '''
        Compute the distance (in meters) between two locations
        specified by longitude and latitude.
        '''
        radius_of_the_earth = 6371000.0 # meters
        ic(f'compute_distance({location1}, {location2})')
        assert isinstance(location1, tuple) and len(location1) == 2, \
            'location1 must be a tuple (latitude, longitude)'
        assert isinstance(location2, tuple) and len(location2) == 2, \
            'location2 must be a tuple (latitude, longitude)'
        lat1 = math.radians(location1[0])
        lon1 = math.radians(location1[1])
        lat2 = math.radians(location2[0])
        lon2 = math.radians(location2[1])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return ic(radius_of_the_earth * c)

    def update_location(self) -> bool:
        '''
        See if the device location has changed; if it has, update it.
        Note: this updates, regardless of prior capture time, though
        it does set the timestamp.
        '''
        current_location = IADPLocation.capture_location()
        current = (current_location['latitude'], current_location['longitude'])
        previous = (self.location['latitude'], self.location['longitude'])
        if IADPLocation.compute_distance(current, previous) <= \
            self.distance_change_required:
            self.location = IADPLocationData(
                raw_data=base64.b64encode(
                    msgpack.packb(
                        bytes(json.dumps(current_location).encode('utf-8'))
                    )
                ),
                attributes=current_location,
                source=self.source,
            )
            self.last_location_update = datetime.datetime.now()
            return ic(True)
        return ic(False)

    def update_location_database(self) -> bool:
        '''Update the location in the database'''
        raise NotImplementedError('update_location_database not implemented')

    @staticmethod
    def load_location_from_database() -> dict:
        '''Load the location from the database'''
        provider = IADPLocation()
        collection_name = provider.get_activity_collection_name()
        ic(f'Collection Name: {collection_name}')
        query = f'''
            FOR doc in `{collection_name}`
            SORT doc.Timestamp.Value DESC
            LIMIT 1
            RETURN doc
        '''
        result = IndalekoDBConfig().db.aql.execute(query)
        data = {}
        if result.empty():
            ic('No data found')
        else:
            for doc in result:
                ic(doc)
                data = doc
                break
        return data

    def save_location_to_database(self) -> bool:
        '''Save the location to the database'''
        assert self.activity_data_collection is not None, 'Activity data collection is required'
        assert self.location is not None, 'Location is required'
        ic(self.location.to_dict())
        return True

    @staticmethod
    def capture_public_ip_address(timeout : int = 10) -> str:
        '''Capture the public IP address of the device'''
        url = 'https://api.ipify.org?format=json'
        response = requests.get(url, timeout=timeout)
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
        if len(data) == 0:
            for field in IADPLocation.get_loc_from_ip(ip_addr):
                if field not in data:
                    data[field] = IADPLocation.get_loc_from_ip(ip_addr)[field]
        return ic(data)

    @staticmethod
    def capture_windows_location(ip_addr : str = None) -> dict:
        '''Capture the location of the device on Windows'''
        if platform.system() != 'Windows':
            raise NotImplementedError('capture_windows_location not implemented for non-Windows')
        return asyncio.run(IADPLocation.retrieve_windows_location(ip_addr))

    @staticmethod
    def get_loc_from_ip(ip_addr : str, location_services : dict = None) -> dict:
        '''Get the location from the IP address'''
        assert ip_addr is not None, 'IP address is required'
        if location_services is None:
            location_services = IADPLocation.load_location_services()
        iterator = cycle(location_services)
        retries = 3 * len(location_services)
        count = 0
        data = {}
        while True:
            if count > retries: break
            try:
                count += 1
                service = next(iterator)
                data = location_services[service][0](ip_addr,
                                                     location_services[service][1], timeout=2)
                if 'latitude' not in data and 'lat' in data:
                    data['latitude'] = data['lat']
                if 'longitude' not in data and 'lon' in data:
                    data['longitude'] = data['lon']
                assert 'latitude' in data, 'Latitude not found'
                assert 'longitude' in data, 'Longitude not found'
                break
            except (requests.exceptions.RequestException, KeyError) as e:
                ic(f'Error occurred: {e}')
        return ic(data)


    @staticmethod
    def capture_location(ip_addr : str = None) -> dict:
        '''Capture the current location of the device'''
        if ip_addr is None:
            ip_addr = IADPLocation.capture_public_ip_address()
        if platform.system() == 'Windows':
            return IADPLocation.capture_windows_location(ip_addr)
        location = IADPLocation.get_loc_from_ip(ip_addr)
        if 'latitude' not in location:
            location['latitude'] = location['lat']
        if 'longitude' not in location:
            location['longitude'] = location['lon']
        ic('Location:', location)
        return location

def check_command(args: argparse.Namespace) -> None:
    '''Check the activity data provider setup'''
    logging.info('Checking the activity data provider setup')

def show_command(args: argparse.Namespace) -> None:
    '''Show the activity data provider setup'''
    logging.info('Showing the activity data provider setup')
    IndalekoDBConfig().start()
    ic(IADPLocation.load_location_from_database())

def test_command(args: argparse.Namespace) -> None:
    '''Test the activity data provider'''
    logging.info('Start: Testing the activity data provider')
    db_location = IADPLocation.load_location_from_database()
    if len(db_location) == 0:
        ic('No location data found')
        current_location = IADPLocation()
        ic(current_location.get_location().to_dict())
        current_location.save_location_to_database()
    return
    timestamp = datetime.datetime.now(datetime.timezone.utc)
    location = IADPLocationData(
        source=IADPLocation.indaleko_activity_provider_location_source,
        ActivityData=captured_location,
        Timestamps = [
            {   'Label' : IndalekoActivityDataProvider.start_time_uuid_str,
                'Value' : timestamp.isoformat(),
                'Description' : 'Start Time',
            },
            {
                'Label' : IndalekoActivityDataProvider.collection_time_uuid_str,
                'Value' : timestamp.isoformat(),
                'Description' : 'Collection Time',
            },
            {
                'Label' : IndalekoActivityDataProvider.end_time_uuid_str,
                'Value' : timestamp.isoformat(),
                'Description' : 'End Time',
            }
        ]
    )
    ic(location.to_dict())
    logging.debug(json.dumps(location.to_dict()))
    logging.info('End: Testing the activity data provider')

def delete_command(args: argparse.Namespace) -> None:
    '''Delete the test activity data provider'''
    logging.info('Deleting the test activity data provider')
    if not IADPLocation.is_provider_registered():
        ic('Location provider does not exist.')
        return
    IADPLocation.remove_provider_registration()
    ic('Location provider was deleted.')


def create_command(args: argparse.Namespace) -> None:
    '''Create the test activity data provider'''
    logging.info('Creating the test activity data provider')
    if IADPLocation.is_provider_registered():
        ic('Location provider already exists.')
        return
    location_provider = IADPLocation()
    assert location_provider.is_provider_registered(), \
        'Location provider registration failed.'
    ic('Location provider was created.')

def main() -> None:
    '''Main function'''
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp = now.isoformat()

    ic('Starting Indaleko Activity Data Provider for Location')
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
        ic('Could not create logging object')
        exit(1)
    logging.info('Starting IADPLocation: Location activity data provider.')
    logging.debug(args)
    args.func(args)
    logging.info('IADPLocation: done processing.')



if __name__ == '__main__':
    main()
