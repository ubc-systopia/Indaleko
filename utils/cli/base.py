"""
This module provides a common cli for building utilities.

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
import inspect
import json
import os
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Union

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from constants import IndalekoConstants
from platforms.machine_config import IndalekoMachineConfig
from utils import IndalekoLogging
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
from utils.cli.handlermixin import IndalekoHandlermixin
from utils.misc.file_name_management import (
    extract_keys_from_file_name,
    find_candidate_files,
    generate_file_name,
)

# pylint: enable=wrong-import-position


class IndalekoBaseCLI:
    """Base class for handling main function logic in collectors and recorders"""

    class cli_features:
        """This class provides a set of features requested for the CLI"""

        debug = True
        db_config = True
        machine_config = True
        configdir = db_config or machine_config
        input = True
        offline = True
        output = True
        datadir = input or output
        logging = True
        performance = True
        platform = True

        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                if hasattr(self, key):
                    assert isinstance(
                        value,
                        bool,
                    ), f"Value must be a boolean: {key, value}"
                    setattr(self, key, value)
                else:
                    raise AttributeError(f"Unknown attribute: {key}")

    def __init__(
        self,
        cli_data: IndalekoBaseCliDataModel,
        handler_mixin: IndalekoHandlermixin | None = None,
        features: Union["IndalekoBaseCLI.cli_features", None] = None,
    ) -> None:
        """
        Initialize the main handler with specific service and config classes

        Args:
            service_class: Type of the service (BaseStorageCollector or BaseStorageRecorder subclass)
            machine_config_class: Type of machine configuration (IndalekoMachineConfig subclass)
        """
        assert cli_data, "cli_data must be provided"
        self.features = features
        if not self.features:
            self.features = IndalekoBaseCLI.cli_features()  # default features
        self.config_data = json.loads(cli_data.model_dump_json())
        self.handler_mixin = handler_mixin
        if not self.handler_mixin:
            self.handler_mixin = IndalekoBaseCLI.default_handler_mixin
        self.pre_parser = self.handler_mixin.get_pre_parser()
        for feature in dir(self.cli_features):
            if feature.startswith("__"):
                continue
            if not getattr(self.features, feature, self.cli_features.__dict__[feature]):
                # this feature is disabled
                continue
            if not getattr(self.cli_features, feature, False):
                ic(f"Feature: {feature} disabled")
                continue
            setup_func_name = f"setup_{feature}_parser"
            setup_func = getattr(self, setup_func_name, None)
            if not setup_func:
                ic(f"Unknown feature: {feature}")
                continue
            setup_func()
        self.pre_parser = self.handler_mixin.get_additional_parameters(self.pre_parser)
        self.args = None

        # Custom command handling
        self.custom_commands = {}
        self.help_texts = []

    def get_args(self) -> argparse.Namespace:
        """This method is used to get the arguments"""
        if not self.args:
            parser = argparse.ArgumentParser(parents=[self.pre_parser], add_help=True)
            self.args = parser.parse_args()
        return self.args

    def setup_debug_parser(self) -> "IndalekoBaseCLI":
        """This method is used to set up the debug parser"""
        pre_args, _ = self.pre_parser.parse_known_args()
        if hasattr(pre_args, "debug"):  # only process it once
            return None
        if not hasattr(pre_args, "debug"):
            self.pre_parser.add_argument(
                "--debug",
                default=False,
                action="store_true",
                help="Debug mode (default=False)",
            )
        return self

    def setup_configdir_parser(self) -> "IndalekoBaseCLI":
        """This method is used to set up the config directory parser"""
        pre_args, _ = self.pre_parser.parse_known_args()
        if hasattr(pre_args, "configdir"):  # only process it once
            return None
        if not hasattr(pre_args, "configdir"):
            self.pre_parser.add_argument(
                "--configdir",
                default=self.config_data["ConfigDirectory"],
                help=f'Path to the config directory (default={self.config_data["ConfigDirectory"]})',
            )
        return self

    def setup_datadir_parser(self) -> "IndalekoBaseCLI":
        """This method is used to set up the data directory parser"""
        pre_args, _ = self.pre_parser.parse_known_args()
        if hasattr(pre_args, "datadir"):  # only process it once
            return None
        if not hasattr(pre_args, "datadir"):
            self.pre_parser.add_argument(
                "--datadir",
                default=self.config_data["DataDirectory"],
                help=f'Path to the data directory (default={self.config_data["DataDirectory"]})',
            )
        return self

    def setup_logging_parser(self) -> "IndalekoBaseCLI":
        """This method is used to set up the logging parser"""
        pre_args, _ = self.pre_parser.parse_known_args()
        if self.cli_features.platform and not hasattr(pre_args, "platform"):
            self.setup_platform_parser()
        if self.cli_features.machine_config and not hasattr(pre_args, "machine_config"):
            self.setup_machine_config_parser()
        if hasattr(pre_args, "logdir"):  # only process it once
            return None
        self.pre_parser.add_argument(
            "--logdir",
            default=self.config_data["LogDirectory"],
            help=f'Path to the log directory (default={self.config_data["LogDirectory"]})',
        )
        self.pre_parser.add_argument(
            "--loglevel",
            type=int,
            default=self.config_data["LogLevel"],
            choices=IndalekoLogging.get_logging_levels(),
            help=f"Logging level to use (default="
            f'{IndalekoLogging.map_logging_level_to_type(self.config_data["LogLevel"])})',
        )
        default_log_file = self.handler_mixin.generate_log_file_name(self.config_data)
        self.pre_parser.add_argument(
            "--logfile",
            default=default_log_file,
            help=f"Log file to use (default={default_log_file})",
        )
        return self

    def setup_db_config_parser(self) -> "IndalekoBaseCLI":
        """This method is used to set up the database configuration parser"""
        pre_args, _ = self.pre_parser.parse_known_args()
        if hasattr(pre_args, "db_config"):  # only process it once
            return None
        if not hasattr(pre_args, "db_config"):
            self.config_data["DBConfigChoices"] = self.handler_mixin.find_db_config_files(
                self.config_data["ConfigDirectory"],
            )
            default_db_config = self.handler_mixin.get_default_file(
                self.config_data["ConfigDirectory"],
                self.config_data["DBConfigChoices"],
            )
            self.pre_parser.add_argument(
                "--db_config",
                choices=self.config_data["DBConfigChoices"],
                default=default_db_config,
                help=f"Database configuration to use (default={default_db_config})",
            )
            return self

    def setup_offline_parser(self) -> "IndalekoBaseCLI":
        """This method is used to set up the offline parser"""
        pre_args, _ = self.pre_parser.parse_known_args()
        if hasattr(pre_args, "offline"):  # only process it once
            return None
        if not hasattr(pre_args, "offline"):
            self.pre_parser.add_argument(
                "--offline",
                default=self.config_data["Offline"],
                action="store_true",
                help="Offline mode (default=False)",
            )
        return self

    def setup_machine_config_parser(self) -> "IndalekoBaseCLI":
        """This method is used to set up the machine configuration parser"""
        if not self.features.machine_config:
            return None
        if self.features.input and not hasattr(self.pre_parser, "inputfile"):
            self.setup_input_parser()
        pre_args, _ = self.pre_parser.parse_known_args()
        if hasattr(pre_args, "machine_config"):
            return None
        if not hasattr(pre_args, "platform"):
            self.setup_platform_parser()  # ordering dependency.
            pre_args, _ = self.pre_parser.parse_known_args()
        self.config_data["MachineConfigChoices"] = self.handler_mixin.find_machine_config_files(
            self.config_data["ConfigDirectory"],
            pre_args.platform,
        )
        default_machine_config_file = self.handler_mixin.get_default_file(
            self.config_data["ConfigDirectory"],
            self.config_data["MachineConfigChoices"],
        )
        self.pre_parser.add_argument(
            "--machine_config",
            choices=self.config_data["MachineConfigChoices"],
            default=default_machine_config_file,
            help=f"Machine configuration to use (default={default_machine_config_file})",
        )
        pre_args, _ = self.pre_parser.parse_known_args()
        if pre_args.machine_config:
            self.config_data["MachineConfigFile"] = pre_args.machine_config
            self.config_data["MachineConfigFileKeys"] = self.handler_mixin.extract_filename_metadata(
                pre_args.machine_config,
            )
        else:
            ic("Warning: no machine configuration file found")
            self.config_data["MachineConfigFile"] = None
            self.config_data["MachineConfigFileKeys"] = None
        return self

    def setup_platform_parser(self) -> "IndalekoBaseCLI":
        """This method is used to set up the platform parser"""
        if not self.features.platform:
            return None
        pre_args, _ = self.pre_parser.parse_known_args()
        if hasattr(pre_args, "platform"):  # only process it once
            return None  # already added
        self.pre_parser.add_argument(
            "--platform",
            default=self.config_data["Platform"],
            help=f'Platform to use (default={self.config_data["Platform"]})',
        )
        pre_args, _ = self.pre_parser.parse_known_args()
        self.config_data["Platform"] = pre_args.platform
        return self

    def setup_output_parser(self) -> "IndalekoBaseCLI":
        """This method is used to set up the output parser"""
        if self.features.machine_config and not hasattr(
            self.pre_parser,
            "machine_config",
        ):
            self.setup_machine_config_parser()
        if not self.config_data.get("FileServiceName"):
            ic(
                f"Output file name not generated due to no service name {self.config_data}",
            )
            return None  # there can be no output file without a service name
        pre_args, _ = self.pre_parser.parse_known_args()
        if hasattr(pre_args, "outputfile"):  # only process it once
            ic(
                f"setup_output_parser: outputfile already processed: {pre_args.outputfile}",
            )
            return None
        storage_id = self.handler_mixin.get_storage_identifier(pre_args)
        if storage_id:
            self.pre_parser.add_argument(
                "--storage",
                default=storage_id,
                help=f"Storage identifier to use (default={storage_id})",
            )
            self.config_data["StorageId"] = storage_id
        output_file = self.handler_mixin.generate_output_file_name(self.config_data)
        self.pre_parser.add_argument(
            "--outputfile",
            default=output_file,
            help=f"Output file to use (default = {output_file})",
        )
        pre_args, _ = self.pre_parser.parse_known_args()
        self.config_data["OutputFile"] = pre_args.outputfile
        self.config_data["OutputFileKeys"] = self.handler_mixin.extract_filename_metadata(output_file)
        return self

    def setup_performance_parser(self) -> "IndalekoBaseCLI":
        """This method is used to set up the performance parser"""
        if not self.config_data.get("FileServiceName"):
            return None  # there can be no perf data without a service name
        self.pre_parser.add_argument(
            "--performance_file",
            default=False,
            action="store_true",
            help="Record performance data to a file (default=False)",
        )
        self.pre_parser.add_argument(
            "--performance_db",
            default=False,
            action="store_true",
            help="Record performance data to the database (default=False)",
        )
        pre_args, _ = self.pre_parser.parse_known_args()
        if pre_args.performance_file:
            self.config_data["PerformanceDataFile"] = self.handler_mixin.generate_perf_file_name(self.config_data)
        if pre_args.performance_db:
            self.config_data["PerformanceDB"] = True
        return self

    def setup_input_parser(self) -> "IndalekoBaseCLI":
        """This method is used to set up the input parser"""
        if not self.cli_features.input:
            return
        pre_args, _ = self.pre_parser.parse_known_args()
        if hasattr(pre_args, "inputfile"):  # only process it once
            return
        assert "InputFileKeys" in self.config_data, "InputFileKeys not found in configuration data"
        prefix = self.config_data["InputFileKeys"].get(
            "prefix",
            self.config_data.get("FilePrefix", IndalekoConstants.default_prefix),
        )
        suffix = self.config_data["InputFileKeys"].get(
            "suffix",
            self.config_data.get("FileSuffix", ".jsonl"),
        )
        self.config_data["InputFilePrefix"] = prefix
        self.config_data["InputFileSuffix"] = suffix
        input_file_keys = self.config_data.get("InputFileKeys", {})
        if "plt" not in input_file_keys and "Platform" in self.config_data:
            input_file_keys["plt"] = self.config_data["Platform"]
        # this needs to be  provided
        assert "svc" in input_file_keys, f"Service not found in input file keys: {input_file_keys}"
        self.config_data["InputFileChoices"] = self.handler_mixin.find_data_files(
            self.config_data["DataDirectory"],
            input_file_keys,
            prefix,
            suffix,
        )
        if self.config_data["InputFileChoices"]:
            self.config_data["InputFile"] = self.handler_mixin.get_default_file(
                self.config_data["DataDirectory"],
                self.config_data["InputFileChoices"],
            )
            self.pre_parser.add_argument(
                "--inputfile",
                choices=self.config_data["InputFileChoices"],
                default=self.config_data["InputFile"],
                help=f'Input file to use (default={self.config_data["InputFile"]})',
            )
            pre_args, _ = self.pre_parser.parse_known_args()
            self.config_data["InputFileKeys"] = self.handler_mixin.extract_filename_metadata(pre_args.inputfile)
        else:
            self.pre_parser.add_argument(
                "--inputfile",
                default=None,
                help="Input file to use",
            )
        # default timestamp is: 1) from the file, 2) from the config, 3) current time
        pre_args, _ = self.pre_parser.parse_known_args()
        timestamp = self.config_data["InputFileKeys"].get("timestamp", None)
        if not timestamp:
            timestamp = datetime.now(UTC).isoformat()
        if not hasattr(pre_args, "timestamp"):
            self.pre_parser.add_argument(
                "--timestamp",
                type=str,
                default=timestamp,
                help=f"Timestamp to use (default={timestamp})",
            )
        pre_args, _ = self.pre_parser.parse_known_args()
        try:
            timestamp = datetime.fromisoformat(self.config_data["Timestamp"])
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=UTC)
        except ValueError:
            ic(f"Invalid timestamp: {pre_args.timestamp}")
            raise ValueError(f"Invalid timestamp: {pre_args.timestamp}")
        self.config_data["Timestamp"] = pre_args.timestamp

    def get_config_data(self: "IndalekoBaseCLI") -> dict[str, Any]:
        """This method is used to get the configuration data"""
        return self.config_data

    def register_command(self, command: str, handler) -> None:
        """
        Register a custom command handler.

        Args:
            command: The command to register (e.g., "/memory")
            handler: The function to call when the command is invoked
        """
        self.custom_commands[command] = handler

    def handle_command(self, command: str) -> bool:
        """
        Handle a custom command.

        Args:
            command: The command to handle

        Returns:
            bool: True if the command was handled, False otherwise
        """
        parts = command.strip().split(maxsplit=1)
        cmd = parts[0].lower()

        if cmd in self.custom_commands:
            return self.custom_commands[cmd](command)

        return False

    def append_help_text(self, text: str) -> None:
        """
        Append text to the help message.

        Args:
            text: The text to append
        """
        self.help_texts.append(text)

    def get_help_text(self) -> str:
        """
        Get the complete help text.

        Returns:
            str: The complete help text
        """
        return "\n".join(self.help_texts)

    class default_handler_mixin(IndalekoHandlermixin):
        """Default handler mixin for the CLI"""

        @staticmethod
        def get_platform_name() -> str:
            """This method is used to get the platform name"""
            return platform.system()

        @staticmethod
        def get_pre_parser() -> argparse.Namespace | None:
            """
            This method is used to get the pre-parser.  Callers can
            set up switches/parameters before we add the common ones.

            Note the default implementation here does not add any additional parameters.
            """
            return argparse.ArgumentParser(add_help=False)

        @staticmethod
        def get_default_file(
            data_directory: str | Path,
            candidates: list[str | Path],
        ) -> str | None:
            """
            This method is used to get the most recently modified file.  Default implementation is to
            return the most recently modified file (or None if the candidate list is empty).
            """
            if isinstance(data_directory, str):
                data_directory = Path(data_directory)
            if not data_directory.exists():
                raise FileNotFoundError(
                    f"Data directory does not exist: {data_directory}",
                )
            valid_files = [data_directory / fname for fname in candidates if (data_directory / fname).is_file()]
            if not valid_files:
                return None
            return str(max(valid_files, key=lambda f: f.stat().st_mtime).name)

        @staticmethod
        def find_db_config_files(
            config_dir: str | Path,
        ) -> list[str] | None:
            if not Path(config_dir).exists():
                return None
            return [
                fname
                for fname, _ in find_candidate_files(["db"], str(config_dir))
                if fname.startswith(IndalekoConstants.default_prefix) and fname.endswith(".ini")
            ]

        @staticmethod
        def find_machine_config_files(
            config_dir: str | Path,
            platform: str = None,
            machine_id: str = None,
        ) -> list[str] | None:
            """
            This method is used to find machine configuration files

            Inputs:
                - config_dir: The directory where the configuration files are stored
                - platform: The platform of the machine
                - machine_id: The machine ID

            Returns:
                - A list of file names

            Notes: If the platform is not provided, it may be inferred from the machine ID
            or the current platform.  If the machine ID is provided and a platform is
            provided, both must match for the file to be considered a candidate.
            """
            if not Path(config_dir).exists():
                return None
            if platform is None:
                return []
            filters = ["_machine_config"]
            if machine_id:
                filters.append(machine_id)
            if platform:
                filters.append(platform)
            return [fname for fname, _ in find_candidate_files(filters, str(config_dir)) if fname.endswith(".json")]

        @staticmethod
        def find_data_files(
            data_dir: str | Path,
            keys: dict[str, str],
            prefix: str,
            suffix: str,
        ) -> list[str] | None:
            """This method is used to find data files"""
            if not Path(data_dir).exists():
                return None
            # the hyphen at the end ensures we don't pick up partial matches
            selection_keys = [f"{key}={value}-" for key, value in keys.items()]
            return [
                fname
                for fname, _ in find_candidate_files(selection_keys, str(data_dir))
                if fname.startswith(prefix) and fname.endswith(suffix) and all([key in fname for key in selection_keys])
            ]

        @staticmethod
        def generate_output_file_name(keys: dict[str, str]) -> str:
            """This method is used to generate an output file name.  Note
            that it assumes the keys are in the desired format. Don't just
            pass in configuration data.
            """
            kwargs = {
                "platform": keys["Platform"],
                "service": keys["FileServiceName"],
                "timestamp": keys["Timestamp"],
            }
            if "MachineConfigFileKeys" in keys and "machine" in keys["MachineConfigFileKeys"]:
                kwargs["machine"] = keys["MachineConfigFileKeys"]["machine"]
            if keys.get("StorageId"):
                kwargs["storage"] = keys["StorageId"]
            if keys.get("UserId"):
                kwargs["userid"] = keys["UserId"]
            if "suffix" not in keys:
                kwargs["suffix"] = "jsonl"
            return generate_file_name(**kwargs)

        @staticmethod
        def generate_log_file_name(keys: dict[str, str]) -> str:
            """This method is used to generate a log file name"""
            kwargs = {
                "service": keys["FileServiceName"],
                "timestamp": keys["Timestamp"],
            }
            if "Platform" in keys:
                kwargs["platform"] = keys["Platform"]
            if (
                "MachineConfigFileKeys" in keys
                and keys["MachineConfigFileKeys"]
                and "machine" in keys["MachineConfigFileKeys"]
            ):
                kwargs["machine"] = keys["MachineConfigFileKeys"]["machine"]
            if "suffix" not in keys:
                kwargs["suffix"] = "log"
            return generate_file_name(**kwargs)

        @staticmethod
        def generate_perf_file_name(keys: dict[str, str]) -> str:
            """
            This method is used to generate a performance file name.
            """
            kwargs = {
                "service": keys["FileServiceName"] + "_perf",
                "timestamp": keys["Timestamp"],
            }
            if "Platform" in keys:
                kwargs["platform"] = keys["Platform"]
            if "MachineConfigFileKeys" in keys and "machine" in keys["MachineConfigFileKeys"]:
                kwargs["machine"] = keys["MachineConfigFileKeys"]["machine"]
            return generate_file_name(**kwargs)

        @staticmethod
        def load_machine_config(keys: dict[str, str]) -> IndalekoMachineConfig:
            """This method is used to load a machine configuration"""
            raise NotImplementedError(
                f"The method {inspect.currentframe().f_code.co_name} must be implemented by the subclass",
            )

        @staticmethod
        def extract_filename_metadata(file_name: str) -> dict:
            """This method is used to parse the file name."""
            return extract_keys_from_file_name(file_name=file_name)

        @staticmethod
        def get_storage_identifier(
            config_data: dict[str, str],
        ) -> str | None:
            """Default is no storage identifier"""
            if config_data.get("StorageId"):
                storage_id = config_data["StorageId"]
            elif "InputFileKeys" in config_data and "storage" in config_data["InputFileKeys"]:
                storage_id = config_data["InputFileKeys"]["storage"]
            else:
                storage_id = None
            return storage_id

        @staticmethod
        def get_additional_parameters(
            pre_parser: argparse.Namespace,
        ) -> argparse.Namespace | None:
            """
            This method is used to add additional parameters to the parser.

            Default is to not add any parameters.
            """
            return pre_parser

        @staticmethod
        def get_user_identifier(
            config_data: dict[str, str],
        ) -> str | None:
            """Default is no user identifier"""
            if config_data.get("UserId"):
                user_id = config_data["UserId"]
            elif "InputFileKeys" in config_data and "userid" in config_data["InputFileKeys"]:
                user_id = config_data["InputFileKeys"]["userid"]
            else:
                user_id = None
            return user_id


def main():
    """Test the main handler"""
    cli = IndalekoBaseCLI()
    args = cli.get_args()
    ic(cli.get_config_data())
    ic(args)


if __name__ == "__main__":
    main()
