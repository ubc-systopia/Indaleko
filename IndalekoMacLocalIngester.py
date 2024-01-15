import argparse
import datetime
import platform
import logging
import os
import json
import jsonlines
import uuid
import msgpack

from IndalekoIngester import IndalekoIngester
from Indaleko import Indaleko
from IndalekoMacLocalIndexer import IndalekoMacLocalIndexer
from IndalekoMacMachineConfig import IndalekoMacOSMachineConfig
from IndalekoMachineConfigSchema import IndalekoMachineConfigSchema
from IndalekoServices import IndalekoService
from IndalekoObject import IndalekoObject
from IndalekoUnix import UnixFileAttributes
from IndalekoRelationshipContains import IndalekoRelationshipContains
from IndalekoRelationshipContained import IndalekoRelationshipContainedBy

class IndalekoMacLocalIngester(IndalekoIngester):
    '''
    This class handles the ingestion of metadata from the Indaleko Unix
    indexing service.
    '''

    mac_local_ingester_uuid = '07670255-1e82-4079-ad6f-f2bb39f44f8f'
    mac_local_ingester_service = IndalekoService.create_service_data(
        service_name='Mac Local Ingester',
        service_description='This service ingests captured index info from the local filesystems of a Mac machine.',
        service_version='1.0',
        service_type='Ingester',
        service_identifier=mac_local_ingester_uuid,
    )

    mac_platform =IndalekoMacLocalIndexer.mac_platform
    mac_local_ingester = 'local_fs_ingester'

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
                logging.warning('Warning: machine ID of indexer file ' +
                      f'({kwargs["machine"]}) does not match machine ID of ingester ' +
                        f'({self.machine_config.machine_id}.)')
        if 'timestamp' not in kwargs:
            kwargs['timestamp'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if 'platform' not in kwargs:
            kwargs['platform'] = IndalekoMacLocalIngester.mac_platform
        if 'ingester' not in kwargs:
            kwargs['ingester'] = IndalekoMacLocalIngester.mac_local_ingester
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
            'Identifier': self.mac_local_ingester_uuid,
            'Version': '1.0'
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
                if IndalekoMacLocalIndexer.mac_platform in x and
                IndalekoMacLocalIndexer.mac_local_indexer_name in x]

    def load_indexer_data_from_file(self: 'IndalekoMacLocalIngester') -> None:
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
            raise ValueError(f'Input file {self.input_file} is of an unknown type')
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
        oid = str(uuid.uuid4())
        kwargs = {
            'source': self.source,
            'raw_data': msgpack.packb(bytes(json.dumps(data).encode('utf-8'))),
            'URI': data['URI'],
            'ObjectIdentifier': oid,
            'Timestamps': [
                {
                    'Label': IndalekoObject.CREATION_TIMESTAMP,
                    'Value': datetime.datetime.fromtimestamp(data['st_birthtime'],
                                                              datetime.timezone.utc).isoformat(),
                    'Description': 'Created',
                },
                {
                    'Label': IndalekoObject.MODIFICATION_TIMESTAMP,
                    'Value': datetime.datetime.fromtimestamp(data['st_mtime'],
                                                              datetime.timezone.utc).isoformat(),
                    'Description': 'Modified',
                },
                {
                    'Label': IndalekoObject.ACCESS_TIMESTAMP,
                    'Value': datetime.datetime.fromtimestamp(data['st_atime'],
                                                              datetime.timezone.utc).isoformat(),
                    'Description': 'Accessed',
                },
                {
                    'Label': IndalekoObject.CHANGE_TIMESTAMP,
                    'Value': datetime.datetime.fromtimestamp(data['st_ctime'],
                                                              datetime.timezone.utc).isoformat(),
                    'Description': 'Changed',
                },
            ],
            'Size': data['st_size'],
            'Attributes': data,
            'Machine': self.machine_config.machine_id,
        }
       
        if 'st_mode' in data:
            kwargs['UnixFileAttributes'] = UnixFileAttributes.map_file_attributes(data['st_mode'])
        
        return IndalekoObject(**kwargs)

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
            if 'S_IFDIR' in obj.args['UnixFileAttributes']: 
                if 'Path' not in obj:
                    logging.warning('Directory object does not have a path: %s', obj.to_json())
                    continue  # skip
                dir_data_by_path[obj['Path']] = obj
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
            'Identifier': self.mac_local_ingester_uuid,
            'Version': '1.0',
        }
        for item in dir_data + file_data:
            parent = item['Path']
            if parent not in dirmap:
                continue
            parent_id = dirmap[parent]
            dir_edge = IndalekoRelationshipContains(
                relationship=
                IndalekoRelationshipContains.DIRECTORY_CONTAINS_RELATIONSHIP_UUID_STR,
                object1={
                    'collection': 'Objects',
                    'object': item.args['ObjectIdentifier'],
                },
                object2={
                    'collection': 'Objects',
                    'object': parent_id,
                },
                source=source
            )
            dir_edges.append(dir_edge)
            self.edge_count += 1
            dir_edge = IndalekoRelationshipContainedBy(
                relationship=
                IndalekoRelationshipContainedBy.CONTAINED_BY_DIRECTORY_RELATIONSHIP_UUID_STR,
                object1={
                    'collection': 'Objects',
                    'object': parent_id,
                },
                object2={
                    'collection': 'Objects',
                    'object': item.args['ObjectIdentifier'],
                },
                source=source
            )
            dir_edges.append(dir_edge)
            self.edge_count += 1
        # Save the data to the ingester output file
        self.write_data_to_file(dir_data + file_data, self.output_file)
        edge_file = self.generate_output_file_name(
            machine=self.machine_id,
            platform=self.platform,
            service='local_ingest',
            storage=self.storage_description,
            collection='Relationships',
            timestamp=self.timestamp,
            output_dir=self.data_dir,
        )
        self.write_data_to_file(dir_edges, edge_file)


