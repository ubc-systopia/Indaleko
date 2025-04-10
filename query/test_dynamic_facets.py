"""
Test script for dynamic facets functionality.

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
import json
from datetime import datetime, timedelta
from pprint import pprint

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from query.result_analysis.facet_generator import FacetGenerator
from query.result_analysis.data_models.facet_data_model import DynamicFacets, Facet


def create_sample_results():
    """Create sample results for testing facets."""
    now = datetime.now()
    
    return [
        # PDF files with different timestamps
        {
            "name": "report-2023.pdf",
            "size": 1048576,
            "Record": {
                "Attributes": {
                    "Label": "report-2023.pdf",
                    "Path": "/home/user/documents/report-2023.pdf",
                    "st_mtime": (now - timedelta(days=30)).timestamp(),
                    "mimeType": "application/pdf"
                }
            },
            "SemanticAttributes": [
                {
                    "Identifier": {"Label": "ContentType"},
                    "Value": "Report"
                },
                {
                    "Identifier": {"Label": "Author"},
                    "Value": "John Smith"
                }
            ]
        },
        {
            "name": "presentation.pdf",
            "size": 2097152,
            "Record": {
                "Attributes": {
                    "Label": "presentation.pdf",
                    "Path": "/home/user/documents/presentations/presentation.pdf",
                    "st_mtime": (now - timedelta(days=15)).timestamp(),
                    "mimeType": "application/pdf"
                }
            },
            "SemanticAttributes": [
                {
                    "Identifier": {"Label": "ContentType"},
                    "Value": "Presentation"
                },
                {
                    "Identifier": {"Label": "Author"},
                    "Value": "Jane Doe"
                }
            ]
        },
        {
            "name": "contract.pdf",
            "size": 512000,
            "Record": {
                "Attributes": {
                    "Label": "contract.pdf",
                    "Path": "/home/user/documents/legal/contract.pdf",
                    "st_mtime": (now - timedelta(days=5)).timestamp(),
                    "mimeType": "application/pdf"
                }
            },
            "SemanticAttributes": [
                {
                    "Identifier": {"Label": "ContentType"},
                    "Value": "Legal"
                },
                {
                    "Identifier": {"Label": "Author"},
                    "Value": "Legal Team"
                }
            ]
        },
        
        # Office documents
        {
            "name": "meeting-notes.docx",
            "size": 128000,
            "Record": {
                "Attributes": {
                    "Label": "meeting-notes.docx",
                    "Path": "/home/user/documents/meeting-notes.docx",
                    "st_mtime": (now - timedelta(days=2)).timestamp(),
                    "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                }
            },
            "SemanticAttributes": [
                {
                    "Identifier": {"Label": "ContentType"},
                    "Value": "Notes"
                },
                {
                    "Identifier": {"Label": "Project"},
                    "Value": "Indaleko"
                }
            ]
        },
        {
            "name": "budget.xlsx",
            "size": 256000,
            "Record": {
                "Attributes": {
                    "Label": "budget.xlsx",
                    "Path": "/home/user/documents/finance/budget.xlsx",
                    "st_mtime": (now - timedelta(days=10)).timestamp(),
                    "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                }
            },
            "SemanticAttributes": [
                {
                    "Identifier": {"Label": "ContentType"},
                    "Value": "Financial"
                },
                {
                    "Identifier": {"Label": "Project"},
                    "Value": "Indaleko"
                }
            ]
        },
        
        # Images
        {
            "name": "diagram.png",
            "size": 1500000,
            "Record": {
                "Attributes": {
                    "Label": "diagram.png",
                    "Path": "/home/user/documents/images/diagram.png",
                    "st_mtime": (now - timedelta(days=20)).timestamp(),
                    "mimeType": "image/png"
                }
            },
            "SemanticAttributes": [
                {
                    "Identifier": {"Label": "ContentType"},
                    "Value": "Diagram"
                },
                {
                    "Identifier": {"Label": "Project"},
                    "Value": "Architecture"
                }
            ]
        },
        {
            "name": "photo.jpg",
            "size": 3000000,
            "Record": {
                "Attributes": {
                    "Label": "photo.jpg",
                    "Path": "/home/user/pictures/photo.jpg",
                    "st_mtime": (now - timedelta(days=45)).timestamp(),
                    "mimeType": "image/jpeg"
                }
            },
            "SemanticAttributes": [
                {
                    "Identifier": {"Label": "ContentType"},
                    "Value": "Photo"
                },
                {
                    "Identifier": {"Label": "Location"},
                    "Value": "Office"
                }
            ]
        },
        
        # Code files
        {
            "name": "main.py",
            "size": 5000,
            "Record": {
                "Attributes": {
                    "Label": "main.py",
                    "Path": "/home/user/projects/indaleko/main.py",
                    "st_mtime": (now - timedelta(days=1)).timestamp(),
                    "mimeType": "text/x-python"
                }
            },
            "SemanticAttributes": [
                {
                    "Identifier": {"Label": "ContentType"},
                    "Value": "SourceCode"
                },
                {
                    "Identifier": {"Label": "Project"},
                    "Value": "Indaleko"
                }
            ]
        },
        {
            "name": "utils.js",
            "size": 8000,
            "Record": {
                "Attributes": {
                    "Label": "utils.js",
                    "Path": "/home/user/projects/website/utils.js",
                    "st_mtime": (now - timedelta(days=12)).timestamp(),
                    "mimeType": "application/javascript"
                }
            },
            "SemanticAttributes": [
                {
                    "Identifier": {"Label": "ContentType"},
                    "Value": "SourceCode"
                },
                {
                    "Identifier": {"Label": "Project"},
                    "Value": "Website"
                }
            ]
        }
    ]


def print_facet_details(facet):
    """Print details of a facet in a readable format."""
    print(f"\n{facet.name} ({facet.type}):")
    print(f"  Field: {facet.field}")
    print(f"  Coverage: {facet.coverage * 100:.1f}%")
    print(f"  Distribution entropy: {facet.distribution_entropy:.3f}")
    
    print("  Values:")
    for i, value in enumerate(facet.values, 1):
        print(f"    {i}. {value.value} ({value.count} results)")
        print(f"       Query: {value.query_refinement}")


def main():
    """Test the dynamic facets functionality."""
    print("Testing Indaleko Dynamic Facets")
    print("==============================\n")
    
    # Create sample results
    sample_results = create_sample_results()
    print(f"Sample results: {len(sample_results)} items")
    
    # Test with different facet generator configurations
    test_cases = [
        {
            "name": "Basic facets",
            "params": {"max_facets": 3, "min_facet_coverage": 0.2, "min_value_count": 1, "conversational": False}
        },
        {
            "name": "High coverage requirement",
            "params": {"max_facets": 3, "min_facet_coverage": 0.5, "min_value_count": 1, "conversational": False}
        },
        {
            "name": "More facets",
            "params": {"max_facets": 5, "min_facet_coverage": 0.2, "min_value_count": 1, "conversational": False}
        },
        {
            "name": "With conversational hints",
            "params": {"max_facets": 3, "min_facet_coverage": 0.2, "min_value_count": 1, "conversational": True}
        }
    ]
    
    for test_case in test_cases:
        print(f"\n===== {test_case['name']} =====")
        
        # Initialize facet generator with test case parameters
        facet_generator = FacetGenerator(**test_case["params"])
        
        # Generate facets
        dynamic_facets = facet_generator.generate(sample_results)
        
        # Print facet structure
        print(f"Generated {len(dynamic_facets.facets)} facets")
        
        # Print each facet
        for facet in dynamic_facets.facets:
            print_facet_details(facet)
        
        # Print suggestions
        print("\nSuggestions:")
        for suggestion in dynamic_facets.suggestions:
            print(f"- {suggestion}")
        
        # Print conversational hints if available
        if dynamic_facets.conversational_hints:
            print("\nConversational hints:")
            for hint in dynamic_facets.conversational_hints:
                print(f"- {hint}")
        
        # Print statistics
        print("\nStatistics:")
        for key, value in dynamic_facets.facet_statistics.items():
            print(f"- {key}: {value}")
    
    print("\nTest completed successfully!")


if __name__ == "__main__":
    main()