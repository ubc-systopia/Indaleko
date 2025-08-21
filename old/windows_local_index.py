import datetime
import json
import logging
import os
import platform

import local_index

from IndalekoWindowsMachineConfig import IndalekoWindowsMachineConfig


class IndalekoWindowsLocalIndexer:
    """Definitions & methods used by the Windows local indexer."""

    WindowsLocalIndexFilePrefix = "windows-local-fs-data"

    def __init__(self) -> None:
        pass


def windows_to_posix(filename):
    """Convert a Win32 filename to a POSIX-compliant one."""
    # Define a mapping of Win32 reserved characters to POSIX-friendly characters
    win32_to_posix = {
        "<": "_lt_",
        ">": "_gt_",
        ":": "_cln_",
        '"': "_qt_",
        "/": "_sl_",
        "\\": "_bsl_",
        "|": "_bar_",
        "?": "_qm_",
        "*": "_ast_",
    }

    for win32_char, posix_char in win32_to_posix.items():
        filename = filename.replace(win32_char, posix_char)

    return filename


def posix_to_windows(filename):
    """Convert a POSIX-compliant filename to a Win32 one."""
    # Define a mapping of POSIX-friendly characters back to Win32 reserved characters
    posix_to_win32 = {
        "_lt_": "<",
        "_gt_": ">",
        "_cln_": ":",
        "_qt_": '"',
        "_sl_": "/",
        "_bsl_": "\\",
        "_bar_": "|",
        "_qm_": "?",
        "_ast_": "*",
    }

    for posix_char, win32_char in posix_to_win32.items():
        filename = filename.replace(posix_char, win32_char)

    return filename


def construct_windows_output_file_name(path: str, configdir="./config"):
    wincfg = IndalekoWindowsMachineConfig(config_dir=configdir)
    machine_guid = wincfg.get_config_data()["MachineGuid"]
    drive = os.path.splitdrive(path)[0][0].upper()
    drive_guid = drive
    for vol in wincfg.get_config_data()["VolumeInfo"]:
        if vol["DriveLetter"] == drive:
            drive_guid = vol["UniqueId"]
            assert "Volume" in drive_guid, f"{drive_guid} is not a volume GUID"
            drive_guid = drive_guid[-38:-2]
            break
        drive_guid = drive  # ugly, but what else can I do at this point?
    timestamp = timestamp = datetime.datetime.now(datetime.UTC).isoformat()
    return posix_to_windows(
        f"{IndalekoWindowsLocalIndexer.WindowsLocalIndexFilePrefix}-machine={machine_guid}-drive={drive_guid}-date={timestamp}.json",
    )


def get_default_index_path():
    return os.path.expanduser("~")


def convert_windows_path_to_guid_uri(
    path: str,
    config: IndalekoWindowsMachineConfig,
) -> str:
    drive = os.path.splitdrive(path)[0][0].upper()
    uri = "\\\\?\\" + drive + ":"  # default format for lettered drives without GUIDs
    for vol in config.get_config_data()["VolumeInfo"]:
        if vol["DriveLetter"] is None:
            continue
        if vol["DriveLetter"] == drive:
            uri = vol["UniqueId"]
        # print(f'Unable to find volume GUID for drive {drive}')
    return uri


def build_stat_dict(
    name: str,
    root: str,
    config: IndalekoWindowsMachineConfig,
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
    stat_dict = {key: getattr(stat_data, key) for key in dir(stat_data) if key.startswith("st_")}
    stat_dict["file"] = name
    stat_dict["path"] = root
    if platform.system() == "Windows":
        if last_drive != os.path.splitdrive(root)[0][0].upper():
            # one entry cache - high hit rate expected
            last_drive = os.path.splitdrive(root)[0][0].upper()
        last_uri = convert_windows_path_to_guid_uri(root, config)
    assert last_uri.startswith(
        "\\\\?\\Volume{",
    ), f"last_uri {last_uri} does not start with \\\\?\\Volume{{"
    stat_dict["URI"] = os.path.join(last_uri, os.path.splitdrive(root)[1], name)
    return (stat_dict, last_uri, last_drive)


def walk_files_and_directories(path: str, config: IndalekoWindowsMachineConfig) -> list:
    data = []
    last_drive = None
    last_uri = None
    for root, dirs, files in os.walk(path):
        for name in dirs + files:
            entry = build_stat_dict(name, root, config, last_uri, last_drive)
            if entry is not None:
                data.append(entry[0])
                last_uri = entry[1]
                last_drive = entry[2]
    return data


def main() -> None:
    # Now parse the arguments
    li = local_index.LocalIndex()
    li.add_arguments(
        "--path",
        type=str,
        default=get_default_index_path(),
        help="Path to index",
    )
    args = li.parse_args()
    machine_config = IndalekoWindowsMachineConfig(config_dir=args.confdir)
    # now I have the path being parsed, let's figure out the drive GUID
    li.set_output_file(construct_windows_output_file_name(args.path))
    args = li.parse_args()
    data = walk_files_and_directories(args.path, machine_config)
    # now I just need to save the data
    output_file = os.path.join(args.outdir, args.output).replace(":", "_")
    with open(output_file, "w") as fd:
        json.dump(data, fd, indent=4)


if __name__ == "__main__":
    main()
