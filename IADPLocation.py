'''Indaleko Activity Data Provider Location'''

import argparse
import datetime
from icecream import ic
import logging

from icecream import ic


from IndalekoActivityData import IndalekoActivityData
from IADPNetworkUtilities import IADPNetworkUtilities

class IADPLocation(IndalekoActivityData):
    '''This defines the class for location data.'''


    def __init__(self, **kwargs):
        '''Initialize the Indaleko Activity Data Provider Location object.'''
        self.network_utilities = IADPNetworkUtilities()
        self.ipv4 = self.network_utilities.get_ipv4_address()
        ic(kwargs)

    def get_current_geolocation(self):
        '''Return the current geolocation.'''
        return None



class IADPLocationTest:

def main():
    '''Test the IADPLocation class.'''
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
