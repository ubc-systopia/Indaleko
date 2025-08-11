"""
Test script for Indaleko ArangoDB custom analyzers

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


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from db.analyzer_manager import (
    IndalekoAnalyzerManager,
    create_custom_analyzers,
    execute_analyzer_creation,
)
from utils import IndalekoLogging


def list_analyzers(manager: IndalekoAnalyzerManager, verbose: bool = False) -> None:
    """List all analyzers in the database."""
    analyzers = manager.list_analyzers()

    for analyzer in analyzers:
        analyzer.get("name", "unknown")
        analyzer.get("type", "unknown")

        if verbose:
            try:
                import json

                json.loads(analyzer.get("properties", "{}"))
            except json.JSONDecodeError:
                pass


def test_analyzer_creation(
    manager: IndalekoAnalyzerManager,
    direct: bool = False,
) -> None:
    """Test analyzer creation using different methods."""
    if direct:
        execute_analyzer_creation()
    else:
        results = create_custom_analyzers()
        for _analyzer, _success in results.items():
            pass


def test_tokenization(manager: IndalekoAnalyzerManager, verbose: bool = False) -> None:
    """Test tokenization for different types of filenames."""
    test_texts = {
        "indaleko_camel_case": [
            "IndalekoObjectDataModel",
            "camelCaseExample",
            "HTTPRequest",
            "XMLParser",
        ],
        "indaleko_snake_case": [
            "indaleko_object_data_model",
            "snake_case_example",
            "http_request",
            "xml_parser",
        ],
        "indaleko_filename": [
            "IndalekoObject-data_model.py",
            "camel-snake_mixed.txt",
            "README(important).md",
            "project-v1.2.3.zip",
        ],
    }


    for analyzer_name, texts in test_texts.items():
        for text in texts:
            success, tokens = manager.test_analyzer(analyzer_name, text)
            if success:
                pass
            else:
                pass


def show_arangosh_command() -> None:
    """Show the arangosh command for creating analyzers."""


def main() -> None:
    """Main function for the test script."""
    parser = argparse.ArgumentParser(
        description="Test ArangoDB custom analyzers for Indaleko",
    )
    parser.add_argument("--list", action="store_true", help="List existing analyzers")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed analyzer information",
    )
    parser.add_argument("--create", action="store_true", help="Create custom analyzers")
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Use direct arangosh execution for creation",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test tokenization with different analyzers",
    )
    parser.add_argument("--command", action="store_true", help="Show arangosh command")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    IndalekoLogging(service_name="test_analyzers", log_level=log_level)

    # Create analyzer manager
    manager = IndalekoAnalyzerManager()

    # Execute requested operations
    if args.list or args.all:
        list_analyzers(manager, args.verbose)

    if args.create or args.all:
        test_analyzer_creation(manager, args.direct)

    if args.test or args.all:
        test_tokenization(manager, args.verbose)

    if args.command or args.all:
        show_arangosh_command()

    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()


if __name__ == "__main__":
    main()
