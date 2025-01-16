'''
This module handles data ingestion into Indaleko from the Linux local data
collector.

Indaleko Linux Local Ingester
Copyright (C) 2024-2025 Tony Mason

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
import logging
import os
import json
import jsonlines
import sys
import uuid

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from data_models import IndalekoSourceIdentifierDataModel
from db import IndalekoDBCollections, IndalekoServiceManager
from platforms.linux.machine_config import IndalekoLinuxMachineConfig
from platforms.unix import UnixFileAttributes
from storage import IndalekoObject
from storage.recorders.base import BaseStorageRecorder
from storage.collectors.local.linux.collector import IndalekoLinuxLocalStorageCollector
import utils.misc.directory_management
import utils.misc.file_name_management
import utils.misc.data_management
from utils.i_logging import IndalekoLogging
# pylint: enable=wrong-import-position


class IndalekoLinuxLocalRecorder(BaseStorageRecorder):
    '''
    This class handles recording of metadata gathered from
    the local Linux file system.
    '''

    linux_local_recorder_uuid = '14ab60a0-3a5a-456f-8400-07c47a274f4b'
    linux_local_recorder_service = {
        'service_name' : 'Linux Local Recorder',
        'service_description' : 'This service records captured metadata from the local Linux filesystems.',
        'service_version' : '1.0',
        'service_type' : IndalekoServiceManager.service_type_storage_recorder,
        'service_identifier' : linux_local_recorder_uuid,
    }

    linux_platform = IndalekoLinuxLocalStorageCollector.linux_platform
    linux_local_recorder = 'local_fs_recorder'

    def __init__(self: BaseStorageRecorder, **kwargs: dict) -> None:
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
                logging.warning('Warning: machine ID of collector file ' +\
                      f'({kwargs["machine"]}) does not match machine ID of recorder ' +\
                        f'({self.machine_config.machine_id}.)')
        if 'timestamp' not in kwargs:
            kwargs['timestamp'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if 'platform' not in kwargs:
            kwargs['platform'] = IndalekoLinuxLocalRecorder.linux_platform
        if 'recorder' not in kwargs:
            kwargs['recorder'] = IndalekoLinuxLocalRecorder.linux_local_recorder
        if 'input_file' not in kwargs:
            kwargs['input_file'] = None
        for key, value in self.linux_local_recorder_service.items():
            if key not in kwargs:
                kwargs[key] = value
        super().__init__(**kwargs)
        self.input_file = kwargs['input_file']
        if 'output_file' not in kwargs:
            self.output_file = self.generate_file_name()
        else:
            self.output_file = kwargs['output_file']
        self.collector_data = []
        self.source = {
            'Identifier' : self.linux_local_recorder_uuid,
            'Version' : '1.0'
        }

    def find_collector_files(self) -> list:
        '''
        Find the collector files in the data directory.
        '''
        if self.data_dir is None:
            raise ValueError('data_dir must be specified')
        return [x for x in IndalekoLinuxLocalStorageCollector.find_collector_files(self.data_dir)
                if IndalekoLinuxLocalStorageCollector.linux_platform in x and
                IndalekoLinuxLocalStorageCollector.linux_local_collector_name in x]

    def load_collector_data_from_file(self : 'IndalekoLinuxLocalRecorder') -> None:
        '''This function loads the collector data from the file.'''
        if self.input_file is None:
            raise ValueError('input_file must be specified')
        if self.input_file.endswith('.jsonl'):
            with jsonlines.open(self.input_file) as reader:
                for entry in reader:
                    self.collector_data.append(entry)
        elif self.input_file.endswith('.json'):
            with open(self.input_file, 'r', encoding='utf-8-sig') as file:
                self.collector_data = json.load(file)
        else:
            raise ValueError(f'Input file {self.input_file} is an unknown type')
        if not isinstance(self.collector_data, list):
            raise ValueError('collector_data is not a list')

    def normalize_collector_data(self, data : dict) -> IndalekoObject:
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
            'raw_data' : utils.misc.data_management.encode_binary_data(bytes(json.dumps(data).encode('utf-8'))),
            'URI' : data['URI'],
            'ObjectIdentifier' : oid,
            'Timestamps' : timestamps,
            'Size' : data['st_size'],
            'Attributes' : data,
            'Machine' : self.machine_config.machine_id,
        }
        if 'st_mode' in data:
            kwargs['PosixFileAttributes'] = UnixFileAttributes.map_file_attributes(data['st_mode'])
        if 'timestamp' not in kwargs:
            if isinstance(self.timestamp, str):
                kwargs['timestamp'] = datetime.datetime.fromisoformat(self.timestamp)
            else:
                kwargs['timestamp'] = self.timestamp
        return IndalekoObject(**kwargs)

    def record(self) -> None:
        '''
        This function ingests the collector file and emits the data needed to
        upload to the database.
        '''
        self.load_collector_data_from_file()
        dir_data = []
        file_data = []
        # Step 1: build the normalized data
        for item in self.collector_data:
            self.input_count += 1
            try:
                obj = self.normalize_collector_data(item)
            except OSError as e:
                logging.error('Error normalizing data: %s', e)
                logging.error('Data: %s', item)
                self.error_count += 1
                continue
            if 'S_IFDIR' in obj.args['PosixFileAttributes']:
                if 'Path' not in obj:
                    logging.warning('Directory object does not have a path: %s', obj.to_json())
                    self.error_count += 1
                    continue # skip
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
            'Identifier' : self.linux_local_recorder_uuid,
            'Version' : '1.0',
        }
        source_id = IndalekoSourceIdentifierDataModel(**source)
        for item in dir_data + file_data:
            parent = item['Path']
            if parent not in dirmap:
                continue
            parent_id = dirmap[parent]
            dir_edges.append(BaseStorageRecorder.build_dir_contains_relationship(
                parent_id, item.args['ObjectIdentifier'], source_id)
            )
            self.edge_count += 1
            dir_edges.append(BaseStorageRecorder.build_contained_by_dir_relationship(
                item.args['ObjectIdentifier'], parent_id, source_id)
            )
            self.edge_count += 1
            volume = item.args.get('Volume')
            if volume:
                dir_edges.append(BaseStorageRecorder.build_volume_contains_relationship(
                    volume, item.args['ObjectIdentifier'], source_id)
                )
                self.edge_count += 1
                dir_edges.append(BaseStorageRecorder.build_contained_by_volume_relationship(
                    item.args['ObjectIdentifier'], volume, source_id)
                )
                self.edge_count += 1
            machine_id = item.args.get('machine_id')
            if machine_id:
                dir_edges.append(BaseStorageRecorder.build_machine_contains_relationship(
                    machine_id, item.args['ObjectIdentifier'], source_id)
                )
                self.edge_count += 1
                dir_edges.append(BaseStorageRecorder.build_contained_by_machine_relationship(
                    item.args['ObjectIdentifier'], machine_id, source_id)
                )
                self.edge_count += 1
        # Save the data to the recorder output file
        ic(self.output_file)
        self.write_data_to_file(dir_data + file_data, self.output_file)
        kwargs = {
            'machine' : self.machine_id,
            'platform' : self.platform,
            'service' : 'local_ingest',
            'collection' : IndalekoDBCollections.Indaleko_Relationship_Collection,
            'timestamp' : self.timestamp,
            'output_dir' : self.data_dir,
        }
        if hasattr(self, 'storage_description') and self.storage_description is not None:
            kwargs['storage'] = self.args['storage_description']
        edge_file = self.generate_output_file_name(**kwargs)
        self.write_data_to_file(dir_edges, edge_file)
        ic(edge_file)

    @staticmethod
    def generate_log_file_name(**kwargs) -> str:
        if 'service' not in kwargs:
            kwargs['service'] = 'ingest'
        target_dir = None
        if 'target_dir' in kwargs:
            target_dir = kwargs['target_dir']
            del kwargs['target_dir']
        if 'suffix' not in kwargs:
            kwargs['suffix'] = 'log'
        file_name = utils.misc.file_name_management.generate_file_name(**kwargs)
        if target_dir is not None:
            file_name = os.path.join(target_dir, file_name)
        return file_name


def main():
    '''
    This is the main handler for the Indaleko Linux Local Ingest
    service.
    '''
    logging_levels = IndalekoLogging.get_logging_levels()

    # step 1: find the collector file I'm going to use
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--configdir',
                            help=f'Path to the config directory (default is {utils.misc.directory_management.indaleko_default_config_dir})',
                            default=utils.misc.directory_management.indaleko_default_config_dir)
    pre_parser.add_argument('--logdir',
                            help=f'Path to the log directory (default is {utils.misc.directory_management.indaleko_default_log_dir})',
                            default=utils.misc.directory_management.indaleko_default_log_dir)
    pre_parser.add_argument('--loglevel',
                        choices=logging_levels,
                        default=logging.DEBUG,
                        help='Logging level to use.')
    pre_parser.add_argument('--datadir',
                            help=f'Path to the data directory (default is {utils.misc.directory_management.indaleko_default_data_dir})',
                            type=str,
                            default=utils.misc.directory_management.indaleko_default_data_dir)
    pre_args, _ = pre_parser.parse_known_args()
    # restrict to linux collector files.
    collector = IndalekoLinuxLocalStorageCollector(
        search_dir = pre_args.datadir,
        prefix=IndalekoLinuxLocalStorageCollector.linux_platform,
        suffix=IndalekoLinuxLocalStorageCollector.linux_local_collector_name,
        machine_config=machine_config,
    )
    collector_files = [f for f in IndalekoLinuxLocalStorageCollector.find_collector_files(pre_args.datadir) if IndalekoLinuxLocalRecorder.linux_platform in f]
    pre_parser.add_argument('--input',
                            choices=collector_files,
                            default=collector_files[-1],
                            help='Linux Local Collector file to ingest.')
    pre_args, _ = pre_parser.parse_known_args()
    collector_file_metadata = utils.misc.file_name_management.extract_keys_from_file_name(pre_args.input)
    timestamp = collector_file_metadata.get('timestamp',
                                          datetime.datetime.now(datetime.timezone.utc).isoformat())
    log_file_name = IndalekoLinuxLocalRecorder.generate_log_file_name(
        platform=collector_file_metadata['platform'],
        recorder=IndalekoLinuxLocalRecorder.linux_local_recorder,
        machine_id = collector_file_metadata['machine'],
        target_dir=pre_args.logdir,
        timestamp=timestamp,
        suffix='log')
    if os.path.exists(log_file_name):
        os.remove(log_file_name)
    logging.basicConfig(
        filename=log_file_name,
        level=pre_args.loglevel,
        format='%(asctime)s - %(levelname)s - %(message)s',
        force=True
    )
    logging.info('Processing %s ' , args.input)
    logging.info('Output file %s ' , output_file)
    logging.info(args)
    parser = argparse.ArgumentParser(parents=[pre_parser])
    parser.add_argument('--reset', action='store_true', help='Reset the service collection.')
    args = parser.parse_args()
    metadata = IndalekoLinuxLocalStorageCollector.extract_metadata_from_collector_file_name(args.input)
    machine_id = metadata['machine']
    if 'platform' in metadata:
        collector_platform = metadata['platform']
        if collector_platform != IndalekoLinuxLocalRecorder.linux_platform:
            print('Warning: platform of collector file ' +\
                  f'({collector_platform}) name does not match platform of collector ' +\
                    f'({IndalekoLinuxLocalRecorder.linux_platform}.)')
    storage = None
    if 'storage' in metadata:
        storage = metadata['storage']
    file_prefix = BaseStorageRecorder.default_file_prefix
    if 'file_prefix' in metadata:
        file_prefix = metadata['file_prefix']
    file_suffix = BaseStorageRecorder.default_file_suffix
    if 'file_suffix' in metadata:
        file_suffix = metadata['file_suffix']
    input_file = os.path.join(args.datadir, args.input)
    machine_id_hex = uuid.UUID(machine_id).hex
    config_files = [x for x in IndalekoLinuxMachineConfig.find_config_files(args.configdir) if machine_id_hex in x]
    if len(config_files) == 0:
        raise ValueError(f'No configuration files found for machine {machine_id}')
    config_file = os.path.join(args.configdir, config_files[-1])
    machine_config = IndalekoLinuxMachineConfig.load_config_from_file(config_file=config_file)
    recorder_args = {
        'machine_config' : machine_config,
        'machine_id' : machine_id,
        'timestamp' : timestamp,
        'platform' : IndalekoLinuxLocalStorageCollector.linux_platform,
        'recorder' : IndalekoLinuxLocalRecorder.linux_local_recorder,
        'file_prefix' : file_prefix,
        'file_suffix' : file_suffix,
        'data_dir' : args.datadir,
        'input_file' : input_file,
    }
    if storage is not None:
        recorder_args['storage_description'] = storage
    recorder = IndalekoLinuxLocalRecorder(**recorder_args)
    logging.info('Ingesting %s ' , args.input)
    recorder.record()

    perf_file_name = os.path.join(
        args.datadir,
        IndalekoPerformanceDataRecorder().generate_perf_file_name(
            platform=collector.windows_platform,
            service=collector.windows_local_collector_name,
            machine=machine_id.replace('-', ''),
        )
    )
    def extract_counters(**kwargs):
        ic(kwargs)
        recorder = kwargs.get('recorder')
        if recorder:
            return ic(recorder.get_counts())
        else:
            return {}
    def record_data(recorder : IndalekoWindowsLocalStorageRecorder):
        recorder.record()
    perf_data = IndalekoPerformanceDataCollector.measure_performance(
        record_data,
        source=IndalekoSourceIdentifierDataModel(
            Identifier=collector.service_identifier,
            Version = collector.service_version,
            Description=collector.service_description),
        description=collector.service_description,
        MachineIdentifier=None,
        process_results_func=extract_counters,
        input_file_name=None,
        output_file_name=output_file,
        recorder=recorder
    )
    if args.performance_db or args.performance_file:
        perf_recorder = IndalekoPerformanceDataRecorder()
        if args.performance_file:
            perf_recorder.add_data_to_file(perf_file_name, perf_data)
            ic('Performance data written to ', perf_file_name)
        if args.performance_db:
            perf_recorder.add_data_to_db(perf_data)
            ic('Performance data written to the database')


    for count_type, count_value in recorder.get_counts().items():
        logging.info('%s: %d', count_type, count_value)
    logging.info('Done')


if __name__ == '__main__':
    main()
