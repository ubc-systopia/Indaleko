"""
This module defines the common data model for input to
query translators.

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

import os
import sys

from pydantic import BaseModel


# from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.query_processing.data_models.query_input import StructuredQuery
from query.utils.llm_connector.llm_base import IndalekoLLMBase


# pylint: enable=wrong-import-position


class TranslatorInput(BaseModel):
    """Define the input data model for the translator."""

    Query: StructuredQuery
    Connector: IndalekoLLMBase
    # Note: I'm not sure what we are using these
    # last few fields for.   I retain them, but
    # we might want to remove them if they are
    # not needed.
    SelectedMetadataAttributes: dict[str, str] | None = None
    AdditionalNotes: str | None = None
    NTruth: int = 1

    class Config:
        """Configuration Info."""
        arbitrary_types_allowed = True


def main() -> None:
    """This allows testing the data model."""
    from icecream import ic
    ic("Testing TranslatorInput")
    TranslatorInput.test_model_main()


if __name__ == "__main__":
    main()
