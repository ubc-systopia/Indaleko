import os, shutil, sys
import json
import random
from datetime import datetime

def generate_random_number(digits):
    rand_digits = ''.join(random.choices('0123456789', k=digits))
    return rand_digits

def generate_UUID():
    uuid = generate_random_number(8) + "-" + generate_random_number(4) + "-" + generate_random_number(4) + "-" + generate_random_number(4) + "-" + generate_random_number(12)
    return uuid

#writes generated metadata in json file
def write_json(machine_config: dict, json_path: str) -> None:
    with open(json_path, 'w') as json_file:
        json.dump(machine_config, json_file, indent=4)

def generate_volume_info() -> dict:
    num_parition = random.randint(2,4)
    volume_list = []
    size = 3072 / num_parition
    filesystem = "apfs"
    for i in range(num_parition):
        disk_name = "disk1" + str(i)
        volume = {
            "UniqueId": "/dev/" + disk_name,
            "VolumeName": disk_name,
            "Size": str(size) + "GB",
            "Filesystem": filesystem
        }
        volume_list.append(volume)
    return volume_list

# main function to run the metadata generator
def generate_machine_config() -> dict:
    uuid = generate_UUID()
    volume_info = generate_volume_info()
    record_timestamp = datetime.now().isoformat()

    name = "macos-hardware-info-" + uuid + record_timestamp + ".json" 
    machine_config = {
        "MachineGuid": uuid,
        "OperatingSystem": {
            "Caption": "macOS",
            "OSArchitecture": "x86_64",
            "Version": "23.3.0"
        },
        "CPU": {
            "Name": "i" + str(random.randint(100,999)),
            "Cores": random.randint(2,6)
        },
        "VolumeInfo": volume_info
    }

    return [name, machine_config]

def main():
    name, config = generate_machine_config()
    config_path = "config/" + name 
    write_json(config, config_path)


if __name__ == '__main__':
    main()