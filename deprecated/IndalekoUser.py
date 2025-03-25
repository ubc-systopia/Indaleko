"""
IndalecoUser.py - This module is used to manage Indaleko Users.


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
import datetime

from Indaleko import Indaleko
from IndalekoDBConfig import IndalekoDBConfig
from IndalekoLogging import IndalekoLogging


class IndalekoUser:
    """This class is used to manage Indaleko Users."""

    def __init__(self):
        """Create an instance of the IndalekoUser class."""
        super().__init__()
        return


def check_command(args: argparse.Namespace) -> None:
    """Check the database connection."""
    logging.debug("check_command invoked")
    print("Checking Database connection")
    db_config = IndalekoDBConfig()
    if db_config is None:
        print("Could not create IndalekoDBConfig object")
        exit(1)
    started = db_config.start(timeout=args.timeout)
    if not started:
        print("Could not start IndalekoDBConfig object")
        exit(1)
    print("Database connection successful")


def main():
    """Main entry point for IndalekoUser."""
    print("Main called")
    start_time = datetime.datetime.now(datetime.UTC).isoformat()
    parser = argparse.ArgumentParser(description="Indaleko User Management")
    parser.add_argument(
        "--timeout",
        type=int,
        default=Indaleko.default_db_timeout,
        help="Timeout for database connection",
    )
    parser.add_argument(
        "--logdir", type=str, default=Indaleko.default_log_dir, help="Log directory"
    )
    parser.add_argument("--log", type=str, default=None, help="Log file name")
    parser.add_argument(
        "--loglevel",
        type=int,
        default=logging.DEBUG,
        choices=IndalekoLogging.get_logging_levels(),
        help="Log level",
    )
    command_subparser = parser.add_subparsers(dest="command")
    parser_check = command_subparser.add_parser(
        "check", help="Check the database connection"
    )
    parser_check.add_argument(
        "--ipaddr", type=str, default=None, help="IP address for database"
    )
    parser_check.set_defaults(func=check_command)
    parser.set_defaults(func=check_command)
    args = parser.parse_args()
    if args.log is None:
        args.log = Indaleko.generate_file_name(
            suffix="log", service="IndalekoUser", timestamp=start_time
        )
    indaleko_logging = IndalekoLogging(
        service_name="IndalekoUser",
        log_level=args.loglevel,
        log_file=args.log,
        log_dir=args.logdir,
    )
    if indaleko_logging is None:
        print("Could not create IndalekoLogging object")
        exit(1)
    logging.info("Starting IndalekoUser")
    logging.debug(args)
    args.func(args)
    logging.info("IndalekoUser completed")


if __name__ == "__main__":
    main()
