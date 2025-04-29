"""
This implements an example of semantic extraction using the ["Unstructured"](htts://unstructured.io) package.

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

# standard library imports
import argparse
import configparser
import logging
import os
import sys
import uuid

# third-party imports
from icecream import ic

#  Find Indaleko Root
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Indaleko imports
# pylint: disable=wrong-import-position
from lookup import UnstructuredLookup
from retrieve import UnstructuredRetrieval

from Indaleko import Indaleko
from semantic.collectors.semantic_collector import SemanticCollector
from utils.i_logging import IndalekoLogging

# pylint: enable=wrong-import-position


class IndalekoUnstructured(SemanticCollector):
    """This class defines the unstructured data collector for the Indaleko project.

    As a collector, the job of this class is to:

        1. Find the file to be processed in the database
        2. Extract the unstructured data from the file
        3. Capture the data, and extract interesting characteristics from the data.

    Note: this simply saves the data to a file for further processing by the recorder.

    """

    config_file_layout = {
        "DATA": {
            "ScriptsDir": "semantic\\collectors\\unstructured\\docker_script.py",
            "BatchSize": 5000,
            "SupportedFormats": ".txt,.pdf,.docx,.html,.pptx",
            "UnstructuredDataDir": f"{Indaleko.default_data_dir}\\semantic",
            "InputFileName": "unstructured_inputs.jsonl",
            "OutputFileName": "unstructured_outputs.jsonl",
        },
        "DOCKER": {
            "DockerImage": "downloads.unstructured.io/unstructured-io/unstructured",
            "DockerTag": "latest",
        },
        "VOLUMES": {
            "HostDrive": "c:\\",
            "HostDriveMount": "/mnt/drive",
            "ProjectDir": os.environ.get("INDALEKO_ROOT"),
            "ProjectDirMount": "/mnt/Indaleko",
            "UnstructuredDataDirMount": "/mnt/semantic",
        },
        "BATCH_SIZES": {
            ".jpg": 20,
            ".jpeg": 20,
        },
    }

    config_file_name = "unstructured_config.ini"

    def __init__(self, **kwargs):
        """Initialize the unstructured data collector"""
        self._name = "Unstructured Data Collector"
        self._provider_id = uuid.UUID("19de2525-fd76-4339-b600-a7bff4d9c47a")
        if "config_file" in kwargs:
            self.config_file = kwargs["config_file"]
            del kwargs["config_file"]
        else:
            self.config_file = os.path.join(
                Indaleko.default_config_dir,
                self.config_file_name,
            )
        if not os.path.exists(self.config_file):
            self.config = configparser.ConfigParser()
            for section, options in self.config_file_layout.items():
                ic(f"Adding section {section} with options {options}")
                self.config[section] = options
            with open(self.config_file, "w", encoding="utf-8-sig") as config_file:
                self.config.write(config_file)
        else:
            self.config = self.load_config_file()
        ic("printing config")
        self.config.write(sys.stdout)
        for key, values in kwargs.items():
            setattr(self, key, values)

    def load_config_file(self) -> configparser.ConfigParser:
        """Load the configuration file for the unstructured data collector"""
        if self.config_file is None:
            self.config_file = os.path.join(
                Indaleko.default_config_dir,
                self.config_file_name,
            )
        config = configparser.ConfigParser()
        config.read(self.config_file, encoding="utf-8-sig")
        ic("loading config")
        config.write(sys.stdout)
        return config

    def get_collector_characteristics(self) -> list:
        """Get the characteristics of the unstructured data collector"""
        return []

    def get_collector_name(self) -> str:
        """Get the name of the unstructured data collector"""
        return self._name

    def get_collector_id(self) -> str:
        """Get the UUID for the unstructured data collector"""
        return self._provider_id

    def retrieve_data(self, data_id: str) -> dict:
        """Retrieve the data for the unstructured data collector"""
        unstructured_retrieve = UnstructuredRetrieval()
        print("Processing files through unstructured")
        unstructured_retrieve.retrieve("unstructured_1")

    def get_collector_description(self) -> str:
        """Get the description of the unstructured data collector"""
        return """This collector provides unstructured data from files."""

    def get_json_schema(self) -> dict:
        """Get the JSON schema for the unstructured data collector"""
        # TODO
        return {}

    def lookup_files(self, args) -> None:
        """Lookup the file objects for the unstructured data collector"""
        lookup = UnstructuredLookup()
        print("Looking up files")
        lookup.generate_input()


def main():
    """This is the main handler for the Indaleko Unstructured Data Collector"""
    ic("Unstructured Data Collector")
    unstructured = IndalekoUnstructured()
    ic(unstructured.config)
    parser = argparse.ArgumentParser(description="Indaleko Unstructured Data Collector")
    parser.add_argument(
        "--log_dir",
        default=Indaleko.default_log_dir,
        type=str,
        help="Directory for log files",
    )
    parser.add_argument(
        "--config_dir",
        default=Indaleko.default_config_dir,
        type=str,
        help="Directory for configuration files",
    )
    parser.add_argument(
        "--data_dir",
        default=Indaleko.default_data_dir,
        type=str,
        help="Directory for data files",
    )
    parser.add_argument("--log_file", default=None, type=str, help="Log file name")
    parser.add_argument(
        "--config_file",
        default=None,
        type=str,
        help="Configuration file name",
    )
    parser.add_argument("--data_file", default=None, type=str, help="Data file name")
    parser.add_argument(
        "--loglevel",
        choices=IndalekoLogging.get_logging_levels(),
        default=logging.DEBUG,
        type=str,
        help="Logging level",
    )

    command_subparser = parser.add_subparsers(dest="command", help="Command to execute")

    ## Subparser to generate input file for unstructured
    parser_lookup = command_subparser.add_parser(
        "lookup",
        help="Creates a jsonl file that contains a list of files to be processed by Unstructured",
    )
    parser_lookup.set_defaults(func=unstructured.lookup_files)

    ## Subparser to run Unstructured on Inputs
    parser_retrieve = command_subparser.add_parser(
        "retrieve",
        help="Creates a jsonl file that contains a list of files processed by Unstructured",
    )
    parser_retrieve.set_defaults(func=unstructured.retrieve_data)

    parser.set_defaults(func=None)
    args = parser.parse_args()
    # ic(args)
    args.func(args)


if __name__ == "__main__":
    main()
