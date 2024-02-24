import os
import json
import uuid
import datetime
import psutil
import argparse

class MacHardwareInfoGenerator:
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


def save_config_to_file(config_data, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(config_data, file, indent=4)


def main():
    parser = argparse.ArgumentParser('Generating Mac Hardware Info Generator', 'python MacHardwareInfoGenerator.py --dir save_at_path')
    parser.add_argument('--save-to-dir', '-d',  help='path to the directory we want to save the directory')
    args = parser.parse_args()

    if not os.path.isdir(args.save_to_dir): 
        print(f'Given dir path is not valid, got: {parser.save_to_dir}')
        return

    timestamp=datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%dT%H-%M-%S.%fZ')
    guid=uuid.uuid4()

    generator = MacHardwareInfoGenerator()
    config_data = generator.generate_config(str(guid))

    file_path = os.path.join(args.save_to_dir, f'macos-hardware-info-{guid}-{timestamp}.json')
    save_config_to_file(config_data, file_path)

    print(f"Configuration saved to: {file_path}")


if __name__ == "__main__":
    main()
