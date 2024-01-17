'''
This module is used to manage the Linux Machine configuration information.
'''
import subprocess
import argparse
import json
import uuid

from IndalekoMachineConfig import IndalekoMachineConfig

class IndalekoLinuxMachineConfig(IndalekoMachineConfig):
    '''
    The IndalekoLinuxMachineConfig class is used to capture information about a
    Linux machine.  It is a specialization of the IndalekoMachineConfig class,
    which is shared across all platforms.
    '''

    linux_machine_config_file_prefix='linux-hardware-info'
    linux_machine_config_uuid_str='c18f5758-357e-46d2-ba60-67720deaac5f'
    linux_machine_config_service_name='Linux Machine Configuration'
    linux_machine_config_service_description='Linux Machine Configuration Service'
    linux_machine_config_service_version='1.0'

    linux_machine_config_service = {
        'service_name': linux_machine_config_service_name,
        'service_description': linux_machine_config_service_description,
        'service_version': linux_machine_config_service_version,
        'service_type': 'Machine Configuration',
        'service_identifier': linux_machine_config_uuid_str,
    }

    @staticmethod
    def execute_command(command):
        '''
        Execute a command and return the output.
        '''
        if not isinstance(command, list):
            raise Exception(f"Command must be a list: {command}")
        try:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT)
            return output.decode().strip()
        except subprocess.CalledProcessError as error:
            raise Exception(f"Error executing {command}: {error.output.decode().strip()}")

    @staticmethod
    def gather_system_information():
        system_info = {}
        system_info['UUID'] = str(uuid.UUID(open('/etc/machine-id').read().strip()))
        return system_info

    @staticmethod
    def parse_ip_addr_output():
        output = IndalekoLinuxMachineConfig.execute_command(['ip', '-c', 'addr'])
        interfaces = {}
        current_interface = None

        for line in output.split('\n'):
            print(f"Line: {line}")
            if 'mtu' in line:
                print('New interface found')
                # New interface found, extract its name and initialize its characteristics list
                # current_interface = line.split(':')[1].strip()
                #interfaces[current_interface] = []
            # elif current_interface:
                # Add characteristics to the current interface
                # interfaces[current_interface].append(line.strip())
        return interfaces


    @staticmethod
    def extract_some_data1():
        cpu_data = {
            l.split(':')[0].strip() : l.split(':')[1].strip() \
                for l in IndalekoLinuxMachineConfig.execute_command(['lscpu']).split('\n')
        }
        ram_data = {
            l.split(':')[0].strip() : l.split(':')[1].strip() \
                for l in open('/proc/meminfo', 'r').readlines()
        }
        disk_data = {
            l.split(':')[0].strip() : l.split(':')[1].strip() \
                for l in IndalekoLinuxMachineConfig.execute_command(['blkid']).split('\n')
        }
        net_data = IndalekoLinuxMachineConfig.parse_ip_addr_output()
        return cpu_data, ram_data, disk_data, net_data

def main():
    parse = argparse.ArgumentParser()
    parse.add_argument('--configdir', type=str, default='./config', help='Directory where configuration data is written.')
    args = parse.parse_args()
    print(f"Config dir: {args.configdir}")
    print(json.dumps(IndalekoLinuxMachineConfig.gather_system_information(),indent=4))
    cpu_data, ram_data, disk_data, net_data = IndalekoLinuxMachineConfig.extract_some_data1()
    #print(json.dumps(cpu_data, indent=4))
    #print(json.dumps(ram_data, indent=4))
    #print(json.dumps(disk_data, indent=4))
    print(json.dumps(net_data, indent=4))


if __name__ == '__main__':
    main()

