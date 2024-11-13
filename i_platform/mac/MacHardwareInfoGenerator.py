import glob
import os
import json
import re
import uuid
import datetime
import psutil
import argparse


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
            "Cores": psutil.cpu_count(logical=False)
        }
        volume_info = self.get_volume_info()

        config_data = {
            "MachineGuid": machine_guid,
            "OperatingSystem": os_info,
            "CPU": cpu_info,
            "VolumeInfo": volume_info
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
                    "Filesystem": volume.fstype
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
    pattern = r'macos-hardware-info-(.*?)-(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.\d{6}Z)'

    # Filter the files based on the pattern and sort them
    sorted_files = sorted(
        (f for f in files if re.match(pattern, f)),
        key=lambda f: datetime.datetime.strptime(
            re.search(pattern, f).group(2), '%Y-%m-%dT%H-%M-%S.%fZ')
    )

    # Now sorted_files contains the sorted list of filenames
    if len(sorted_files):
        print('found the following files in ', dir_path)
        for file in sorted_files:
            print(file)
        return os.path.join(dir_path,  sorted_files[-1])
    return []


def save_config_to_file(config_data, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(config_data, file, indent=4)


def main():
    parser = argparse.ArgumentParser('Generating Mac Hardware Info Generator', 'python MacHardwareInfoGenerator.py --dir save_at_path')
    parser.add_argument('--save-to-dir', '-d', default='./config/',  help='path to the directory we want to save the directory')
    args = parser.parse_args()

    if not os.path.isdir(args.save_to_dir): 
        print(f'Given dir path is not valid, got: {args.save_to_dir}')
        return

    generator = MacHardwareInfoGenerator()

    timestamp = datetime.datetime.now(
        datetime.UTC).strftime('%Y-%m-%dT%H-%M-%S.%fZ')
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
        args.save_to_dir, f'macos-hardware-info-{guid}-{timestamp}.json')
    save_config_to_file(config_data, file_path)

    print(f"Configuration saved to: {file_path}")


if __name__ == "__main__":
    main()
