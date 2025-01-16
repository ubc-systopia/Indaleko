"""
This is the generic class for an Indaleko Local Storage Recorder.

An Indaleko local storage recorder takes information about some (or all) of the data that is stored in
local file system(s) on this machine. It is derived from the generic base for all
recorders, but includes support for local-specific options.

Project Indaleko
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
"""

import argparse
import inspect
import json
import jsonlines
import logging
import os
from pathlib import Path
import sys
import tempfile
import uuid

from typing import Union, Callable, Any

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models import IndalekoSourceIdentifierDataModel
from db import IndalekoDBCollections
from perf.perf_collector import IndalekoPerformanceDataCollector
from perf.perf_recorder import IndalekoPerformanceDataRecorder
from platforms.machine_config import IndalekoMachineConfig
from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
from utils.cli.runner import IndalekoCLIRunner
from utils.decorators import type_check
from storage import IndalekoObject
from storage.collectors import BaseStorageCollector
from storage.recorders import BaseStorageRecorder
# pylint: enable=wrong-import-position

class BaseLocalStorageRecorder(BaseStorageRecorder):
    '''This is the base class for all local storage recorders in Indaleko.'''

    def __init__(self, **kwargs):
        '''This is the constructor for the base local storage recorder.'''
        ic(kwargs)
        if 'args' in kwargs:
            self.args = kwargs['args']
            self.output_type = getattr(self.args, 'output_type', 'file')
        else:
            self.args = None
            self.output_type = 'file'
        if 'storage' in kwargs:
            self.storage_description = kwargs['storage']
        super().__init__(**kwargs)
        self.dir_data_by_path = {}
        self.dir_data = []
        self.file_data = []
        self.dirmap = {}
        self.dir_edges = []
        self.collector_data = []

    def find_collector_files(self) -> list:
        '''This function should be overridden: it is used to find the collector files for the recorder.'''
        raise NotImplementedError('This function must be overridden by the derived class')

    def load_collector_data_from_file(self : 'BaseLocalStorageRecorder') -> None:
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



    @staticmethod
    def load_machine_config(keys: dict[str, str]) -> IndalekoMachineConfig:
        '''Load the machine configuration'''
        if keys.get('debug'):
            ic(f'local_recorder_mixin.load_machine_config: {keys}')
        if 'machine_config_file' not in keys:
            raise ValueError(f'{inspect.currentframe().f_code.co_name}: machine_config_file must be specified')
        offline = keys.get('offline', False)
        platform_class = keys['class'] # must exist
        return platform_class.load_config_from_file(
            config_file=str(keys['machine_config_file']),
            offline=offline)

    @staticmethod
    @type_check
    def get_additional_parameters(pre_parser : argparse.ArgumentParser) -> argparse.ArgumentParser:
        '''This function adds common switches for local storage recorders to a parser.'''
        default_output_type = 'file'
        output_type_choices = [default_output_type]
        output_type_help = 'Output type: file  = write to a file, '
        output_type_choices.append('incremental')
        output_type_help += 'incremental = add new entries, update changed entries in database, '
        output_type_choices.append('bulk')
        output_type_help += 'bulk = write all entries to the database using the bulk uploader interface, '
        output_type_choices.append('docker')
        output_type_help += 'docker = copy to the docker volume'
        output_type_help += f' (default={default_output_type})'
        pre_parser.add_argument('--output_type',
                                choices=output_type_choices,
                                default=default_output_type,
                                help=output_type_help)
        pre_parser.add_argument('--arangoimport',
                                default=False,
                                help='Use arangoimport to load data (default=False)',
                                action='store_true')
        pre_parser.add_argument('--bulk',
                                default=False,
                                help='Use bulk loader to load data (default=False)',
                                action='store_true')
        return pre_parser

    @staticmethod
    def get_local_storage_recorder() -> 'BaseLocalStorageRecorder':
        '''This function should be overridden: it is used to create the appropriate local storage recorder.'''
        raise NotImplementedError('This function must be overridden by the derived class')

    @staticmethod
    def execute_command(command : str) -> None:
        '''Execute a command'''
        result = os.system(command)
        logging.info('Command %s result: %d', command, result)
        print(f'Command {command} result: {result}')

    class local_recorder_mixin(IndalekoBaseCLI.default_handler_mixin):
        '''This is the mixin for the local recorder'''
        @staticmethod
        def get_pre_parser() -> Union[argparse.ArgumentParser, None]:
            '''This method is used to get the pre-parser'''
            parser = argparse.ArgumentParser(add_help=False)
            parser.add_argument('--path',
                                help='Path to the directory from which to collect metadata',
                                type=str,
                                default=os.path.expanduser('~'))
            return parser

        @staticmethod
        def load_machine_config(keys : dict[str, str]) -> IndalekoMachineConfig:
            assert 'class' in keys, '(machine config) class must be specified'
            return BaseLocalStorageRecorder.load_machine_config(keys)

        @staticmethod
        def get_additional_parameters(pre_parser):
            '''This method is used to add additional parameters to the parser.'''
            return BaseLocalStorageRecorder.get_additional_parameters(pre_parser)


    @staticmethod
    def local_run(keys: dict[str, str]) -> Union[dict, None]:
        '''Run the recorder'''
        args = keys['args'] # must be there.
        cli = keys['cli'] # must be there.
        config_data = cli.get_config_data()
        debug = hasattr(args, 'debug') and args.debug
        if debug:
            ic(config_data)
        recorder_class = keys['parameters']['RecorderClass']
        machine_config_class = keys['parameters']['MachineConfigClass']
        # collector_class = keys['parameters']['CollectorClass'] # unused for now
        # recorders have the machine_id so they need to find the
        # matching machine configuration file.
        kwargs = {
            'machine_config': cli.handler_mixin.load_machine_config(
                {
                    'machine_config_file' : str(Path(args.configdir) / args.machine_config),
                    'offline' : args.offline,
                    'class' : machine_config_class
                }
            ),
            'timestamp': config_data['Timestamp'],
            'input_file' : str(Path(args.datadir) / args.inputfile),
            'offline': args.offline,
            'args' : args,
        }
        if 'InputFileKeys' in config_data and \
            'storage' in config_data['InputFileKeys'] and \
            config_data['InputFileKeys']['storage']:
            kwargs['storage_description'] = config_data['InputFileKeys']['storage']
        def record(recorder : BaseLocalStorageRecorder):
            recorder.record()
        def extract_counters(**kwargs):
            recorder = kwargs.get('recorder')
            if recorder:
                return recorder.get_counts()
            else:
                return {}
        recorder = recorder_class(**kwargs)
        def capture_performance(
            task_func : Callable[..., Any],
            output_file_name : Union[Path, str] = None
        ):
            perf_data = IndalekoPerformanceDataCollector.measure_performance(
                task_func,
                source=IndalekoSourceIdentifierDataModel(
                    Identifier=recorder.get_recorder_service_uuid(),
                    Version = recorder.get_recorder_service_version(),
                    Description=recorder.get_recorder_service_description()
                ),
                description=recorder.get_recorder_service_description(),
                MachineIdentifier=uuid.UUID(kwargs['machine_config'].machine_id),
                process_results_func=extract_counters,
                input_file_name=str(Path(args.datadir) / args.inputfile),
                output_file_name=output_file_name,
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

        # Step 1: normalize the data and gather the performance.
        if args.debug:
            ic('Normalizing data')
        capture_performance(record)
        # Step 2: record the time to save the object data.
        if args.debug:
            ic('Writing object data to file')
        capture_performance(recorder.write_object_data_to_file, args.outputfile)
        # Step 3: record the time to save the edge data.
        if args.debug:
            ic('Writing edge data to file')
        capture_performance(recorder.write_edge_data_to_file, recorder.output_edge_file)

        if args.arangoimport and args.bulk:
            ic('Warning: both arangoimport and bulk upload specified.  Using arangoimport ONLY.')
        if args.arangoimport:
            # Step 4: upload the data to the database using the arangoimport utility
            if args.debug:
                ic('Using arangoimport to load object data')
            capture_performance(recorder.arangoimport_object_data)
            if args.debug:
                ic('Using arangoimport to load relationship data')
            capture_performance(recorder.arangoimport_relationship_data)
        elif args.bulk:
            # Step 5: upload the data to the database using the bulk uploader
            if args.debug:
                ic('Using bulk uploader to load object data')
            capture_performance(recorder.bulk_upload_object_data)
            if args.debug:
                ic('Using bulk uploader to load relationship data')
            capture_performance(recorder.bulk_upload_relationship_data)

    @staticmethod
    def local_recorder_runner(
        collector_class: BaseStorageCollector,
        recorder_class : BaseStorageRecorder,
        machine_config_class : IndalekoMachineConfig) -> None:
        '''This is the CLI handler for local storage recorders.'''
        runner = IndalekoCLIRunner(
            cli_data=IndalekoBaseCliDataModel(
                Service=recorder_class.get_recorder_service_name(),
                InputFileKeys={
                    'plt' : collector_class.get_collector_platform_name(),
                    'svc' : collector_class.get_collector_service_name(),
                },
            ),
            handler_mixin=recorder_class.local_recorder_mixin,
            Run=recorder_class.local_run,
            RunParameters={
                'CollectorClass' : collector_class,
                'MachineConfigClass' : machine_config_class,
                'RecorderClass' : recorder_class
            }
        )
        runner.run()

    @staticmethod
    def write_object_data_to_file(recorder : 'BaseLocalStorageRecorder') -> None:
        '''Write the object data to a file'''
        data_file_name, count = recorder.record_data_in_file(
            recorder.dir_data + recorder.file_data,
            recorder.data_dir,
            recorder.output_object_file,
        )
        recorder.object_data_load_string = recorder.build_load_string(
            collection=IndalekoDBCollections.Indaleko_Object_Collection,
            file=data_file_name
        )
        logging.info('Load string: %s', recorder.object_data_load_string)
        print('Load string: ', recorder.object_data_load_string)
        if hasattr(recorder, 'output_count'): # should be there
            recorder.output_count += count

    @staticmethod
    def write_edge_data_to_file(recorder : 'BaseLocalStorageRecorder') -> int:
        '''Write the edge data to a file'''
        data_file_name, count = recorder.record_data_in_file(
            recorder.dir_edges,
            recorder.data_dir,
            recorder.output_edge_file
        )
        recorder.relationship_data_load_string = recorder.build_load_string(
            collection=IndalekoDBCollections.Indaleko_Relationship_Collection,
            file=data_file_name
        )
        logging.info('Load string: %s', recorder.relationship_data_load_string)
        print('Load string: ', recorder.relationship_data_load_string)
        if hasattr(recorder, 'edge_count'):
            recorder.edge_count += count

    @staticmethod
    def record_data_in_file(
            data : list,
            dir_name : Union[Path, str],
            preferred_file_name : Union[Path, str, None] = None) -> tuple[str,int]:
        '''
        Record the specified data in a file.

        Inputs:
            - data: The data to record
            - preferred_file_name: The preferred file name (if any)

        Returns:
            - The name of the file where the data was recorded
            - The number of entries that were written to the file

        Notes:
            A temporary file is always created to hold the data, and then it is renamed to the
            preferred file name if it is provided.
        '''
        temp_file_name = ""
        with tempfile.NamedTemporaryFile(dir=dir_name, delete=False) as tf:
            temp_file_name = tf.name
        count = BaseStorageRecorder.write_data_to_file(data, temp_file_name)
        if preferred_file_name is None:
            return temp_file_name, count
        # try to rename the file
        try:
            if os.path.exists(preferred_file_name):
                os.remove(preferred_file_name)
            os.rename(temp_file_name, preferred_file_name)
        except (
            FileNotFoundError,
            PermissionError,
            FileExistsError,
            OSError,
        ) as e:
            logging.error(
                'Unable to rename temp file %s to output file %s',
                temp_file_name,
                preferred_file_name
            )
            print(f'Unable to rename temp file {temp_file_name} to output file {preferred_file_name}')
            print(f'Error: {e}')
            preferred_file_name=temp_file_name
        return preferred_file_name, count

    def get_object_path(self : 'BaseLocalStorageRecorder', obj : IndalekoObject):
        '''Given an Indaleko object, return a valid local path to the object'''
        return obj['Path'] # default is no change


    def is_object_directory(self : 'BaseLocalStorageRecorder', obj: IndalekoObject) -> bool:
        '''Return True if the object is a directory'''
        return 'S_IFDIR' in obj.args['PosixFileAttributes']


    def normalize(self) -> None:
        '''Normalize the data from the collector'''
        self.load_collector_data_from_file()
        # Step 1: build the normalized data
        for item in self.collector_data:
            try:
                obj = self.normalize_collector_data(item)
            except OSError as e:
                logging.error('Error normalizing data: %s', e)
                logging.error('Data: %s', item)
                self.error_count += 1
                continue
            if self.is_object_directory(obj):
                if 'Path' not in obj.indaleko_object.Record.Attributes:
                    logging.warning('Directory object does not have a path: %s', obj.serialize())
                    continue # skip
                self.dir_data_by_path[self.get_object_path(obj)] = obj
                self.dir_data.append(obj)
                self.dir_count += 1
            else:
                self.file_data.append(obj)
                self.file_count += 1

    def record(self) -> None:
        '''
        This function processes and records the collector file and emits the data needed to
        upload to the database.
        '''
        self.normalize()
        assert len(self.dir_data) + len(self.file_data) > 0, 'No data to record'
        self.build_dirmap()
        self.build_edges()
        kwargs={
            'machine' : self.machine_id,
            'platform' : self.platform,
            'service' : self.recorder_data.RecorderServiceName,
            'collection' : IndalekoDBCollections.Indaleko_Object_Collection,
            'timestamp' : self.timestamp,
            'output_dir' : self.data_dir,
        }
        if self.storage_description:
            kwargs['storage'] = self.storage_description

        self.output_object_file = self.generate_output_file_name(**kwargs)
        kwargs['collection'] = IndalekoDBCollections.Indaleko_Relationship_Collection
        self.output_edge_file = self.generate_output_file_name(**kwargs)

    def build_dirmap(self) -> None:
        '''This function builds the directory/file map'''
        for item in self.dir_data:
            fqp = os.path.join(item['Path'], item['Name'])
            identifier = item.args['ObjectIdentifier']
            self.dirmap[fqp] = identifier

    def build_edges(self) -> None:
        '''Build the edges between files and directories.'''
        # TODO: this should be abstracted out to allow
        # moving this into the base class.
        source_id = IndalekoSourceIdentifierDataModel(
            Identifier = str(self.recorder_data.RecorderServiceUUID),
            Version='1.0',
        )
        for item in self.dir_data + self.file_data:
            parent = item['Path']
            if parent not in self.dirmap:
                continue
            parent_id = self.dirmap[parent]
            self.dir_edges.append(BaseStorageRecorder.build_dir_contains_relationship(
                parent_id, item.args['ObjectIdentifier'], source_id)
            )
            self.edge_count += 1
            self.dir_edges.append(BaseStorageRecorder.build_contained_by_dir_relationship(
                item.args['ObjectIdentifier'], parent_id, source_id)
            )
            self.edge_count += 1
            volume = item.args.get('Volume')
            if volume:
                self.dir_edges.append(BaseStorageRecorder.build_volume_contains_relationship(
                    volume, item.args['ObjectIdentifier'], source_id)
                )
                self.edge_count += 1
                self.dir_edges.append(BaseStorageRecorder.build_contained_by_volume_relationship(
                    item.args['ObjectIdentifier'], volume, source_id)
                )
                self.edge_count += 1
            machine_id = item.args.get('machine_id')
            if machine_id:
                self.dir_edges.append(BaseStorageRecorder.build_machine_contains_relationship(
                    machine_id, item.args['ObjectIdentifier'], source_id)
                )
                self.edge_count += 1
                self.dir_edges.append(BaseStorageRecorder.build_contained_by_machine_relationship(
                    item.args['ObjectIdentifier'], machine_id, source_id)
                )
                self.edge_count += 1


    @staticmethod
    def arangoimport_object_data(recorder : 'IndalekoWindowsLocalStorageRecorder') -> None:
        '''Import the object data into the database'''
        if recorder.object_data_load_string is None:
            raise ValueError('object_data_load_string must be set')
        recorder.execute_command(recorder.object_data_load_string)


    @staticmethod
    def arangoimport_relationship_data(recorder : 'IndalekoWindowsLocalStorageRecorder') -> None:
        '''Import the relationship data into the database'''
        if recorder.relationship_data_load_string is None:
            raise ValueError('relationship_data_load_string must be set')
        recorder.execute_command(recorder.relationship_data_load_string)


    @staticmethod
    def bulk_upload_object_data(recorder : 'IndalekoWindowsLocalStorageRecorder') -> None:
        '''Bulk upload the object data to the database'''
        raise NotImplementedError('bulk_upload_object_data must be implemented')


    @staticmethod
    def bulk_upload_relationship_data(recorder : 'IndalekoWindowsLocalStorageRecorder') -> None:
        '''Bulk upload the relationship data to the database'''
        raise NotImplementedError('bulk_upload_relationship_data must be implemented')
