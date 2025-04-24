"""
This module defines the query history data model for Indaleko.

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
from textwrap import dedent
from typing import Any, TypeVar

from pydantic import BaseModel, Field, field_validator

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

T = TypeVar("T", bound="IndalekoQueryHistoryDataModel")

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel  # noqa: E402
from data_models.record import IndalekoRecordDataModel  # noqa: E402
from query.query_processing.data_models.parser_data import ParserResults  # noqa: E402
from query.query_processing.data_models.query_input import StructuredQuery  # noqa: E402
from query.query_processing.data_models.translator_response import TranslatorOutput

# pylint: enable=wrong-import-position


class QueryHistoryData(BaseModel):
    """This class defines the baseline data that is stored in the query history."""

    OriginalQuery: str = Field(
        ...,
        title="OriginalQuery",
        description="The original query from the user.",
    )

    ParsedResults: ParserResults = Field(
        ...,
        title="ParsingResults",
        description="The results of parsing the query.",
    )

    LLMName: str = Field(
        ...,
        title="LLMName",
        description="The name of the LLM that processed the query.",
    )

    LLMQuery: StructuredQuery = Field(
        ...,
        title="LLMQuery",
        description="The structured query submitted to the LLM for processing.",
    )

    TranslatedOutput: TranslatorOutput = Field(
        ...,
        title="TranslatedOutput",
        description="The translated output from the LLM.",
    )

    ExecutionPlan: dict[str, Any] | None = Field(
        None,
        title="ExecutionPlan",
        description="The execution plan for the query.",
    )

    RawResults: list[dict[str, Any]] = Field(
        ...,
        title="Results",
        description="The results of the database query.",
    )

    AnalyzedResults: list[dict[str, Any]] | None = Field(
        ...,
        title="AnalyzedResults",
        description="The analyzed results of the database query.",
    )

    Facets: Any = Field(
        ...,
        title="Facets",
        description="The facets extracted from the query results (can be list, dict, or object).",
    )

    RankedResults: Any = Field(
        ...,
        title="RankedResults",
        description="The ranked results of the database query (can be list, dict, or object).",
    )

    StartTimestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        title="StartTimestamp",
        description="The timestamp of when the query processing started.",
    )

    EndTimestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        title="EndTimestamp",
        description="The timestamp of when the query processing ended.",
    )

    ElapsedTime: float | None = Field(
        None,
        title="ElapsedTime",
        description="The elapsed time in seconds.",
    )

    ResourceUtilization: dict[str, Any] | None = Field(
        None,
        title="ResourceUtilization",
        description="Resource utilization metrics such as CPU and memory usage.",
    )

    query_activity_id: str | None = Field(
        None,
        title="QueryActivityID",
        description="Reference ID to the query activity in the activity context system.",
    )

    @staticmethod
    def validate_timestamp(ts: str | datetime) -> datetime:
        """Ensure that the timestamp is in UTC"""
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        return ts

    @field_validator("StartTimestamp", mode="before")
    @classmethod
    def ensure_starttime(cls, value: datetime):
        return cls.validate_timestamp(value)

    @field_validator("EndTimestamp", mode="before")
    @classmethod
    def ensure_endtime(cls, value: datetime):
        return cls.validate_timestamp(value)

    @field_validator("ElapsedTime", mode="before")
    @classmethod
    def calculate_elapsed_time(
        cls: type[T],
        value: float | None = None,
        values: dict[str, Any] | None = None,
    ) -> float:
        """Calculate the elapsed time if it is not provided."""
        if value is None:
            start = values.get("StartTimestamp", datetime.now(UTC))
            end = values.get("EndTimestamp", datetime.now(UTC))
            value = (end - start).total_seconds()
        return value

    class Config:
        """Sample configuration data for the data model."""

        json_schema_extra = {
            "example": {
                "OriginalQuery": "Show me the latest performance data",
                "Categorization": {
                    "Intent": "search",
                    "Entities": {"PerformanceData": "latest"},
                },
                "ImportantTerms": {"PerformanceData": "latest"},
                "GeneratedAQL": "FOR doc IN PerformanceData SORT doc.Timestamp DESC LIMIT 1 RETURN doc",
                "LLMExplanations": {
                    "Intent": "search",
                    "Rationale": "The user wants to see the latest performance data.",
                    "AlternativesConsidered": [
                        {
                            "Intent": "search",
                            "Rationale": "The user wants to see the latest performance data.",
                        },
                    ],
                },
                "ExecutionPlan": {
                    "plan": {
                        "nodes": [],
                        "rules": [],
                        "collections": ["PerformanceData"],
                        "estimatedCost": 10.5,
                    },
                    "cacheable": True,
                    "warnings": [],
                    "analysis": {
                        "summary": {"estimated_cost": 10.5},
                        "warnings": [],
                        "recommendations": [],
                    },
                },
                "QueryResults": {
                    "Results": [
                        {
                            "Timestamp": "2024-07-30T23:38:48.319654+00:00",
                            "Data": "Base64EncodedData",
                        },
                    ],
                },
                "StartTimestamp": "2024-07-30T23:38:48.319654+00:00",
                "EndTimestamp": "2024-07-30T23:38:48.319654+00:00",
                "ElapsedTime": 0.0,
                "ResourceUtilization": {"CPU": 0.0, "Memory": 0.0},
            },
        }


class IndalekoQueryHistoryDataModel(IndalekoBaseModel):
    """
    This class defines the data model for the Indaleko query history.
    """

    Record: IndalekoRecordDataModel = Field(
        ...,
        title="Record",
        description="The record associated with the performance data.",
    )

    QueryHistory: QueryHistoryData | None = Field(
        None,
        title="QueryHistory",
        description=dedent(
            """
            The query history data. If omitted, the query history
            can be retrieved from the database using the record,
            as the Data element in the Record conforms to this
            schema (or a successor schema - use the version number.)
            """,
        ),
    )

    class Config:
        """Sample configuration data for the data model."""

        json_schema_extra = {
            "example": {
                "Record": IndalekoRecordDataModel.Config.json_schema_extra["example"],
                "QueryHistory": QueryHistoryData.Config.json_schema_extra["example"],
            },
        }


def main():
    """This allows testing the data model."""
    IndalekoQueryHistoryDataModel.test_model_main()


if __name__ == "__main__":
    main()
