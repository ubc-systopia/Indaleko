"""
This module defines the locally installed database support.

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
from datetime import datetime, timezone
import os
import sys

from icecream import ic
from typing import Union

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from constants import IndalekoConstants
from db import IndalekoDBConfig
from data_models.db_config import (
    IndalekoDBConfigDataModel,
    IndalekoDBConfigUserDataModel,
    IndalekoDBConfigDockerConfigurationDataModel,
)

# from utils import IndalekoDocker, IndalekoLogging, IndalekoSingleton
# from utils.data_validation import validate_ip_address, validate_hostname
from utils.misc.directory_management import indaleko_default_config_dir

# import utils.misc.file_name_management
# pylint: enable=wrong-import-position


class IndalekoDBLocal:
    """
    Class used to manage local installations of the database.
    """

    def __init__(
        self, config_data: Union[None, IndalekoDBConfigDataModel] = None
    ) -> None:
        """
        Set up the docker configuration for the database.

        * config_data: the configuration data for the installation, if any.

        If no configuration data is provided, a docker based configuration
        will be created.
        """
        self.config_data = config_data
        if config_data is None:
            self.generate_new_config()

    def generate_new_config(self) -> None:
        """Generate a new configuration for the docker database."""
        self.config_data = IndalekoDBLocal.generate_docker_config()

    @staticmethod
    def generate_remote_config(
        admin_password: str,
        db_user: str,
        db_password: str,
        port: int = 8529,
        ssl: bool = True,
        hostname: str = "activitycontext.work",
        timestamp: datetime = datetime.now(timezone.utc),
        admin_user: str = "root",
    ) -> IndalekoDBConfigDataModel:
        """Generate remote configuration data."""
        new_config_data = {
            "Timestamp": timestamp,
            "Docker": False,
            "Local": False,
            "Name": IndalekoConstants.project_name,
            "AdminUser": IndalekoDBConfigUserDataModel(
                Name=admin_user, Password=admin_password
            ),
            "DBUser": IndalekoDBConfigUserDataModel(
                Name=db_user,
                Password=db_password,
            ),
            "Hostname": hostname,
            "Port": port,
        }
        if ssl:
            new_config_data["SSL"] = True
        return IndalekoDBConfigDataModel(**new_config_data)

    @staticmethod
    def generate_local_config(
        hostname: str = "localhost",
        port: int = 8529,
        ssl: bool = False,
        timestamp: datetime = datetime.now(timezone.utc),
    ) -> IndalekoDBConfigDataModel:
        """Generate a new docker configuration."""
        new_config_data = {
            "Timestamp": timestamp,
            "Docker": True,
            "Local": False,
            "Name": IndalekoConstants.project_name,
            "AdminUser": IndalekoDBConfigUserDataModel(
                Name="root", Password=IndalekoDBConfig.generate_random_password()
            ),
            "DBUser": IndalekoDBConfigUserDataModel(
                Name=IndalekoDBConfig.generate_random_username(),
                Password=IndalekoDBConfig.generate_random_password(),
            ),
            "DockerConfiguration": IndalekoDBConfigDockerConfigurationDataModel(
                ContainerName=f"arango-{IndalekoConstants.default_prefix}-"
                f"{timestamp.strftime('%Y%m%d%H%M%S')}",
                VolumeName=f"{IndalekoConstants.default_prefix}-db-1-"
                f"{timestamp.strftime('%Y%m%d%H%M%S')}",
            ),
            "Hostname": hostname,
            "Port": port,
        }
        if ssl:
            new_config_data["SSL"] = True
        return IndalekoDBConfigDataModel(**new_config_data)


def main2():
    """Construct a new configuration file."""
    parser = argparse.ArgumentParser(description="Indaleko DB Configuration Generator.")
    parser.add_argument(
        "--hostname", help="Hostname for the database", default="localhost"
    )
    parser.add_argument("--port", help="Port for the database", default=8529)
    parser.add_argument("--ssl", help="Use SSL", default=False, action="store_true")
    parser.add_argument(
        "--timestamp",
        help="Timestamp for the configuration",
        default=datetime.now(timezone.utc),
    )
    parser.add_argument(
        "--admin_user", help="Admin user for the database", default="root"
    )
    parser.add_argument(
        "--admin_password",
        help="Admin password for the database",
        default=IndalekoDBConfig.generate_random_password(),
    )
    parser.add_argument(
        "--db_user",
        help="Database user for the database",
        default=IndalekoDBConfig.generate_random_username(),
    )
    parser.add_argument(
        "--docker", help="Use Docker", default=False, action="store_true"
    )
    args = parser.parse_args()
    ic(args)


def add_command(args: argparse.Namespace) -> None:
    """List the current configuration files."""
    ic("add")
    ic(args)


def list_command(args: argparse.Namespace) -> None:
    """List the current configuration files."""
    ic("list")
    ic(args)


def main():
    """Construct a new docker configuration for the database."""
    parser = argparse.ArgumentParser(description="Indaleko DB Configuration Generator.")
    parser.add_argument(
        "--config_dir",
        help="Configuration directory to use",
        default=indaleko_default_config_dir,
    )
    subparsers = parser.add_subparsers(
        dest="command", title="command", help="Command to execute"
    )
    list_parser = subparsers.add_parser(
        "list", help="List the current configuration files."
    )
    list_parser.set_defaults(func=list_command)
    add_parser = subparsers.add_parser("add", help="Add a new configuration file.")
    add_parser.add_argument(
        "--hostname", help="Hostname for the database", default="localhost"
    )
    add_parser.add_argument("--port", help="Port for the database", default=8529)
    add_parser.add_argument("--ssl", help="Use SSL", default=False, action="store_true")
    add_parser.add_argument(
        "--timestamp",
        help="Timestamp for the configuration",
        default=datetime.now(timezone.utc),
    )
    add_parser.add_argument(
        "--admin_user", help="Admin user for the database", default="root"
    )
    add_parser.add_argument(
        "--admin_password",
        help="Admin password for the database",
        default=IndalekoDBConfig.generate_random_password(),
    )
    add_parser.add_argument(
        "--db_user",
        help="Database user for the database",
        default=IndalekoDBConfig.generate_random_username(),
    )
    add_parser.add_argument(
        "--docker", help="Use Docker", default=False, action="store_true"
    )
    add_parser.set_defaults(func=add_command)
    args = parser.parse_args()
    ic(args)
    args.func(args)


if __name__ == "__main__":
    main()
