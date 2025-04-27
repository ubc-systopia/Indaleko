"""
This is the activity data provider discovery mechanism.

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

from pathlib import Path

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from Indaleko import Indaleko
from activity.collectors.known_semantic_attributes import KnownSemanticAttributes
from utils import IndalekoLogging


# pylint: enable=wrong-import-position


class IndalekoActivityDataProviderCollectorDiscovery:
    """
    The Indaleko activity data providers are dynamically recognized and added to
    the database.  This class provides the mechanism to discover and add new
    data providers.
    """

    default_config_dir = None  # os.path.join(os.environ['INDALEKO_ROOT'], Indaleko.default_config_dir)
    default_data_dir = None  # os.path.join(os.environ['INDALEKO_ROOT'], Indaleko.default_data_dir)
    default_log_dir = None  # os.path.join(os.environ['INDALEKO_ROOT'], Indaleko.default_log_dir)
    default_provider_dir = str(
        Path(os.environ["INDALEKO_ROOT"]) / "activity" / "collectors",
    )

    def __init__(self, **kwargs):
        """Initialize the data provider discovery mechanism"""
        for dir_name in ["config_dir", "data_dir", "log_dir"]:
            if dir_name in kwargs:
                setattr(self, dir_name, kwargs[dir_name])
            elif os.environ["INDALEKO_ROOT"] is not None:
                setattr(
                    self,
                    dir_name,
                    os.path.join(
                        os.environ["INDALEKO_ROOT"],
                        getattr(Indaleko, f"default_{dir_name}"),
                    ),
                )
            else:
                setattr(self, dir_name, getattr(Indaleko, f"default_{dir_name}"))
        self.provider_dir = kwargs.get(
            "provider_dir",
            IndalekoActivityDataProviderCollectorDiscovery.default_provider_dir,
        )
        self.config_dir = kwargs.get(
            "config_dir",
            IndalekoActivityDataProviderCollectorDiscovery.default_config_dir,
        )
        self.data_dir = kwargs.get(
            "data_dir",
            IndalekoActivityDataProviderCollectorDiscovery.default_data_dir,
        )
        self.log_dir = kwargs.get(
            "log_dir",
            IndalekoActivityDataProviderCollectorDiscovery.default_log_dir,
        )
        self.data_providers = IndalekoActivityDataProviderCollectorDiscovery.find_data_providers(
            self.provider_dir,
        )

    @staticmethod
    def find_data_providers(provider_dir: str) -> list:
        """Find the data providers in the specified directory"""
        data_providers = []

        # Step 1: Build a list of subdirectories
        subdirectories = [f.name for f in os.scandir(provider_dir) if f.is_dir() and not f.name.startswith("_")]
        for subdir in subdirectories:
            ic(subdir)
            module = KnownSemanticAttributes.safe_import(
                f"activity.collectors.{subdir}",
            )
            if hasattr(module, "activity_providers"):
                for provider in module.activity_providers():
                    data_providers.append(
                        {
                            "category": subdir,
                            "provider_class": provider,
                            "module": module,
                        },
                    )
        return data_providers

    @staticmethod
    def initialize_project() -> bool:
        """Initialize the project"""
        ic("Initialize project")

    @staticmethod
    def list_data_providers(args: argparse.Namespace):
        """List the data providers available"""
        discovery = IndalekoActivityDataProviderCollectorDiscovery()
        for provider in discovery.data_providers:
            ic(provider)

    @staticmethod
    def show_registrations(args: argparse.Namespace):
        """Show the existing registrations for the data providers"""
        ic(f"Show registrations: {args}")


def main():
    """
    This is the interactive interface to the activity data provider discovery
    mechanism.
    """
    parser = argparse.ArgumentParser(
        description="Indaleko Activity Data Provider Discovery Tool",
    )
    parser.add_argument(
        "--logdir",
        type=str,
        default=IndalekoActivityDataProviderCollectorDiscovery.default_log_dir,
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
        default=IndalekoActivityDataProviderCollectorDiscovery.default_provider_dir,
        help="Directory for the data providers "
        f"(default: {IndalekoActivityDataProviderCollectorDiscovery.default_provider_dir})",
    )
    parser_list.set_defaults(
        func=IndalekoActivityDataProviderCollectorDiscovery.list_data_providers,
    )
    parser.set_defaults(
        func=IndalekoActivityDataProviderCollectorDiscovery.list_data_providers,
    )
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
