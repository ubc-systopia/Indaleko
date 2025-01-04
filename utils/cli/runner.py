'''
This module provides a common cli based runner.

Indaleko Windows Local Recorder
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
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sys
from uuid import UUID

from typing import Type, Union, TypeVar, Any, Callable
from abc import ABC, abstractmethod

from icecream import ic
from pydantic import BaseModel

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from platforms.machine_config import IndalekoMachineConfig
from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
from utils.cli.data_models.runner_data import IndalekoCLIRunnerData
from utils.cli.handlermixin import IndalekoHandlermixin
from utils.misc.file_name_management import find_candidate_files, generate_file_name, extract_keys_from_file_name
from utils import IndalekoLogging
# pylint: enable=wrong-import-position

class IndalekoCLIRunner:
    '''This class provides a common CLI runner'''

    def __init__(self,
            cli_data : Union[IndalekoBaseCliDataModel, None] = None,
            handler_mixin : Union[IndalekoHandlermixin, None] = None,
            features : Union[IndalekoBaseCLI.cli_features, None] = None,
            additional_parameters : Union[Callable[[argparse.ArgumentParser], argparse.ArgumentParser], None] = None,
            **kwargs : dict[str, Any]) -> None:
        keys = {}
        keys['SetupLogging'] = kwargs.get('SetupLogging', IndalekoCLIRunner.default_runner_mixin.setup_logging)
        keys['LoadConfiguration'] = kwargs.get('LoadConfiguration', IndalekoCLIRunner.default_runner_mixin.load_configuration)
        keys['PerformanceConfiguration'] = kwargs.get('PerformanceConfiguration', IndalekoCLIRunner.default_runner_mixin.performance_configuration)
        keys['Run'] = kwargs.get('Run', IndalekoCLIRunner.default_runner_mixin.run)
        keys['PerformanceRecording'] = kwargs.get('PerformanceRecording', IndalekoCLIRunner.default_runner_mixin.performance_recording)
        keys['Cleanup'] = kwargs.get('Cleanup', IndalekoCLIRunner.default_runner_mixin.cleanup)
        self.runner_data = IndalekoCLIRunnerData(**keys)
        if not cli_data:
            cli_data = IndalekoBaseCliDataModel()
        if not handler_mixin:
            handler_mixin = IndalekoBaseCLI.default_handler_mixin
        if not features:
            features = IndalekoBaseCLI.cli_features()
        setattr(self, 'cli', IndalekoBaseCLI(cli_data=cli_data, handler_mixin=handler_mixin, features=features))
        # could add more command line args here, if useful
        if additional_parameters:
            self.cli.pre_parser = additional_parameters(self.cli.pre_parser)
        self.parser = argparse.ArgumentParser(parents=[self.cli.pre_parser])
        self.args = self.parser.parse_args()
        if self.args.debug:
            ic(self.args)
            ic(self.cli.get_config_data())

    def setup(self) -> None:
        '''This method is used to setup the CLI runner'''
        if self.runner_data.SetupLogging:
            if self.args.debug:
                ic('Setup Logging')
            self.runner_data.SetupLogging(self.args)
        if self.runner_data.LoadConfiguration:
            if self.args.debug:
                ic('Load Configuration')
            self.runner_data.LoadConfiguration({
                'args':self.args,
                'cli':self.cli
            })
        if self.runner_data.PerformanceConfiguration:
            if self.args.debug:
                ic('Performance Configuration')
            self.runner_data.PerformanceConfiguration()

    def cleanup(self) -> None:
        '''This method is used to cleanup the CLI runner'''
        if self.runner_data.PerformanceRecording:
            if self.args.debug:
                ic('Performance Recording')
            self.runner_data.PerformanceRecording()
        if self.runner_data.Cleanup:
            if self.args.debug:
                ic('Cleanup')
            self.runner_data.Cleanup()
        if self.args.debug:
            ic('cleanup called')

    def run(self) -> None:
        self.setup()
        if self.runner_data.Run:
            if self.args.debug:
                ic('Run')
            self.runner_data.Run(
                {
                    'args': self.args,
                    'cli': self.cli,
                }
            )
        self.cleanup()

    class CLIRunnerMixin(ABC):
        '''This class provides a mixin for the CLI runner'''

        @abstractmethod
        def setup_logging(kwargs : dict[str, Any] = {}) -> None:
            '''This method is used to setup logging'''

        @abstractmethod
        def load_configuration(kwargs : dict[str, Any] = {}) -> IndalekoMachineConfig:
            '''This method is used to load configuration'''

        @abstractmethod
        def performance_configuration(kwargs : dict[str, Any] = {}) -> bool:
            '''
            This method is used to configure performance.  Return of False indicates
            performace information is not being recorded.
            '''

        @abstractmethod
        def run(kwargs : dict[str, Any] = {}) -> None:
            '''This method is used to run the core CLI utility'''

        @abstractmethod
        def performance_recording(kwargs : dict[str, Any] = {}) -> None:
            '''This method is used to record performance'''

        @abstractmethod
        def cleanup(kwargs : dict[str, Any] = {}) -> None:
            '''This method is used to cleanup'''

    class default_runner_mixin(CLIRunnerMixin):
        '''This class provides a default runner mixin'''

        @staticmethod
        def setup_logging(
            args : argparse.Namespace,
            **kwargs : dict[str, Any]) -> None:
            '''
            This method is used to setup logging:

            Inputs:
                * args - the parsed arguments
                * cli - the CLI object
                * kwargs - additional arguments
            '''
            if not getattr(args, 'logdir'):
                return
            filename = kwargs.get('logfile', None)
            filename : Path = Path(args.logdir) / args.logfile
            log_level : int = getattr(args, 'log_level', logging.INFO)
            log_format : str = kwargs.get('log_format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            force : bool = kwargs.get('force', False)
            if filename is None:
                return
            logging.basicConfig(filename=str(filename), level=log_level, format=log_format, force=force)

        @staticmethod
        def load_configuration(kwargs : dict[str, Any] = {}) -> Union[IndalekoMachineConfig, None]:
            '''This method is used to load configuration'''
            args : Union[argparse.Namespace, None]= kwargs.get('args', None)
            cli : Union[IndalekoBaseCLI, None] = kwargs.get('cli', None)
            if not args or not cli:
                ic('load_configuration: No args or cli, returning None')
                return None
            if not hasattr(args, 'machine_config'):
                ic('No machine configuration file specified, returning None')
                return None
            if not cli.handler_mixin.load_machine_config:
                ic('No handler to load machine configuration')
                return None
            machine_config_file = str(Path(args.configdir) / args.machine_config)
            kwargs['machine_config_file'] = machine_config_file
            kwargs['offline'] = args.offline
            kwargs['debug'] = args.debug
            machine_config = cli.handler_mixin.load_machine_config(kwargs)
            if args.debug:
                ic(machine_config)
            return machine_config

            return True

        @staticmethod
        def performance_configuration():
            '''This method is used to configure performance'''
            return True

        @abstractmethod
        def run(kwargs : dict[str, Any] = {}) -> None:
            '''This method is used to run the core CLI utility'''
            ic('Invoked the default run method, which does nothing.  Please override.')

        @staticmethod
        def performance_recording():
            '''This method is used to record performance'''
            pass

        @staticmethod
        def cleanup():
            '''This method is used to cleanup'''
            pass
