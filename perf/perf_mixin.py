"""
This module provides functionality to link external components with
the functionality of the performance classes.

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
import sys

from abc import abstractmethod
from typing import Any, Union

# from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
# from perf_collector import IndalekoPerformanceDataCollector
from perf_recorder import IndalekoPerformanceDataRecorder

# pylint: enable=wrong-import-position


class IndalekoPerformanceMixin:
    """Mixin class to handle performance measurement functionality"""

    @abstractmethod
    def get_platform_config_data(
        self, args: argparse.Namespace
    ) -> Union[None, dict[str, Any]]:
        """Retrieve information about the current platform state (e.g, version data)"""

    @abstractmethod
    def setup_performance_measurement(self, args: argparse.Namespace) -> None:
        """Configure performance measurement based on CLI args"""

    @abstractmethod
    def extract_counters(self) -> dict[str, int]:
        """Extract performance counters"""

    @abstractmethod
    def record_performance(
        self, perf_data: dict[str, Any], args: argparse.Namespace
    ) -> None:
        """Record performance data based on configuration"""


class base_performance_mixin(IndalekoPerformanceMixin):
    """Mixin class to handle performance measurement functionality"""

    def setup_performance_measurement(self, args):
        """Configure performance measurement based on CLI args"""
        self.perf_enabled = args.performance_file or args.performance_db
        if self.perf_enabled:
            self.perf_file_name = os.path.join(
                args.datadir,
                IndalekoPerformanceDataRecorder().generate_perf_file_name(
                    platform=self.platform,
                    service=self.service_name,
                    machine=self.machine_id,
                ),
            )

    def extract_counters(self):
        """Extract performance counters"""
        return self.get_counts()

    def record_performance(self, perf_data, args):
        """Record performance data based on configuration"""
        if not self.perf_enabled:
            return

        perf_recorder = IndalekoPerformanceDataRecorder()
        if args.performance_file:
            perf_recorder.add_data_to_file(self.perf_file_name, perf_data)
            logging.info("Performance data written to %s", self.perf_file_name)

        if args.performance_db:
            perf_recorder.add_data_to_db(perf_data)
            logging.info("Performance data written to database")
