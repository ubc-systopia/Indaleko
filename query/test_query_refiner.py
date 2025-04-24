"""
Test script for query refinement functionality.

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
import time

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from query.result_analysis.data_models.facet_data_model import (
    DynamicFacets,
    Facet,
    FacetType,
    FacetValue,
)
from query.result_analysis.query_refiner import QueryRefiner


def create_sample_facets():
    """Create sample facets for testing query refinement."""
    # Create file type facet
    file_type_facet = Facet(
        name="File Type",
        field="file_type",
        type=FacetType.FILE_TYPE,
        values=[
            FacetValue(value="pdf", count=15, query_refinement="file_type:pdf"),
            FacetValue(value="docx", count=7, query_refinement="file_type:docx"),
            FacetValue(value="xlsx", count=5, query_refinement="file_type:xlsx"),
        ],
        coverage=0.85,
        distribution_entropy=0.65,
    )

    # Create date facet
    date_facet = Facet(
        name="Date",
        field="date",
        type=FacetType.DATE,
        values=[
            FacetValue(
                value="This month",
                count=10,
                query_refinement='date:"this month"',
            ),
            FacetValue(
                value="Last month",
                count=12,
                query_refinement='date:"last month"',
            ),
            FacetValue(value="Last year", count=8, query_refinement='date:"last year"'),
        ],
        coverage=0.90,
        distribution_entropy=0.70,
    )

    # Create author facet
    author_facet = Facet(
        name="Author",
        field="author",
        type=FacetType.AUTHOR,
        values=[
            FacetValue(
                value="John Smith",
                count=8,
                query_refinement='author:"John Smith"',
            ),
            FacetValue(value="Jane Doe", count=7, query_refinement='author:"Jane Doe"'),
            FacetValue(
                value="Alice Johnson",
                count=5,
                query_refinement='author:"Alice Johnson"',
            ),
        ],
        coverage=0.60,
        distribution_entropy=0.80,
    )

    # Create location facet
    location_facet = Facet(
        name="Location",
        field="location",
        type=FacetType.LOCATION,
        values=[
            FacetValue(
                value="documents",
                count=20,
                query_refinement="location:documents",
            ),
            FacetValue(
                value="downloads",
                count=8,
                query_refinement="location:downloads",
            ),
            FacetValue(value="desktop", count=12, query_refinement="location:desktop"),
        ],
        coverage=0.95,
        distribution_entropy=0.75,
    )

    # Create a dynamic facets object
    facets = DynamicFacets(
        facets=[file_type_facet, date_facet, author_facet, location_facet],
        suggestions=[
            "Filter by PDF files",
            "Focus on documents from this month",
            "Look for files by John Smith",
        ],
        original_count=50,
        facet_statistics={
            "most_common_file_type": "pdf",
            "most_common_file_type_count": 15,
            "date_range_days": 365,
        },
        conversational_hints=[
            "I found many PDF files. Would you like to focus on those?",
            "These results span a full year. Would you like to narrow by time period?",
        ],
    )

    return facets


def main():
    """Test the query refinement functionality."""
    print("Testing Indaleko Query Refinement")
    print("===============================\n")

    # Create the query refiner
    refiner = QueryRefiner()

    # Initialize with a basic query
    original_query = "find documents about machine learning"
    print(f"Original query: {original_query}")
    refiner.initialize_state(original_query)

    # Get sample facets
    facets = create_sample_facets()

    # Test various refinements
    test_cases = [
        {
            "name": "Add file type refinement",
            "facet": facets.facets[0],
            "value": facets.facets[0].values[0],
        },
        {
            "name": "Add date refinement",
            "facet": facets.facets[1],
            "value": facets.facets[1].values[0],
        },
        {
            "name": "Add author refinement",
            "facet": facets.facets[2],
            "value": facets.facets[2].values[0],
        },
        {
            "name": "Remove file type refinement",
            "remove": (facets.facets[0].name, facets.facets[0].values[0].value),
        },
        {
            "name": "Add location refinement",
            "facet": facets.facets[3],
            "value": facets.facets[3].values[0],
        },
        {"name": "Clear all refinements"},
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n===== Test {i}: {test_case['name']} =====")

        if "facet" in test_case and "value" in test_case:
            # Apply a refinement
            refined_query, state = refiner.apply_refinement(
                test_case["facet"],
                test_case["value"],
            )
            print(f"Refined query: {refined_query}")
            print("Active refinements:")
            for j, refinement in enumerate(state.active_refinements, 1):
                print(
                    f"  {j}. {refinement.facet_name}: {refinement.value} → {refinement.query_fragment}",
                )

        elif "remove" in test_case:
            # Remove a refinement
            facet_name, value = test_case["remove"]
            refined_query, state = refiner.remove_refinement(facet_name, value)
            print(f"After removing {facet_name}: {value}")
            print(f"Refined query: {refined_query}")
            print("Active refinements:")
            for j, refinement in enumerate(state.active_refinements, 1):
                print(
                    f"  {j}. {refinement.facet_name}: {refinement.value} → {refinement.query_fragment}",
                )

        elif "name" in test_case and test_case["name"] == "Clear all refinements":
            # Clear all refinements
            original, state = refiner.clear_refinements()
            print(f"Cleared all refinements. Back to: {original}")
            print(f"Active refinements: {len(state.active_refinements)}")

        # Small delay between tests for readability
        time.sleep(0.5)

    # Test facet options generation
    print("\n\n===== Test: Generate Facet Options =====")
    options = refiner.get_facet_options(facets)
    print(f"Generated {len(options)} facet selection options:")
    for key, option in options.items():
        print(f"  [{key}] {option['display']}")

    print("\nTest completed successfully!")


if __name__ == "__main__":
    main()
