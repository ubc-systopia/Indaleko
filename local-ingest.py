import argparse
import json
import os
import logging
import sys
import uuid
import datetime
import re
import datetime
import ctypes
from get_machine_config import IndalekoWindowsMachine

class LocalFileSystemMetadata:

    def __init__(self):
        pass

    def get_output_file_name(self):
        assert False, 'get_output_file_name not implemented in base class: please override'

    def get_uri_for_file(self, file_name: str) -> str:
        assert False, 'get_uri_for_file not implemented in base class: please override'


class WindowsHardwareInfo:

    def __init__(self, config_dir : str = './config'):
        self.config_dir = config_dir
        self.config_files = [x for x in os.listdir(self.config_dir) if x.startswith('windows-hardware-info')]
        assert len(self.config_files) > 0, 'At least one windows-hardware-info file should exist'
        self.win_machine_info = self.config_files[-1] # newest one gets used - note don't handle the multi GUID case
        self.machine_config = self.__get_machine_config_info__()
        self.__build_drive_map__()

    def __build_drive_map__(self):
        '''Given the config data, build a map of drive letters to volume
        GUIDs'''
        self.drive_map = {}
        for volume in self.machine_config['VolumeInfo']:
            if volume['DriveLetter'] is None:
                continue
            self.drive_map[volume['DriveLetter']] = volume['UniqueId']

    def __get_machine_config_info__(self):
        '''
        Get the machine configuration captured by powershell.
        Note that this PS script requires admin privileges so it might
        be easier to do this in an application that elevates on Windows so it
        can be done dynamically.  For now, we assume it has been captured.
        '''
        # Regular expression to match the GUID and timestamp
        pattern = r"windows-hardware-info-(?P<guid>[a-fA-F0-9\-]+)-(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.\d+Z)\.json"
        match = re.match(pattern, self.win_machine_info)
        assert match, 'Filename format not recognized.'
        guid = match.group("guid")
        timestamp = match.group("timestamp").replace("-", ":")
        self.guid = uuid.UUID(guid)
        # %f can only handle up to 6 digits and it seems Windows gives back
        # more sometimes. Note this truncates, it doesn't round.  I doubt
        # it matters.
        decimal_position = timestamp.rindex('.')
        if len(timestamp) - decimal_position - 2 > 6:
            timestamp = timestamp[:decimal_position + 7] + "Z"
        self.timestamp = datetime.datetime.strptime(timestamp, "%Y:%m:%dT%H:%M:%S.%fZ")
        # So now let's load this configuration data
        assert os.path.exists(os.path.join(self.config_dir, self.win_machine_info)), 'Machine info file not found'
        with open(os.path.join(self.config_dir, self.win_machine_info), 'r', encoding='utf-8-sig') as fd:
            self.data = fd.read()
        return json.loads(self.data)




class WindowsLocalFileSystemMetadata(LocalFileSystemMetadata):

    def __init__(self, config_dir : str = './config'):
        self.config_dir = config_dir
        super().__init__()
        self.machine_config = IndalekoWindowsMachine()
        self.__get_machine_config_info__()

    def get_output_file_name(self):
        ofn = 'data/windows-local-file-system-data'
        ofn += '.json'
        return ofn

    def get_volume_guid_for_path(path):
        """
        Get the volume GUID for the given path on Windows.
        """
        # Define the function from the kernel32.dll
        GetVolumeNameForVolumeMountPointW = ctypes.windll.kernel32.GetVolumeNameForVolumeMountPointW

        # Create a buffer for the result
        volume_path_name = ctypes.create_unicode_buffer(261)  # MAX_PATH + 1

        # Call the function
        if not GetVolumeNameForVolumeMountPointW(path, volume_path_name, len(volume_path_name)):
            raise ctypes.WinError()

        return volume_path_name.value


    @staticmethod
    def get_volume_name_from_file(file_name: str) -> str:
        drive_letter = os.path.splitdrive(file_name)[0]+'\\'
        return WindowsLocalFileSystemMetadata.get_volume_guid_for_path(drive_letter)



def main():

    # Now parse the arguments
    logging_levels = sorted(set([l for l in logging.getLevelNamesMapping()]))
    parser = argparse.ArgumentParser()
    parser.add_argument('--loglevel', type=int, default=logging.WARNING, choices=logging_levels,
                        help='Logging level to use (lower number = more logging)')
    parser.add_argument('--output', type=str, default='TODO',
                        help='Name and location of where to save the fetched metadata')
    parser.add_argument('--config', type=str, default='msgraph-config.json',
                        help='Name and location from whence to retrieve the Microsoft Graph Config info')
    parser.add_argument('--host', type=str,
                        help='URL to use for ArangoDB (overrides config file)')
    parser.add_argument('--port', type=int,
                        help='Port number to use (overrides config file)')
    parser.add_argument('--user', type=str,
                        help='user name (overrides config file)')
    parser.add_argument('--password', type=str,
                        help='user password (overrides config file)')
    parser.add_argument('--database', type=str,
                        help='Name of the database to use (overrides config file)')
    parser.add_argument('--reset', action='store_true',
                        default=False, help='Clean database before running')
    args = parser.parse_args()
    print(args)
    hwconfig = WindowsHardwareInfo()
    print(hwconfig.drive_map)

if __name__ == "__main__":
    main()
