'''
This module handles data ingestion into Indaleko from the Google Drive data
indexer.

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
import datetime
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
from storage.collectors.cloud.g_drive import IndalekoGDriveCloudStorageCollector
from storage.recorders.data_model import IndalekoStorageRecorderDataModel
from storage.recorders.cloud.cloud_base import BaseCloudStorageRecorder
from utils.misc.file_name_management import find_candidate_files, extract_keys_from_file_name
from utils.misc.data_management import encode_binary_data
# pylint: enable=wrong-import-position


class IndalekoGDriveCloudStorageRecorder(BaseCloudStorageRecorder):
    '''
    This class provides the Google Drive Ingester for Indaleko.
    '''

    gdrive_recorder_uuid = '4d74bd0b-e502-4df8-9f9e-13ce711d60aa'
    gdrive_recorder_service = {
        'service_name': 'Google Drive Recorder',
        'service_description': 'This service records metadata collected from Google Drive.',
        'service_version': '1.0.0',
        'service_type': IndalekoServiceManager.service_type_storage_recorder,
        'service_identifier': gdrive_recorder_uuid,
    }

    gdrive_platform = IndalekoGDriveCloudStorageCollector.gdrive_platform
    gdrive_recorder = 'recorder'

    recorder_data = IndalekoStorageRecorderDataModel(
        RecorderPlatformName=gdrive_platform,
        RecorderServiceName=gdrive_recorder,
        RecorderServiceUUID=uuid.UUID(gdrive_recorder_uuid),
        RecorderServiceVersion=gdrive_recorder_service['service_version'],
        RecorderServiceDescription=gdrive_recorder_service['service_description'],
    )

    def __init__(self, **kwargs: dict) -> None:
        '''Initialize the Google Drive Ingester'''
        for key, value in self.gdrive_recorder_service.items():
            if key not in kwargs:
                kwargs[key] = value
        if 'platform' not in kwargs:
            kwargs['platform'] = self.gdrive_platform
        if 'recorder' not in kwargs:
            kwargs['recorder'] = self.gdrive_recorder
        if 'user_id_ not in kwargs':
            assert 'input_file' in kwargs
            keys = extract_keys_from_file_name(kwargs['input_file'])
            assert 'userid' in keys, f'userid not found in input file name: {kwargs["input_file"]}'
            self.user_id = keys['userid']
        else:
            self.user_id = kwargs['user_id']
        super().__init__(**kwargs)
        self.output_file = kwargs.get('output_file', self.generate_file_name())
        self.source = {
            'Identifier': self.gdrive_recorder_uuid,
            'Version': self.gdrive_recorder_service['service_version'],
        }
        self.root_dir = None
        self.id_map = {}

    def find_collector_files(self) -> list:
        '''This function finds the files that the collector has produced:'''
        if self.data_dir is None:
            raise ValueError('data_dir is required')
        candidates = find_candidate_files(
            [
                IndalekoGDriveCloudStorageCollector.gdrive_platform,
                IndalekoGDriveCloudStorageCollector.gdrive_collector_name,
            ],
            self.data_dir
        )
        if self.debug:
            ic(candidates)
        return candidates

    def get_object_path(self, obj: IndalekoObject):
        '''Given an Indaleko object, return a valid local path to the object'''
        if 'parents' in obj:  # use parent if there is one
            return obj['parents'][0]
        return self.root_dir['id']  # otherwise use the root directory

    def build_dirmap(self) -> None:
        '''
        This function builds the directory/file map.  It is
        specific to Google Drive.
        '''
        # First: build the directory map from the list of known directories.
        self.dirmap = {item['id']: item.args['ObjectIdentifier'] for item in self.dir_data}
        for item in self.file_data:
            # now, walk through all the files
            parent_id = item['Path']
            # use the ID in the path field if we have info on it.
            # otherwise, just use the root directory.
            item.args['Path'] = self.root_dir['id'] if parent_id == '/' else parent_id

    def normalize_collector_data(self, data: dict) -> dict:
        '''
        Given some metadata, this will create a record that can be inserted into the
        Object collection.
        '''
        if data is None:
            raise ValueError('data is required')
        if not isinstance(data, dict):
            raise ValueError('data must be a dictionary')
        oid = data.get('ObjectIdentifier', uuid.uuid4())
        timestamps = []
        if 'createdTime' in data:
            timestamps.append(
                {
                    'Label': IndalekoObject.CREATION_TIMESTAMP,
                    'Value': datetime.datetime.fromisoformat(data['createdTime']).isoformat(),
                    'Description': 'Creation Time',
                }
            )
        if 'modifiedTime' in data:
            # No distinction between modified and changed.
            timestamps.append(
                {
                    'Label': IndalekoObject.MODIFICATION_TIMESTAMP,
                    'Value': datetime.datetime.fromisoformat(data['modifiedTime']).isoformat(),
                    'Description': 'Modification Time',
                }
            )
            timestamps.append(
                {
                    'Label': IndalekoObject.CHANGE_TIMESTAMP,
                    'Value': datetime.datetime.fromisoformat(data['modifiedTime']).isoformat(),
                    'Description': 'Access Time',
                }
            )
        if 'viewedByMeTime' in data:
            timestamps.append(
                {
                    'Label': IndalekoObject.ACCESS_TIMESTAMP,
                    'Value': datetime.datetime.fromisoformat(data['viewedByMeTime']).isoformat(),
                    'Description': 'Viewed Time',
                }
            )
        if not self.root_dir:
            path = data['id'] # root directory
        else:
            path = self.root_dir['id']
        if 'parents' in data:
            path = data['parents'][0]
        name = data['name']
        data['Path'] = path
        data['Name'] = name
        kwargs = {
            'source': self.source,
            'raw_data': encode_binary_data(bytes(json.dumps(data), 'utf-8')),
            'URI': data.get('webViewLink', None),
            'Path': path,
            'Name': name,
            'ObjectIdentifier': str(oid),
            'Timestamps': timestamps,
            'Size': int(data.get('size', 0)),
            'Attributes': data,
            'Label': name,
        }
        kwargs['PosixFileAttributes'] = \
            UnixFileAttributes.map_file_attributes(
                self.map_gdrive_attributes_to_unix_attributes(data)
            )
        kwargs['WindowsFileAttributes'] = \
            IndalekoWindows.map_file_attributes(
                self.map_gdrive_attributes_to_windows_attributes(data)
            )
        if 'timestamp' not in kwargs:
            if isinstance(self.timestamp, str):
                kwargs['timestamp'] = datetime.datetime.fromisoformat(self.timestamp)
            else:
                assert isinstance(self.timestamp, datetime.datetime)
                kwargs['timestamp'] = self.timestamp
        assert kwargs.get('Path')
        obj = IndalekoObject(**kwargs)
        if not self.root_dir:
            self.root_dir = obj
            self.id_map[data['id']] = obj
        elif data['capabilities']['canAddChildren']:
            self.id_map[data['id']] = obj
        return obj

    @staticmethod
    def map_gdrive_attributes_to_unix_attributes(data: dict) -> dict:
        '''Map Google Drive attributes to Unix attributes'''
        if data is None:
            raise ValueError('data is required')
        if not isinstance(data, dict):
            raise ValueError('data must be a dictionary')
        attributes = 0
        if 'mimeType' in data:
            if data['mimeType'] == 'application/vnd.google-apps.folder':
                attributes |= UnixFileAttributes.FILE_ATTRIBUTES['S_IFDIR']
            else:
                attributes |= UnixFileAttributes.FILE_ATTRIBUTES['S_IFREG']
        return attributes

    @staticmethod
    def map_gdrive_attributes_to_windows_attributes(data: dict) -> dict:
        '''Map Google Drive attributes to Windows attributes'''
        if data is None:
            raise ValueError('data is required')
        if not isinstance(data, dict):
            raise ValueError('data must be a dictionary')
        attributes = 0
        if 'mimeType' in data:
            if data['mimeType'] == 'application/vnd.google-apps.folder':
                attributes |= IndalekoWindows.FILE_ATTRIBUTES['FILE_ATTRIBUTE_DIRECTORY']
            else:
                attributes |= IndalekoWindows.FILE_ATTRIBUTES['FILE_ATTRIBUTE_NORMAL']
        return attributes


def main() -> None:
    '''Main entry point for the Google Drive Recorder'''
    BaseCloudStorageRecorder.cloud_recorder_runner(
        IndalekoGDriveCloudStorageCollector,
        IndalekoGDriveCloudStorageRecorder,
    )


if __name__ == '__main__':
    main()
