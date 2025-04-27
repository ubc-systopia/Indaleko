"""
This module is a location activity data provider for Indaleko.

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
import logging
import os
import sys
from typing import Any

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# This logic is part of what allows me to execute it locally or as part of the
# overall package/project.  It's a bit of a hack, but it works.
# pylint: disable=wrong-import-position
from activity.collectors.base import CollectorBase
from utils.i_logging import IndalekoLogging

# pylint: enable=wrong-import-position


class LocationCollector(CollectorBase):
    """
    Base class for location activity data providers.
    """

    def __init__(self, **kwargs):
        self.config = kwargs.get("config", {})
        self.data = []

    def collect_data(self) -> None:
        """
        Collect location data. This method should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement this method")

    def process_data(self, data: Any) -> dict[str, Any]:
        """
        Process the collected data. This method should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement this method")

    def store_data(self, data: dict[str, Any]) -> None:
        """
        Store the processed data. This method should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement this method")


def list_data_providers_command(args: argparse.Namespace):
    """List the data providers available"""
    ic(args)
    ic("This needs to be implemented")


def main():
    """This is a test interface for the location provider."""
    from Indaleko import Indaleko

    parser = argparse.ArgumentParser(description="Location provider test interface")
    # pylint: disable=no-member
    # the reference is valid, but pylint doesn't see it
    parser.add_argument(
        "--logdir",
        type=str,
        default=Indaleko.default_log_dir,
        help="Directory for log files",
    )

    parser.add_argument("--log", type=str, default=None, help="Log file name")
    parser.add_argument(
        "--loglevel",
        type=int,
        default=logging.DEBUG,
        choices=IndalekoLogging.get_logging_levels(),
        help="Logging level",
    )
    command_subparser = parser.add_subparsers(dest="command", help="Command to execute")
    parser_list = command_subparser.add_parser(
        "list",
        help="List the data providers available",
    )
    parser_list.add_argument(
        "--providerdir",
        type=str,
    )
    parser_list.set_defaults(func=list_data_providers_command)
    parser.set_defaults(func=list_data_providers_command)
    parser.add_argument(
        "--config",
        type=str,
        help="Configuration file for the location provider",
    )
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
