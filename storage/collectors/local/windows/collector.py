'''
This module handles gathering metadata from Windows local file systems.

Indaleko Windows Local Collector
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
import logging
from pathlib import Path
import os
import sys
import uuid

from typing import Union

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from db import IndalekoServiceManager
from platforms.windows.machine_config import IndalekoWindowsMachineConfig
from storage.collectors.local.local_base import BaseLocalStorageCollector
from storage.collectors.data_model import IndalekoStorageCollectorDataModel
from utils.cli.base import IndalekoBaseCLI
# pylint: enable=wrong-import-position


class IndalekoWindowsLocalStorageCollector(BaseLocalStorageCollector):
    '''
    This is the class that collects metadata from Windows local file systems.
    '''
    windows_platform = 'Windows'
    windows_local_collector_name = 'fs_collector'

    indaleko_windows_local_collector_uuid = '0793b4d5-e549-4cb6-8177-020a738b66b7'
    indaleko_windows_local_collector_service_name = 'Windows Local collector'
    indaleko_windows_local_collector_service_description = \
        'This service collects metadata from the local filesystems of a Windows machine.'
    indaleko_windows_local_collector_service_version = '1.0'
    indaleko_windows_local_collector_service_type = IndalekoServiceManager.service_type_storage_collector

    collector_data = IndalekoStorageCollectorDataModel(
        CollectorPlatformName=windows_platform,
        CollectorServiceName=windows_local_collector_name,
        CollectorServiceUUID=uuid.UUID(indaleko_windows_local_collector_uuid),
        CollectorServiceVersion=indaleko_windows_local_collector_service_version,
        CollectorServiceDescription=indaleko_windows_local_collector_service_description
    )

    indaleko_windows_local_collector_service = {
        'service_name': indaleko_windows_local_collector_service_name,
        'service_description': indaleko_windows_local_collector_service_description,
        'service_version': indaleko_windows_local_collector_service_version,
        'service_type': indaleko_windows_local_collector_service_type,
        'service_identifier': indaleko_windows_local_collector_uuid,
    }

    @staticmethod
    def windows_to_posix(filename):
        """
        Convert a Win32 filename to a POSIX-compliant one.
        """
        # Define a mapping of Win32 reserved characters to POSIX-friendly characters
        win32_to_posix = {
            '<': '_lt_', '>': '_gt_', ':': '_cln_', '"': '_qt_',
            '/': '_sl_', '\\': '_bsl_', '|': '_bar_', '?': '_qm_', '*': '_ast_'
        }
        for win32_char, posix_char in win32_to_posix.items():
            filename = filename.replace(win32_char, posix_char)
        return filename

    @staticmethod
    def posix_to_windows(filename):
        """
        Convert a POSIX-compliant filename to a Win32 one.
        """
        # Define a mapping of POSIX-friendly characters back to Win32 reserved characters
        posix_to_win32 = {
            '_lt_': '<', '_gt_': '>', '_cln_': ':', '_qt_': '"',
            '_sl_': '/', '_bsl_': '\\', '_bar_': '|', '_qm_': '?', '_ast_': '*'
        }
        for posix_char, win32_char in posix_to_win32.items():
            filename = filename.replace(posix_char, win32_char)
        return filename

    def __init__(self, **kwargs):
        for key, value in self.indaleko_windows_local_collector_service.items():
            if key not in kwargs:
                kwargs[key] = value
        if 'platform' not in kwargs:
            kwargs['platform'] = IndalekoWindowsLocalStorageCollector.windows_platform
        if 'collector_data' not in kwargs:
            kwargs['collector_data'] = IndalekoWindowsLocalStorageCollector.collector_data
        super().__init__(**kwargs)
        if not hasattr(self, 'storage') and 'storage' in kwargs:
            self.storage = kwargs['storage']

    def generate_windows_collector_file_name(self, **kwargs) -> str:
        if 'platform' not in kwargs:
            kwargs['platform'] = IndalekoWindowsLocalStorageCollector.windows_platform
        if 'collector_name' not in kwargs:
            kwargs['collector_name'] = IndalekoWindowsLocalStorageCollector.get_collector_service_name()
        if 'machine_id' not in kwargs:
            kwargs['machine_id'] = uuid.UUID(self.machine_config.machine_id).hex
        if 'storage_description' not in kwargs and getattr(self, 'storage'):
            kwargs['storage_description'] = self.storage
        file_name = self.generate_collector_file_name(**kwargs)
        assert 'storage' in file_name, f'File name {file_name} does not contain "storage", '
        'kwargs={kwargs}, dir(self)={dir(self)}'
        return file_name

    def convert_windows_path_to_guid_uri(self, path: str) -> str:
        '''This method handles converting a Windows path to a volume GUID based URI.'''
        drive = os.path.splitdrive(path)[0][0].upper()
        uri = '\\\\?\\' + drive + ':'  # default format for lettered drives without GUIDs
        mapped_guid = self.machine_config.map_drive_letter_to_volume_guid(drive)
        if mapped_guid is not None:
            uri = '\\\\?\\Volume{' + mapped_guid + '}\\'
        else:
            print(f'Ugh, cannot map {drive} to a GUID')
            uri = '\\\\?\\' + drive + ':'
        return uri

    def build_stat_dict(self, name: str, root: str, last_uri: str = None, last_drive: str = None) -> tuple:
        '''
        Given a file name and a root directory, this will return a dict
        constructed from the file system metadata ("stat") for that file.
        Note: on error this returns an empty dictionary.  If the full path to
        the file does not exist, this returns None.
        '''
        file_path = os.path.join(root, name)
        if not os.path.exists(file_path):
            if name in os.listdir(root):
                if os.path.lexists(file_path):
                    logging.warning('File %s is an invalid link', file_path)
                else:
                    logging.warning('File %s exists in directory %s but not accessible', name, root)
            else:
                logging.warning('File %s does not exist in directory %s', file_path, root)
            return None
        if last_uri is None:
            last_uri = file_path
        lstat_data = None
        try:
            lstat_data = os.lstat(file_path)
            stat_data = os.stat(file_path)
        except Exception as e:  # pylint: disable=broad-except
            # at least for now, we log and skip errors
            logging.warning('Unable to stat %s : %s', file_path, e)
            self.error_count += 1
            if lstat_data is not None:
                self.bad_symlink_count += 1
            return None

        if stat_data.st_ino != lstat_data.st_ino:
            logging.info('File %s is a symlink, collecting symlink metadata', file_path)
            self.good_symlink_count += 1
            stat_data = lstat_data
        stat_dict = {key: getattr(stat_data, key)
                     for key in dir(stat_data) if key.startswith('st_')}
        stat_dict['Name'] = name
        stat_dict['Path'] = root
        if last_drive != os.path.splitdrive(root)[0][0].upper():
            last_drive = os.path.splitdrive(root)[0][0].upper()
            last_uri = self.convert_windows_path_to_guid_uri(root)
            assert last_uri.startswith('\\\\?\\Volume{'), \
                f'last_uri {last_uri} does not start with \\\\?\\Volume{{'
        stat_dict['URI'] = os.path.join(last_uri, os.path.splitdrive(root)[1], name)
        stat_dict['Collector'] = str(self.get_collector_service_identifier())
        assert last_uri.startswith('\\\\?\\Volume{')
        if last_uri.startswith('\\\\?\\Volume{'):
            stat_dict['Volume GUID'] = last_uri[11:-2]
        stat_dict['ObjectIdentifier'] = str(uuid.uuid4())
        return (stat_dict, last_uri, last_drive)

    def collect(self) -> list:
        data = []
        last_drive = None
        last_uri = None
        for root, dirs, files in os.walk(self.path):
            for name in dirs + files:
                entry = self.build_stat_dict(name, root, last_uri, last_drive)
                if entry is None:
                    self.not_found_count += 1
                    continue
                if len(entry) == 0:
                    self.error_count += 1
                    continue
                if name in dirs:
                    self.dir_count += 1
                else:
                    self.file_count += 1
                data.append(entry[0])
                last_uri = entry[1]
                last_drive = entry[2]
        self.data = data

    class windows_local_collector_mixin(BaseLocalStorageCollector.local_collector_mixin):

        @staticmethod
        def get_storage_identifier(args: argparse.Namespace) -> Union[str, None]:
            '''This method is used to get the storage identifier for a path'''
            if not hasattr(args, 'path'):
                return
            if not os.path.exists(args.path):
                ic(f'Path {args.path} does not exist')
                return None
            config = IndalekoWindowsMachineConfig.load_config_from_file(
                config_file=str(Path(args.configdir) / args.machine_config),
                offline=args.offline,
                debug=args.debug
            )
            drive = os.path.splitdrive(args.path)[0][0].upper()
            mapped_guid = config.map_drive_letter_to_volume_guid(drive)
            if mapped_guid is not None:
                return uuid.UUID(mapped_guid).hex
            return None

        @staticmethod
        def generate_output_file_name(keys):
            '''Generate the output file name'''
            return IndalekoBaseCLI.default_handler_mixin.generate_output_file_name(keys)

    cli_handler_mixin = windows_local_collector_mixin


def main():
    '''The CLI handler for the windows local storage collector.'''
    BaseLocalStorageCollector.local_collector_runner(
        IndalekoWindowsLocalStorageCollector,
        IndalekoWindowsMachineConfig
    )


if __name__ == '__main__':
    main()
