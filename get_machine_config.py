import platform
import subprocess
import json
import multiprocessing
import datetime
import os
import platform

class IndalekoWindowsMachine:


    def __init__(self):
        self.max_execution_time = 60
        self.platform = platform.system()
        assert self.platform == 'Windows', 'Windows specific configuration requires execution on windows platform'
        self.data = {}
        self.operations = self.l()
        self.operations += self.capture_partition_operations()
        self.operations += self.capture_volume_operations()
        self.operations += self.capture_machine_operations()
        cpu_count = min(multiprocessing.cpu_count(), 48)
        self.pool = multiprocessing.Pool(cpu_count)
        print('24 ', len(self.operations), type(self.operations))
        self.results = self.pool.map(IndalekoWindowsMachine.process_operation, self.operations)
        for item in self.results:
            dt, name, output, exec_time = item
            if len(output) == 0:
                continue # skip
            if dt not in self.data:
                self.data[dt] = {}
            self.data[dt] = (name, output, exec_time)


    @staticmethod
    def process_operation(item: tuple) -> tuple():
        data_class, data_name, command, max_execution_time = item
        start = datetime.datetime.now(datetime.timezone.utc)
        try:
            operation_results = IndalekoWindowsMachine.capture_powershell_output(
                command, max_execution_time)
        except subprocess.TimeoutExpired as e:
            operation_results = {}
        end = datetime.datetime.now(datetime.timezone.utc)
        result = (data_class, data_name, operation_results, str(end - start))
        return result

    def capture_wmi_operations(self):
        operations = []
        wmi_data_types = self.capture_powershell_output('Get-WmiObject -List',
                                                        self.max_execution_time)
        w32_wmi_data_types = [
            x for x in wmi_data_types if x['Name'].startswith('Win32_')]
        cim_data_types = [
            x for x in wmi_data_types if x['Name'].startswith('CIM_')]
        self.data['cim_data'] = {}
        self.data['wim_data'] = {}
        for dt in cim_data_types:
            name = dt['Name']
            operations.append(('cim_data', name, 'Get-WmiObject -Class {}'.format(name), self.max_execution_time))
        for dt in w32_wmi_data_types:
            name = dt['Name']
            operations.append(('wim_data', name, 'Get-WmiObject -Class {}'.format(name), self.max_execution_time))
        return operations

    def capture_partition_operations(self) -> list:
        return [('os_data', 'partition_data', 'Get-Partition', self.max_execution_time)]

    def capture_machine_operations(self):
        return [('-File windows-hardware-info.ps1', 'os_data', 'hardware_data', self.max_execution_time)]

    def capture_volume_operations(self):
        return [('os_data', 'volume_data', 'Get-Volume', self.max_execution_time)]

    def capture_machine_operations(self):
        return [('os_data', 'hardware_data', '-File windows-hardware-info.ps1', self.max_execution_time)]

    @staticmethod
    def capture_powershell_output(cmd: str, max_execution_time: int) -> dict:
        ps_cmd = ['powershell.exe', cmd + ' | ConvertTo-Json']
        result = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=max_execution_time)
        if 0 != result.returncode:
            output = json.loads('{}')
        else:
            try:
                output = json.loads(result.stdout)
            except json.decoder.JSONDecodeError as e:
                output = json.loads('{}')
        return output


class IndalekoLinuxMachine:

    def __init__(self):
        self.platform = platform.system()
        assert self.platform == 'Linux', 'Linux specific configuration requires execution on linux platform'
        self.data = {}


        self.operations = self.capture_linux_operations()
        cpu_count = min(multiprocessing.cpu_count(), 48)
        self.pool = multiprocessing.Pool(cpu_count)
        self.results = self.pool.map(IndalekoLinuxMachine.process_operation, self.operations)
        for item in self.results:
            dt, name, output, exec_time = item
            if len(output) == 0:
                continue


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=str, default='machine-config.json', help='Name of output file for machine configuration data')
    args = parser.parse_args()
    data = {}
    if os.path.exists(args.output):
        with open(args.output, 'rt') as fd:
            data = json.load(fd)
    else:
        start = datetime.datetime.now(datetime.timezone.utc)
        machineinfo = IndalekoWindowsMachine()
        end = datetime.datetime.now(datetime.timezone.utc)
        with open(args.output, 'wt') as fd:
            json.dump(machineinfo.data, fd)
        data = machineinfo.data
    print('Data Captured: {}'.format(len(data)))
    print(' Elapsed Time: {}'.format(end - start))
    print(json.dumps(data, indent=4))


if __name__ == "__main__":
    main()
