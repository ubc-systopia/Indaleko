import local_index
import datetime
import os
import re
import uuid
import json
import logging
import platform

class IndalekoWindowsMachineConfig:
    '''
    This is the analog to the version in the config script.  In this class we
    look for and load the captured configuration data.  We have this separation
    because currently the machine guid requires admin privileges to get.
    '''
    def __init__(self, config_dir : str):
        self.config_file = self.__find_hw_info_file__()
        self.config_dir = config_dir
        self.config_data = None
        assert self.config_dir is not None, 'No config directory specified'
        self.config_data = self.get_config_data()

    def __load__config_data__(self):
        with open(self.config_file, 'rt', encoding='utf-8-sig') as fd:
            self.config_data = json.load(fd)


    def get_config_data(self):
        if self.config_data is None:
            self.__load__config_data__()
        return self.config_data

    def __find_hw_info_file__(self, configdir = './config'):
        candidates = [x for x in os.listdir(configdir) if x.startswith('windows-hardware-info') and x.endswith('.json')]
        assert len(candidates) > 0, 'At least one windows-hardware-info file should exist'
        for candidate in candidates:
            file, guid, timestamp = self.get_guid_timestamp_from_file_name(candidate)
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

def construct_windows_output_file_name(path : str, configdir = './config'):
    wincfg = IndalekoWindowsMachineConfig(config_dir=configdir)
    machine_guid = wincfg.get_config_data()['MachineGuid']
    drive = os.path.splitdrive(path)[0][0].upper()
    drive_guid = drive
    for vol in wincfg.get_config_data()['VolumeInfo']:
        if vol['DriveLetter'] == drive:
            drive_guid = vol['UniqueId']
            assert 'Volume' in drive_guid, f'{drive_guid} is not a volume GUID'
            drive_guid = drive_guid[-38:-2]
            break
        else:
            drive_guid=drive # ugly, but what else can I do at this point?
    timestamp = timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return posix_to_windows(f'windows-local-fs-data-machine={machine_guid}-drive={drive_guid}-date={timestamp}.json')


def get_default_index_path():
    return os.path.expanduser("~")

def convert_windows_path_to_guid_uri(path : str, config : IndalekoWindowsMachineConfig) -> str:
    drive = os.path.splitdrive(path)[0][0].upper()
    uri = '\\\\?\\' + drive + ':' # default format for lettered drives without GUIDs
    for vol in config.get_config_data()['VolumeInfo']:
        if vol['DriveLetter'] == drive:
            uri = vol['UniqueId']
    return uri

def build_stat_dict(name: str, root : str, config : IndalekoWindowsMachineConfig, last_uri = None, last_drive = None) -> tuple:
    file_path = os.path.join(root, name)
    last_uri = file_path
    try:
        stat_data = os.stat(file_path)
    except:
        # at least for now, we just skip errors
        logging.warning(f'Unable to stat {file_path}')
        return None
    stat_dict = {key : getattr(stat_data, key) for key in dir(stat_data) if key.startswith('st_')}
    stat_dict['file'] = name
    stat_dict['path'] = root
    if platform.system() == 'Windows':
        if last_drive != os.path.splitdrive(root)[0][0].upper():
            # one entry cache - high hit rate expected
            last_drive = os.path.splitdrive(root)[0][0].upper()
        last_uri = convert_windows_path_to_guid_uri(root, config)
    stat_dict['URI'] = os.path.join(last_uri, name)
    return (stat_dict, last_uri, last_drive)

def walk_files_and_directories(path: str, config : IndalekoWindowsMachineConfig) -> list:
    files_data = []
    dirs_data = []
    last_drive = None
    last_uri = None
    for root, dirs, files in os.walk(path):
        for name in files + dirs:
            entry = build_stat_dict(name, root, config, last_uri, last_drive)
            if entry is not None:
                files_data.append(entry[0])
                last_uri = entry[1]
                last_drive = entry[2]
    return dirs_data + files_data


def main():
    # Now parse the arguments
    li = local_index.LocalIngest()
    li.add_arguments('--path', type=str, default=get_default_index_path(), help='Path to index')
    args = li.parse_args()
    machine_config = IndalekoWindowsMachineConfig(config_dir=args.confdir)
    # now I have the path being parsed, let's figure out the drive GUID
    li.set_output_file(construct_windows_output_file_name(args.path))
    args = li.parse_args()
    data = walk_files_and_directories(args.path, machine_config)
    # now I just need to save the data
    output_file = os.path.join(args.outdir, args.output).replace(':', '_')
    with open(output_file, 'wt') as fd:
        json.dump(data, fd, indent=4)



if __name__ == "__main__":
    main()
