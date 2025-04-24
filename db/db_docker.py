"""
This module defines the docker database support.

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

import os
import sys
from datetime import UTC, datetime

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from constants import IndalekoConstants
from data_models.db_config import (
    IndalekoDBConfigDataModel,
    IndalekoDBConfigDockerConfigurationDataModel,
    IndalekoDBConfigUserDataModel,
)
from db import IndalekoDBConfig

# from utils import IndalekoDocker, IndalekoLogging, IndalekoSingleton
# from utils.data_validation import validate_ip_address, validate_hostname
# from utils.misc.directory_management import indaleko_default_config_dir
# import utils.misc.file_name_management
# pylint: enable=wrong-import-position


class IndalekoDBDocker:
    """
    Class used to manage docker installations of the database.
    """

    def __init__(
        self,
        config_data: None | IndalekoDBConfigDataModel = None,
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
        self.config_data = IndalekoDBDocker.generate_docker_config()

    @staticmethod
    def generate_docker_config(
        hostname: str = "localhost",
        port: int = 8529,
        ssl: bool = False,
        timestamp: datetime = datetime.now(UTC),
    ) -> IndalekoDBConfigDataModel:
        """Generate a new docker configuration."""
        new_config_data = {
            "Timestamp": timestamp,
            "Docker": True,
            "Local": False,
            "Name": IndalekoConstants.project_name,
            "AdminUser": IndalekoDBConfigUserDataModel(
                Name="root",
                Password=IndalekoDBConfig.generate_random_password(),
            ),
            "DBUser": IndalekoDBConfigUserDataModel(
                Name=IndalekoDBConfig.generate_random_username(),
                Password=IndalekoDBConfig.generate_random_password(),
            ),
            "DockerConfiguration": IndalekoDBConfigDockerConfigurationDataModel(
                ContainerName=f"arango-{IndalekoConstants.default_prefix}-{timestamp.strftime('%Y%m%d%H%M%S')}",
                VolumeName=f"{IndalekoConstants.default_prefix}-db-1-{timestamp.strftime('%Y%m%d%H%M%S')}",
            ),
            "Hostname": hostname,
            "Port": port,
        }
        if ssl:
            new_config_data["SSL"] = True
        return IndalekoDBConfigDataModel(**new_config_data)


def main():
    """Construct a new docker configuration for the database."""
    ic("Not yet implemented")


if __name__ == "__main__":
    main()
