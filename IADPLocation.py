'''Indaleko Activity Data Provider Location'''

import argparse
import datetime
from icecream import ic
import json
import logging
import math
import platform
import sys

from IndalekoActivityData import IndalekoActivityData
from IADPNetworkUtilities import IADPNetworkUtilities
from Indaleko import Indaleko
from IndalekoLogging import IndalekoLogging
from IADPLocationRegistration import IADPLocationRegistration
from IndalekoDBConfig import IndalekoDBConfig
from IADPLocationData import IADPLocationData
from IndalekoActivityDataProvider import IndalekoActivityDataProvider

class IADPLocation:
    '''This defines the class for location data.'''


    def __init__(self, debug : bool = False):
        '''Initialize the Indaleko Activity Data Provider Location object.'''
        self.network_utilities = IADPNetworkUtilities()
        self.ipv4 = self.network_utilities.get_ipv4_address()
        self.ipv6 = self.network_utilities.get_ipv6_address()
        self.service_registration = IADPLocationRegistration()
        self.debug = debug

    def get_current_geolocation(self) -> tuple:
        '''Return the current geolocation.'''
        return

    def load_location_from_database(self : 'IADPLocation') -> dict:
        '''Load the location data from the database.'''
        collection_name = self.service_registration.activity_provider_collection.name
        if self.debug:
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
            ic('No location data found')
        else:
            for doc in result:
                ic(doc)
                data = doc
                break
        return ic(data)

    def add_location_to_database(self : 'IADPLocation') -> bool:
        '''Add the location data to the database.'''
        data = self.capture_location()
        ic('add_location_to_database: ', data)
        if len(data) > 0:
            doc = self.service_registration.activity_provider_collection.insert(data)
            if self.debug:
                ic(doc)
            return True
        return False

    def capture_location(self : 'IADPLocation') -> dict:
        '''Capture the location data.'''
        data = {}
        if platform.system() == 'Windows':
            ic('Capturing Windows location')
            windows_location = self.network_utilities.capture_windows_location()
            if windows_location is not None:
                ic(windows_location)
                location_data = IADPLocationData(
                    location={
                        'longitude' : windows_location['longitude'],
                        'latitude' : windows_location['latitude'],
                    },
                    ActivityData=windows_location,
                    ActivityTimestamps=[IndalekoActivityData.create_collection_timestamp()],
                    raw_data=bytes(json.dumps(windows_location), encoding='utf-8')
                )
                data = location_data.to_dict()
        # Default to using IP geolocation.
        if len(data) == 0:
            ip_location = None
            if self.ipv6 is not None:
                ip_location = self.network_utilities.retrieve_ip_location(self.ipv6)
            if ip_location is None:
                ip_location = self.network_utilities.retrieve_ip_location(self.ipv4)
            if ip_location is not None:
                data = ip_location
        # capture network state as well
        if len(data) > 0:
            data['Network'] = {}
            if self.ipv4 is not None:
                data['Network']['IPv4'] = self.ipv4
            if self.ipv6 is not None:
                data['Network']['IPv6'] = self.ipv6
        return data

    @staticmethod
    def compute_distance(location1 : tuple, location2 : tuple) -> float:
        '''
        Compute the distance (in meters) between two locations
        specified by longitude and latitude.
        '''
        radius_of_the_earth = 6371000.0 # meters
        ic(f'compute_distance({location1}, {location2})')
        assert isinstance(location1, tuple) and len(location1) == 2, \
            f'location1 must be a tuple (latitude, longitude) is type {type(location1)}'
        assert isinstance(location2, tuple) and len(location2) == 2, \
            f'location2 must be a tuple (latitude, longitude) is type {type(location2)}'
        lat1 = math.radians(location1[0])
        lon1 = math.radians(location1[1])
        lat2 = math.radians(location2[0])
        lon2 = math.radians(location2[1])
        diff_latitude = lat2 - lat1
        diff_longitude = lon2 - lon1
        a = math.sin(diff_latitude / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(diff_longitude / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return ic(radius_of_the_earth * c)



class IADPLocationTest:
    '''Test the IADPLocation class.'''

    def __init__(self, args: argparse.Namespace, debug : bool = False):
        '''Initialize the IADPLocationTest object.'''
        ic('Initializing IADPLocationTest')
        self.args = args
        self.debug = debug
        if self.debug:
            ic(args)

    def check_command(self) -> None:
        '''Check the base functionality.'''
        if self.debug:
            ic('Checking IADPLocation')
        location = IADPLocation(self.debug)
        if self.debug:
            ic(location)

    def test_command(self) -> None:
        '''Test the base functionality.'''
        if self.debug:
            ic('Testing IADPLocation')
        location = IADPLocation(self.debug)
        if self.debug:
            ic(location.load_location_from_database())
            # ic(location.get_current_geolocation())
            ic(location.capture_location())

    def add_command(self) -> None:
        '''Add the current location to the database'''
        if self.debug:
            ic('Adding location to database')
        location = IADPLocation(self.debug)
        ic(location.add_location_to_database())



def main():
    '''Test the IADPLocation class.'''
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp = now.isoformat()
    parser = argparse.ArgumentParser(description='Test the IADPNetworkUtilities class')
    parser.add_argument('--debug', '-d',
                        action='store_true',
                        help='Debug flag')
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
    command_subparsers = parser.add_subparsers(help='Command subparsers', dest='command')
    parser_check = command_subparsers.add_parser('check', help='Check the base functionality')
    parser_check.set_defaults(func=IADPLocationTest.check_command)
    parser_test = command_subparsers.add_parser('test', help='Test the base functionality')
    parser_test.add_argument('--service',
                             type=str,
                             default='all',
                             choices=['all', 'ip', 'ipv4', 'ipv6', 'geo', ],
                             help='Service to test')
    parser_test.set_defaults(func=IADPLocationTest.test_command)
    parser_add = command_subparsers.add_parser('add', help='Add the current location to the database')
    parser_add.set_defaults(func=IADPLocationTest.add_command)
    parser.set_defaults(func=IADPLocationTest.test_command)
    args = parser.parse_args()
    if args.debug:
        ic('Testing IADPLocation')
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
        sys.exit(1)
    logging.info('Starting IADPLocation: Network utilities.')
    logging.debug(args)
    test = IADPLocationTest(args, args.debug)
    args.func(test)
    logging.info('IADPLocation: done processing.')

if __name__ == '__main__':
    main()
