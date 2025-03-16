"""This is the Indaleko Query Module"""

import argparse
import datetime
import logging

from Indaleko import Indaleko
from IndalekoLogging import IndalekoLogging


class IndalekoQuery:
    """This class represents the base class for Indaleko Queries."""

    service_name = "IndalekoQuery"

    def __init__(self):
        """Create an instance of the IndalekoQuery class."""


def check_command(args: argparse.Namespace) -> None:
    """Check the database"""
    print("This is the Indaleko Query Module: check command")
    print(args)


def show_command(args: argparse.Namespace) -> None:
    """Show the query setup information"""
    print("This is the Indaleko Query Module: show command")
    print(args)


def main():
    """Main entry point for the program"""
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp = now.isoformat()
    print("Indaleko Query Module: Start")
    parser = argparse.ArgumentParser(
        description="Indaleko Activity Data Provider Management."
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
        "check", help="Check the activity data provider setup"
    )
    parser_check.set_defaults(func=check_command)
    parser_show = command_subparser.add_parser(
        "show", help="Show the activity data provider setup"
    )
    parser_show.add_argument(
        "--inactive", action="store_true", help="Show inactive providers"
    )
    parser_show.set_defaults(func=show_command)
    print("Indaleko Query Module: Finished")
    parser.set_defaults(func=show_command)
    args = parser.parse_args()
    if args.log is None:
        args.log = Indaleko.generate_file_name(
            suffix="log", service=IndalekoQuery.service_name, timestamp=timestamp
        )
    indaleko_logging = IndalekoLogging(
        service_name=IndalekoQuery.service_name,
        log_level=args.loglevel,
        log_file=args.log,
        log_dir=args.logdir,
    )
    if indaleko_logging is None:
        print("Could not create logging object")
        exit(1)
    logging.info("Starting IndalekoQuery")
    logging.debug(args)
    args.func(args)
    logging.info("IndalekoQuery: done processing.")


if __name__ == "__main__":
    main()
