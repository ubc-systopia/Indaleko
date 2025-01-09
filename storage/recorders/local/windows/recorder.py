'''
This module handles processing and recording data from the Windows local data
collector.

Indaleko Windows Local Recorder
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
import inspect
import json
import logging
from pathlib import Path
import os
import uuid
import tempfile
import sys

from icecream import ic
from typing import Any, Union

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from db import IndalekoDBCollections, IndalekoServiceManager
from data_models import IndalekoSourceIdentifierDataModel
from perf.perf_collector import IndalekoPerformanceDataCollector
from perf.perf_recorder import IndalekoPerformanceDataRecorder
from platforms.windows.machine_config import IndalekoWindowsMachineConfig
from platforms.unix import UnixFileAttributes
from platforms.windows_attributes import IndalekoWindows
from storage import IndalekoObject
from storage.recorders.base import BaseStorageRecorder
from storage.recorders.data_model import IndalekoStorageRecorderDataModel
from storage.collectors.local.windows.collector import IndalekoWindowsLocalCollector
from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
from utils.cli.runner import IndalekoCLIRunner
import utils.misc.directory_management
from utils.misc.file_name_management import find_candidate_files
from utils.misc.data_management import encode_binary_data
from utils import IndalekoLogging
from perf.perf_collector import IndalekoPerformanceDataCollector
from perf.perf_recorder import IndalekoPerformanceDataRecorder
# pylint: enable=wrong-import-position

class IndalekoWindowsLocalStorageRecorder(BaseStorageRecorder):
    '''
    This class handles recording of metadata from the Indaleko Windows
    collector service.
    '''

    windows_local_recorder_uuid = '429f1f3c-7a21-463f-b7aa-cd731bb202b1'
    windows_local_recorder_service = {
        'service_name' : 'Windows Local Recorder',
        'service_description' : 'This service records metadata collected from the local filesystems of a Windows machine.',
        'service_version' : '1.0',
        'service_type' : IndalekoServiceManager.service_type_storage_recorder,
        'service_identifier' : windows_local_recorder_uuid,
    }

    windows_platform = IndalekoWindowsLocalCollector.windows_platform
    windows_local_recorder_name = 'fs_recorder'

    windows_recorder_data = IndalekoStorageRecorderDataModel(
        RecorderPlatformName=windows_platform,
        RecorderServiceName=windows_local_recorder_service['service_name'],
        RecorderServiceUUID=uuid.UUID(windows_local_recorder_uuid),
        RecorderServiceVersion=windows_local_recorder_service['service_version'],
        RecorderServiceDescription=windows_local_recorder_service['service_description'],
    )

    def __init__(self, **kwargs) -> None:
        assert 'machine_config' in kwargs, 'machine_config must be specified'
        self.machine_config = kwargs['machine_config']
        if 'machine_id' not in kwargs:
            kwargs['machine_id'] = self.machine_config.machine_id
        for key, value in self.windows_local_recorder_service.items():
            if key not in kwargs:
                kwargs[key] = value
        if 'platform' not in kwargs:
            kwargs['platform'] = IndalekoWindowsLocalStorageRecorder.windows_platform
        if 'recorder_data' not in kwargs:
            kwargs['recorder_data'] = IndalekoWindowsLocalStorageRecorder.windows_recorder_data
        super().__init__(**kwargs)


    def find_collector_files(self) -> list:
        '''This function finds the files to record:
            search_dir: path to the search directory
            prefix: prefix of the file to record
            suffix: suffix of the file to record (default is .json)
        '''
        if self.data_dir is None:
            raise ValueError('data_dir must be specified')
        return [x for x in find_candidate_files(
            [
                IndalekoWindowsLocalCollector.windows_platform,
                IndalekoWindowsLocalCollector.windows_local_collector_name
            ],
            self.data_dir)
        ]

    def normalize_collector_data(self, data: dict) -> IndalekoObject:
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
            'raw_data' : encode_binary_data(bytes(json.dumps(data).encode('utf-8'))),
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


    def record(self) -> None:
        '''
        This function processes and records the collector file and emits the data needed to
        upload to the database.
        '''
        self.load_collector_data_from_file()
        dir_data_by_path = {}
        dir_data = []
        file_data = []
        # Step 1: build the normalized data
        for item in self.collector_data:
            try:
                obj = self.normalize_collector_data(item)
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
            'Identifier' : self.windows_local_recorder_uuid,
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
            collection=IndalekoDBCollections.Indaleko_Object_Collection,
            file=self.output_file
        )
        logging.info('Load string: %s', load_string)
        print('Load string: ', load_string)
        temp_file_name = ""
        with tempfile.NamedTemporaryFile(dir=self.data_dir, delete=False) as tf:
            temp_file_name = tf.name
        kwargs={
            'machine' : self.machine_id,
            'platform' : self.platform,
            'service' : IndalekoWindowsLocalStorageRecorder.windows_local_recorder_name,
            'storage' : self.storage_description,
            'collection' : IndalekoDBCollections.Indaleko_Relationship_Collection,
            'timestamp' : self.timestamp,
            'output_dir' : self.data_dir,
        }
        edge_file = self.generate_output_file_name(**kwargs)
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
            collection=IndalekoDBCollections.Indaleko_Relationship_Collection,
            file=edge_file
        )
        logging.info('Load string: %s', load_string)
        print('Load string: ', load_string)


def old_main():
    '''
    This is the main handler for the Indaleko Windows Local Recorder
    service.
    '''
    logging_levels = IndalekoLogging.get_logging_levels()

    # step 1: find the machine configuration file
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--configdir', '-c',
                            help=f'Path to the config directory (default is {utils.misc.directory_management.indaleko_default_config_dir})',
                            default=utils.misc.directory_management.indaleko_default_config_dir)
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
                            help=f'Path to the data directory (default is {utils.misc.directory_management.indaleko_default_data_dir})',
                            type=str,
                            default=utils.misc.directory_management.indaleko_default_data_dir)
    pre_args, _ = pre_parser.parse_known_args()
    machine_config = IndalekoWindowsMachineConfig.load_config_from_file(config_file=default_config_file)
    collector = IndalekoWindowsLocalCollector(
        search_dir=pre_args.datadir,
        prefix=IndalekoWindowsLocalCollector.windows_platform,
        suffix=IndalekoWindowsLocalCollector.windows_local_collector_name,
        machine_config=machine_config
    )
    collector_files = collector.find_collector_files(pre_args.datadir)
    parser = argparse.ArgumentParser(parents=[pre_parser])
    parser.add_argument('--input',
                        choices=collector_files,
                        default=collector_files[-1],
                        help='Windows Local Collector file to process and record.')
    parser.add_argument('--reset', action='store_true', help='Reset the service collection.')
    parser.add_argument('--logdir',
                        help=f'Path to the log directory (default is {utils.misc.directory_management.indaleko_default_log_dir})',
                        default=utils.misc.directory_management.indaleko_default_log_dir)
    parser.add_argument('--loglevel',
                        choices=logging_levels,
                        default=logging.DEBUG,
                        help='Logging level to use.')
    parser.add_argument('--performance_file',
                        default=False,
                        action='store_true',
                        help='Record performance data to a file')
    parser.add_argument('--performance_db',
                        default=False,
                        action='store_true',
                        help='Record performance data to the database')
    args = parser.parse_args()
    collector_file_metadata = IndalekoWindowsLocalCollector.extract_metadata_from_collector_file_name(args.input)
    timestamp = collector_file_metadata.get('timestamp',
                             datetime.datetime.now(datetime.timezone.utc).isoformat())
    machine_id = 'unknown'
    if 'machine' in collector_file_metadata:
        if collector_file_metadata['machine'] != machine_config.machine_id:
            print('Warning: machine ID of collector file ' +\
                  f'({collector_file_metadata["machine"]}) does not match machine ID of recorder ' +\
                    f'({machine_config.machine_id})')
        machine_id = collector_file_metadata['machine']
    if 'timestamp' in collector_file_metadata:
        timestamp = collector_file_metadata['timestamp']
    if 'platform' in collector_file_metadata:
        collector_platform = collector_file_metadata['platform']
        if collector_platform != IndalekoWindowsLocalStorageRecorder.windows_platform:
            print('Warning: platform of collector file ' +\
                  f'({collector_platform}) name does not match platform of recorder ' +\
                    f'({IndalekoWindowsLocalStorageRecorder.windows_platform}.)')
    storage = 'unknown'
    if 'storage' in collector_file_metadata:
        storage = collector_file_metadata['storage']
    file_prefix = BaseStorageRecorder.default_file_prefix
    if 'file_prefix' in collector_file_metadata:
        file_prefix = collector_file_metadata['file_prefix']
    file_suffix = BaseStorageRecorder.default_file_suffix
    if 'file_suffix' in collector_file_metadata:
        file_suffix = collector_file_metadata['file_suffix']
    input_file = os.path.join(args.datadir, args.input)
    recorder = IndalekoWindowsLocalStorageRecorder(
        machine_config=machine_config,
        machine_id = machine_id,
        timestamp=timestamp,
        platform=IndalekoWindowsLocalCollector.windows_platform,
        recorder = IndalekoWindowsLocalStorageRecorder.windows_local_recorder_name,
        storage_description = storage,
        file_prefix = file_prefix,
        file_suffix = file_suffix,
        data_dir=args.datadir,
        input_file=input_file,
        log_dir=args.logdir
    )
    output_file = recorder.generate_file_name()
    log_file_name = recorder.generate_file_name(
        platform=collector_file_metadata['platform'],
        recorder=IndalekoWindowsLocalStorageRecorder.windows_local_recorder_name,
        machine_id=collector_file_metadata['machine'],
        target_dir=args.logdir,
        timestamp=timestamp,
        suffix='.log')
    logging.basicConfig(filename=os.path.join(log_file_name),
                                level=logging.DEBUG,
                                format='%(asctime)s - %(levelname)s - %(message)s',
                                force=True)
    logging.info('Processing %s ' , args.input)
    logging.info('Output file %s ' , output_file)
    logging.info(args)
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
    total = 0
    for count_type, count_value in recorder.get_counts().items():
        logging.info('%s: %d', count_type, count_value)
        total += count_value
    logging.info('Total: %d', total)
    logging.info('Done')

class local_recorder_mixin(IndalekoBaseCLI.default_handler_mixin):
    '''This is the mixin for the local recorder'''
    @staticmethod
    def load_machine_config(keys: dict[str, str]) -> IndalekoWindowsMachineConfig:
        '''Load the machine configuration'''
        ic(f'local_collector_mixin.load_machine_config: {keys}')
        if keys.get('debug'):
            ic(f'local_collector_mixin.load_machine_config: {keys}')
        if 'machine_config_file' not in keys:
            raise ValueError(f'{inspect.currentframe().f_code.co_name}: machine_config_file must be specified')
        offline = keys.get('offline', False)
        return IndalekoWindowsMachineConfig.load_config_from_file(
            config_file=str(keys['machine_config_file']),
            offline=offline)

@staticmethod
def local_run(keys: dict[str, str]) -> Union[dict, None]:
    '''Run the collector'''
    args = keys['args'] # must be there.
    cli = keys['cli'] # must be there.
    config_data = cli.get_config_data()
    debug = hasattr(args, 'debug') and args.debug
    if debug:
        ic(config_data)
    # recorders have the machine_id so they need to find the
    # matching machine configuration file.
    kwargs = {
        'machine_config': cli.handler_mixin.load_machine_config(
            {
                'machine_config_file' : str(Path(args.configdir) / args.machine_config),
                'offline' : args.offline
            }
        ),
        'timestamp': config_data['Timestamp'],
        'path': args.path,
        'offline': args.offline
    }
    def record(recorder : IndalekoWindowsLocalStorageRecorder):
        data = recorder.collect()
        output_file = Path(args.datadir) / args.outputfile
        recorder.write_data_to_file(data, str(output_file))
    def extract_counters(**kwargs):
        recorder = kwargs.get('recorder')
        if recorder:
            return recorder.get_counts()
        else:
            return {}
    recorder = IndalekoWindowsLocalStorageRecorder(**kwargs)
    perf_data = IndalekoPerformanceDataCollector.measure_performance(
        record,
        source=IndalekoSourceIdentifierDataModel(
            Identifier=recorder.service_identifier,
            Version = recorder.service_version,
            Description=recorder.service_description),
        description=recorder.service_description,
        MachineIdentifier=uuid.UUID(kwargs['machine_config'].machine_id),
        process_results_func=extract_counters,
        input_file_name=None,
        output_file_name=str(Path(args.datadir) / args.outputfile),
        recorder=recorder
    )
    if args.performance_db or args.performance_file:
        perf_recorder = IndalekoPerformanceDataRecorder()
        if args.performance_file:
            perf_file = str(Path(args.datadir) / config_data['PerformanceDataFile'])
            perf_recorder.add_data_to_file(perf_file, perf_data)
            if (debug):
                ic('Performance data written to ', config_data['PerformanceDataFile'])
        if args.performance_db:
            perf_recorder.add_data_to_db(perf_data)
            if (debug):
                ic('Performance data written to the database')

def main():
    '''This is the CLI handler for the Windows local storage collector.'''
    runner = IndalekoCLIRunner(
        cli_data=IndalekoBaseCliDataModel(
            Service=IndalekoWindowsLocalStorageRecorder.windows_local_recorder_name,
            InputFileKeys={
                'plt' : IndalekoWindowsLocalCollector.windows_platform,
                'svc' : IndalekoWindowsLocalCollector.windows_local_collector_name,
            }
        ),
        handler_mixin=local_recorder_mixin,
        Run=local_run,
    )
    runner.run()


if __name__ == '__main__':
    main()
