#!/usr/bin/env python3
"""
Indaleko Project - Test Script for Semantic Performance CLI Integration

This module provides a standalone test for the semantic performance monitoring
CLI integration, allowing users to verify that the CLI commands work correctly.

Note: Semantic extractors should only run on machines where data is physically
stored. Storage recorders should add device-file relationships (UUID:
f3dde8a2-cff5-41b9-bd00-0f41330895e1) between files and the machines
where they're stored.
"""

import argparse
import json
import os
import sys

# Add Indaleko root to path if needed
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Global variable to track if we're in mock mode
_MISSING_IMPORTS = False

# Try to import required modules directly
try:
    from semantic.cli_integration import (
        SemanticPerformanceCliIntegration,
        register_semantic_performance_cli,
    )
    from utils.cli.base import IndalekoBaseCLI
    from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
except ImportError as e:
    print(f"WARNING: Missing dependencies: {e}")
    print("The test will create mock objects for missing dependencies.")
    _MISSING_IMPORTS = True

    # Create simplified mock classes
    class IndalekoBaseCliDataModel:
        def __init__(self, **kwargs):
            self.RegistrationServiceName = kwargs.get(
                "RegistrationServiceName", "TestCLI",
            )
            self.FileServiceName = kwargs.get("FileServiceName", "TestCLI")
            self.ConfigDirectory = kwargs.get("ConfigDirectory", "./config")
            self.DataDirectory = kwargs.get("DataDirectory", "./data")
            self.LogDirectory = kwargs.get("LogDirectory", "./logs")
            self.LogLevel = kwargs.get("LogLevel", 20)
            self.Offline = kwargs.get("Offline", False)
            self.Platform = kwargs.get("Platform", sys.platform)
            self.Timestamp = kwargs.get("Timestamp", "2023-01-01T00:00:00Z")

        def model_dump_json(self):
            return json.dumps(self.__dict__)

    class IndalekoBaseCLI:
        """Simple mock CLI class for testing."""

        class cli_features:
            def __init__(self, **kwargs):
                self.machine_config = kwargs.get("machine_config", False)
                self.input = kwargs.get("input", False)
                self.output = kwargs.get("output", False)
                self.offline = kwargs.get("offline", False)
                self.logging = kwargs.get("logging", False)
                self.performance = kwargs.get("performance", False)
                self.platform = kwargs.get("platform", False)

        def __init__(self, cli_data=None, handler_mixin=None, features=None):
            self.prompt = "Test> "
            self.args = None
            self.custom_commands = {}
            self.help_texts = []

        def output(self, message):
            print(message)

        def register_command(self, command, handler):
            self.custom_commands[command] = handler

        def append_help_text(self, text):
            self.help_texts.append(text)

        def run(self):
            """Simplified run method for testing."""
            print("\nTest Semantic Performance CLI")
            print("Available commands: /perf, /experiments, /report")

            while True:
                user_input = input(self.prompt).strip()

                if user_input.lower() in ["exit", "quit"]:
                    break

                if user_input.startswith(("/perf", "/experiments", "/report")):
                    command_parts = user_input.split(maxsplit=1)
                    command = command_parts[0]
                    args = command_parts[1] if len(command_parts) > 1 else ""

                    if command in self.custom_commands:
                        handler = self.custom_commands[command]
                        handler(args.split())
                    else:
                        print(f"No handler registered for command: {command}")
                else:
                    print(f"Unknown command: {user_input}")

        class default_handler_mixin:
            @staticmethod
            def get_pre_parser():
                return argparse.ArgumentParser(add_help=False)

    class SemanticPerformanceCliIntegration:
        """Basic mock integration class."""

        def __init__(self, cli_instance):
            self.cli = cli_instance

        def handle_perf_command(self, args):
            print(f"[MOCK] Handling perf command: {args}")
            if not args:
                self.cli.output("Performance Monitoring Commands:")
                self.cli.output("  /perf status - Show monitoring status")
                self.cli.output("  /perf enable - Enable monitoring")
                self.cli.output("  /perf disable - Disable monitoring")
            elif args[0] == "status":
                self.cli.output("[MOCK] Performance monitoring is disabled")

        def handle_experiments_command(self, args):
            print(f"[MOCK] Handling experiments command: {args}")
            self.cli.output("Experiments Commands:")
            self.cli.output("  /experiments list - List experiments")

        def handle_report_command(self, args):
            print(f"[MOCK] Handling report command: {args}")
            self.cli.output("Report Commands:")
            self.cli.output("  /report generate - Generate report")

    # Mock registration function
    def register_semantic_performance_cli(cli_instance):
        """Register mock CLI integration."""
        print("[MOCK] Registering performance CLI integration")
        return SemanticPerformanceCliIntegration(cli_instance)


