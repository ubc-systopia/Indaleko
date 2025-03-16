"""
This module provides a common cli based runner.

Indaleko Windows Local Recorder
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
import logging
import os
from pathlib import Path
import sys

from abc import ABC, abstractmethod
from icecream import ic
from typing import Type, Union, Any

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from platforms.machine_config import IndalekoMachineConfig
from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
from utils.cli.data_models.runner_data import IndalekoCLIRunnerData
from utils.cli.handlermixin import IndalekoHandlermixin

# from utils import IndalekoLogging
# pylint: enable=wrong-import-position


class IndalekoCLIRunner:
    """This class provides a common CLI runner"""

    def __init__(
        self,
        cli_data: Union[IndalekoBaseCliDataModel, None] = None,
        handler_mixin: Union[IndalekoHandlermixin, None] = None,
        features: Union[IndalekoBaseCLI.cli_features, None] = None,
        **kwargs: dict[str, Any],
    ) -> None:
        keys = {}
        keys["SetupLogging"] = IndalekoCLIRunner.default_runner_mixin.setup_logging
        keys["LoadConfiguration"] = kwargs.get(
            "LoadConfiguration",
            IndalekoCLIRunner.default_runner_mixin.load_configuration,
        )
        keys["PerformanceConfiguration"] = kwargs.get(
            "PerformanceConfiguration",
            IndalekoCLIRunner.default_runner_mixin.performance_configuration,
        )
        keys["Run"] = kwargs.get("Run", IndalekoCLIRunner.default_runner_mixin.run)
        keys["RunParameters"] = kwargs.get("RunParameters", {})
        keys["PerformanceRecording"] = kwargs.get(
            "PerformanceRecording",
            IndalekoCLIRunner.default_runner_mixin.performance_recording,
        )
        keys["Cleanup"] = kwargs.get(
            "Cleanup", IndalekoCLIRunner.default_runner_mixin.cleanup
        )
        self.runner_data = IndalekoCLIRunnerData(**keys)
        if not cli_data:
            cli_data = IndalekoBaseCliDataModel()
        if not handler_mixin:
            handler_mixin = IndalekoBaseCLI.default_handler_mixin()
        if not features:
            features = IndalekoBaseCLI.cli_features()
        self.cli = IndalekoBaseCLI(
            cli_data=cli_data, handler_mixin=handler_mixin, features=features
        )
        self.args = self.cli.get_args()
        if self.args.debug:
            ic(self.args)
            ic(self.cli.get_config_data())

    def setup(self) -> None:
        """This method is used to setup the CLI runner"""
        if self.runner_data.SetupLogging:
            if self.args.debug:
                ic("Setup Logging")
            self.runner_data.SetupLogging(self.args)
        if self.runner_data.LoadConfiguration:
            if self.args.debug:
                ic("Load Configuration")
            data_class = None
            if self.runner_data.RunParameters:
                data_class = self.runner_data.RunParameters.get("MachineConfigClass")
            kwargs = {"args": self.args, "cli": self.cli, "class": data_class}
            self.runner_data.LoadConfiguration(kwargs)
        if self.runner_data.PerformanceConfiguration:
            if self.args.debug:
                ic("Performance Configuration")
            self.runner_data.PerformanceConfiguration()

    def cleanup(self) -> None:
        """This method is used to cleanup the CLI runner"""
        if self.runner_data.PerformanceRecording:
            if self.args.debug:
                ic("Performance Recording")
            self.runner_data.PerformanceRecording()
        if self.runner_data.Cleanup:
            if self.args.debug:
                ic("Cleanup")
            self.runner_data.Cleanup()
        if self.args.debug:
            ic("cleanup called")

    def run(self) -> None:
        self.setup()
        ic(self.args)
        if self.runner_data.Run:
            if self.args.debug:
                ic("Run")
            self.runner_data.Run(
                {
                    "args": self.args,
                    "cli": self.cli,
                    "parameters": self.runner_data.RunParameters,
                }
            )
        self.cleanup()

    class CLIRunnerMixin(ABC):
        """This class provides a mixin for the CLI runner"""

        @abstractmethod
        def get_pre_parser() -> Union[argparse.ArgumentParser, None]:
            """This method is used to get the pre-parser"""

        @abstractmethod
        def setup_logging(kwargs: dict[str, Any] = {}) -> None:
            """This method is used to setup logging"""

        @abstractmethod
        def load_configuration(kwargs: dict[str, Any] = {}) -> IndalekoMachineConfig:
            """This method is used to load configuration"""

        @abstractmethod
        def add_parameters(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
            """This method is used to add parameters to an existing parser"""

        @abstractmethod
        def performance_configuration(kwargs: dict[str, Any] = {}) -> bool:
            """
            This method is used to configure performance.  Return of False indicates
            performace information is not being recorded.
            """

        @abstractmethod
        def run(kwargs: dict[str, Any] = {}) -> None:
            """This method is used to run the core CLI utility"""

        @abstractmethod
        def performance_recording(kwargs: dict[str, Any] = {}) -> None:
            """This method is used to record performance"""

        @abstractmethod
        def cleanup(kwargs: dict[str, Any] = {}) -> None:
            """This method is used to cleanup"""

    class default_runner_mixin(CLIRunnerMixin):
        """This class provides a default runner mixin"""

        @staticmethod
        def get_pre_parser() -> Union[argparse.ArgumentParser, None]:
            """
            This method is used to get the pre-parser.  This implementation
            does not add any initial arguments to the parser.
            """
            pre_parser = argparse.ArgumentParser(add_help=False)
            return pre_parser

        @staticmethod
        def setup_logging(args: argparse.Namespace, **kwargs: dict[str, Any]) -> None:
            """
            This method is used to setup logging:

            Inputs:
                * args - the parsed arguments
                * cli - the CLI object
                * kwargs - additional arguments
            """
            if not getattr(args, "logdir"):
                return
            filename = kwargs.get("logfile", None)
            filename: Path = Path(args.logdir) / args.logfile
            log_level: int = getattr(args, "log_level", logging.INFO)
            log_format: str = kwargs.get(
                "log_format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            force: bool = kwargs.get("force", True)
            if filename is None:
                return
            logging.basicConfig(
                filename=str(filename), level=log_level, format=log_format, force=force
            )
            logging.info(f"Logging started: {filename}")
            assert os.path.exists(filename), f"Failed to create log file: {filename}"

        @staticmethod
        def load_configuration(
            kwargs: dict[str, Any] = {},
        ) -> Union[IndalekoMachineConfig, None]:
            """This method is used to load configuration"""
            args: Union[argparse.Namespace, None] = kwargs.get("args", None)
            cli: Union[IndalekoBaseCLI, None] = kwargs.get("cli", None)
            machine_config_class: Type[IndalekoMachineConfig] = kwargs["class"]
            if not args or not cli:
                ic("load_configuration: No args or cli, returning None")
                return None
            if not hasattr(args, "machine_config"):
                ic("No machine configuration file specified, returning None")
                return None
            if not cli.handler_mixin.load_machine_config:
                ic("No handler to load machine configuration")
                return None
            machine_config_file = str(Path(args.configdir) / args.machine_config)
            kwargs["machine_config_file"] = machine_config_file
            kwargs["offline"] = args.offline
            kwargs["debug"] = args.debug
            kwargs["machine_config_class"] = machine_config_class
            machine_config = cli.handler_mixin.load_machine_config(kwargs)
            if args.debug:
                ic(machine_config)
            return machine_config

        @staticmethod
        def add_parameters(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
            """
            This method is used to add parameters to an existing parser.

            The default implementation does not add any additional parameters.
            """
            return parser

        @staticmethod
        def performance_configuration():
            """This method is used to configure performance"""
            return True

        @abstractmethod
        def run(kwargs: dict[str, Any] = {}) -> None:
            """This method is used to run the core CLI utility"""
            ic("Invoked the default run method, which does nothing.  Please override.")

        @staticmethod
        def performance_recording():
            """This method is used to record performance"""
            pass

        @staticmethod
        def cleanup():
            """This method is used to cleanup"""
            pass
