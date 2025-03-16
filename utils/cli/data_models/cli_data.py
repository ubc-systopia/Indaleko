"""
This module defines the base data model used in the CLI components of Indaleko.

Indaleko Windows Local Collector
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

from datetime import datetime, timezone
import logging
import os
import platform
import sys
from typing import Optional, List, Dict, Any, Union
from uuid import UUID

from pydantic import Field, AwareDatetime
from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from constants import IndalekoConstants
from data_models.base import IndalekoBaseModel
from db import IndalekoDBConfig
from utils.misc.directory_management import (
    indaleko_default_config_dir,
    indaleko_default_data_dir,
    indaleko_default_log_dir,
)
from utils.misc.file_name_management import indaleko_file_name_prefix

# pylint: enable=wrong-import-position


class IndalekoBaseCliDataModel(IndalekoBaseModel):
    """Defines the base data model for the CLI"""

    Timestamp: AwareDatetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        title="Timestamp",
        description="The timestamp for the data.",
    )

    RegistrationServiceName: str = Field(
        ...,
        title="RegistrationServiceName",
        description="The registration service name of the running service.",
    )

    FileServiceName: str = Field(
        ...,
        title="FileServiceName",
        description="The file service name of the running service.",
    )

    Platform: Optional[Union[str, None]] = Field(
        default_factory=lambda: platform.system(),
        title="Platform",
        description="The platform for the machine.",
    )

    MachineConfigChoices: List[str] = Field(
        default_factory=list,
        title="MachineConfigChoices",
        description="Available machine configuration files.",
    )

    MachineConfigFile: Optional[Union[str, None]] = Field(
        None,
        title="MachineConfigFile",
        description="The selected machine configuration file.",
    )

    MachineConfigFileKeys: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        title="MachineConfigFileKeys",
        description="Keys for the machine configuration file.",
    )

    StorageId: Optional[UUID] = None

    UserID: Optional[str] = None

    ConfigDirectory: str = indaleko_default_config_dir

    DataDirectory: str = indaleko_default_data_dir

    LogDirectory: str = indaleko_default_log_dir

    InputFileKeys: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        title="InputFileKeys",
        description="Keys for the input file.",
    )

    InputFileChoices: Optional[List[str]] = Field(
        default_factory=list,
        title="InputFileChoices",
        description="Available input files.",
    )

    InputFile: Optional[str] = Field(
        None, title="InputFile", description="The selected input file."
    )

    InputFileKeys: Optional[dict[str, str]] = Field(
        default_factory=dict, title="InputFileKeys", description="Keys for input files."
    )

    OutputFile: Optional[str] = Field(
        None, title="OutputFile", description="The output file."
    )

    OutputFileKeys: Optional[list[str]] = Field(
        default_factory=list,
        title="OutputFileKeys",
        description="Keys for output files.",
    )

    LogFile: Optional[str] = Field(None, title="LogFile", description="The log file.")

    LogLevel: int = Field(logging.DEBUG, title="LogLevel", description="Logging level.")

    Offline: Optional[Union[bool, None]] = Field(
        None, title="Offline", description="Run in offline mode."
    )

    DBConfigChoices: Optional[List[str]] = Field(
        default_factory=list,
        title="DBConfigChoices",
        description="Available database configuration files.",
    )

    DBConfigFile: str = Field(
        IndalekoConstants.default_db_config_file_name,
        title="DBConfigFile",
        description="Database configuration file.",
    )

    FilePrefix: str = Field(
        indaleko_file_name_prefix,
        title="FilePrefix",
        description="Prefix for file names.",
    )

    FileSuffix: str = Field(
        "", title="FileSuffix", description="Suffix for file names."
    )

    FileKeys: Dict[str, str] = Field(
        default_factory=dict,
        title="FileKeys",
        description="These are keys and their values for identifying relevant files.",
    )

    PerformanceDataFile: Optional[Union[str, None]] = Field(
        None,
        title="PerformanceDataFile",
        description="The file to which performance data is written.",
    )

    RecordPerformanceInDB: Optional[Union[bool, None]] = Field(
        None,
        title="RecordPerformanceInDB",
        description="Record performance data in the database.",
    )

    AdditionalPreOptions: Dict[str, Any] = Field(
        default_factory=dict,
        title="AdditionalOptions",
        description="Additional CLI options (added first)",
    )

    AdditionalPostOptions: Dict[str, Any] = Field(
        default_factory=dict,
        title="AdditionalOptions",
        description="Additional CLI options (added last)",
    )

    class Config:
        """Configuration for the base CLI data model"""

        json_schema_extra = {
            "example": {
                "Platform": platform.system(),
                "MachineId": "3d49ea9c-e527-4e29-99b5-9715bbde1148",
                "StorageId": "e45e2942-cced-486e-8800-43e75bfad8b1",
                "ConfigDirectory": indaleko_default_config_dir,
                "DataDirectory": indaleko_default_data_dir,
                "LogDirectory": indaleko_default_log_dir,
                "InputFileChoices": ["file1", "file2"],
                "InputFile": "file1",
                "InputFileKeys": {"key1": "value1", "key2": "value2"},
                "OutputFile": "output.txt",
                "OutputFileKeys": ["key1", "key2"],
                "LogFile": "log.txt",
                "Offline": False,
                "DBConfigChoices": ["db1", "db2"],
                "DBConfigFile": IndalekoDBConfig.default_db_config_file,
                "FilePrefix": indaleko_file_name_prefix,
                "FileSuffix": "",
            }
        }


def main():
    """Test code for the base CLI data model"""
    ic("Testing Base CLI Data Model")
    cli_data = IndalekoBaseCliDataModel()
    ic(cli_data)
    cli_data.test_model_main()


if __name__ == "__main__":
    main()
