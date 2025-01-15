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
from typing import Any, Union, Callable

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
from platforms.machine_config import IndalekoMachineConfig
from platforms.windows.machine_config import IndalekoWindowsMachineConfig
from platforms.unix import UnixFileAttributes
from platforms.windows_attributes import IndalekoWindows
from storage import IndalekoObject
from storage.recorders.base import BaseStorageRecorder
from storage.recorders.data_model import IndalekoStorageRecorderDataModel
from storage.recorders.local.local_base import BaseLocalStorageRecorder
from storage.collectors import BaseStorageCollector
from storage.collectors.local.windows.collector import IndalekoWindowsLocalStorageCollector
from utils.decorators import type_check
from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
from utils.cli.runner import IndalekoCLIRunner
from utils.misc.file_name_management import find_candidate_files
from utils.misc.data_management import encode_binary_data
from perf.perf_collector import IndalekoPerformanceDataCollector
from perf.perf_recorder import IndalekoPerformanceDataRecorder
# pylint: enable=wrong-import-position

class IndalekoWindowsLocalStorageRecorder(BaseLocalStorageRecorder):
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

    windows_platform = IndalekoWindowsLocalStorageCollector.windows_platform
    windows_local_recorder_name = 'fs_recorder'

    recorder_data = IndalekoStorageRecorderDataModel(
        RecorderPlatformName=windows_platform,
        RecorderServiceName=windows_local_recorder_name,
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
        super().__init__(**kwargs)
        self.output_file = kwargs.get('output_file', self.generate_file_name())
        self.source = {
            'Identifier' : self.windows_local_recorder_uuid,
            'Version' : self.windows_local_recorder_service['service_version'],
        }
        self.dir_data_by_path = {}
        self.dir_data = []
        self.file_data = []
        self.dirmap = {}
        self.dir_edges = []


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
                IndalekoWindowsLocalStorageCollector.windows_platform,
                IndalekoWindowsLocalStorageCollector.windows_local_collector_name
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
            if 'S_IFDIR' in obj.args['PosixFileAttributes'] or \
               'FILE_ATTRIBUTE_DIRECTORY' in obj.args['WindowsFileAttributes']:
                if 'Path' not in obj.indaleko_object.Record.Attributes:
                    logging.warning('Directory object does not have a path: %s', obj.serialize())
                    continue # skip
                self.dir_data_by_path[os.path.join(obj['Path'], obj['Volume GUID'])] = obj
                self.dir_data.append(obj)
                self.dir_count += 1
            else:
                self.file_data.append(obj)
                self.file_count += 1

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
            Identifier = self.windows_local_recorder_uuid,
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

    def record_data_in_file(
            data : list,
            dir_name : Union[Path, str],
            preferred_file_name : Union[Path, str, None] = None) -> str:
        '''
        Record the specified data in a file.

        Inputs:
            - data: The data to record
            - preferred_file_name: The preferred file name (if any)

        Returns:
            - The name of the file where the data was recorded

        Notes:
            A temporary file is always created to hold the data, and then it is renamed to the
            preferred file name if it is provided.
        '''
        temp_file_name = ""
        with tempfile.NamedTemporaryFile(dir=dir_name, delete=False) as tf:
            temp_file_name = tf.name
        BaseStorageRecorder.write_data_to_file(data, temp_file_name)
        if preferred_file_name is None:
            return temp_file_name
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
        return preferred_file_name

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
            'service' : IndalekoWindowsLocalStorageRecorder.windows_local_recorder_name,
            'storage' : self.storage_description,
            'collection' : IndalekoDBCollections.Indaleko_Object_Collection,
            'timestamp' : self.timestamp,
            'output_dir' : self.data_dir,
        }
        self.output_object_file = self.generate_output_file_name(**kwargs)
        kwargs['collection'] = IndalekoDBCollections.Indaleko_Relationship_Collection
        self.output_edge_file = self.generate_output_file_name(**kwargs)

    @staticmethod
    def write_object_data_to_file(recorder : 'IndalekoWindowsLocalStorageRecorder') -> None:
        '''Write the object data to a file'''
        data_file_name = IndalekoWindowsLocalStorageRecorder.record_data_in_file(
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

    @staticmethod
    def write_edge_data_to_file(recorder : 'IndalekoWindowsLocalStorageRecorder') -> None:
        '''Write the edge data to a file'''
        data_file_name = IndalekoWindowsLocalStorageRecorder.record_data_in_file(
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


def main():
    '''This is the CLI handler for the Windows local storage collector.'''
    BaseLocalStorageRecorder.local_recorder_runner(
        IndalekoWindowsLocalStorageCollector,
        IndalekoWindowsLocalStorageRecorder,
        IndalekoWindowsMachineConfig
    )

if __name__ == '__main__':
    main()
