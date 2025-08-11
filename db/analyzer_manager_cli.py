"""
This module provides a CLI for managing ArangoDB analyzers for Indaleko.

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

# Import analyzer manager functionality but not the CLI class
from db.analyzer_manager import (
    IndalekoAnalyzerManager,
    execute_analyzer_creation,
)

# Import the CLI base class
from utils.cli.base import IndalekoBaseCLI


class IndalekoAnalyzerManagerCLI(IndalekoBaseCLI):
    """CLI for managing ArangoDB analyzers."""

    @staticmethod
    def list_analyzers_command(args) -> None:
        """List all analyzers in the database."""
        manager = IndalekoAnalyzerManager()
        analyzers = manager.list_analyzers()

        for analyzer in analyzers:

            # Show properties if requested
            if args.verbose:
                try:
                    import json

                    json.loads(analyzer.get("properties", "{}"))
                except:
                    pass

    @staticmethod
    def create_analyzers_command(args) -> None:
        """Create custom analyzers."""
        manager = IndalekoAnalyzerManager()

        if args.analyzer:
            # Create specific analyzer
            if args.analyzer == "camel_case":
                manager.create_camel_case_analyzer()
            elif args.analyzer == "snake_case":
                manager.create_snake_case_analyzer()
            elif args.analyzer == "filename":
                manager.create_filename_analyzer()
            else:
                pass
        elif args.direct:
            # Use direct execution via arangosh
            if execute_analyzer_creation():
                pass
            else:
                # Show alternative method if direct execution fails
                pass
        else:
            # Create using Python API
            results = manager.create_all_analyzers()
            for _success in results.values():
                pass

    @staticmethod
    def delete_analyzer_command(args) -> None:
        """Delete an analyzer."""
        if not args.analyzer:
            return

        manager = IndalekoAnalyzerManager()
        manager.delete_analyzer(args.analyzer)

    @staticmethod
    def test_analyzer_command(args) -> None:
        """Test an analyzer on a string."""
        if not args.analyzer or not args.text:
            return

        manager = IndalekoAnalyzerManager()
        success, tokens = manager.test_analyzer(args.analyzer, args.text)

        if success:
            pass
        else:
            pass

    @staticmethod
    def command_command(args) -> None:
        """Show arangosh command for analyzer creation."""

    @staticmethod
    def setup_parsers(subparsers) -> None:
        """Set up command-line parsers for the analyzer manager."""
        # List analyzers command
        list_parser = subparsers.add_parser("list", help="List all analyzers")
        list_parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help="Show analyzer properties",
        )
        list_parser.set_defaults(func=IndalekoAnalyzerManagerCLI.list_analyzers_command)

        # Create analyzers command
        create_parser = subparsers.add_parser("create", help="Create custom analyzers")
        create_parser.add_argument(
            "--analyzer",
            choices=["camel_case", "snake_case", "filename"],
            help="Specific analyzer to create (default: all)",
        )
        create_parser.add_argument(
            "--direct",
            action="store_true",
            help="Execute analyzer creation directly using arangosh",
        )
        create_parser.set_defaults(
            func=IndalekoAnalyzerManagerCLI.create_analyzers_command,
        )

        # Delete analyzer command
        delete_parser = subparsers.add_parser("delete", help="Delete an analyzer")
        delete_parser.add_argument("analyzer", help="Name of the analyzer to delete")
        delete_parser.set_defaults(
            func=IndalekoAnalyzerManagerCLI.delete_analyzer_command,
        )

        # Test analyzer command
        test_parser = subparsers.add_parser("test", help="Test an analyzer on a string")
        test_parser.add_argument("analyzer", help="Name of the analyzer to test")
        test_parser.add_argument("text", help="Text to analyze")
        test_parser.set_defaults(func=IndalekoAnalyzerManagerCLI.test_analyzer_command)

        # Command command to show the arangosh command
        command_parser = subparsers.add_parser(
            "command",
            help="Show arangosh command for analyzer creation",
        )
        command_parser.set_defaults(func=IndalekoAnalyzerManagerCLI.command_command)


def main() -> None:
    """Main entry point for the analyzer manager CLI."""
    from db.analyzer_manager import execute_analyzer_creation

    # Create the argument parser
    parser = argparse.ArgumentParser(
        description="Indaleko ArangoDB Analyzer Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Add debug flag
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    # Add direct execution flag
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Execute analyzer creation directly using arangosh",
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Set up command parsers
    IndalekoAnalyzerManagerCLI.setup_parsers(subparsers)

    # Parse arguments
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Handle direct execution request
    if args.direct:
        if execute_analyzer_creation():
            pass
        else:
            pass
        return

    # Execute the appropriate command
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
