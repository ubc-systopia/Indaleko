"""
Sets up the environment for Indaleko.

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
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "pyproject.toml")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


class SetupIndalekoDevelopmentEnvironment:
    """This class is used to set up the development environment for Indaleko."""

    def __init__(self, **kwargs) -> None:
        """Initialize the class."""
        self.venv_name = None
        self.venv_command = None
        self.cwd = os.getcwd()
        for key, value in kwargs.items():
            setattr(self, key, value)

    def install_uv_windows(self) -> bool:
        """Install the uv package on Windows."""
        try:
            with tempfile.TemporaryFile() as temp_file:
                # powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
                subprocess.run(
                    [
                        "powershell",
                        "-ExecutionPolicy",
                        "ByPass",
                        "-c",
                        "irm https://astral.sh/uv/install.ps1 | iex",
                    ],
                    check=True,
                    stdout=temp_file,
                )
                temp_file.seek(0)
                for line in temp_file.readlines():
                    line = line.decode("utf-8")
                    if "Installing to " in line:
                        install_dir = line.split()[-1]
                        if install_dir not in os.environ["PATH"]:
                            os.environ["PATH"] += os.pathsep + install_dir

            return True
        except subprocess.CalledProcessError:
            return False

    def install_uv_linux(self) -> bool:
        """Install the uv package on Linux."""
        try:
            with tempfile.TemporaryFile() as temp_file:
                # curl -fsSL https://astral.sh/uv/install.sh | sh
                curl_process = subprocess.Popen(
                    ["curl", "-LsSf", "https://astral.sh/uv/install.sh"],
                    stdout=subprocess.PIPE,
                )
                sh_process = subprocess.Popen(
                    ["sh"],
                    stdin=curl_process.stdout,
                    stdout=temp_file,
                )
                curl_process.stdout.close()
                sh_process.communicate()
                temp_file.seek(0)
                for line in temp_file.readlines():
                    line = line.decode("utf-8")
                    if "installing to " in line:
                        install_dir = line.split()[-1]
                        if install_dir not in os.environ["PATH"]:
                            os.environ["PATH"] += os.pathsep + install_dir

            # curl -fsSL https://astral.sh/uv/install.sh | sh
            curl_process = subprocess.Popen(
                ["curl", "-LsSf", "https://astral.sh/uv/install.sh"],
                stdout=subprocess.PIPE,
            )
            sh_process = subprocess.Popen(["sh"], stdin=curl_process.stdout)
            curl_process.stdout.close()  # Allow curl_process to receive a SIGPIPE if sh_process exits
            sh_process.communicate()
            return True
        except subprocess.CalledProcessError:
            return False

    def install_uv_darwin(self) -> bool:
        """
        Install the uv package on macOS.
        Note: at least for now, this is the same as Linux.
        """
        return self.install_uv_linux()

    def install_uv(self) -> None:
        """
        Installs the 'uv' package if it is not already installed.

        Note: Exits the script if installation fails.
        """
        try:
            subprocess.run(["uv", "--version"], check=True)
            # if we get here, then it is installed
            return None
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        system = sys.platform
        if system.startswith("win"):
            return self.install_uv_windows()
        if system.startswith("linux"):
            return self.install_uv_linux()
        if system.startswith("darwin"):
            return self.install_uv_darwin()
        sys.exit(1)

    def check_python_version(self, min_version=(3, 12)) -> None:
        """Ensure Python version is at least 3.12."""
        if sys.version_info < min_version:
            f"{min_version[0]}.{min_version[1]}"
            sys.exit(1)
        else:
            pass

    def compute_venv_name(
        self,
        platform: str | None = None,
        python_version: tuple | None = None,
    ) -> str:
        """
        This routine constructs a virtual environment name that incorporates
        the platform and python version information.

        Inputs:
            platform: str: The platform to use for the virtual environment name.
            If this is None, the current platform is used.

            python_version: str: The Python version to use for the virtual environment name.
            If this is None, the current Python version is used.

        Returns:
            str: The name of the virtual environment.
        """
        if self.venv_name is not None:
            return self.venv_name
        if platform is None:
            platform = sys.platform
        if python_version is None:
            python_version = (sys.version_info.major, sys.version_info.minor)
        self.venv_name = f".venv-{platform}-python{python_version[0]}.{python_version[1]}"
        return self.venv_name

    def check_or_create_virtualenv(
        self,
        platform: str | None = None,
        python_version: str | None = None,
    ) -> None:
        """Check if a virtual environment exists and create one if it does not."""
        if platform is None:
            platform = sys.platform
        if python_version is None:
            python_version = (sys.version_info.major, sys.version_info.minor)
        if not hasattr(sys, "real_prefix") and not (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix):
            if not pathlib.Path("pyproject.toml").exists():
                try:
                    subprocess.run(
                        [
                            "uv",
                            "venv",
                            self.compute_venv_name(
                                platform=platform,
                                python_version=python_version,
                            ),
                            "--python",
                            f"python{python_version[0]}.{python_version[1]}",
                        ],
                        check=True,
                    )
                except subprocess.CalledProcessError:
                    sys.exit(1)
            try:
                subprocess.run(
                    [
                        "uv",
                        "venv",
                        self.compute_venv_name(
                            platform=platform,
                            python_version=python_version,
                        ),
                    ],
                    check=True,
                )
            except subprocess.CalledProcessError:
                sys.exit(1)
        if sys.platform.startswith("win"):
            self.venv_command = os.path.join(
                self.cwd,
                self.venv_name,
                "Scripts",
                "activate",
            )
        else:
            self.venv_command = os.path.join(
                self.cwd,
                self.venv_name,
                "bin",
                "activate",
            )

    def handle_lock_file(self, lock_file: str | None = None, reset_lock_file: bool = False) -> None:
        """Handle the creation or usage of the .uv.lock file."""
        platform_identifier = sys.platform
        platform_lock_file = f".uv.{platform_identifier}.lock"
        main_lock_file = ".uv.lock"
        if lock_file is not None:
            if not os.path.exists(lock_file):
                sys.exit(1)
            main_lock_file = lock_file

        if reset_lock_file and pathlib.Path(main_lock_file).exists():
            os.remove(main_lock_file)

        if not pathlib.Path(main_lock_file).exists():
            # Attempt to use the platform-specific lock file
            if os.path.exists(platform_lock_file):
                shutil.copy(platform_lock_file, main_lock_file)
            else:
                # No platform lock file found; ask if user wants to create one
                existing_lock_files = {f for f in os.listdir() if "lock" in f}
                try:
                    subprocess.run(
                        [
                            "uv",
                            "lock",
                        ],
                        check=True,
                    )
                except subprocess.CalledProcessError:
                    sys.exit(1)
                current_lock_files = {f for f in os.listdir() if "lock" in f}
                new_lock_files = current_lock_files - existing_lock_files
                if len(new_lock_files) != 1:
                    sys.exit(1)
                new_lock_file = new_lock_files.pop()
                pathlib.Path(new_lock_file).rename(platform_lock_file)
        else:
            pass

    def install_dependencies(
        self,
        platform: str | None = None,
        python_version: tuple | None = None,
    ) -> None:
        """Install project dependencies using 'uv'."""
        try:
            venv_name = self.compute_venv_name(
                platform=platform,
                python_version=python_version,
            )
            os.environ["VIRTUAL_ENV"] = venv_name
            subprocess.run(
                ["uv", "pip", "install", "--requirement", "pyproject.toml"],
                check=True,
            )
        except subprocess.CalledProcessError:
            sys.exit(1)

    def find_best_lockfile(self) -> str | None:
        """
        Find the best lock file to use in the current directory.

        Returns:
            str: The best lock file to use.
            None: no lock files were found.
        """
        lock_files = [f for f in os.listdir() if "lock" in f]
        best_lockfile = None
        for lockfile in lock_files:
            if sys.platform in lockfile:
                best_lockfile = lockfile
                break
        if best_lockfile is not None:
            return best_lockfile
        for lockfile in lock_files:
            if lockfile in {".uv.lock", "uv.lock"}:
                best_lockfile = lockfile
                break
        if best_lockfile is not None:
            return best_lockfile
        if len(lock_files) > 0:
            return lock_files.pop()
        return None

    def get_venv_activation_command(self) -> str:
        """Get the command to activate the virtual environment based on the current platform."""
        if sys.platform.startswith("win"):
            return f"{self.cwd}\\{self.venv_name}\\Scripts\\activate"
        return f"source {self.cwd}/{self.venv_name}/bin/activate"

    def main(self) -> None:
        """Handle installation for the development environment."""
        # First, let's see what lock files already exist.
        default_lock_file = self.find_best_lockfile()
        parser = argparse.ArgumentParser(
            description="Setup environment for the project.",
        )
        parser.add_argument(
            "--python-version",
            type=str,
            default="3.12",
            help="Specify the Python version to use for the virtual environment.",
        )
        parser.add_argument(
            "--force-install",
            action="store_true",
            help="Force reinstall 'uv' package.",
        )
        parser.add_argument(
            "--lock-file",
            type=str,
            default=default_lock_file,
            help=f"Specify a custom lock file to use. Default is {default_lock_file}",
        )
        parser.add_argument(
            "--reset-lock-file",
            action="store_true",
            help="Reset the lock file to the platform-specific lock file.",
        )
        args = parser.parse_args()


        # Step 1: Check to see if the python version is supported
        self.check_python_version()

        # Step 2: Check if 'uv' is installed
        self.install_uv()

        # Step 3: Ensure we're either in a virtual environment with Python 3.12 or create one
        self.check_or_create_virtualenv()

        # Step 4: Handle lock file construction based on existing files and user input
        if args.lock_file:
            pass
        self.handle_lock_file(
            lock_file=args.lock_file,
            reset_lock_file=args.reset_lock_file,
        )
        if args.reset_lock_file:
            pass

        # Step 5: Install dependencies with 'uv'
        self.install_dependencies()

        # Final Step: Guide the user on next steps
        # TODO: Add instructions for activating the virtual environment, since this is platform-specific


def main() -> None:
    """Main entry point for the setup environment script."""
    setup = SetupIndalekoDevelopmentEnvironment()
    setup.main()


if __name__ == "__main__":
    cwd = os.getcwd()
    os.chdir(os.environ["INDALEKO_ROOT"])
    main()
    os.chdir(cwd)
