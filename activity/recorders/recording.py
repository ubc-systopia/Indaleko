"""
This module handles recording of activity data from the various providers.
"""

import argparse
import datetime
import os
import sys

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db import IndalekoDBConfig

# pylint: enable=wrong-import-position


class Recording:
    """
    This class handles the recording of data from the various providers.
    """

    def __init__(self, **kwargs):
        self._db_config = IndalekoDBConfig()
        for key, value in kwargs.items():
            setattr(self, key, value)


class RecordingInterface:
    """
    This class defines the command line interface used to test the recording
    class.
    """

    @staticmethod
    def list_command(args):
        """List the current recordings"""
        print("List")
        recording_agent = Recording()
        ic(recording_agent)

    @staticmethod
    def test_db_command(args):
        """Test the database connection"""
        print("Test DB")
        db = IndalekoDBConfig()
        ic(db)


def main():
    """This allows testing the data model"""
    now = datetime.datetime.now(datetime.UTC)
    parser = argparse.ArgumentParser(description="Recording interface CLI for testing")
    command_subparser = parser.add_subparsers(dest="command", help="Command to execute")
    parser_list = command_subparser.add_parser("list", help="List the recordings")
    parser_list.set_defaults(func=RecordingInterface.list_command)
    parser_test_db = command_subparser.add_parser(
        "test_db",
        help="Test the database connection",
    )
    parser_test_db.set_defaults(func=RecordingInterface.test_db_command)
    parser.set_defaults(func=RecordingInterface.list_command)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
