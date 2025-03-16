"""
IndalekoDataManager.py - A tool for managing the data collected by Indaleko.

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
import datetime

from icecream import ic

from Indaleko import Indaleko


class IndalekoDataManager:
    """
    This class contains the relevant information for the data manger.

    The functionality of the data manager is to identify and codify the data
    collected by Indaleko.
    """

    @staticmethod
    def list_data(args: argparse.Namespace):
        """List the data collected by Indaleko"""
        ic(f"List data: {args}")

    @staticmethod
    def rebuild_data(args: argparse.Namespace):
        """Rebuild the data collected by Indaleko"""
        ic(f"Rebuild data: {args}")


def main():
    """This is the main function for the Indaleko Data Manager tool"""
    # parser = argparse.ArgumentParser(description='Indaleko Data Manager')
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp = now.isoformat()
    ic(timestamp)
    parser = argparse.ArgumentParser(description="Indaleko Data Manager")
    parser.add_argument(
        "--config_dir",
        default=Indaleko.default_config_dir,
        type=str,
        help="Directory containing the configuration files",
    )
    parser.add_argument(
        "--data_dir",
        default=Indaleko.default_data_dir,
        type=str,
        help="Directory containing the data files",
    )
    command_subparser = parser.add_subparsers(dest="command", help="Command to execute")
    parser_list = command_subparser.add_parser(
        "list", help="List the data collected by Indaleko"
    )
    parser_list.set_defaults(func=IndalekoDataManager.list_data)
    parser_rebuild = command_subparser.add_parser(
        "rebuild", help="Rebuild the data collected by Indaleko"
    )
    parser_rebuild.set_defaults(func=IndalekoDataManager.rebuild_data)
    parser.set_defaults(func=IndalekoDataManager.list_data)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