class TestCLI(IndalekoBaseCLI):
    """Simple CLI for testing the Semantic Performance CLI integration."""

    def __init__(self):
        """Initialize the test CLI."""
        super().__init__()
        self.prompt = "Test> "

    def output(self, message: str) -> None:
        """Override output method to print to console."""
        print(message)

    def run(self) -> None:
        """Run the test CLI."""
        print("\nSemantic Performance CLI Integration Test")
        print("=======================================")
        print("Type 'exit' or 'quit' to exit.")
        print("Available commands:")
        print("  /perf - Show performance monitoring commands")
        print("  /experiments - List and run performance experiments")
        print("  /report - Generate performance reports")
        print()

        while True:
            user_input = input(self.prompt).strip()

            if user_input.lower() in ["exit", "quit", "bye", "leave"]:
                break

            # Handle CLI integration commands
            if user_input.startswith(("/perf", "/experiments", "/report")):
                command_parts = user_input.split(maxsplit=1)
                command = command_parts[0]
                args = command_parts[1] if len(command_parts) > 1 else ""

                if command == "/perf":
                    self.perf_integration.handle_perf_command(args.split())
                elif command == "/experiments":
                    self.perf_integration.handle_experiments_command(args.split())
                elif command == "/report":
                    self.perf_integration.handle_report_command(args.split())
            else:
                print(f"Unknown command: {user_input}")
                print("Try /perf, /experiments, or /report")


def test_cli_integration(args: list[str] | None = None) -> None:
    """
    Test the Semantic Performance CLI integration.

    Args:
        args: Command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Test Semantic Performance CLI Integration",
    )
    parser.add_argument("--command", help="Execute a single command and exit")
    parser.add_argument(
        "--mock", action="store_true", help="Force mock mode even if imports succeeded",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Show detailed error information",
    )
    parsed_args = parser.parse_args(args)

    # Force mock mode if requested
    global _MISSING_IMPORTS
    if parsed_args.mock:
        _MISSING_IMPORTS = True
        print("Running in mock mode due to --mock flag")

    try:
        # Create the test CLI
        cli = TestCLI()

        # Store arguments
        cli.args = parsed_args

        # Register the performance CLI integration
        cli.perf_integration = register_semantic_performance_cli(cli)

        # If a command was provided, execute it and exit
        if parsed_args.command:
            command_parts = parsed_args.command.split(maxsplit=1)
            command = command_parts[0]
            cmd_args = command_parts[1] if len(command_parts) > 1 else ""

            if command == "/perf":
                cli.perf_integration.handle_perf_command(cmd_args.split())
            elif command == "/experiments":
                cli.perf_integration.handle_experiments_command(cmd_args.split())
            elif command == "/report":
                cli.perf_integration.handle_report_command(cmd_args.split())
            else:
                print(f"Unknown command: {command}")
        else:
            # Run the interactive CLI
            cli.run()

    except Exception as e:
        print(f"Error: {e!s}")
        if parsed_args.debug:
            import traceback

            traceback.print_exc()
        else:
            print("Use --debug for more detailed error information")


if __name__ == "__main__":
    try:
        test_cli_integration()
    except Exception as e:
        print(f"Error running test CLI integration: {e}")
        print("Use --debug flag for more details")

        try:
            import docker

            print("docker module is available")
        except ImportError:
            print("docker module is MISSING")

        try:
            from icecream import ic

            print("icecream module is available")
        except ImportError:
            print("icecream module is MISSING")
