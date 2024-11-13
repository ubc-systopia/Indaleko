'''
This module handles data ingestion into Indaleko from the Windows local data
indexer.

Indaleko Windows Local Ingester
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
import json
import jsonlines
import logging
import os
import platform
import uuid
import tempfile

from icecream import ic

from IndalekoIngester import IndalekoIngester
from IndalekoWindowsMachineConfig import IndalekoWindowsMachineConfig
from Indaleko import Indaleko
from IndalekoWindowsLocalIndexer import IndalekoWindowsLocalIndexer
from IndalekoObject import IndalekoObject
from IndalekoUnix import UnixFileAttributes
from IndalekoWindows import IndalekoWindows
from IndalekoRelationshipContains import IndalekoRelationshipContains
from IndalekoRelationshipContained import IndalekoRelationshipContainedBy
class IndalekoWindowsLocalIngester(IndalekoIngester):
    '''
    This class handles ingestion of metadata from the Indaleko Windows
    indexing service.
    '''

    windows_local_ingester_uuid = '429f1f3c-7a21-463f-b7aa-cd731bb202b1'
    windows_local_ingester_service = {
        'service_name' : 'Windows Local Ingester',
        'service_description' : 'This service ingests captured index info from the local filesystems of a Windows machine.',
        'service_version' : '1.0',
        'service_type' : 'Ingester',
        'service_identifier' : windows_local_ingester_uuid,
    }

    windows_platform = IndalekoWindowsLocalIndexer.windows_platform
    windows_local_ingester = 'local_fs_ingester'

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
            kwargs['platform'] = IndalekoWindowsLocalIngester.windows_platform
        if 'ingester' not in kwargs:
            kwargs['ingester'] = IndalekoWindowsLocalIngester.windows_local_ingester
        if 'input_file' not in kwargs:
            kwargs['input_file'] = None
        for key, value in self.windows_local_ingester_service.items():
            if key not in kwargs:
                kwargs[key] = value
        super().__init__(**kwargs)
        self.input_file = kwargs['input_file']
        if 'output_file' not in kwargs:
            self.output_file = self.generate_file_name()
        else:
            self.output_file = kwargs['output_file']
        self.indexer_data = []
        self.source = {
            'Identifier' : self.windows_local_ingester_uuid,
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

    def load_indexer_data_from_file(self : 'IndalekoWindowsLocalIngester') -> None:
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

    def normalize_index_data(self, data: dict) -> IndalekoObject:
        '''
        Given some metadata, this will create a record that can be inserted into the
        Object collection.
        '''
        if data is None:
            raise ValueError('Data cannot be None')
        if not isinstance(data, dict):
            raise ValueError('Data must be a dictionary')
        if 'ObjectIdentifier' in data:
            oid = data['ObjectIdentifier']
        else:
            oid = str(uuid.uuid4())
        timestamps = []
        if 'st_birthtime' in data:
            timestamps.append({
                'Label' : IndalekoObject.CREATION_TIMESTAMP,
                'Value' : datetime.datetime.fromtimestamp(data['st_birthtime'],
                                                          datetime.timezone.utc).isoformat(),
                'Description' : 'Created',
            })
        if 'st_mtime' in data:
            timestamps.append({
                'Label' : IndalekoObject.MODIFICATION_TIMESTAMP,
                'Value' : datetime.datetime.fromtimestamp(data['st_mtime'],
                                                          datetime.timezone.utc).isoformat(),
                'Description' : 'Modified',
            })
        if 'st_atime' in data:
            timestamps.append({
                'Label' : IndalekoObject.ACCESS_TIMESTAMP,
                'Value' : datetime.datetime.fromtimestamp(data['st_atime'],
                                                          datetime.timezone.utc).isoformat(),
                'Description' : 'Accessed',
            })
        if 'st_ctime' in data:
            timestamps.append({
                'Label' : IndalekoObject.CHANGE_TIMESTAMP,
                'Value' : datetime.datetime.fromtimestamp(data['st_ctime'],
                                                          datetime.timezone.utc).isoformat(),
                'Description' : 'Changed',
            })
        kwargs = {
            'source' : self.source,
            'raw_data' : Indaleko.encode_binary_data(bytes(json.dumps(data).encode('utf-8'))),
            'URI' : data['URI'],
            'ObjectIdentifier' : oid,
            'Timestamps' : timestamps,
            'Size' : data['st_size'],
            'Attributes' : data,
            'Machine' : self.machine_config.machine_id,
        }
        if 'Volume GUID' in data:
            kwargs['Volume'] = data['Volume GUID']
        elif data['URI'].startswith('\\\\?\\Volume{'):
            kwargs['Volume'] = data['URI'][11:47]
        if 'st_mode' in data:
            kwargs['PosixFileAttributes'] = UnixFileAttributes.map_file_attributes(data['st_mode'])
        if 'st_file_attributes' in data:
            kwargs['WindowsFileAttributes'] = \
                IndalekoWindows.map_file_attributes(data['st_file_attributes'])
        if 'st_ino' in data:
            kwargs['LocalIdentifier'] = str(data['st_ino'])
        if 'Name' in data:
            kwargs['Label'] = data['Name']
        if 'timestamp' not in kwargs:
            if isinstance(self.timestamp, str):
                kwargs['timestamp'] = datetime.datetime.fromisoformat(self.timestamp)
            else:
                kwargs['timestamp'] = self.timestamp
        indaleko_object = IndalekoObject(**kwargs)
        return indaleko_object


    def ingest(self) -> None:
        '''
        This function ingests the indexer file and emits the data needed to
        upload to the database.
        '''
        self.load_indexer_data_from_file()
        dir_data_by_path = {}
        dir_data = []
        file_data = []
        # Step 1: build the normalized data
        for item in self.indexer_data:
            try:
                obj = self.normalize_index_data(item)
            except OSError as e:
                logging.error('Error normalizing data: %s', e)
                logging.error('Data: %s', item)
                self.error_count += 1
                continue
            if 'S_IFDIR' in obj.args['PosixFileAttributes'] or \
               'FILE_ATTRIBUTE_DIRECTORY' in obj.args['WindowsFileAttributes']:
                if 'Path' not in obj.indaleko_object.Record.Attributes:
                    logging.warning('Directory object does not have a path: %s', obj.serialize())
                    continue # skip
                dir_data_by_path[os.path.join(obj['Path'], obj['Volume GUID'])] = obj
                dir_data.append(obj)
                self.dir_count += 1
            else:
                file_data.append(obj)
                self.file_count += 1
        # Step 2: build a table of paths to directory uuids
        dirmap = {}
        for item in dir_data:
            fqp = os.path.join(item['Path'], item['Name'])
            identifier = item.args['ObjectIdentifier']
            dirmap[fqp] = identifier
        # now, let's build a list of the edges, using our map.
        dir_edges = []
        source = {
            'Identifier' : self.windows_local_ingester_uuid,
            'Version' : '1.0',
        }
        for item in dir_data + file_data:
            parent = item['Path']
            if parent not in dirmap:
                continue
            parent_id = dirmap[parent]
            dir_edge = IndalekoRelationshipContains(
                relationship = \
                    IndalekoRelationshipContains.DIRECTORY_CONTAINS_RELATIONSHIP_UUID_STR,
                object1 = {
                    'collection' : Indaleko.Indaleko_Object_Collection,
                    'object' : item.args['ObjectIdentifier'],
                },
                object2 = {
                    'collection' : Indaleko.Indaleko_Object_Collection,
                    'object' : parent_id,
                },
                source = source
            )
            dir_edges.append(dir_edge)
            self.edge_count += 1
            dir_edge = IndalekoRelationshipContainedBy(
                relationship = \
                    IndalekoRelationshipContainedBy.CONTAINED_BY_DIRECTORY_RELATIONSHIP_UUID_STR,
                object1 = {
                    'collection' : Indaleko.Indaleko_Object_Collection,
                    'object' : parent_id,
                },
                object2 = {
                    'collection' : Indaleko.Indaleko_Object_Collection,
                    'object' : item.args['ObjectIdentifier'],
                },
                source = source
            )
            dir_edges.append(dir_edge)
            self.edge_count += 1
        # Save the data to the ingester output file
        temp_file_name = ""
        with tempfile.NamedTemporaryFile(dir=self.data_dir, delete=False) as tf:
            temp_file_name = tf.name
        self.write_data_to_file(dir_data + file_data, temp_file_name)
        try:
            if os.path.exists(self.output_file):
                os.remove(self.output_file)
            os.rename(temp_file_name, self.output_file)
        except (
            FileNotFoundError,
            PermissionError,
            FileExistsError,
            OSError,
        ) as e:
            logging.error(
                'Unable to rename temp file %s to output file %s',
                temp_file_name,
                self.output_file
            )
            print(f'Unable to rename temp file {temp_file_name} to output file {self.output_file}')
            print(e)
            self.output_file = temp_file_name
        load_string = self.build_load_string(
            collection=Indaleko.Indaleko_Object_Collection,
            file=self.output_file
        )
        logging.info('Load string: %s', load_string)
        print('Load string: ', load_string)
        temp_file_name = ""
        with tempfile.NamedTemporaryFile(dir=self.data_dir, delete=False) as tf:
            temp_file_name = tf.name
        edge_file = self.generate_output_file_name(
            machine=self.machine_id,
            platform=self.platform,
            service='ingest',
            storage=self.storage_description,
            collection=Indaleko.Indaleko_Relationship_Collection,
            timestamp=self.timestamp,
            output_dir=self.data_dir,
        )
        self.write_data_to_file(dir_edges, temp_file_name)
        try:
            if os.path.exists(edge_file):
                os.remove(edge_file)
            os.rename(temp_file_name, edge_file)
        except (
            FileNotFoundError,
            PermissionError,
            FileExistsError,
            OSError,
        ) as e:
            logging.error(
                'Unable to rename temp file %s to output file %s',
                temp_file_name,
                edge_file
            )
            print(f'Unable to rename temp file {temp_file_name} to output file {edge_file}')
            print(f'Error: {e}')
            print(f'Target file name is {edge_file[len(self.data_dir)+1:]}')
            print(f'Target file name length is {len(edge_file[len(self.data_dir)+1:])}')
            edge_file=temp_file_name
        load_string = self.build_load_string(
            collection=Indaleko.Indaleko_Relationship_Collection,
            file=edge_file
        )
        logging.info('Load string: %s', load_string)
        print('Load string: ', load_string)


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
    timestamp = metadata.get('timestamp',
                             datetime.datetime.now(datetime.timezone.utc).isoformat())
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
        if indexer_platform != IndalekoWindowsLocalIngester.windows_platform:
            print('Warning: platform of indexer file ' +\
                  f'({indexer_platform}) name does not match platform of ingester ' +\
                    f'({IndalekoWindowsLocalIngester.windows_platform}.)')
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
    ingester = IndalekoWindowsLocalIngester(
        machine_config=machine_config,
        machine_id = machine_id,
        timestamp=timestamp,
        platform=IndalekoWindowsLocalIndexer.windows_platform,
        ingester = IndalekoWindowsLocalIngester.windows_local_ingester,
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
