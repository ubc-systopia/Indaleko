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
from data_models import IndalekoRecordDataModel
from db import IndalekoServiceManager
from platforms.linux.machine_config import IndalekoLinuxMachineConfig
from platforms.unix import UnixFileAttributes
from storage import IndalekoObject
from storage.collectors.local.linux.collector import IndalekoLinuxLocalStorageCollector
from storage.recorders.base import BaseStorageRecorder
from storage.recorders.local.local_base import BaseLocalStorageRecorder
from utils.misc.data_management import encode_binary_data
from storage.recorders.data_model import IndalekoStorageRecorderDataModel
# pylint: enable=wrong-import-position


class IndalekoLinuxLocalStorageRecorder(BaseLocalStorageRecorder):
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

    recorder_data = IndalekoStorageRecorderDataModel(
        RecorderPlatformName = linux_platform,
        RecorderServiceName = linux_local_recorder,
        RecorderServiceUUID = uuid.UUID(linux_local_recorder_uuid),
        RecorderServiceVersion = linux_local_recorder_service['service_version'],
        RecorderServiceDescription = linux_local_recorder_service['service_description'],
    )


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
            kwargs['platform'] = IndalekoLinuxLocalStorageRecorder.linux_platform
        if 'recorder' not in kwargs:
            kwargs['recorder'] = IndalekoLinuxLocalStorageRecorder.linux_local_recorder
        for key, value in self.linux_local_recorder_service.items():
            if key not in kwargs:
                kwargs[key] = value
        super().__init__(**kwargs)
        self.input_file = kwargs['input_file']
        if 'output_file' not in kwargs:
            self.output_file = self.generate_file_name()
        else:
            self.output_file = kwargs['output_file']
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
            'URI': data['URI'],
            'ObjectIdentifier': oid,
            'Timestamps': timestamps,
            'Size': data['st_size'],
            'Machine': self.machine_config.machine_id,
            'SemanticAttributes': self.map_posix_storage_attributes_to_semantic_attributes(data),
        }
        if 'st_mode' in data:
            kwargs['PosixFileAttributes'] = UnixFileAttributes.map_file_attributes(data['st_mode'])
        if 'st_ino' in data:
            kwargs['LocalIdentifier'] = str(data['st_ino'])
        if 'Name' in data:
            kwargs['Label'] = data['Name']
        if 'Path' in data:
            kwargs['LocalPath'] = data['Path']
        if 'timestamp' not in kwargs:
            if isinstance(self.timestamp, str):
                kwargs['timestamp'] = datetime.datetime.fromisoformat(self.timestamp)
            else:
                kwargs['timestamp'] = self.timestamp
        kwargs['Record'] = IndalekoRecordDataModel(
            SourceIdentifier=self.source,
            Timestamp=kwargs['timestamp'],
            Data=encode_binary_data(bytes(json.dumps(data).encode('utf-8')))
        )
        return IndalekoObject(**kwargs)


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
    '''This is the CLI handler for the Linux local storage recorder.'''
    BaseLocalStorageRecorder.local_recorder_runner(
        IndalekoLinuxLocalStorageCollector,
        IndalekoLinuxLocalStorageRecorder,
        IndalekoLinuxMachineConfig
    )

if __name__ == '__main__':
    main()
