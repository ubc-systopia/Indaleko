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
import os
import sys

# Import the CLI base class
from utils.cli.base import IndalekoBaseCLI

# Import analyzer manager functionality but not the CLI class
from db.analyzer_manager import (
    IndalekoAnalyzerManager,
    execute_analyzer_creation,
    create_custom_analyzers_script,
    get_arangosh_command
)


class IndalekoAnalyzerManagerCLI(IndalekoBaseCLI):
    """CLI for managing ArangoDB analyzers."""

    @staticmethod
    def list_analyzers_command(args):
        """List all analyzers in the database."""
        manager = IndalekoAnalyzerManager()
        analyzers = manager.list_analyzers()

        print(f"Found {len(analyzers)} analyzers:")
        for analyzer in analyzers:
            print(f"  - {analyzer.get('name')} (type: {analyzer.get('type')})")

            # Show properties if requested
            if args.verbose:
                try:
                    import json
                    properties = json.loads(analyzer.get('properties', '{}'))
                    print(f"    Properties: {json.dumps(properties, indent=4)}")
                except:
                    pass

    @staticmethod
    def create_analyzers_command(args):
        """Create custom analyzers."""
        manager = IndalekoAnalyzerManager()

        if args.analyzer:
            # Create specific analyzer
            if args.analyzer == "camel_case":
                success = manager.create_camel_case_analyzer()
                print(f"CamelCase analyzer created: {success}")
            elif args.analyzer == "snake_case":
                success = manager.create_snake_case_analyzer()
                print(f"snake_case analyzer created: {success}")
            elif args.analyzer == "filename":
                success = manager.create_filename_analyzer()
                print(f"filename analyzer created: {success}")
            else:
                print(f"Unknown analyzer: {args.analyzer}")
        else:
            # Create all analyzers
            if args.direct:
                # Use direct execution via arangosh
                print("Executing analyzer creation directly using arangosh...")
                if execute_analyzer_creation():
                    print("✅ Custom analyzers created successfully")
                else:
                    print("❌ Failed to create custom analyzers")
                    # Show alternative method if direct execution fails
                    print("\nAlternative commands:")
                    print(f"1. Direct arangosh command: {get_arangosh_command()}")
                    print("2. Manual execution: Create a file with the following content and run with arangosh:")
                    print(f"   ```\n{create_custom_analyzers_script()}\n   ```")
            else:
                # Create using Python API
                results = manager.create_all_analyzers()
                print("Analyzer creation results:")
                for analyzer, success in results.items():
                    print(f"  - {analyzer}: {'✅ Success' if success else '❌ Failed'}")

    @staticmethod
    def delete_analyzer_command(args):
        """Delete an analyzer."""
        if not args.analyzer:
            print("Error: Must specify an analyzer to delete")
            return

        manager = IndalekoAnalyzerManager()
        success = manager.delete_analyzer(args.analyzer)
        print(f"Analyzer {args.analyzer} deleted: {success}")

    @staticmethod
    def test_analyzer_command(args):
        """Test an analyzer on a string."""
        if not args.analyzer or not args.text:
            print("Error: Must specify both analyzer and text")
            return

        manager = IndalekoAnalyzerManager()
        success, tokens = manager.test_analyzer(args.analyzer, args.text)

        if success:
            print(f"Testing analyzer '{args.analyzer}' on text: '{args.text}'")
            print(f"Tokenized result: {tokens}")
        else:
            print(f"Failed to test analyzer '{args.analyzer}'")

    @staticmethod
    def command_command(args):
        """Show arangosh command for analyzer creation."""
        print("Command to create analyzers using arangosh:")
        print(get_arangosh_command())

    @staticmethod
    def setup_parsers(subparsers):
        """Set up command-line parsers for the analyzer manager."""
        # List analyzers command
        list_parser = subparsers.add_parser('list', help='List all analyzers')
        list_parser.add_argument('-v', '--verbose', action='store_true',
                                help='Show analyzer properties')
        list_parser.set_defaults(func=IndalekoAnalyzerManagerCLI.list_analyzers_command)

        # Create analyzers command
        create_parser = subparsers.add_parser('create', help='Create custom analyzers')
        create_parser.add_argument('--analyzer', choices=['camel_case', 'snake_case', 'filename'],
                                  help='Specific analyzer to create (default: all)')
        create_parser.add_argument('--direct', action='store_true',
                                  help='Execute analyzer creation directly using arangosh')
        create_parser.set_defaults(func=IndalekoAnalyzerManagerCLI.create_analyzers_command)

        # Delete analyzer command
        delete_parser = subparsers.add_parser('delete', help='Delete an analyzer')
        delete_parser.add_argument('analyzer', help='Name of the analyzer to delete')
        delete_parser.set_defaults(func=IndalekoAnalyzerManagerCLI.delete_analyzer_command)

        # Test analyzer command
        test_parser = subparsers.add_parser('test', help='Test an analyzer on a string')
        test_parser.add_argument('analyzer', help='Name of the analyzer to test')
        test_parser.add_argument('text', help='Text to analyze')
        test_parser.set_defaults(func=IndalekoAnalyzerManagerCLI.test_analyzer_command)

        # Command command to show the arangosh command
        command_parser = subparsers.add_parser('command', help='Show arangosh command for analyzer creation')
        command_parser.set_defaults(func=IndalekoAnalyzerManagerCLI.command_command)


def main():
    """Main entry point for the analyzer manager CLI."""
    from db.analyzer_manager import execute_analyzer_creation
    
    # Create the argument parser
    parser = argparse.ArgumentParser(
        description='Indaleko ArangoDB Analyzer Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Add debug flag
    parser.add_argument('-d', '--debug', action='store_true',
                       help='Enable debug logging')

    # Add direct execution flag
    parser.add_argument('--direct', action='store_true',
                        help='Execute analyzer creation directly using arangosh')

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Set up command parsers
    IndalekoAnalyzerManagerCLI.setup_parsers(subparsers)

    # Parse arguments
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level,
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Handle direct execution request
    if args.direct:
        print("Executing analyzer creation directly using arangosh...")
        if execute_analyzer_creation():
            print("✅ Custom analyzers created successfully")
        else:
            print("❌ Failed to create custom analyzers")
        return

    # Execute the appropriate command
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()