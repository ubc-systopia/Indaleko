'''
Sets up the environment for Indaleko.

Project Indaleko
Copyright (C) 2024 Tony Mason

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
'''

import argparse
import os
import pathlib
import sys
import subprocess
import shutil
import tempfile

from typing import Union

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'pyproject.toml')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

class SetupIndalekoDevelopmentEnvironment:
    '''This class is used to set up the development environment for Indaleko.'''

    def __init__(self, **kwargs):
        '''Initialize the class.'''
        self.venv_name = None
        self.venv_command = None
        self.cwd = os.getcwd()
        for key, value in kwargs.items():
            setattr(self, key, value)

    def install_uv_windows(self) -> bool:
        '''Install the uv package on Windows.'''
        print('Installing uv on Windows')
        try:
            with tempfile.TemporaryFile() as temp_file:
                # powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
                subprocess.run(
                    [
                        "powershell",
                        "-ExecutionPolicy",
                        "ByPass",
                        "-c",
                        "irm https://astral.sh/uv/install.ps1 | iex"
                    ],
                    check=True,
                    stdout=temp_file
                )
                temp_file.seek(0)
                for line in temp_file.readlines():
                    line=line.decode('utf-8')
                    print(line)
                    if 'Installing to ' in line:
                        install_dir = line.split()[-1]
                        print(f"Installed to {install_dir}")
                        if install_dir not in os.environ['PATH']:
                            os.environ['PATH'] += os.pathsep + install_dir
                            print(f'You will need to add {install_dir} to your PATH.  Adding it temporarily now.')

            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to install 'uv': {e}")
            return False

    def install_uv_linux(self) -> bool:
        '''Install the uv package on Linux.'''
        try:
            with tempfile.TemporaryFile() as temp_file:
                # curl -fsSL https://astral.sh/uv/install.sh | sh
                curl_process = subprocess.Popen(
                    [
                        "curl",
                        "-LsSf",
                        "https://astral.sh/uv/install.sh"
                    ],
                    stdout=subprocess.PIPE
                )
                sh_process = subprocess.Popen(
                    ["sh"],
                    stdin=curl_process.stdout, stdout=temp_file
                )
                curl_process.stdout.close()
                sh_process.communicate()
                temp_file.seek(0)
                for line in temp_file.readlines():
                    line=line.decode('utf-8')
                    if 'installing to ' in line:
                        install_dir = line.split()[-1]
                        print(f"Installed to {install_dir}")
                        if install_dir not in os.environ['PATH']:
                            os.environ['PATH'] += os.pathsep + install_dir
                            print(f'You will need to add {install_dir} to your PATH.  Adding it temporarily now.')

            # curl -fsSL https://astral.sh/uv/install.sh | sh
            curl_process = subprocess.Popen(["curl", "-LsSf", "https://astral.sh/uv/install.sh"], stdout=subprocess.PIPE)
            sh_process = subprocess.Popen(["sh"], stdin=curl_process.stdout)
            curl_process.stdout.close()  # Allow curl_process to receive a SIGPIPE if sh_process exits
            sh_process.communicate()
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to install 'uv': {e}")
            return False

    def install_uv_darwin(self) -> bool:
        '''
        Install the uv package on macOS.
        Note: at least for now, this is the same as Linux.
        '''
        return self.install_uv_linux()

    def install_uv(self) -> None:
        """
        Installs the 'uv' package if it is not already installed.

        Note: Exits the script if installation fails.
        """
        try:
            subprocess.run(
                [
                    'uv',
                    '--version'
                ],
                check=True
            )
            # if we get here, then it is installed
            return
        except (subprocess.CalledProcessError, FileNotFoundError):
            print('UV is not installed, attempting to install it now.')
        system = sys.platform
        if system.startswith('win'):
            return self.install_uv_windows()
        elif system.startswith('linux'):
            return self.install_uv_linux()
        elif system.startswith('darwin'):
            return self.install_uv_darwin()
        else:
            print(f"Unsupported platform: {system}")
            sys.exit(1)

    def check_python_version(self, min_version=(3, 12)):
        """Ensure Python version is at least 3.12."""
        if sys.version_info < min_version:
            min_version_str = f"{min_version[0]}.{min_version[1]}"
            print(f"Error: Python {min_version_str} or higher is required to run this script.")
            sys.exit(1)
        else:
            print(f"Using Python {sys.version_info.major}.{sys.version_info.minor}, which is acceptable.")

    def compute_venv_name(self, platform : str = None, python_version : tuple = None) -> str:
        '''
        This routine constructs a virtual environment name that incorporates
        the platform and python version information.

        Inputs:
            platform: str: The platform to use for the virtual environment name.
            If this is None, the current platform is used.

            python_version: str: The Python version to use for the virtual environment name.
            If this is None, the current Python version is used.

        Returns:
            str: The name of the virtual environment.
        '''
        if self.venv_name is not None:
            return self.venv_name
        if platform is None:
            platform = sys.platform
        if python_version is None:
            python_version = (sys.version_info.major, sys.version_info.minor)
        self.venv_name = f".venv-{platform}-python{python_version[0]}.{python_version[1]}"
        return self.venv_name


    def check_or_create_virtualenv(self,
                                   platform : str = None,
                                   python_version : str = None) -> None:
        '''Check if a virtual environment exists and create one if it does not.'''
        if platform is None:
            platform = sys.platform
        if python_version is None:
            python_version = (sys.version_info.major, sys.version_info.minor)
        if not hasattr(sys, 'real_prefix')\
        and not (hasattr(sys, 'base_prefix')\
        and sys.base_prefix != sys.prefix):
            print(f"No virtual environment detected. Creating one with 'uv' using Python {sys.version}...")
            if not pathlib.Path('pyproject.toml').exists():
                try:
                    subprocess.run(
                        [
                            "uv",
                            "venv",
                            self.compute_venv_name(
                                platform=platform,
                                python_version=python_version
                            ),
                            "--python",
                            f"python{python_version[0]}.{python_version[1]}"
                        ],
                        check=True
                    )
                except subprocess.CalledProcessError as e:
                    print(f"Failed to create virtual environment: {e}")
                    sys.exit(1)
            try:
                subprocess.run(
                    [
                        "uv",
                        "venv",
                        self.compute_venv_name(
                            platform=platform,
                            python_version=python_version
                        ),
                    ],
                    check=True
                )
            except subprocess.CalledProcessError as e:
                print(f"Failed to create virtual environment: {e}")
                sys.exit(1)
        if sys.platform.startswith('win'):
            self.venv_command = os.path.join(self.cwd, self.venv_name, 'Scripts', 'activate')
        else:
            self.venv_command = os.path.join(self.cwd, self.venv_name, 'bin', 'activate')

    def handle_lock_file(
            self,
            lock_file : str = None,
            reset_lock_file : bool = False):
        """Handle the creation or usage of the .uv.lock file."""
        platform_identifier = sys.platform
        platform_lock_file = f".uv.{platform_identifier}.lock"
        main_lock_file = ".uv.lock"
        if lock_file is not None:
            if not os.path.exists(lock_file):
                print(f"Error: Lock file {lock_file} does not exist.")
                sys.exit(1)
            main_lock_file = lock_file
        print(f"Using lock file: {main_lock_file}")

        if reset_lock_file and pathlib.Path(main_lock_file).exists():
            os.remove(main_lock_file)
            print(f"Removed lock file: {main_lock_file}")

        if not pathlib.Path(main_lock_file).exists():
            # Attempt to use the platform-specific lock file
            if os.path.exists(platform_lock_file):
                shutil.copy(platform_lock_file, main_lock_file)
                print(f"Using platform-specific lock file: {platform_lock_file}")
            else:
                # No platform lock file found; ask if user wants to create one
                existing_lock_files = set(f for f in os.listdir() if 'lock' in f)
                try:
                    subprocess.run(
                        [
                            "uv",
                            "lock",
                        ],
                        check=True
                    )
                except subprocess.CalledProcessError as e:
                    print(f"Failed to create platform lock file: {e}")
                    sys.exit(1)
                current_lock_files = set(f for f in os.listdir() if 'lock' in f)
                new_lock_files = current_lock_files - existing_lock_files
                if len(new_lock_files) != 1:
                    print(f"Error: Expected one new lock file, found {len(new_lock_files)}")
                    print(f'Before: {existing_lock_files}')
                    print(f'After: {current_lock_files}')
                    sys.exit(1)
                new_lock_file = new_lock_files.pop()
                pathlib.Path(new_lock_file).rename(platform_lock_file)
        else:
            print(f"Using existing lock file: {main_lock_file}")

    def install_dependencies(
        self,
        platform : str = None,
        python_version : tuple = None) -> None:
        """Install project dependencies using 'uv'."""
        try:
            venv_name = self.compute_venv_name(
                platform=platform,
                python_version=python_version
            )
            os.environ['VIRTUAL_ENV'] = venv_name
            subprocess.run(
                [
                    "uv",
                    "pip",
                    "install",
                    "--requirement",
                    "pyproject.toml"
                ],
                check=True)
            print("Environment setup complete.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install environment: {e}")
            print('Please verify internet connectivity, as that is a common source of this error.')
            sys.exit(1)

    def find_best_lockfile(self) -> Union[str, None]:
        '''
        Find the best lock file to use in the current directory.

        Returns:
            str: The best lock file to use.
            None: no lock files were found.
        '''
        lock_files = [f for f in os.listdir() if 'lock' in f]
        best_lockfile = None
        for lockfile in lock_files:
            if sys.platform in lockfile:
                best_lockfile = lockfile
                break
        if best_lockfile is not None:
            return best_lockfile
        for lockfile in lock_files:
            if '.uv.lock' == lockfile\
                or 'uv.lock' == lockfile:
                best_lockfile = lockfile
                break
        if best_lockfile is not None:
            return best_lockfile
        if len(lock_files) > 0:
            return lock_files.pop()
        return None

    def get_venv_activation_command(self) -> str:
        '''Get the command to activate the virtual environment based on the current platform.'''
        if sys.platform.startswith('win'):
            return f'{self.cwd}\\{self.venv_name}\\Scripts\\activate'
        return f'source {self.cwd}/{self.venv_name}/bin/activate'

    def main(self):
        '''Handle installation for the development environment.'''
        # First, let's see what lock files already exist.
        default_lock_file = self.find_best_lockfile()
        parser = argparse.ArgumentParser(description="Setup environment for the project.")
        parser.add_argument(
            '--python-version',
            type=str,
            default="3.12",
            help="Specify the Python version to use for the virtual environment."
        )
        parser.add_argument(
            '--force-install',
            action='store_true',
            help="Force reinstall 'uv' package."
        )
        parser.add_argument(
            '--lock-file',
            type=str,
            default=default_lock_file,
            help=f"Specify a custom lock file to use. Default is {default_lock_file}"
        )
        parser.add_argument(
            '--reset-lock-file',
            action='store_true',
            help="Reset the lock file to the platform-specific lock file."
        )
        args = parser.parse_args()

        print(args)

        # Step 1: Check to see if the python version is supported
        print('Checking python version:')
        self.check_python_version()
        print(f'Python version {sys.version_info} is supported')

        # Step 2: Check if 'uv' is installed
        print('Checking if uv is installed:')
        self.install_uv()
        print('uv is installed')

        # Step 3: Ensure we're either in a virtual environment with Python 3.12 or create one
        print('Checking for virtual environment:')
        self.check_or_create_virtualenv()
        print('Virtual environment created')

        # Step 4: Handle lock file construction based on existing files and user input
        print('Checking lock file:')
        if args.lock_file:
            print(f'Using custom lock file: {args.lock_file}')
        self.handle_lock_file(
            lock_file = args.lock_file,
            reset_lock_file = args.reset_lock_file)
        if args.reset_lock_file:
            print('Lock file reset')
        print('Lock file checked')

        # Step 5: Install dependencies with 'uv'
        print('Installing dependencies:')
        self.install_dependencies()
        print('Dependencies installed')

        # Final Step: Guide the user on next steps
        print("\nNext steps:")
        print("1. Activate the virtual environment if it's not already active: " + self.get_venv_activation_command())
        # TODO: Add instructions for activating the virtual environment, since this is platform-specific
        print(f"2. Run 'python {os.getcwd()}/db/db_config.py' to verify the database is set up properly.")
        print(f'   If it is not set up, you will need to run the setup script: python {os.getcwd()}/db/db_setup.py')
        print("3. Refer to the README for more detailed instructions.")

def main() -> None:
    '''Main entry point for the setup environment script.'''
    setup = SetupIndalekoDevelopmentEnvironment()
    setup.main()

if __name__ == "__main__":
    cwd = os.getcwd()
    os.chdir(os.environ['INDALEKO_ROOT'])
    main()
    os.chdir(cwd)
