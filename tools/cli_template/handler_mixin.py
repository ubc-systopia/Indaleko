#!/usr/bin/env python3
# Allow skipping linting/formatting for this template file
# ruff: noqa
# isort: skip_file
"""Template Handler Mixin for a new Indaleko CLI tool.
"""Template Handler Mixin for a new Indaleko CLI tool.

Customize this mixin to define your tool's arguments and behavior.
"""

import argparse
import logging
from typing import Any

from utils.cli.handlermixin import IndalekoHandlermixin


class TemplateHandlerMixin(IndalekoHandlermixin):
    """Sample HandlerMixin stub for IndalekoCLIRunner."""

    @staticmethod
    def get_pre_parser() -> argparse.ArgumentParser | None:
        """Define initial arguments (before the main parser)."""
        return argparse.ArgumentParser(add_help=False)

    @staticmethod
    def setup_logging(args: argparse.Namespace, **kwargs: dict[str, Any]) -> None:
        """Configure logging based on parsed args."""

    @staticmethod
    def load_configuration(kwargs: dict[str, Any]) -> None:
        """Load tool-specific configuration (e.g., from file or env)."""

    @staticmethod
    def add_parameters(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        """Add tool-specific CLI arguments to the parser."""
        return parser

    @staticmethod
    def performance_configuration(_kwargs: dict[str, Any]) -> bool:
        """Configure performance recording; return False to skip."""
        return False

    @staticmethod
    def run(kwargs: dict[str, Any]) -> None:
        """Main entry point for CLI execution."""
        args = kwargs.get("args")
        logging.info("Running %s with args %s", TemplateHandlerMixin.__name__, args)

    @staticmethod
    def performance_recording(_kwargs: dict[str, Any]) -> None:
        """Hook for recording performance after run()."""

    @staticmethod
    def cleanup(_kwargs: dict[str, Any]) -> None:
        """Cleanup hook (e.g., close resources)."""
