"""
Query refinement manager for Indaleko search.

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
import re
import sys
from datetime import datetime
from typing import Any

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from pydantic import Field

from data_models.base import IndalekoBaseModel
from query.result_analysis.data_models.facet_data_model import (
    DynamicFacets,
    Facet,
    FacetType,
    FacetValue,
)


class ActiveRefinement(IndalekoBaseModel):
    """Represents an active query refinement."""

    facet_name: str = Field(..., description="Name of the facet")
    facet_type: FacetType = Field(..., description="Type of facet")
    value: str = Field(..., description="Selected facet value")
    query_fragment: str = Field(..., description="Query fragment for this refinement")
    applied_at: datetime = Field(
        default_factory=datetime.now, description="When this refinement was applied",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "facet_name": "File Type",
                "facet_type": "file_type",
                "value": "pdf",
                "query_fragment": "file_type:pdf",
                "applied_at": "2024-04-10T12:30:45Z",
            },
        }


class QueryRefinementState(IndalekoBaseModel):
    """Tracks the state of query refinements."""

    original_query: str = Field(..., description="Original unrefined query")
    active_refinements: list[ActiveRefinement] = Field(
        default_factory=list, description="Currently active refinements",
    )
    refinement_history: list[ActiveRefinement] = Field(
        default_factory=list, description="History of all refinements that were applied",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "original_query": "find documents about machine learning",
                "active_refinements": [
                    {
                        "facet_name": "File Type",
                        "facet_type": "file_type",
                        "value": "pdf",
                        "query_fragment": "file_type:pdf",
                        "applied_at": "2024-04-10T12:30:45Z",
                    },
                ],
                "refinement_history": [
                    {
                        "facet_name": "File Type",
                        "facet_type": "file_type",
                        "value": "pdf",
                        "query_fragment": "file_type:pdf",
                        "applied_at": "2024-04-10T12:30:45Z",
                    },
                ],
            },
        }


class QueryRefiner:
    """
    Manages the refinement of queries based on facet selections.
    """

    def __init__(self):
        """Initialize the QueryRefiner."""
        self.current_state = None
        self.facet_mappings = {
            FacetType.FILE_TYPE: self._apply_file_type_refinement,
            FacetType.DATE: self._apply_date_refinement,
            FacetType.LOCATION: self._apply_location_refinement,
            FacetType.SIZE: self._apply_size_refinement,
            FacetType.AUTHOR: self._apply_author_refinement,
            FacetType.SEMANTIC: self._apply_semantic_refinement,
            FacetType.TAG: self._apply_tag_refinement,
            FacetType.CUSTOM: self._apply_custom_refinement,
            FacetType.CONTENT_TYPE: self._apply_content_type_refinement,
        }

    def initialize_state(self, query: str) -> QueryRefinementState:
        """
        Initialize a new query refinement state.

        Args:
            query: The original query string

        Returns:
            A new QueryRefinementState object
        """
        self.current_state = QueryRefinementState(original_query=query)
        return self.current_state

    def apply_refinement(
        self, facet: Facet, value: FacetValue, add_to_history: bool = True,
    ) -> tuple[str, QueryRefinementState]:
        """
        Apply a facet refinement to the current query.

        Args:
            facet: The facet to apply
            value: The facet value to apply
            add_to_history: Whether to add this refinement to history

        Returns:
            Tuple of (refined query string, updated refinement state)
        """
        if self.current_state is None:
            raise ValueError("Must initialize state with initialize_state() first")

        # Create the refinement
        refinement = ActiveRefinement(
            facet_name=facet.name,
            facet_type=facet.type,
            value=value.value,
            query_fragment=value.query_refinement,
        )

        # Add to active refinements and history
        self.current_state.active_refinements.append(refinement)
        if add_to_history:
            self.current_state.refinement_history.append(refinement)

        # Generate the refined query
        refined_query = self._generate_refined_query()

        return refined_query, self.current_state

    def remove_refinement(
        self, facet_name: str, value: str,
    ) -> tuple[str, QueryRefinementState]:
        """
        Remove an active refinement.

        Args:
            facet_name: The name of the facet to remove
            value: The value to remove

        Returns:
            Tuple of (refined query string, updated refinement state)
        """
        if self.current_state is None:
            raise ValueError("Must initialize state with initialize_state() first")

        # Remove from active refinements
        self.current_state.active_refinements = [
            r
            for r in self.current_state.active_refinements
            if not (r.facet_name == facet_name and r.value == value)
        ]

        # Generate the refined query
        refined_query = self._generate_refined_query()

        return refined_query, self.current_state

    def clear_refinements(self) -> tuple[str, QueryRefinementState]:
        """
        Clear all active refinements.

        Returns:
            Tuple of (original query string, updated refinement state)
        """
        if self.current_state is None:
            raise ValueError("Must initialize state with initialize_state() first")

        # Clear active refinements
        self.current_state.active_refinements = []

        # Return the original query
        return self.current_state.original_query, self.current_state

    def _generate_refined_query(self) -> str:
        """
        Generate a refined query string based on active refinements.

        Returns:
            Refined query string
        """
        if not self.current_state.active_refinements:
            return self.current_state.original_query

        # Start with the original query
        base_query = self.current_state.original_query.strip()

        # Group refinements by type
        refinements_by_type = {}
        for refinement in self.current_state.active_refinements:
            if refinement.facet_type not in refinements_by_type:
                refinements_by_type[refinement.facet_type] = []
            refinements_by_type[refinement.facet_type].append(refinement)

        # Add refinements
        added_refinements = []
        for facet_type, refinements in refinements_by_type.items():
            if facet_type in self.facet_mappings:
                refined_fragment = self.facet_mappings[facet_type](refinements)
                added_refinements.append(refined_fragment)

        # Combine the query with refinements
        if added_refinements:
            # Check if original query is already structured
            if re.search(r':\s*["\']?[\w\s-]+["\']?', base_query):
                # Already has filters, add more with AND
                refined_query = f"{base_query} AND {' AND '.join(added_refinements)}"
            else:
                # Simple query, add filters
                refined_query = f"{base_query} {' '.join(added_refinements)}"
        else:
            refined_query = base_query

        return refined_query

    def _apply_file_type_refinement(self, refinements: list[ActiveRefinement]) -> str:
        """Apply file type refinements."""
        if len(refinements) == 1:
            return refinements[0].query_fragment
        else:
            values = [f'"{r.value}"' for r in refinements]
            return f'file_type:({" OR ".join(values)})'

    def _apply_date_refinement(self, refinements: list[ActiveRefinement]) -> str:
        """Apply date refinements."""
        if len(refinements) == 1:
            return refinements[0].query_fragment
        else:
            # Date refinements typically don't combine well with OR
            # Using the most recent one as precedence
            newest = max(refinements, key=lambda r: r.applied_at)
            return newest.query_fragment

    def _apply_location_refinement(self, refinements: list[ActiveRefinement]) -> str:
        """Apply location refinements."""
        if len(refinements) == 1:
            return refinements[0].query_fragment
        else:
            values = [f'"{r.value}"' for r in refinements]
            return f'location:({" OR ".join(values)})'

    def _apply_size_refinement(self, refinements: list[ActiveRefinement]) -> str:
        """Apply size refinements."""
        if len(refinements) == 1:
            return refinements[0].query_fragment
        else:
            # Size refinements typically don't combine well with OR
            # Using the most recent one as precedence
            newest = max(refinements, key=lambda r: r.applied_at)
            return newest.query_fragment

    def _apply_author_refinement(self, refinements: list[ActiveRefinement]) -> str:
        """Apply author refinements."""
        if len(refinements) == 1:
            return refinements[0].query_fragment
        else:
            values = [f'"{r.value}"' for r in refinements]
            return f'author:({" OR ".join(values)})'

    def _apply_semantic_refinement(self, refinements: list[ActiveRefinement]) -> str:
        """Apply semantic refinements."""
        # Group by facet name since semantic could be different attributes
        by_facet_name = {}
        for r in refinements:
            if r.facet_name not in by_facet_name:
                by_facet_name[r.facet_name] = []
            by_facet_name[r.facet_name].append(r)

        fragments = []
        for facet_name, facet_refinements in by_facet_name.items():
            if len(facet_refinements) == 1:
                fragments.append(facet_refinements[0].query_fragment)
            else:
                field = facet_name.lower()
                values = [f'"{r.value}"' for r in facet_refinements]
                fragments.append(f'{field}:({" OR ".join(values)})')

        return " AND ".join(fragments)

    def _apply_tag_refinement(self, refinements: list[ActiveRefinement]) -> str:
        """Apply tag refinements."""
        if len(refinements) == 1:
            return refinements[0].query_fragment
        else:
            values = [f'"{r.value}"' for r in refinements]
            return f'tag:({" OR ".join(values)})'

    def _apply_content_type_refinement(
        self, refinements: list[ActiveRefinement],
    ) -> str:
        """Apply content type refinements."""
        if len(refinements) == 1:
            return refinements[0].query_fragment
        else:
            values = [f'"{r.value}"' for r in refinements]
            return f'content_type:({" OR ".join(values)})'

    def _apply_custom_refinement(self, refinements: list[ActiveRefinement]) -> str:
        """Apply custom refinements."""
        return " AND ".join(r.query_fragment for r in refinements)

    def get_facet_options(
        self, facets: DynamicFacets,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Generate facet selection options for display.

        Args:
            facets: DynamicFacets object with available facets

        Returns:
            Dictionary mapping selection keys to facet selection options
        """
        options = {}
        option_count = 1

        for facet in facets.facets:
            for value in facet.values[:7]:  # Limit to 7 values per facet
                key = str(option_count)
                options[key] = {
                    "facet": facet,
                    "value": value,
                    "display": f"{facet.name}: {value.value} ({value.count} results)",
                }
                option_count += 1

        return options

    def format_active_refinements(self) -> str:
        """
        Format the active refinements for display.

        Returns:
            Formatted string of active refinements
        """
        if not self.current_state or not self.current_state.active_refinements:
            return "No active refinements"

        lines = ["Active Refinements:"]
        for i, ref in enumerate(self.current_state.active_refinements, 1):
            lines.append(f"{i}. {ref.facet_name}: {ref.value}")

        return "\n".join(lines)

    def get_active_refinement_by_index(self, index: int) -> ActiveRefinement | None:
        """
        Get an active refinement by its index.

        Args:
            index: 1-based index of the refinement

        Returns:
            The ActiveRefinement or None if not found
        """
        if not self.current_state or not self.current_state.active_refinements:
            return None

        idx = index - 1  # Convert to 0-based
        if 0 <= idx < len(self.current_state.active_refinements):
            return self.current_state.active_refinements[idx]

        return None
