"""
Learning event data model for the knowledge base updating feature.

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
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
# pylint: enable=wrong-import-position


class LearningEventType(str, Enum):
    """Types of learning events in the knowledge base."""
    query_success = "query_success"
    user_feedback = "user_feedback"
    entity_discovery = "entity_discovery"
    schema_update = "schema_update"
    pattern_discovery = "pattern_discovery"


class LearningEventDataModel(IndalekoBaseModel):
    """Record of a system learning event."""
    event_id: UUID = uuid4()
    event_type: LearningEventType
    timestamp: datetime = datetime.now(timezone.utc)
    source: str  # Origin of the learning (query, user, system)
    confidence: float  # Confidence in the learned information (0-1)
    content: Dict[str, Any]  # The actual learned information
    metadata: Dict[str, Any] = {}  # Additional context
    
    class Config:
        """Sample configuration data for the data model."""
        json_schema_extra = {
            "example": {
                "event_id": "981a3522-c394-40b0-a82c-a9d7fa1f7e01",
                "event_type": LearningEventType.query_success,
                "timestamp": datetime.now(timezone.utc),
                "source": "query_execution",
                "confidence": 0.85,
                "content": {
                    "query": "Find documents about Indaleko",
                    "result_count": 5,
                    "entities": ["Indaleko"],
                    "patterns": ["subject_search"]
                },
                "metadata": {
                    "user_id": "user123",
                    "session_id": "session456",
                    "execution_time": 0.23
                }
            }
        }