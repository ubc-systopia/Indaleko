#!/usr/bin/env python3
"""
Test script for the Indaleko Analytics CLI integration.

This script demonstrates how to test the analytics capabilities through the CLI.

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
import os
import sys
import time

# Add the project root to the Python path
current_path = os.path.dirname(os.path.abspath(__file__))
if current_path not in sys.path:
    sys.path.append(current_path)

# Import Indaleko components
from db.db_config import IndalekoDBConfig
from query.analytics_integration import AnalyticsIntegration


def test_cli_integration():
    """Test the analytics CLI integration by simulating CLI commands."""
    print("\n===== Testing Indaleko Analytics CLI Integration =====\n")

    # Create a dummy CLI instance for testing
    class DummyCLI:
        def __init__(self):
            self.commands = {}
            self.help_text = []
            self.db_config = IndalekoDBConfig()

        def register_command(self, command, handler):
            """Register a command with the CLI."""
            self.commands[command] = handler
            print(f"Registered command: {command}")

        def append_help_text(self, text):
            """Append help text to the CLI."""
            self.help_text.append(text)
            print(f"Added help text: {text}")

    # Create a dummy CLI instance
    cli = DummyCLI()

    # Initialize the analytics integration
    analytics = AnalyticsIntegration(cli, cli.db_config, debug=True)

    # Test commands
    test_commands = [
        "/analytics help",
        "/analytics stats",
        "/analytics files",
        "/analytics types",
        "/analytics ages",
        "/analytics report --output ./analytics_test_output --visualize",
    ]

    # Execute test commands
    for i, command in enumerate(test_commands, 1):
        print(f"\n==== Test {i}: {command} ====\n")

        # Skip the first part of the command (the "/analytics" part)
        args = command.split(maxsplit=1)[1] if len(command.split()) > 1 else ""

        # Execute the command
        start_time = time.time()
        result = analytics.handle_analytics_command(args)
        end_time = time.time()

        # Display the result and timing
        print(f"\n==== Result of {command} ====")
        print(result)
        print(f"Command execution time: {end_time - start_time:.2f} seconds")
        print("=" * 50)


def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(
        description="Test Indaleko Analytics CLI Integration",
    )
    parser.add_argument(
        "--quick", "-q", action="store_true", help="Run only quick tests",
    )

    args = parser.parse_args()

    # Create output directory if it doesn't exist
    os.makedirs("./analytics_test_output", exist_ok=True)

    # Run tests
    test_cli_integration()

    print("\n===== Analytics CLI Integration Tests Completed =====")
    print(f"Test output directory: {os.path.abspath('./analytics_test_output')}")


if __name__ == "__main__":
    main()
