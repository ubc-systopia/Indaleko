"""
Project Indaleko
Copyright (C) 2024-2025 Tony Mason.

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


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.named_entity import NamedEntityCollection
from query.query_processing.data_models.query_output import (
    LLMCollectionCategoryQueryResponse,
    LLMIntentQueryResponse,
)


# pylint: enable=wrong-import-position


class ParserResults(BaseModel):
    """This data class is used to store the results from the NL parser."""

    OriginalQuery: str
    Intent: LLMIntentQueryResponse
    Entities: NamedEntityCollection
    Categories: LLMCollectionCategoryQueryResponse
