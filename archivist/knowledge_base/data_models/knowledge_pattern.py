"""
Knowledge pattern data model for the knowledge base updating feature.

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
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel


# pylint: enable=wrong-import-position


class KnowledgePatternType(str, Enum):
    """Types of knowledge patterns."""

    query_pattern = "query_pattern"
    entity_relationship = "entity_relationship"
    schema_update = "schema_update"
    user_preference = "user_preference"


class KnowledgePatternDataModel(IndalekoBaseModel):
    """A learned pattern in the knowledge base."""

    pattern_id: UUID = uuid4()
    pattern_type: KnowledgePatternType
    created_at: datetime = datetime.now(UTC)
    updated_at: datetime = datetime.now(UTC)
    confidence: float  # Confidence score (0-1)
    usage_count: int = 1  # How often this pattern has been used
    pattern_data: dict[str, Any]  # The actual pattern information
    source_events: list[UUID] = []  # Learning events that contributed to this pattern

    class Config:
        """Sample configuration data for the data model."""

        json_schema_extra = {
            "example": {
                "pattern_id": "a81b3522-c394-40b0-a82c-a9d7fa1f7e03",
                "pattern_type": KnowledgePatternType.query_pattern,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
                "confidence": 0.92,
                "usage_count": 5,
                "pattern_data": {
                    "intent": "find_documents",
                    "entity_types": ["topic"],
                    "collection": "Objects",
                    "query_template": "FOR doc IN @@collection FILTER LIKE(doc.Label, @entity) RETURN doc",
                    "success_rate": 0.88,
                },
                "source_events": [
                    "981a3522-c394-40b0-a82c-a9d7fa1f7e01",
                    "a91b3522-c394-40b0-a82c-a9d7fa1f7e04",
                ],
            },
        }
