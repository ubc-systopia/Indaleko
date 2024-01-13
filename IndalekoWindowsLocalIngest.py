'''
This module handles data ingestion into Indaleko from the Windows local data
indexer.
'''
import argparse
import os
import datetime

from IndalekoIngest import IndalekoIngest
from IndalekoWindowsMachineConfig import IndalekoWindowsMachineConfig
from Indaleko import Indaleko

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


    def __init__(self, data_dir : str, reset: bool = False) -> None:
        super().__init__(reset=reset)
        self.data_dir = data_dir
        assert os.path.isdir(self.data_dir), f'{self.data_dir} must be a directory'

    @staticmethod
    def find_data_files(data_dir : str = Indaleko.default_data_dir) -> list:
        '''Given a directory, this returns a list of files that meet the naming convention.'''

def main():
    '''This is the main handler for the Indaleko Windows Local Ingest service.'''
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--datadir', '-d',
                            help='Path to the data directory', default=Indaleko.default_data_dir)
    pre_parser.add_argument('--configdir', '-c',
                            help='Path to the config directory', default=Indaleko.default_config_dir)
    pre_args, _ = pre_parser.parse_known_args()


    config_files = IndalekoWindowsMachineConfig.find_config_files(pre_args.configdir)
    assert isinstance(config_files, list), 'config_files must be a list'
    if len(config_files) == 0:
        print(f'No config files found in {pre_args.configdir}, exiting.')
        return
    parser = argparse.ArgumentParser(parents=[pre_parser])
    parser.add_argument('--config', choices=config_files, default=config_files[-1],)
    parser.add_argument('--input', choices=config_files, default=config_files[-1],
                        help='Windows Local Indexer file to ingest.')
    parser.add_argument('--reset', action='store_true', help='Reset the service collection.')
    parser.add_argument('--logdir', '-l', help='Path to the log directory', default=Indaleko.default_log_dir)
    args = parser.parse_args()
    print(args)
    ingester = IndalekoWindowsLocalIngest(args.datadir, args.input, reset=args.reset)

if __name__ == '__main__':
    main()
