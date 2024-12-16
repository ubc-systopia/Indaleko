"""Generic log management for Indaleko"""

import logging
import os
import datetime
import argparse
import platform
import sys

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# This logic is part of what allows me to execute it locally or as part of the
# overall package/project.  It's a bit of a hack, but it works.
# pylint: disable=wrong-import-position
from utils import IndalekoSingleton
from utils.misc.directory_management import indaleko_default_log_dir
import utils.misc.file_name_management
# pylint: enable=wrong-import-position


class IndalekoLogging(IndalekoSingleton):
    """Class for managing Indaleko logging."""

    def __init__(self, **kwargs):
        """Initialize a new instance of the IndalekoLogging class object."""
        if self._initialized:
            return
        self.log_level = kwargs.get('log_level', logging.DEBUG)
        self.log_dir = kwargs.get('log_dir', indaleko_default_log_dir)
        self.log_file = kwargs.get('log_file', IndalekoLogging.generate_log_file_name(**kwargs))
        log_name = os.path.join(self.log_dir, self.log_file)
        logging.basicConfig(filename=log_name,
                            level=self.log_level,
                            format='%(asctime)s %(levelname)s %(message)s')
        logging.info('IndalekoLogging initialized, logging level set to %s', self.log_level)
        self._initialized = True


    def __del__(self):
        """Delete an instance of the IndalekoLogging class object."""
        logging.info('IndalekoLogging terminated.')

    def get_log_file_name(self) -> str:
        """Return the log file name."""
        return self.log_file

    @staticmethod
    def get_logging_levels() -> list:
        """Return a list of valid logging levels."""
        if platform.python_version() < '3.12':
            logging_levels = []
            if hasattr(logging, 'CRITICAL'):
                logging_levels.append('CRITICAL')
            if hasattr(logging, 'ERROR'):
                logging_levels.append('ERROR')
            if hasattr(logging, 'WARNING'):
                logging_levels.append('WARNING')
            if hasattr(logging, 'WARN'):
                logging_levels.append('WARN')
            if hasattr(logging, 'INFO'):
                logging_levels.append('INFO')
            if hasattr(logging, 'DEBUG'):
                logging_levels.append('DEBUG')
            if hasattr(logging, 'NOTSET'):
                logging_levels.append('NOTSET')
            if hasattr(logging, 'FATAL'):
                logging_levels.append('FATAL')
        else:
            logging_levels = sorted(set(logging.getLevelNamesMapping()))
        return logging_levels

    @staticmethod
    def map_logging_type_to_level(logging_type : str) -> int:
        """Map a logging type to a logging level."""
        return logging.getLevelNamesMapping()[logging_type]

    @staticmethod
    def generate_log_file_name(**kwargs) -> str:
        now = datetime.datetime.now(datetime.timezone.utc)
        timestamp=now.isoformat()
        service_name = kwargs.get('service_name', 'unknown_service')
        fnargs = {
            'service': service_name,
            'timestamp': timestamp,
            'suffix': 'log'
        }
        if 'platform' in kwargs:
            fnargs['platform'] = kwargs['platform']
        fname = utils.misc.file_name_management.generate_file_name(
            **fnargs
        )
        return fname

    @staticmethod
    def list_service_logs(service_name : str, logs_dir : str = None) -> list:
        """List the log files for a given service."""
        if logs_dir is None:
            logs_dir = indaleko_default_log_dir
        return [x for x in os.listdir(logs_dir) if service_name in x]

    @staticmethod
    def list_logs(**kwargs) -> list:
        """List all log files filtered against the arguments."""
        if 'log_dir' in kwargs:
            log_dir = kwargs['log_dir']
        else:
            log_dir = indaleko_default_log_dir
        logs = os.listdir(log_dir)
        return logs

def list_logs(args : argparse.Namespace) -> None:
    """List all log files filtered against the arguments."""
    print('List logs')
    logs = IndalekoLogging.list_logs()
    if args.service is not None:
        logs = [x for x in logs if args.service in x]
    if args.platform is not None:
        logs = [x for x in logs if args.platform in x]
    for log in logs:
        print(f'\t{log}')

def cleanup_logs(args: argparse.Namespace) -> None:
    """Cleanup logs."""
    print(args)
    logging.info('Cleanup logs')
    logs = IndalekoLogging.list_logs()
    if args.service is not None:
        logging.debug('Filtering for service %s', args.service)
        logs = [x for x in logs if args.service in x]
    if args.platform is not None:
        logging.debug('Filtering for platform %s', args.platform)
        logs = [x for x in logs if args.platform in x]
    for log in logs:
        log_name = os.path.join(args.log_dir, log)
        if args.log_file in log_name:
            logging.info(f'Skipping log {log_name}')
            continue
        print(f'\t{log_name}\targs.logfile={args.log_file}')
        logging.info(f'Deleting log {log_name}')
        os.remove(log_name)

def prune_logs(args: argparse.Namespace) -> None:
    """This keeps only the last instance of any given log file"""
    # First, let's figure out the prefixes.
    logging.info('Prune logs')
    logs = IndalekoLogging.list_logs()
    if hasattr(args, 'service') and args.service is not None:
        logging.debug('Filtering for service %s', args.service)
        logs = [x for x in logs if args.service in x]
    if hasattr(args, 'platform') and args.platform is not None:
        logging.debug('Filtering for platform %s', args.platform)
        logs = [x for x in logs if args.platform in x]
    prefixes=[]
    for log in logs:
        prefix = log.split('ts=')[0]
        if prefix not in prefixes:
            prefixes.append(prefix)
    logging.debug('Prefixes: %s', prefixes)
    for prefix in prefixes:
        prefix_logs = [x for x in logs if prefix in x]
        prefix_logs.pop(-1) # save the newest one
        for log in prefix_logs:
            log_name = os.path.join(args.log_dir, log)
            if args.log_file == log_name:
                logging.info(f'Skipping log {log_name}')
                continue
            logging.info(f'Deleting log {log_name}')
            os.remove(log_name)


def main():
    """Main function for the IndalekoLogging class."""
    print("Welcome to Indaleko Logging Management")
    print(f'DEBUG maps to {IndalekoLogging.map_logging_type_to_level("DEBUG")}')
    indaleko_logging = IndalekoLogging(service_name='IndalekoLogging')
    assert indaleko_logging is not None, "IndalekoLogging is None"
    parser = argparse.ArgumentParser(description="Indaleko logging management")
    parser.add_argument('--log-dir', default=indaleko_default_log_dir, type=str, help='Directory where logs are stored.')
    parser.add_argument('--service', default=None, type=str, help='Service name to filter logs against.')
    parser.add_argument('--platform', default=platform.system(), type=str, help='Platform to filter logs against.')
    subparsers = parser.add_subparsers(dest='command')
    list_parser = subparsers.add_parser('list')
    list_parser.add_argument('--all', action='store_true', help='List all logs.')
    list_parser.set_defaults(func=list_logs)
    cleanup_parser = subparsers.add_parser('cleanup')
    cleanup_parser.add_argument('--all', action='store_true', help='Cleanup all logs.')
    cleanup_parser.set_defaults(func=cleanup_logs)
    prune_parser = subparsers.add_parser('prune')
    prune_parser.set_defaults(func=prune_logs)
    parser.set_defaults(func=list_logs)
    args = parser.parse_args()
    args.log_file = indaleko_logging.get_log_file_name()
    args.func(args)

if __name__ == '__main__':
    main()
