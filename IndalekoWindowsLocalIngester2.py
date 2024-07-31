'''
This module handles gathering supplemental metadata from the Windows local file system.

Indaleko Windows Local Ingester 2
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
import platform
import logging
import os
import json
import jsonlines
import uuid
import filetype

from IndalekoIngester import IndalekoIngester
from IndalekoWindowsMachineConfig import IndalekoWindowsMachineConfig
from Indaleko import Indaleko
from IndalekoWindowsLocalIndexer import IndalekoWindowsLocalIndexer
from IndalekoServices import IndalekoService
from IndalekoObject import IndalekoObject
from IndalekoUnix import UnixFileAttributes
from IndalekoWindows import IndalekoWindows
from IndalekoRelationshipContains import IndalekoRelationshipContains
from IndalekoRelationshipContained import IndalekoRelationshipContainedBy


class IndalekoWindowsLocalSupplementalIngester(IndalekoIngester):

    windows_local_supplemental_ingester_uuid = 'e38c23ea-0f21-40dd-9efc-3de49f282bba'
    windows_local_supplemental_ingester_service = IndalekoService.create_service_data(
        service_name = 'Windows Local Supplemental Ingester',
        service_description = 'This service generates and updates entries based upon extracted metadata from local files',
        service_version = '1.0',
        service_type = 'Ingester',
        service_identifier = windows_local_supplemental_ingester_uuid,
    )

    windows_platform = IndalekoWindowsLocalIndexer.windows_platform
    windows_local_ingester = 'supplemental_fs_ingester'

    def __init__(self, **kwargs) -> None:
        if 'input_file' not in kwargs:
            raise ValueError('input_file must be specified')
        if 'machine_config' not in kwargs:
            raise ValueError('machine_config must be specified')
        self.machine_config = kwargs['machine_config']
        if 'machine_id' not in kwargs:
            kwargs['machine_id'] = self.machine_config.machine_id
        else:
            kwargs['machine_id'] = self.machine_config.machine_id
            if kwargs['machine_id'] != self.machine_config.machine_id:
                logging.warning('Warning: machine ID of indexer file ' +\
                      f'({kwargs["machine"]}) does not match machine ID of ingester ' +\
                        f'({self.machine_config.machine_id}.)')
        if 'timestamp' not in kwargs:
            kwargs['timestamp'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if 'platform' not in kwargs:
            kwargs['platform'] = IndalekoWindowsLocalSupplementalIngester.windows_platform
        if 'ingester' not in kwargs:
            kwargs['ingester'] = IndalekoWindowsLocalSupplementalIngester.windows_local_ingester
        if 'input_file' not in kwargs:
            kwargs['input_file'] = None
        super().__init__(**kwargs)
        self.input_file = kwargs['input_file']
        if 'output_file' not in kwargs:
            self.output_file = self.generate_file_name()
        else:
            self.output_file = kwargs['output_file']
        self.indexer_data = []
        self.source = {
            'Identifier' : self.windows_local_supplemental_ingester_uuid,
            'Version' : '1.0'
        }


    def find_indexer_files(self) -> list:
        '''This function finds the files to ingest:
            search_dir: path to the search directory
            prefix: prefix of the file to ingest
            suffix: suffix of the file to ingest (default is .json)
        '''
        if self.data_dir is None:
            raise ValueError('data_dir must be specified')
        return [x for x in super().find_indexer_files(self.data_dir)
                if IndalekoWindowsLocalIndexer.windows_platform in x and
                IndalekoWindowsLocalIndexer.windows_local_indexer_name in x]

    def load_indexer_data_from_file(self : 'IndalekoWindowsLocalSupplementalIngester') -> None:
        '''This function loads the indexer data from the file.'''
        if self.input_file is None:
            raise ValueError('input_file must be specified')
        if self.input_file.endswith('.jsonl'):
            with jsonlines.open(self.input_file) as reader:
                for entry in reader:
                    self.indexer_data.append(entry)
        elif self.input_file.endswith('.json'):
            with open(self.input_file, 'r', encoding='utf-8-sig') as file:
                self.indexer_data = json.load(file)
        else:
            raise ValueError(f'Input file {self.input_file} is an unknown type')
        if not isinstance(self.indexer_data, list):
            raise ValueError('indexer_data is not a list')

    def collect_index_data(self, data: dict) -> dict:
        if 'ObjectIdentifier' not in data:
            return None # can't deal with old data files currently
        oid = data['ObjectIdentifier']
        file_type = None
        return {
            'ObjectIdentifier' : oid,
            'FileType' : file_type,
        }
        pass

    def ingest(self) -> None:
        '''
        This function ingests the indexer file and uses it to generate the
        supplemental data and add it to the database.
        '''
        data = []
        self.load_indexer_data_from_file()
        for item in self.indexer_data:
            obj = self.collect_index_data(item)
            if obj is not None:
                data.append(obj)
        self.write_data_to_file(data, self.output_file)

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
                            help=f'Path to the config directory (default is {Indaleko.default_config_dir})',
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
                            help=f'Configuration file to use. (default: {default_config_file})')
    pre_parser.add_argument('--datadir',
                            help=f'Path to the data directory (default is {Indaleko.default_data_dir})',
                            type=str,
                            default=Indaleko.default_data_dir)
    pre_args, _ = pre_parser.parse_known_args()
    machine_config = IndalekoWindowsMachineConfig.load_config_from_file(config_file=default_config_file)
    indexer = IndalekoWindowsLocalIndexer(
        search_dir=pre_args.datadir,
        prefix=IndalekoWindowsLocalIndexer.windows_platform,
        suffix=IndalekoWindowsLocalIndexer.windows_local_indexer_name,
        machine_config=machine_config
    )
    indexer_files = indexer.find_indexer_files(pre_args.datadir)
    parser = argparse.ArgumentParser(parents=[pre_parser])
    parser.add_argument('--input',
                        choices=indexer_files,
                        default=indexer_files[-1],
                        help='Windows Local Indexer file to ingest.')
    parser.add_argument('--reset', action='store_true', help='Reset the service collection.')
    parser.add_argument('--logdir',
                        help=f'Path to the log directory (default is {Indaleko.default_log_dir})',
                        default=Indaleko.default_log_dir)
    parser.add_argument('--loglevel',
                        choices=logging_levels,
                        default=logging.DEBUG,
                        help='Logging level to use.')
    args = parser.parse_args()
    metadata = IndalekoWindowsLocalIndexer.extract_metadata_from_indexer_file_name(args.input)
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    machine_id = 'unknown'
    if 'machine' in metadata:
        if metadata['machine'] != machine_config.machine_id:
            print('Warning: machine ID of indexer file ' +\
                  f'({metadata["machine"]}) does not match machine ID of ingester ' +\
                    f'({machine_config.machine_id})')
        machine_id = metadata['machine']
    if 'timestamp' in metadata:
        timestamp = metadata['timestamp']
    if 'platform' in metadata:
        indexer_platform = metadata['platform']
        if indexer_platform != IndalekoWindowsLocalSupplementalIngester.windows_platform:
            print('Warning: platform of indexer file ' +\
                  f'({indexer_platform}) name does not match platform of ingester ' +\
                    f'({IndalekoWindowsLocalSupplementalIngester.windows_platform}.)')
    storage = 'unknown'
    if 'storage' in metadata:
        storage = metadata['storage']
    file_prefix = IndalekoIngester.default_file_prefix
    if 'file_prefix' in metadata:
        file_prefix = metadata['file_prefix']
    file_suffix = IndalekoIngester.default_file_suffix
    if 'file_suffix' in metadata:
        file_suffix = metadata['file_suffix']
    input_file = os.path.join(args.datadir, args.input)
    ingester = IndalekoWindowsLocalSupplementalIngester(
        machine_config=machine_config,
        machine_id = machine_id,
        timestamp=timestamp,
        platform=IndalekoWindowsLocalIndexer.windows_platform,
        ingester = IndalekoWindowsLocalSupplementalIngester.windows_local_ingester,
        storage_description = storage,
        file_prefix = file_prefix,
        file_suffix = file_suffix,
        data_dir=args.datadir,
        input_file=input_file,
        log_dir=args.logdir
    )
    output_file = ingester.generate_file_name()
    log_file_name = ingester.generate_file_name(
        target_dir=args.logdir, suffix='.log')
    logging.basicConfig(filename=os.path.join(log_file_name),
                                level=logging.DEBUG,
                                format='%(asctime)s - %(levelname)s - %(message)s',
                                force=True)
    logging.info('Ingesting %s ' , args.input)
    logging.info('Output file %s ' , output_file)
    ingester.ingest()
    total=0
    for count_type, count_value in ingester.get_counts().items():
        logging.info('%s: %d', count_type, count_value)
        total += count_value
    logging.info('Total: %d', total)
    logging.info('Done')


if __name__ == '__main__':
    main()
