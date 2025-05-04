#!/usr/bin/env python3
"""CLI entrypoint for the Enhanced Data Generator tool.

This module provides a command-line interface for generating synthetic
metadata records to test Indaleko's search capabilities.
"""

import os
import sys
from pathlib import Path

# Bootstrap project root so imports of `utils` and other top-level packages work
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    # Walk up until we find the project entry point
    while not (current_path / "Indaleko.py").exists():
        current_path = current_path.parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

from tools.data_generator_enhanced.handler_mixin import DataGeneratorHandlerMixin

from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
from utils.cli.runner import IndalekoCLIRunner
from utils.logging_setup import setup_logging


def run_data_generator(kwargs: dict) -> None:
    """Wrapper to invoke the handler mixin's run method."""
    DataGeneratorHandlerMixin.run(kwargs)


def main() -> None:
    """Main entrypoint for the Enhanced Data Generator."""
    # Configure logging (console + file with rotation) before running
    setup_logging()
    cli_data = IndalekoBaseCliDataModel(
        RegistrationServiceName="DataGeneratorService",
        FileServiceName="data_generator_enhanced",
    )
    runner = IndalekoCLIRunner(
        cli_data=cli_data,
        handler_mixin=DataGeneratorHandlerMixin(),
        features=IndalekoBaseCLI.cli_features(),
        Run=run_data_generator,
        RunParameters={},
    )
    runner.run()


if __name__ == "__main__":
    main()
