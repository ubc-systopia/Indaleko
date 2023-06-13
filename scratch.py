import subprocess

'''
This is just a scratch script for figuring out how to do certain things.
'''

def capture_powershell_output(command: list = ['Get-Partition'], output: str = 'scratch.json'):
    '''Given a command to execute, use the specified shell and capture its
    output'''
    cmd = ' '.join(command) + ' | ConvertTo-Json'
    print(cmd)
    result = subprocess.run(['powershell.exe'] + [cmd], capture_output=True, text=True)
    print(result.stdout)

def foo():
    result = subprocess.run(['powershell.exe', 'Get-Partition | ConvertTo-Json'], capture_output=True, text=True)
    print(result.stdout)

def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=str, default='machine-config.json',
                        help='Name of output file for machine configuration data')
    args = parser.parse_args()
    print(args)
    capture_powershell_output() # ['Get-WmiObject', '-Class', 'Win32_LogicalDisk', '-Filter', '"DriveType=3"'])


if __name__ == "__main__":
    main()
