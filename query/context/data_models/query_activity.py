"""
Query Activity Data Model for the Indaleko Activity Context system.

This module defines the data model used to represent queries in the
Indaleko Activity Context system.

Project Indaleko
Copyright (C) 2025 Tony Mason

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
import uuid
from datetime import UTC, datetime
from typing import Any

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from pydantic import Field, validator

from data_models.base import IndalekoBaseModel

# pylint: enable=wrong-import-position


class QueryActivityData(IndalekoBaseModel):
    """Data model for query activities in the activity context system."""

    query_id: uuid.UUID = Field(..., description="Unique identifier for the query")
    query_text: str = Field(..., description="The text of the query")
    execution_time: float | None = Field(
        None,
        description="Query execution time in milliseconds",
    )
    result_count: int | None = Field(None, description="Number of results returned")
    context_handle: uuid.UUID | None = Field(
        None,
        description="Associated activity context",
    )
    query_params: dict[str, Any] | None = Field(None, description="Query parameters")
    relationship_type: str | None = Field(
        None,
        description="Relationship to previous query (refinement, broadening, pivot)",
    )
    previous_query_id: uuid.UUID | None = Field(
        None,
        description="ID of the previous query in the exploration path",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the query was executed",
    )

    # Add pydantic validator to ensure timezone awareness
    @validator("timestamp")
    def ensure_timezone(cls, v):
        """Ensure the timestamp has a timezone."""
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v

    class Config:
        """Configuration for the QueryActivityData model."""

        json_schema_extra = {
            "example": {
                "query_id": "00000000-0000-0000-0000-000000000000",
                "query_text": "Find documents about Indaleko",
                "execution_time": 123.45,
                "result_count": 5,
                "context_handle": "00000000-0000-0000-0000-000000000000",
                "query_params": {"database": "main", "limit": 10},
                "relationship_type": "refinement",
                "previous_query_id": "00000000-0000-0000-0000-000000000000",
                "timestamp": "2025-04-20T15:30:45.123456Z",
            },
        }


def main():
    """Test code for QueryActivityData model."""
    # Create a test instance
    test_instance = QueryActivityData(
        query_id=uuid.uuid4(),
        query_text="Find documents about Indaleko",
        execution_time=123.45,
        result_count=5,
        context_handle=uuid.uuid4(),
        query_params={"database": "main", "limit": 10},
        relationship_type="refinement",
        previous_query_id=uuid.uuid4(),
    )

    # Print as JSON
    print(test_instance.model_dump_json(indent=2))

    # Test serialization to dictionary
    print("\nSerialized to dictionary:")
    print(test_instance.model_dump())

    # Test building ArangoDB document
    print("\nArangoDB document:")
    print(test_instance.build_arangodb_doc())


if __name__ == "__main__":
    main()
