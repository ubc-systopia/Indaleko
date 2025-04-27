"""
This module defines the data model for describing the Indaleko Database Configuration.

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
from pydantic import AwareDatetime, BaseModel, Field


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


class IndalekoDBConfigUserDataModel(BaseModel):
    """
    This class defines the data model used for user data information in the database.
    """

    Name: str = Field(..., title="Name", description="The name of the database user.")

    Password: str = Field(
        ...,
        title="Password",
        description="The password of the database user.",
    )


class IndalekoDBConfigDockerConfigurationDataModel(BaseModel):
    """
    This class defines the data model for the Docker database Configuration.
    """

    ContainerName: str = Field(
        ...,
        title="Container Name",
        description="The name of the docker container.",
    )

    VolumeName: str = Field(
        ...,
        title="Volume Name",
        description="The name of the docker volume.",
    )


class IndalekoDBConfigDataModel(BaseModel):
    """
    This class defines the data model for the Indaleko Database Configuration.
    """

    Type: str = Field(
        "arangodb",
        title="DatabaseType",
        description="The type of database being used.",
    )

    Docker: bool = Field(
        False,
        title="Docker",
        description="Whether the database is running in a docker container.",
    )

    Local: bool = Field(
        False,
        title="Local",
        description="Whether the database is running locally.",
    )

    Name: str = Field(
        "Indaleko",
        title="Database Name",
        description="The name of the database being used.",
    )

    Timestamp: AwareDatetime = Field(
        datetime.now(UTC),
        title="Timestamp",
        description="The timestamp of when this configuration was constructed.",
    )

    AdminUser: IndalekoDBConfigUserDataModel
    DBUser: IndalekoDBConfigUserDataModel

    DockerConfiguration: IndalekoDBConfigDockerConfigurationDataModel | None = Field(
        None,
        title="Docker Configuration",
        description="The docker configuration for the database.",
    )

    Hostname: str = Field(
        "localhost",
        title="Hostname where the database is running",
        description="The hostname of the machine where the database is running.",
    )

    Port: int = Field(
        8529,
        title="Port",
        description="The port number for the database.",
    )

    SSL: bool = Field(
        False,
        title="SSL",
        description="Whether the database is using SSL.",
    )

    class Config:
        """Sample configuration data for the data model."""

        json_schema_extra = {
            "example": {
                "Type": "arangodb",
                "Docker": False,
                "Local": True,
                "Name": "Indaleko",
                "Timestamp": datetime.now(UTC).isoformat(),
                "AdminUser": {"Name": "root", "Password": "password"},
                "DBUser": {"Name": "indaleko", "Password": "password"},
                "DockerConfiguration": {
                    "ContainerName": "indaleko",
                    "VolumeName": "indaleko",
                },
                "Hostname": "localhost",
                "Port": 8529,
            },
        }


def main():
    """This allows testing the data model."""
    ic("Testing the DBConfigDataModel")
    db_config_data = IndalekoDBConfigDataModel(
        **IndalekoDBConfigDataModel.Config.json_schema_extra["example"],
    )
    ic(db_config_data.model_dump_json(indent=2, exclude_unset=True, exclude_none=True))
    print(
        db_config_data.model_dump_json(indent=2, exclude_unset=True, exclude_none=True),
    )


if __name__ == "__main__":
    main()
