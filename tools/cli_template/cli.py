"""
CLI template entrypoint for a new Indaleko tool.

Customize this file to wire your handler mixin into the shared runner.
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

from handler_mixin import TemplateHandlerMixin

from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
from utils.cli.runner import IndalekoCLIRunner


def run_template(kwargs: dict) -> None:
    """Wrapper to invoke the handler mixin's run method."""
    TemplateHandlerMixin.run(kwargs)


def main() -> None:
    """Main entrypoint for the CLI template."""
    cli_data = IndalekoBaseCliDataModel(
        RegistrationServiceName="TemplateService",
        FileServiceName="template_service",
    )
    runner = IndalekoCLIRunner(
        cli_data=cli_data,
        handler_mixin=TemplateHandlerMixin(),
        features=IndalekoBaseCLI.cli_features(),
        Run=run_template,
        RunParameters={},
    )
    runner.run()


if __name__ == "__main__":
    main()
