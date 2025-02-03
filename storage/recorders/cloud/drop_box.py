'''
IndalekoDropboxRecorder.py

This script is used to ingest the files that have been indexed from Dropbox.  It
will create a JSONL file with the ingested metadata suitable for uploading to
the Indaleko database.

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
'''
import json
import os
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
from db import IndalekoServiceManager
from platforms.unix import UnixFileAttributes
from platforms.windows_attributes import IndalekoWindows
from storage import IndalekoObject
from storage.collectors.cloud.drop_box import IndalekoDropboxCloudStorageCollector
from storage.recorders.data_model import IndalekoStorageRecorderDataModel
from storage.recorders.cloud.cloud_base import BaseCloudStorageRecorder
from utils.misc.file_name_management import find_candidate_files, extract_keys_from_file_name
from utils.misc.data_management import encode_binary_data
# pylint: enable=wrong-import-position


class IndalekoDropboxCloudStorageRecorder(BaseCloudStorageRecorder):
    '''
    This class handles ingestion of metadata from the Indaleko Dropbox indexer.
    '''

    dropbox_recorder_uuid = '389ce9e0-3924-4cd1-be8d-5dc4b268e668'
    dropbox_recorder_service = {
        'service_name': 'Dropbox Recorder',
        'service_description': 'This service records metadata collected from Dropbox.',
        'service_version': '1.0',
        'service_type': IndalekoServiceManager.service_type_storage_recorder,
        'service_identifier': dropbox_recorder_uuid,
    }

    dropbox_platform = IndalekoDropboxCloudStorageCollector.dropbox_platform
    dropbox_recorder = 'recorder'

    recorder_data = IndalekoStorageRecorderDataModel(
        RecorderPlatformName=dropbox_platform,
        RecorderServiceName=dropbox_recorder,
        RecorderServiceUUID=uuid.UUID(dropbox_recorder_uuid),
        RecorderServiceVersion=dropbox_recorder_service['service_version'],
        RecorderServiceDescription=dropbox_recorder_service['service_description'],
    )

    def __init__(self, **kwargs) -> None:
        '''Build a new Dropbox recorder.'''
        for key, value in self.dropbox_recorder_service.items():
            if key not in kwargs:
                kwargs[key] = value
        if 'platform' not in kwargs:
            kwargs['platform'] = self.dropbox_platform
        if 'recorder' not in kwargs:
            kwargs['recorder'] = self.dropbox_recorder
        if 'user_id' not in kwargs:
            assert 'input_file' in kwargs
            keys = extract_keys_from_file_name(kwargs['input_file'])
            assert 'userid' in keys, f'userid not found in input file name: {kwargs["input_file"]}'
            self.user_id = keys['userid']
        else:
            self.user_id = kwargs['user_id']
        super().__init__(**kwargs)
        self.output_file = kwargs.get('output_file', self.generate_file_name())
        self.source = {
            'Identifier': self.dropbox_recorder_uuid,
            'Version': self.dropbox_recorder_service['service_version'],
        }
        self.dir_data.append(self.build_dummy_root_dir_entry())

    def build_dummy_root_dir_entry(self) -> IndalekoObject:
        '''This is used to build a dummy root directory object.'''
        dummy_attributes = {
            'Indexer': IndalekoDropboxCloudStorageCollector.indaleko_dropbox_collector_uuid,
            'ObjectIdentifier': str(uuid.uuid4()),
            'FolderMetadata': True,
            'Metadata': True,
            'path_lower': '/',
            'path_display': '/',
            'name': '',
            'user_id': self.user_id
        }
        return self.normalize_collector_data(dummy_attributes)

    def find_collector_files(self) -> list:
        '''This function finds the files produced by the collector.'''
        if self.data_dir is None:
            raise ValueError('data_dir must be specified')
        candidates = find_candidate_files(
            [
                IndalekoDropboxCloudStorageCollector.dropbox_platform,
                IndalekoDropboxCloudStorageCollector.dropbox_collector_name
            ],
            self.data_dir
        )
        if self.debug:
            ic(candidates)
        return candidates

    def normalize_collector_data(self, data: dict) -> IndalekoObject:
        '''
        Given some metadata, this will create a record that can be inserted into the
        Object collection.
        '''
        if data is None:
            raise ValueError('Data cannot be None')
        if not isinstance(data, dict):
            raise ValueError('Data must be a dictionary')
        if 'ObjectIdentifier' not in data:
            raise ValueError('Data must contain an ObjectIdentifier')
        if 'user_id' not in data:
            data['user_id'] = self.user_id
        timestamps = []
        size = 0
        if 'FolderMetadata' in data:
            unix_file_attributes = UnixFileAttributes.FILE_ATTRIBUTES['S_IFDIR']
            windows_file_attributes = IndalekoWindows.FILE_ATTRIBUTES['FILE_ATTRIBUTE_DIRECTORY']
        if 'FileMetadata' in data:
            unix_file_attributes = UnixFileAttributes.FILE_ATTRIBUTES['S_IFREG']
            windows_file_attributes = IndalekoWindows.FILE_ATTRIBUTES['FILE_ATTRIBUTE_NORMAL']
        # ArangoDB is VERY fussy about the timestamps.  If there is no TZ
        # data, it will fail the schema validation.
        timestamps = [
            {
                'Label': IndalekoObject.MODIFICATION_TIMESTAMP,
                'Value': data['client_modified'],
                'Description': 'Client Modified'
            },
            {
                'Label': IndalekoObject.CHANGE_TIMESTAMP,
                'Value': data['server_modified'],
                'Description': 'Server Modified'
            },
        ]
        size = data['size']
        name = data['name']
        data['Name'] = name
        path = data['path_display']
        if path == '/' and name == '':
            pass  # root directory
        elif path.endswith(name):
            path = os.path.dirname(path)
            assert len(path) < len(data['path_display'])
            if len(path) == 1 and path[0] == '/':
                test_path = path + name
            else:
                test_path = path + '/' + name
            assert test_path == data['path_display'], f'test_path: {test_path}, path_display: {data["path_display"]}'
        else:
            # unexpected, so let's dump some data
            ic('Path does not end with child name')
            ic(data)
            ic(name)
            ic(path)
            raise ValueError('Path does not end with child name')
        assert path
        data['Path'] = path
        kwargs = {
            'source': self.source,
            'raw_data': encode_binary_data(bytes(json.dumps(data).encode('utf-8'))),
            'URI': 'https://www.dropbox.com/home' + data['path_display'],
            'Path': path,
            'Name': name,
            'ObjectIdentifier': data['ObjectIdentifier'],
            'Timestamps': timestamps,
            'Size': size,
            'Attributes': data,
            'Label': name,
            'PosixFileAttributes': UnixFileAttributes.map_file_attributes(unix_file_attributes),
            'WindowsFileAttributes': IndalekoWindows.map_file_attributes(windows_file_attributes),
        }
        obj = IndalekoObject(**kwargs)
        if 'Path' not in obj:
            ic(obj)
            ic(obj.indaleko_object)
            ic(data)
            ic(path)
            ic(name)
            ic(obj.args)
            exit(0)
        return obj


def main() -> None:
    '''This is the main handler for the Dropbox recorder.'''
    BaseCloudStorageRecorder.cloud_recorder_runner(
        IndalekoDropboxCloudStorageCollector,
        IndalekoDropboxCloudStorageRecorder,
    )


if __name__ == '__main__':
    main()
