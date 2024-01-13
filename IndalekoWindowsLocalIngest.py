'''
This module handles data ingestion into Indaleko from the Windows local data
indexer.
'''
import argparse
import os
import datetime
import platform
import logging

from IndalekoIngest import IndalekoIngest
from IndalekoWindowsMachineConfig import IndalekoWindowsMachineConfig
from Indaleko import Indaleko
from IndalekoWindowsLocalIndexer import IndalekoWindowsLocalIndexer

class IndalekoWindowsLocalIngest(IndalekoIngest):
    '''
    This class handles ingestion of metadata from the Indaleko Windows
    indexing service.
    '''

    WindowsLocalIngester_UUID = '429f1f3c-7a21-463f-b7aa-cd731bb202b1'
    WindowsLocalIngesterService = {
        'name': WindowsLocalIngester_UUID,
        'description': 'This service ingests captured index info from the local filesystems of a Windows machine.',
        'version': '1.0',
        'identifier': WindowsLocalIngester_UUID,
        'created': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'type': 'Ingester',
    }
    windows_platform = IndalekoWindowsLocalIndexer.windows_platform
    windows_local_ingester = 'local-fs-ingester'

    def __init__(self, **kwargs) -> None:
        assert 'machine_config' in kwargs, 'machine_config must be specified'
        self.machine_config = kwargs['machine_config']
        if 'machine_id' not in kwargs:
            kwargs['machine_id'] = self.machine_config.machine_id
        super().__init__(**kwargs)


    def find_indexer_files(self) -> list:
        return [x for x in super().find_indexer_files(self.data_dir)
                if IndalekoWindowsLocalIndexer.windows_platform in x and
                IndalekoWindowsLocalIndexer.windows_local_indexer in x]

def main():
    '''
    This is the main handler for the Indaleko Windows Local Ingest
    service.
    '''
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
        logging_levels = sorted(set([level for level in logging.getLevelNamesMapping()]))

    # step 1: find the machine configuration file
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--configdir', '-c',
                            help='Path to the config directory',
                            default=Indaleko.default_config_dir)
    pre_args, _ = pre_parser.parse_known_args()
    config_files = IndalekoWindowsMachineConfig.find_config_files(pre_args.configdir)
    assert isinstance(config_files, list), 'config_files must be a list'
    if len(config_files) == 0:
        print(f'No config files found in {pre_args.configdir}, exiting.')
        return
    default_config_file = IndalekoWindowsMachineConfig.get_most_recent_config_file(pre_args.configdir)
    pre_parser = argparse.ArgumentParser(add_help=False, parents=[pre_parser])
    pre_parser.add_argument('--config',
                            choices=config_files,
                            default=default_config_file,
                            help='Configuration file to use.')
    pre_parser.add_argument('--datadir', '-d',
                            help='Path to the data directory',
                            default=Indaleko.default_data_dir)
    pre_args, _ = pre_parser.parse_known_args()
    machine_config = IndalekoWindowsMachineConfig.load_config_from_file(config_file=default_config_file)
    indexer = IndalekoWindowsLocalIndexer(
        search_dir=pre_args.datadir,
        prefix=IndalekoWindowsLocalIndexer.windows_platform,
        suffix=IndalekoWindowsLocalIndexer.windows_local_indexer,
        machine_config=machine_config
    )
    indexer_files = indexer.find_indexer_files(pre_args.datadir)
    parser = argparse.ArgumentParser(add_help=False, parents=[pre_parser])
    parser.add_argument('--input', '-i',
                        choices=indexer_files,
                        default=indexer_files[-1],
                        help='Windows Local Indexer file to ingest.')
    parser.add_argument('--reset', action='store_true', help='Reset the service collection.')
    parser.add_argument('--logdir', '-l', help='Path to the log directory', default=Indaleko.default_log_dir)
    parser.add_argument('--loglevel',
                        choices=logging_levels,
                        default=logging.DEBUG,
                        help='Logging level to use.')
    args = parser.parse_args()
    print(args)
    # next thing to do is generate a log file name and initialize logging
    # ingester = IndalekoWindowsLocalIngest(args.datadir, args.input,
    # reset=args.reset)
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ingester = IndalekoWindowsLocalIngest(
        machine_config=machine_config,
        timestamp=timestamp,
        platform=IndalekoWindowsLocalIndexer.windows_platform,
        ingester = IndalekoWindowsLocalIngest.windows_local_ingester,
        output_dir=args.datadir,
        input_file=args.input,
        log_dir=args.logdir
    )
    print(ingester.get_default_outfile_name())

if __name__ == '__main__':
    main()
