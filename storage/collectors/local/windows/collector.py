'''
This module handles gathering metadata from Windows local file systems.

Indaleko Windows Local Collector
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
import inspect
import logging
import os
import sys
import uuid

from pathlib import Path
from typing import Union

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from data_models import IndalekoSourceIdentifierDataModel
from db import IndalekoServiceManager
from platforms.windows.machine_config import IndalekoWindowsMachineConfig
from perf.perf_collector import IndalekoPerformanceDataCollector
from perf.perf_recorder import IndalekoPerformanceDataRecorder
from utils.i_logging import IndalekoLogging
from storage.collectors.base import BaseStorageCollector
from storage.collectors.data_model import IndalekoStorageCollectorDataModel
from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
from utils.cli.runner import IndalekoCLIRunner
from utils.i_logging import IndalekoLogging
from utils.misc.directory_management import indaleko_default_config_dir, indaleko_default_data_dir, indaleko_default_log_dir
from utils.misc.file_name_management import find_candidate_files
# pylint: enable=wrong-import-position


class IndalekoWindowsLocalCollector(BaseStorageCollector):
    '''
    This is the class that collects metadata from Windows local file systems.
    '''
    windows_platform = 'Windows'
    windows_local_collector_name = 'fs_collector'

    indaleko_windows_local_collector_uuid = '0793b4d5-e549-4cb6-8177-020a738b66b7'
    indaleko_windows_local_collector_service_name = 'Windows Local collector'
    indaleko_windows_local_collector_service_description = 'This service collects metadata from the local filesystems of a Windows machine.'
    indaleko_windows_local_collector_service_version = '1.0'
    indaleko_windows_local_collector_service_type = IndalekoServiceManager.service_type_storage_collector

    windows_collector_data = IndalekoStorageCollectorDataModel(
        CollectorPlatformName = windows_platform,
        CollectorServiceName = indaleko_windows_local_collector_service_name,
        CollectorServiceUUID = uuid.UUID(indaleko_windows_local_collector_uuid),
        CollectorServiceVersion = indaleko_windows_local_collector_service_version,
        CollectorServiceDescription = indaleko_windows_local_collector_service_description
    )

    indaleko_windows_local_collector_service ={
        'service_name' : indaleko_windows_local_collector_service_name,
        'service_description' : indaleko_windows_local_collector_service_description,
        'service_version' : indaleko_windows_local_collector_service_version,
        'service_type' : indaleko_windows_local_collector_service_type,
        'service_identifier' : indaleko_windows_local_collector_uuid,
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
        assert 'machine_config' in kwargs, 'machine_config must be specified'
        self.machine_config = kwargs['machine_config']
        if 'machine_id' not in kwargs:
            kwargs['machine_id'] = self.machine_config.machine_id
        for key, value in self.indaleko_windows_local_collector_service.items():
            if key not in kwargs:
                kwargs[key] = value
        if 'platform' not in kwargs:
            kwargs['platform'] = IndalekoWindowsLocalCollector.windows_platform
        if 'collector_data' not in kwargs:
            kwargs['collector_data'] =  IndalekoWindowsLocalCollector.windows_collector_data
        super().__init__(**kwargs)

    def generate_windows_collector_file_name(self, **kwargs) -> str:
        if 'platform' not in kwargs:
            kwargs['platform'] = IndalekoWindowsLocalCollector.windows_platform
        if 'collector_name' not in kwargs:
            kwargs['collector_name'] = IndalekoWindowsLocalCollector.windows_local_collector_name
        if 'machine_id' not in kwargs:
            kwargs['machine_id'] = uuid.UUID(self.machine_config.machine_id).hex
        return BaseStorageCollector.generate_collector_file_name(**kwargs)

    def convert_windows_path_to_guid_uri(self, path : str) -> str:
        '''This method handles converting a Windows path to a volume GUID based URI.'''
        drive = os.path.splitdrive(path)[0][0].upper()
        uri = '\\\\?\\' + drive + ':' # default format for lettered drives without GUIDs
        mapped_guid = self.machine_config.map_drive_letter_to_volume_guid(drive)
        if mapped_guid is not None:
            uri = '\\\\?\\Volume{' + mapped_guid + '}\\'
        else:
            print(f'Ugh, cannot map {drive} to a GUID')
            uri = '\\\\?\\' + drive + ':'
        return uri


    def build_stat_dict(self, name: str, root : str, last_uri = None, last_drive = None) -> tuple:
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
        except Exception as e: # pylint: disable=broad-except
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
        stat_dict = {key : getattr(stat_data, key) \
                     for key in dir(stat_data) if key.startswith('st_')}
        stat_dict['Name'] = name
        stat_dict['Path'] = root
        if last_drive != os.path.splitdrive(root)[0][0].upper():
            last_drive = os.path.splitdrive(root)[0][0].upper()
            last_uri = self.convert_windows_path_to_guid_uri(root)
            assert last_uri.startswith('\\\\?\\Volume{'), \
                f'last_uri {last_uri} does not start with \\\\?\\Volume{{'
        stat_dict['URI'] = os.path.join(last_uri, os.path.splitdrive(root)[1], name)
        stat_dict['Collector'] = str(self.service_identifier)
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
        return data

class local_collector_mixin(IndalekoBaseCLI.default_handler_mixin):
    @staticmethod
    def load_machine_config(keys: dict[str, str]) -> IndalekoWindowsMachineConfig:
        '''Load the machine configuration'''
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
    def collect(collector : IndalekoWindowsLocalCollector):
        data = collector.collect()
        output_file = Path(args.datadir) / args.outputfile
        collector.write_data_to_file(data, str(output_file))
    def extract_counters(**kwargs):
        collector = kwargs.get('collector')
        if collector:
            return collector.get_counts()
        else:
            return {}
    collector = IndalekoWindowsLocalCollector(**kwargs)
    perf_data = IndalekoPerformanceDataCollector.measure_performance(
        collect,
        source=IndalekoSourceIdentifierDataModel(
            Identifier=collector.service_identifier,
            Version = collector.service_version,
            Description=collector.service_description),
        description=collector.service_description,
        MachineIdentifier=uuid.UUID(kwargs['machine_config'].machine_id),
        process_results_func=extract_counters,
        input_file_name=None,
        output_file_name=str(Path(args.datadir) / args.outputfile),
        collector=collector
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

@staticmethod
def add_storage_local_parameters(parser : argparse.ArgumentParser) -> argparse.ArgumentParser:
    '''Add the parameters for the local collector path to use.'''
    default_path = os.path.expanduser('~')
    if default_path == '~':
        default_path = os.path.abspath(os.sep)
    parser.add_argument('--path',
                        help=f'Path to the directory from which to collect metadata (default={default_path})',
                        type=str,
                        default=default_path)
    return parser


def main():
    '''This is the CLI handler for the Windows local storage collector.'''
    runner = IndalekoCLIRunner(
        cli_data=IndalekoBaseCliDataModel(
            Service=IndalekoWindowsLocalCollector.windows_local_collector_name,
        ),
        handler_mixin=local_collector_mixin,
        features=IndalekoBaseCLI.cli_features(input=False),
        additional_parameters=add_storage_local_parameters,
        Run=local_run,
    )
    runner.run()



if __name__ == '__main__':
    main()
