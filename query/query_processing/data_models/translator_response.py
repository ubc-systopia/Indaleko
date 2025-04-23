"""
This module defines the common data model for output from
the query translators.

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
from datetime import UTC, datetime
from typing import Any

from pydantic import Field, validator

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from data_models.base import IndalekoBaseModel

# from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
# from query.llm_base import IndalekoLLMBase
# from data_models.collection_metadata_data_model import IndalekoCollectionMetadataDataModel
# from data_models.db_index import IndalekoCollectionIndexDataModel
# from data_models.named_entity import NamedEntityCollection
# from query.query_processing.data_models.query_output import StructuredQuery
# pylint: enable=wrong-import-position


class TranslatorOutput(IndalekoBaseModel):
    """
    Define the output data model for the translator.
    """

    aql_query: str
    explanation: str
    confidence: float
    observations: str | None = None
    performance_info: dict[str, Any] = {}
    additional_notes: str | None = None
    bind_vars: dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @validator("timestamp")
    def ensure_timezone(cls, v):
        """Ensure the timestamp has a timezone."""
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v

    class Config:
        arbitrary_types_allowed = True

        json_schema_extra = {
            "example": {
                "aql_query": "FOR doc IN collection FILTER doc.attribute == @value RETURN doc",
                "explanation": "The query filters documents in the collection where the attribute equals the provided value.",
                "confidence": 0.95,
                "observations": "Consider indexing the attribute for faster query performance.",
                "performance_info": {
                    "translation_time": 0.123,
                    "token_budget": 150,
                    "input_tokens": 75,
                    "output_tokens": 50,
                },
                "bind_vars": {"value": "example"},
                "additional_notes": "Have a nice day!",
                "timestamp": "2025-02-17T12:34:56.789Z",
            },
        }
