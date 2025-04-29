"""
Facet data models for Indaleko.

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
from typing import Any

from pydantic import Field

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from data_models.base import IndalekoBaseModel


class FacetType(str, Enum):
    """Enum for different types of facets."""

    DATE = "date"
    FILE_TYPE = "file_type"
    CONTENT_TYPE = "content_type"
    LOCATION = "location"
    SIZE = "size"
    AUTHOR = "author"
    SEMANTIC = "semantic"
    TAG = "tag"
    CUSTOM = "custom"


class FacetValue(IndalekoBaseModel):
    """Represents a single value within a facet with its count."""

    value: str = Field(..., description="The facet value")
    count: int = Field(..., description="Number of results with this value")
    query_refinement: str = Field(
        ...,
        description="Query string to refine by this value",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "value": "pdf",
                "count": 15,
                "query_refinement": "file_type:pdf",
            },
        }


class Facet(IndalekoBaseModel):
    """Represents a facet that can be used to refine search results."""

    name: str = Field(..., description="Human-readable name of the facet")
    field: str = Field(..., description="Field or property this facet represents")
    type: FacetType = Field(..., description="Type of facet")
    values: list[FacetValue] = Field(
        default_factory=list,
        description="Available values for this facet",
    )
    coverage: float = Field(
        default=0.0,
        description="Percentage of results this facet covers (0.0-1.0)",
    )
    distribution_entropy: float = Field(
        default=0.0,
        description="Entropy of value distribution (higher means more balanced)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "File Type",
                "field": "file_ext",
                "type": "file_type",
                "values": [
                    {"value": "pdf", "count": 15, "query_refinement": "file_type:pdf"},
                    {"value": "docx", "count": 7, "query_refinement": "file_type:docx"},
                ],
                "coverage": 0.85,
                "distribution_entropy": 0.65,
            },
        }


class DynamicFacets(IndalekoBaseModel):
    """Collection of facets dynamically generated from search results."""

    facets: list[Facet] = Field(default_factory=list, description="Available facets")
    suggestions: list[str] = Field(
        default_factory=list,
        description="Suggested refinements",
    )
    original_count: int = Field(default=0, description="Original number of results")
    facet_statistics: dict[str, Any] = Field(
        default_factory=dict,
        description="Statistics about facets",
    )
    conversational_hints: list[str] = Field(
        default_factory=list,
        description="Natural language suggestions for refining the search",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "facets": [
                    {
                        "name": "File Type",
                        "field": "file_ext",
                        "type": "file_type",
                        "values": [
                            {
                                "value": "pdf",
                                "count": 15,
                                "query_refinement": "file_type:pdf",
                            },
                            {
                                "value": "docx",
                                "count": 7,
                                "query_refinement": "file_type:docx",
                            },
                        ],
                        "coverage": 0.85,
                        "distribution_entropy": 0.65,
                    },
                ],
                "suggestions": [
                    "Try filtering by PDF files",
                    "Consider documents from last month",
                ],
                "original_count": 45,
                "facet_statistics": {
                    "most_common_type": "pdf",
                    "date_range": "3 months",
                },
                "conversational_hints": [
                    "I found many PDF files. Would you like to focus on those?",
                    "These results span 3 months. Would you like to narrow by time period?",
                ],
            },
        }
