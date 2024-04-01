'''Indaleko Acivity Data Provider: Location'''

import argparse
import datetime
import logging

from IndalekoActivityDataProvider import IndalekoActivityDataProvider
from Indaleko import Indaleko
from IndalekoLogging import IndalekoLogging

class IADPLocation(IndalekoActivityDataProvider):
    '''Indaleko Acivity Data Provider for location information'''

    def __init__(self):
        super().__init__()

    def get_location(self):
        '''Get the location of the device.'''

def check_command(args: argparse.Namespace) -> None:
    '''Check the activity data provider setup'''
    logging.info('Checking the activity data provider setup')

def show_command(args: argparse.Namespace) -> None:
    '''Show the activity data provider setup'''
    logging.info('Showing the activity data provider setup')

def test_command(args: argparse.Namespace) -> None:
    '''Test the activity data provider'''
    logging.info('Testing the activity data provider')

def delete_command(args: argparse.Namespace) -> None:
    '''Delete the test activity data provider'''
    logging.info('Deleting the test activity data provider')

def create_command(args: argparse.Namespace) -> None:
    '''Create the test activity data provider'''
    logging.info('Creating the test activity data provider')



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