def main():
    '''
    This is the main handler for the Indaleko Mac Local Ingest service.
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
    config_files = IndalekoMacOSMachineConfig.find_config_files(pre_args.configdir)
    assert isinstance(config_files, list), 'config_files must be a list'
    if len(config_files) == 0:
        print(f'No config files found in {pre_args.configdir}, exiting.')
        return
    default_config_file = IndalekoMacOSMachineConfig.get_most_recent_config_file(pre_args.configdir)
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
    machine_config = IndalekoMacOSMachineConfig.load_config_from_file(config_file=default_config_file)
    indexer = IndalekoMacLocalIndexer(
        search_dir=pre_args.datadir,
        prefix=IndalekoMacLocalIndexer.mac_platform,
        suffix=IndalekoMacLocalIndexer.mac_local_indexer_name,
        machine_config=machine_config
    )
    indexer_files = indexer.find_indexer_files(pre_args.datadir)
    parser = argparse.ArgumentParser(parents=[pre_parser])
    parser.add_argument('--input',
                        choices=indexer_files,
                        default=indexer_files[-1],
                        help='Mac Local Indexer file to ingest.')
    parser.add_argument('--reset', action='store_true', help='Reset the service collection.')
    parser.add_argument('--logdir',
                        help=f'Path to the log directory (default is {Indaleko.default_log_dir})',
                        default=Indaleko.default_log_dir)
    parser.add_argument('--loglevel',
                        choices=logging_levels,
                        default=logging.DEBUG,
                        help='Logging level to use.')
    args = parser.parse_args()
    metadata = IndalekoMacLocalIndexer.extract_metadata_from_indexer_file_name(args.input)
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    machine_id = 'unknown'
    if 'machine' in metadata:
        if metadata['machine'] != machine_config.machine_id:
            print('Warning: machine ID of indexer file ' +
                  f'({metadata["machine"]}) does not match machine ID of ingester ' +
                    f'({machine_config.machine_id})')
        machine_id = metadata['machine']
    if 'timestamp' in metadata:
        timestamp = metadata['timestamp']
    if 'platform' in metadata:
        indexer_platform = metadata['platform']
        if indexer_platform != IndalekoMacLocalIngester.mac_platform:
            print('Warning: platform of indexer file ' +
                  f'({indexer_platform}) name does not match platform of ingester ' +
                    f'({IndalekoMacLocalIngester.mac_platform}.)')
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
    ingester = IndalekoMacLocalIngester(
        machine_config=machine_config,
        machine_id=machine_id,
        timestamp=timestamp,
        platform=IndalekoMacLocalIndexer.mac_platform,
        ingester=IndalekoMacLocalIngester.mac_local_ingester,
        storage_description=storage,
        file_prefix=file_prefix,
        file_suffix=file_suffix,
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
    logging.info('Ingesting %s ', args.input)
    logging.info('Output file %s ', output_file)
    ingester.ingest()
    counts = ingester.get_counts()
    for count_type, count_value in counts.items():
        logging.info('%s: %d', count_type, count_value)
    logging.info('Done')

if __name__ == '__main__':
    main()