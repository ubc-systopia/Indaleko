import platform
import subprocess
import json

class IndalekoWindowsMachine:


    def __init__(self):
        self.platform = platform.system()
        assert self.platform == 'Windows', 'Windows specific configuration requires execution on windows platform'
        self.capture_wmi_data()
        self.capture_partition_data()
        self.capture_volume_data()
        self.capture_machine_data()
        #self.capture_w32_disk_data()
        #self.capture_w32_os_data()
        #self.capture_w32_net_data()

    def capture_wmi_data(self):
        wmi_data_types = self.capture_powershell_output('Get-WmiObject -List')
        w32_wmi_data_types = [x for x in wmi_data_types if x['Name'].startswith('Win32_')]
        self.wmi_data = {}
        for dt in w32_wmi_data_types:
            try:
                self.wmi_data[dt['Name']] = self.capture_powershell_output('Get-WmiObject -Class {}'.format(dt['Name']))
                print('collected data for {}'.format(dt['Name']))
            except:
                # ignore commands that don't work.
                continue
        cim_data_types = [x for x in wmi_data_types if x.startswith('CIM_')]
        self.cim_data = {}
        for dt in cim_data_types:
            try:
                self.cim_data[dt['Name']] = self.capture_powershell_output('Get-WmiObject -Class {}'.format(dt['Name']))
                print('collected data for {}'.format(dt['Name']))
            except:
                #ignore commands that don't work
                continue
        print('WMI data size is {}'.format(len(self.wmi_data)))
        print('CIM data size is {}'.format(len(self.cim_data)))


    def capture_volume_data(self):
        result = subprocess.run(['powershell.exe', 'Get-Volume | ConvertTo-Json'], capture_output=True, text=True)
        assert result.returncode == 0, 'Get-Volume failed ({})'.format(result.returncode)
        self.volume_data = result.stdout

    def capture_partition_data(self):
        result = subprocess.run(
            ['powershell.exe', 'Get-Partition | ConvertTo-Json'], capture_output=True, text=True)
        assert result.returncode == 0, 'Get-Partition failed ({})'.format(
            result.returncode)
        self.partition_data = result.stdout

    def capture_machine_data(self):
        result = subprocess.run(
            ['powershell.exe', '-File', 'windows-hardware-info.ps1'], capture_output=True, text=True)
        assert result.returncode == 0, 'get-windows-machine-info.ps1 failed ({})'.format(result.returncode)
        self.machine_data = result.stdout

    def capture_w32_disk_data(self):
        result = subprocess.run(['powershell.exe', 'Get-WmiObject -Class Win32_LogicalDisk -Filter "DriveType=3" | ConvertTo-Json'], capture_output=True, text=True)
        assert result.returncode == 0, 'Get-WmiObject failed ({})'.format(
            result.returncode)
        self.w32_disk_data = result.stdout

    def capture_w32_processor_data(self):
        result = subprocess.run(
            ['powershell.exe', 'Get-WmiObject -Class Win32_Processor | ConvertTo-Json'], capture_output=True, text=True)
        assert result.returncode == 0, 'Get-WmiObject failed ({})'.format(
            result.returncode)
        self.w32_processor_data = result.stdout


    def capture_w32_os_data(self):
        self.w32_os_data = self.capture_powershell_output(
            'Get-WmiObject -Class Win32_OperatingSystem')


    def capture_w32_net_data(self):
        self.w32_net_data = self.capture_powershell_output(
            'Get-WmiObject -Class Win32_NetworkAdapterConfiguration')


    def capture_powershell_output(self, cmd: str) -> dict:
        result = subprocess.run(['powershell.exe', cmd + ' | ConvertTo-Json'], capture_output=True, text=True)
        assert result.returncode == 0, 'Powershell command {} failed ({})'.format(result.returncode)
        return json.loads(result.stdout)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=str, default='machine-config.json', help='Name of output file for machine configuration data')
    args = parser.parse_args()
    print(args)
    machineinfo = IndalekoWindowsMachine()
    print(machineinfo)


if __name__ == "__main__":
    main()
