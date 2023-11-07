import argparse
import json
import os
import logging
import sys
import uuid
import datetime
import re
import ctypes
import local_ingest
import platform
import subprocess
import json
import multiprocessing
import os

class IndalekoWindowsMachineConfig:
    '''
    This is the analog to the version in the config script.  In this class we
    look for and load the captured configuration data.  We have this separation
    because currently the machine guid requires admin privileges to get.
    '''
    def __init__(self, hwinfo : str = None):
        self.config_file = self.__find_hw_info_file__()

    def __find_hw_info_file__(self, configdir = './config'):
        candidates = [x for x in os.listdir(configdir) if x.startswith('windows-hardware-info') and x.endswith('.json')]
        assert len(candidates) > 0, 'At least one windows-hardware-info file should exist'
        for candidate in candidates:
            file, guid, timestamp = self.get_guid_timestamp_from_file_name(candidate)
        print(timestamp)
        return configdir + '/' + candidates[-1]

    @staticmethod
    def get_guid_timestamp_from_file_name(file_name : str) -> tuple:
        '''
        Get the machine configuration captured by powershell.
        Note that this PS script requires admin privileges so it might
        be easier to do this in an application that elevates on Windows so it
        can be done dynamically.  For now, we assume it has been captured.
        '''
        # Regular expression to match the GUID and timestamp
        pattern = r"windows-hardware-info-(?P<guid>[a-fA-F0-9\-]+)-(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.\d+Z)\.json"
        match = re.match(pattern, file_name)
        assert match, 'Filename format not recognized.'
        guid = uuid.UUID(match.group("guid"))
        timestamp = match.group("timestamp").replace("-", ":")
        # %f can only handle up to 6 digits and it seems Windows gives back
        # more sometimes. Note this truncates, it doesn't round.  I doubt
        # it matters.
        decimal_position = timestamp.rindex('.')
        if len(timestamp) - decimal_position - 2 > 6:
            timestamp = timestamp[:decimal_position + 7] + "Z"
        timestamp = datetime.datetime.strptime(timestamp, "%Y:%m:%dT%H:%M:%S.%fZ")
        return (file_name, guid, timestamp)

    @staticmethod
    def get_most_recent_config_file(config_dir : str):
        candidates = [x for x in os.listdir(config_dir) if x.startswith('windows-hardware-info') and x.endswith('.json')]
        assert len(candidates) > 0, 'At least one windows-hardware-info file should exist'
        candidate_files = [(timestamp, filename) for filename, guid, timestamp in [IndalekoWindowsMachineConfig.get_guid_timestamp_from_file_name(x) for x in candidates]]
        candidate_files.sort(key=lambda x: x[0])
        return candidate_files[0][1]



class WindowsHardwareInfo:

    def __init__(self, config_dir : str = './config'):
        self.config_dir = config_dir
        self.config_files = [x for x in os.listdir(self.config_dir) if x.startswith('windows-hardware-info')]
        assert len(self.config_files) > 0, 'At least one windows-hardware-info file should exist'
        self.win_machine_info = self.config_files[-1] # newest one gets used - note don't handle the multi GUID case
        self.machine_config = self.__get_most_recent_config_info__()
        self.__build_drive_map__()

    def __build_drive_map__(self):
        '''Given the config data, build a map of drive letters to volume
        GUIDs'''
        self.drive_map = {}
        for volume in self.machine_config['VolumeInfo']:
            if volume['DriveLetter'] is None:
                continue
            self.drive_map[volume['DriveLetter']] = volume['UniqueId']

    def __load_machine_config_info__(self):
        assert self.win_machine_info is not None, 'Config file must be specified'
        assert os.path.exists(os.path.join(self.config_dir, self.win_machine_info)), 'Machine info file not found'
        self.data = {}
        with open(os.path.join(self.config_dir, self.win_machine_info), 'r', encoding='utf-8-sig') as fd:
            self.data = fd.read()
        return json.loads(self.data)

    def __get_config_info__(self, config_file : str):
        assert config_file is not None, 'Config file must be specified'
        self.win_machine_info = config_file
        return self.__load_machine_config_info__()

    def __get_most_recent_config_info__(self):
        '''
        Load the configuration data that's been previously captured.  Uses the
        most recent config file.
        '''
        self.win_machine_info = IndalekoWindowsMachineConfig.get_most_recent_config_file(self.config_dir)
        return self.__load_machine_config_info__(self.win_machine_info)



class WindowsLocalFileSystemMetadata(local_ingest.LocalFileSystemMetadata):

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
    li = local_ingest.LocalIngest()
    li.set_output_file('windows-local-file-system-data.json')
    li.set_config_file('windows-local-file-system-data.json')
    li.parse_args()
    print(li.args)
    wmc = IndalekoWindowsMachineConfig()
    print(wmc.get_most_recent_config_file('./config'))

if __name__ == '__main__':
    main()
