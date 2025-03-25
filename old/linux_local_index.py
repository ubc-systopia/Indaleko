import local_index
import datetime
import json
import logging
import platform
import os
import uuid


class IndalekoLinuxMachineConfig:
    """
    This is the analog to the version in the config script.  In this class we
    look for and load the captured machine configuration data.  We ahve this
    separation because different platforms require different steps to gather up
    machine information.
    """

    def __init__(self, config_dir: str):
        assert platform.system() == "Linux", "This class is for Linux"
        assert config_dir is not None, f"No config directory specified: {config_dir}"
        assert os.path.exists(config_dir), "Config directory does not exist"
        self.config_dir = config_dir
        # Note, for the moment I'm just going to fake the data - we really
        # should collect useful info here.
        with open("/etc/machine-id", "rt") as fd:
            self.config_data = {
                "MachineUuid": fd.read().strip(),
            }

    def __load__config_data__(self):
        with open(self.config_file, "rt", encoding="utf-8-sig") as fd:
            self.config_data = json.load(fd)

    def get_config_data(self):
        if self.config_data is None:
            self.__load__config_data__()
        return self.config_data

    def __find_hw_info_file__(self, configdir="./config"):
        candidates = [
            x
            for x in os.listdir(configdir)
            if x.startswith("linux-hardware-info") and x.endswith(".json")
        ]
        assert (
            len(candidates) > 0
        ), "At least one windows-hardware-info file should exist"
        for candidate in candidates:
            file, guid, timestamp = self.get_guid_timestamp_from_file_name(candidate)
        return configdir + "/" + candidates[-1]

    @staticmethod
    def get_most_recent_config_file(config_dir: str):
        candidates = [
            x
            for x in os.listdir(config_dir)
            if x.startswith("linux-hardware-info") and x.endswith(".json")
        ]
        assert len(candidates) > 0, "At least one linux-hardware-info file should exist"
        candidate_files = [
            (timestamp, filename)
            for filename, guid, timestamp in [
                IndalekoLinuxMachineConfig.get_guid_timestamp_from_file_name(x)
                for x in candidates
            ]
        ]
        candidate_files.sort(key=lambda x: x[0])
        return candidate_files[0][1]


def construct_linux_output_file_name(path: str, configdir="./config"):
    linuxcfg = IndalekoLinuxMachineConfig(config_dir=configdir)
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return f'linux-local-fs-data-machine={linuxcfg.get_config_data()["MachineUuid"]}-date={timestamp}.json'


def build_stat_dict(
    name: str,
    root: str,
    config: IndalekoLinuxMachineConfig,
    last_uri=None,
    last_drive=None,
) -> tuple:
    file_path = os.path.join(root, name)
    last_uri = file_path
    try:
        stat_data = os.stat(file_path)
    except:
        # at least for now, we just skip errors
        logging.warning(f"Unable to stat {file_path}")
        return None
    stat_dict = {
        key: getattr(stat_data, key) for key in dir(stat_data) if key.startswith("st_")
    }
    stat_dict["file"] = name
    stat_dict["path"] = root
    stat_dict["URI"] = os.path.join(last_uri, name)
    return (stat_dict, last_uri, last_drive)


def walk_files_and_directories(path: str, config: IndalekoLinuxMachineConfig) -> list:
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


def get_default_index_path():
    return os.path.expanduser("~")


def main():
    # Now parse the arguments
    li = local_index.LocalIndex()
    li.add_arguments(
        "--path", type=str, default=get_default_index_path(), help="Path to index"
    )
    args = li.parse_args()
    print(args)
    machine_config = IndalekoLinuxMachineConfig(config_dir=args.confdir)
    # now I have the path being parsed, let's figure out the drive GUID
    li.set_output_file(construct_linux_output_file_name(args.path))
    args = li.parse_args()
    data = walk_files_and_directories(args.path, machine_config)
    # now I just need to save the data
    output_file = os.path.join(args.outdir, args.output).replace(":", "_")
    with open(output_file, "wt") as fd:
        json.dump(data, fd, indent=4)


if __name__ == "__main__":
    main()
