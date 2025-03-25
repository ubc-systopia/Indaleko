"""
The purpose of this package is to define the core data types used in Indaleko.

Indaleko is a Unified Private Index (UPI) service that enables the indexing of
storage content (e.g., files, databases, etc.) in a way that extracts useful
metadata and then uses it for creating a rich index service that can be used in
a variety of ways, including improving search results, enabling development of
non-traditional data visualizations, and mining relationships between objects to
enable new insights.

Indaleko is not a storage engine.  Rather, it is a metadata service that relies
upon storage engines to provide the data to be indexed.  The storage engines can
be local (e.g., a local file system,) remote (e.g., a cloud storage service,) or
even non-traditional (e.g., applications that provide access to data in some
way, such as Discord, Teams, Slack, etc.)

Indaleko uses three distinct classes of metadata to enable its functionality:

* Storage metadata - this is the metadata that is provided by the storage
  services
* Semantic metadata - this is the metadata that is extracted from the objects,
  either by the storage service or by semantic transducers that act on the files
  when it is available on the local device(s).
* Activity context - this is metadata that captures information about how the
  file was used, such as when it was accessed, by what application, as well as
  ambient information, such as the location of the device, the person with whom
  the user was interacting, ambient conditions (e.g., temperature, humidity, the
  music the user is listening to, etc.) and even external events (e.g., current
  news, weather, etc.)

To do this, Indaleko stores information of various types in databases.  One of
the purposes of this package is to encapsulate the data types used in the system
as well as the schemas used to validate the data.

The general architecture of Indaleko attempts to be flexible, while still
capturing essential metadata that is used as part of the indexing functionality.
Thus, to that end, we define both a generic schema and in some cases a flexible
set of properties that can be extracted and stored.  Since this is a prototype
system, we have strived to "keep it simple" yet focus on allowing us to explore
a broad range of storage systems, semantic transducers, and activity data sources.

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
"""

import argparse
import datetime
import glob
import json
import os
import psutil
import re
import socket
import uuid
import sys

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from utils.misc.directory_management import (
    indaleko_default_config_dir,
    indaleko_create_secure_directories,
)

# pylint: enable=wrong-import-position


class MacHardwareInfoGenerator:
    @staticmethod
    def read_config_from_file(config_path) -> dict:
        config_data = None

        with open(config_path) as f:
            config_data = json.load(f)

        return config_data

    def generate_config(self, guid):
        machine_guid = guid
        os_info = {
            "Caption": "macOS",
            "OSArchitecture": os.uname().machine,
            "Version": os.uname().release,
        }
        cpu_info = {
            "Name": self.get_cpu_name(),
            "Cores": psutil.cpu_count(logical=False),
        }
        volume_info = self.get_volume_info()
        hostname = socket.gethostname()
        config_data = {
            "MachineGuid": machine_guid,
            "OperatingSystem": os_info,
            "CPU": cpu_info,
            "VolumeInfo": volume_info,
            "Hostname": hostname,
        }
        return config_data

    def get_cpu_name(self):
        try:
            import platform

            return platform.processor()
        except Exception as e:
            print(f"Error getting CPU name: {e}")
            return "Unknown CPU"

    def get_volume_info(self):
        volumes = psutil.disk_partitions()
        volume_info = []

        for volume in volumes:
            try:
                usage = psutil.disk_usage(volume.mountpoint)
                volume_data = {
                    "UniqueId": volume.device,
                    "VolumeName": volume.device.split("/")[-1],
                    "Size": self.convert_bytes(usage.total),
                    "Filesystem": volume.fstype,
                }
                volume_info.append(volume_data)
            except Exception as e:
                print(f"Error getting volume info for {volume.device}: {e}")

        return volume_info

    def convert_bytes(self, bytes):
        kb = bytes / 1024
        mb = kb / 1024
        gb = mb / 1024
        return f"{gb:.2f} GB"


def find_all_config_files(dir_path):
    # Get a list of all json files in the directory
    files = glob.glob(os.path.join(dir_path, "*.json"))

    # get the list files only
    files = [os.path.basename(f) for f in files]

    # Define the pattern
    pattern = r"macos-hardware-info-(.*?)-(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.\d{6}Z)"

    # Filter the files based on the pattern and sort them
    sorted_files = sorted(
        (f for f in files if re.match(pattern, f)),
        key=lambda f: datetime.datetime.strptime(
            re.search(pattern, f).group(2), "%Y-%m-%dT%H-%M-%S.%fZ"
        ),
    )

    # Now sorted_files contains the sorted list of filenames
    if len(sorted_files):
        print("found the following files in ", dir_path)
        for file in sorted_files:
            print(file)
        return os.path.join(dir_path, sorted_files[-1])
    return []


def save_config_to_file(config_data, file_path):
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(config_data, file, indent=4)


def main():
    indaleko_create_secure_directories()  # make sure they exist.
    parser = argparse.ArgumentParser(
        "Generating Mac Hardware Info Generator",
        "python MacHardwareInfoGenerator.py --dir save_at_path",
    )
    parser.add_argument(
        "--save-to-dir",
        "-d",
        default=indaleko_default_config_dir,
        type=str,
        help=f"path to the directory we want to save the directory (default={indaleko_default_config_dir})",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.save_to_dir):
        print(f"Given dir path is not valid, got: {args.save_to_dir}")
        return

    generator = MacHardwareInfoGenerator()

    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H-%M-%S.%fZ")
    guid = uuid.uuid4().__str__()

    config_data = generator.generate_config(str(guid))

    ## The following makes the code crash if uncommented.
    # if args.skip:
    #     print('checking if we need to create a new config ...')
    #     # search config directory for mac-hardware-info
    #     latest_config_file = find_all_config_files(args.save_to_dir)

    #     latest_config = None
    #     if latest_config_file:
    #         latest_config = MacHardwareInfoGenerator.read_config_from_file(
    #             latest_config_file)

    #         if latest_config:
    #             latest_config['MachineGuid'] = guid
    #             if latest_config == config_data:
    #                 print('Config is the same! Skip creating a new one')
    #                 return
    #         else:
    #             print(f"Warning: the latest config file seems to be an invalid json file, path={
    #                   latest_config_file}. Saving a new config ...")

    file_path = os.path.join(
        args.save_to_dir, f"macos-hardware-info-{guid}-{timestamp}.json"
    )
    save_config_to_file(config_data, file_path)

    print(f"Configuration saved to: {file_path}")


if __name__ == "__main__":
    main()
