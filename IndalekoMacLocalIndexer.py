'''
This module handles data ingestion into Indaleko from the Mac local file
system indexer.

Indaleko Mac Local Indexer
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
import os
import logging
import platform

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from Indaleko import Indaleko
from storage.collectors.base import BaseStorageCollector
from IndalekoMacMachineConfig import IndalekoMacOSMachineConfig
# pylint: enable=wrong-import-position


class IndalekoMacLocalIndexer(BaseStorageCollector):
    '''
    This is the class that indexes Mac local file systems.
    '''
    mac_platform = 'Mac'
    mac_local_indexer_name = 'fs-indexer'

    indaleko_mac_local_indexer_uuid = '14d6c989-0d1e-4ccc-8aea-a75688a6bb5f'
    indaleko_mac_local_indexer_service_name = 'Mac Local Indexer'
    indaleko_mac_local_indexer_service_description = 'This service indexes the local filesystems of a Mac machine.'
    indaleko_mac_local_indexer_service_version = '1.0'
    indaleko_mac_local_indexer_service_type = 'Indexer'

    indaleko_mac_local_indexer_service ={
        'service_name' : indaleko_mac_local_indexer_service_name,
        'service_description' : indaleko_mac_local_indexer_service_description,
        'service_version' : indaleko_mac_local_indexer_service_version,
        'service_type' : indaleko_mac_local_indexer_service_type,
        'service_identifier' : indaleko_mac_local_indexer_uuid,
    }

    def __init__(self, **kwargs):
        assert 'machine_config' in kwargs, 'machine_config must be specified'
        self.machine_config = kwargs['machine_config']
        if 'machine_id' not in kwargs:
            kwargs['machine_id'] = self.machine_config.machine_id
        super().__init__(**kwargs,
                         platform=IndalekoMacLocalIndexer.mac_platform,
                         indexer_name=IndalekoMacLocalIndexer.mac_local_indexer_name,
                         **IndalekoMacLocalIndexer.indaleko_mac_local_indexer_service
        )

        self.dir_count=0
        self.file_count=0

    def build_stat_dict(self, name: str, root : str, last_uri = None) -> tuple:
        '''
        Given a file name and a root directory, this will return a dict
        constructed from the file system metadata ("stat") for that file.
        Returns: dict_stat, last_uri
        '''

        file_path = os.path.join(root, name)

        if last_uri is None:
            last_uri = file_path
        try:
            stat_data = os.stat(file_path)
        except Exception as e: # pylint: disable=broad-except
            # at least for now, we just skip errors
            logging.warning('Unable to stat %s : %s', file_path, e)
            self.error_count += 1
            return None

        stat_dict = {key : getattr(stat_data, key) \
                    for key in dir(stat_data) if key.startswith('st_')}
        stat_dict['Name'] = name
        stat_dict['Path'] = root
        stat_dict['URI'] = os.path.join(root, name)
        stat_dict['Indexer'] = self.service_identifier

        return (stat_dict, last_uri)


    def index(self) -> list:
        data = []
        last_uri = None

        # indexing path itself has to have a root node
        root_entry= self.build_stat_dict(os.path.basename(self.path), os.path.dirname(self.path), last_uri)
        if root_entry:
            data.append(root_entry[0])
            last_uri=root_entry[1]

        for root, dirs, files in os.walk(self.path):
            for name in dirs + files:
                entry = self.build_stat_dict(name, root, last_uri)
                if name in dirs:
                    self.dir_count += 1
                else:
                    self.file_count += 1
                if entry is not None:
                    data.append(entry[0])
                    last_uri = entry[1]
        return data

def main():
    '''This is the main handler for the Indaleko Mac Local Indexer
    service.'''
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

     # Step 1: find the machine configuration file
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--configdir',
                            help='Path to the config directory',
                            default=Indaleko.default_config_dir)
    pre_args, _ = pre_parser.parse_known_args()

    config_files = IndalekoMacOSMachineConfig.find_config_files(pre_args.configdir)
    default_config_file = IndalekoMacOSMachineConfig.get_most_recent_config_file(pre_args.configdir)

    # Step 2: figure out the default config file
    pre_parser = argparse.ArgumentParser(add_help=False, parents=[pre_parser])
    pre_parser.add_argument('--config', choices=config_files, default=default_config_file)
    pre_parser.add_argument('--path', help='Path to the directory to index', type=str,
                            default=os.path.expanduser('~'))
    pre_args, _ = pre_parser.parse_known_args()
    print(pre_args.config)

    # Step 3: now we can compute the machine config and drive GUID
    machine_config = IndalekoMacOSMachineConfig.load_config_from_file(config_file=pre_args.config)

    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    indexer = IndalekoMacLocalIndexer(machine_config=machine_config, timestamp=timestamp)
    output_file = indexer.generate_windows_indexer_file_name()
    parser= argparse.ArgumentParser(parents=[pre_parser])
    parser.add_argument('--datadir', '-d',
                        help='Path to the data directory',
                        default=Indaleko.default_data_dir)
    parser.add_argument('--output', '-o',
                        help='name to assign to output directory',
                        default=output_file)
    parser.add_argument('--logdir', '-l',
                        help='Path to the log directory',
                        default=Indaleko.default_log_dir)
    parser.add_argument('--loglevel',
                        type=int,
                        default=logging.DEBUG,
                        choices=logging_levels,
                        help='Logging level to use (lower number = more logging)')

    args = parser.parse_args()
    args.path=os.path.abspath(args.path)
    indexer = IndalekoMacLocalIndexer(timestamp=timestamp,
                                          path=args.path,
                                          machine_config=machine_config)
    output_file = indexer.generate_windows_indexer_file_name()
    log_file_name = indexer.generate_windows_indexer_file_name(target_dir=args.logdir, suffix='.log')
    logging.basicConfig(filename=os.path.join(log_file_name),
                                level=args.loglevel,
                                format='%(asctime)s - %(levelname)s - %(message)s',
                                force=True)
    logging.info('Indexing %s ' , pre_args.path)
    logging.info('Output file %s ' , output_file)
    data = indexer.index()
    indexer.write_data_to_file(data, output_file)
    counts = indexer.get_counts()
    for count_type, count_value in counts.items():
        logging.info('%s: %d', count_type, count_value)
    logging.info('Done')

if __name__ == '__main__':
    main()
