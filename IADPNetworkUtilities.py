'''Indaleko Activity Data Provider Network Utilities'''

import argparse
import asyncio
import datetime
import json
import logging
import os
import platform
import random
import requests
import sys

if platform.system() == 'Windows':
    import winsdk.windows.devices.geolocation as wdg

from icecream import ic

from IndalekoSingleton import IndalekoSingleton
from IndalekoLogging import IndalekoLogging
from Indaleko import Indaleko

class IADPNetworkUtilities(IndalekoSingleton):
    '''This defines the class for network utilities.'''

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

    def __init__(self) -> None:
        '''Initialize the network utilities object.'''
        if self._initialized:
            return
        self.public_ipv4_address = self.retrieve_public_ipv4_address()
        self.public_ipv6_address = self.retrieve_public_ipv6_address()
        super().__init__()
        self._initialized = True

    @staticmethod
    def retrieve_public_ipv4_address(timeout=10) -> str:
        '''Get the public IPv4 address.'''
        try:
            response = requests.get('https://api.ipify.org?format=json', timeout=timeout)
            response.raise_for_status()
            return response.json()['ip']
        except requests.exceptions.RequestException as exception:
            ic(exception)
            return None

    @staticmethod
    def retrieve_public_ipv6_address(timeout=10) -> str:
        '''Get the public IPv6 address.'''
        try:
            response = requests.get('https://api64.ipify.org?format=json', timeout=timeout)
            response.raise_for_status()
            return response.json()['ip']
        except requests.exceptions.RequestException as exception:
            ic(exception)
            return None

    def get_ipv4_address(self) -> str:
        '''Return the public IPv4 address.'''
        return self.public_ipv4_address

    def get_ipv6_address(self) -> str:
        '''Return the public IPv6 address.'''
        return self.public_ipv6_address

    def get_public_ip_addresses(self) -> dict:
        '''Return the public IP addresses.'''
        return {
            'IPv4' : self.get_ipv4_address(),
            'IPv6' : self.get_ipv6_address(),
        }

    @staticmethod
    def get_network_geolocation(ip_address : str) -> dict:
        '''Get the network geolocation.'''
        try:
            response = requests.get(f'https://ipapi.co/{ip_address}/json/')
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exception:
            ic(exception)
            return None

    @staticmethod
    async def retrieve_windows_location() -> dict:
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
        return data

    @staticmethod
    def load_location_services(config_dir : str = './config', location_services = None) -> dict:
        '''Load the location services'''
        if location_services is None:
            location_services = IADPNetworkUtilities.location_services
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
                location_service_data[service] = [location_services[service][0],api_key]
                ic(location_service_data[service])
                assert len(location_service_data[service]) <= 2, \
                    ic(f'Too many entries {location_service_data[service]}')
        return ic(location_service_data)

    @staticmethod
    def retrieve_ip_location(ip_addr : str, location_services : dict = None) -> dict:
        '''Retrieve the location of the IP address.'''
        assert isinstance(ip_addr, str), f'Expected string, got {type(ip_addr)}'
        if location_services is None:
            location_services = IADPNetworkUtilities.load_location_services()
        count = 0
        retries = 3 * len(location_services)
        data = {}
        while count < retries:
            count += 1
            try:
                service = random.choice(list(location_services.keys()))
                ic(service)
                ic(location_services[service])
                data = location_services[service][0](ip_addr,
                                                     location_services[service][1],
                                                     timeout=2)
                ic(data)
                if data is not None:
                    break
            except (requests.exceptions.RequestException, KeyError) as exception:
                ic(f'Error: {exception}')
        return data

class IADPNetworkUtilitiesTest():
    '''Test the IADPNetworkUtilities class.'''

    @staticmethod
    def check_command(args : argparse.Namespace) -> None:
        '''Check the network utilities.'''
        ic(args)
        ic(IADPNetworkUtilities.retrieve_public_ipv4_address())
        ic(IADPNetworkUtilities.retrieve_public_ipv6_address())


    @staticmethod
    def test_command(args : argparse.Namespace) -> None:
        '''Test the network utilities.'''
        ic(args)
        network_utilities = IADPNetworkUtilities()
        if args.service == 'all' or args.service[:2] == 'ip':
            if args.service == 'ip' or args.service == 'ipv4':
                ic(network_utilities.get_ipv4_address())
            if args.service == 'ip' or args.service == 'ipv6':
                ic(network_utilities.get_ipv6_address())
        if args.service == 'all' or args.service == 'geo':
            if platform.system() == 'Windows':
                ic(asyncio.run(IADPNetworkUtilities.retrieve_windows_location()))
            ic(IADPNetworkUtilities.retrieve_ip_location(network_utilities.get_ipv4_address()))

def main():
    '''Test the IADPNetworkUtilities class.'''
    ic('Testing IADPNetworkUtilities')
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp = now.isoformat()

    ic('Testing Network Utilities')
    parser = argparse.ArgumentParser(description='Test the IADPNetworkUtilities class')
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
    parser_check.set_defaults(func=IADPNetworkUtilitiesTest.check_command)
    parser_test = command_subparsers.add_parser('test', help='Test the base functionality')
    parser_test.add_argument('--service',
                             type=str,
                             default='all',
                             choices=['all', 'ip', 'ipv4', 'ipv6', 'geo', ],
                             help='Service to test')
    parser_test.set_defaults(func=IADPNetworkUtilitiesTest.test_command)
    parser.set_defaults(func=IADPNetworkUtilitiesTest.test_command, service='all')
    args = parser.parse_args()
    args = parser.parse_args()
    if args.log is None:
        args.log = Indaleko.generate_file_name(
            suffix='log',
            service='IADPNetworkUtilities',
            timestamp=timestamp
        )
    indaleko_logging = IndalekoLogging(
        service_name='IADPNetworkUtilities',
        log_level=args.loglevel,
        log_file=args.log,
        log_dir=args.logdir
    )
    if indaleko_logging is None:
        ic('Could not create logging object')
        sys.exit(1)
    logging.info('Starting IADPNetworkUtilities: Network utilities.')
    logging.debug(args)
    args.func(args)
    logging.info('IADPNetworkUtilities: done processing.')

if __name__ == '__main__':
    main()
