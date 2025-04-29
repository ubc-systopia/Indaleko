"""
Feedback record data model for the knowledge base updating feature.

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


class FeedbackType(str, Enum):
    """Types of feedback records."""

    explicit_positive = "explicit_positive"
    explicit_negative = "explicit_negative"
    implicit_positive = "implicit_positive"
    implicit_negative = "implicit_negative"


class FeedbackRecordDataModel(IndalekoBaseModel):
    """Record of user feedback on system performance."""

    feedback_id: UUID = uuid4()
    feedback_type: FeedbackType
    timestamp: datetime = datetime.now(UTC)
    user_id: UUID | None = None  # Anonymous if None
    query_id: UUID | None = None  # Associated query if relevant
    pattern_id: UUID | None = None  # Pattern being evaluated
    feedback_strength: float  # How strong the feedback is (0-1)
    feedback_data: dict[str, Any]  # Detailed feedback information

    class Config:
        """Sample configuration data for the data model."""

        json_schema_extra = {
            "example": {
                "feedback_id": "b81c3522-c394-40b0-a82c-a9d7fa1f7e05",
                "feedback_type": FeedbackType.explicit_positive,
                "timestamp": datetime.now(UTC),
                "user_id": "user123",
                "query_id": "query789",
                "pattern_id": "a81b3522-c394-40b0-a82c-a9d7fa1f7e03",
                "feedback_strength": 0.9,
                "feedback_data": {
                    "comment": "These results were exactly what I was looking for",
                    "result_relevance": 0.95,
                    "result_completeness": 0.85,
                    "interaction": "clicked_result",
                },
            },
        }
