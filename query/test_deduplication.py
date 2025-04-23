"""
Test script for the result deduplication functionality.

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

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from query.result_analysis.result_formatter import (
    deduplicate_results,
    format_results_for_display,
)


def create_sample_results():
    """Create sample results for testing deduplication."""
    return [
        # Two copies of the same file
        {
            "name": "report-2023.pdf",
            "size": 1048576,
            "checksum": "abc123",
            "Record": {
                "Attributes": {
                    "Label": "report-2023.pdf",
                    "Path": "/home/user/documents/report-2023.pdf",
                    "st_mtime": 1672531200,
                    "mimeType": "application/pdf",
                },
            },
        },
        {
            "name": "report-2023-backup.pdf",
            "size": 1048576,
            "checksum": "abc123",  # Same checksum
            "Record": {
                "Attributes": {
                    "Label": "report-2023-backup.pdf",
                    "Path": "/home/user/backups/report-2023-backup.pdf",
                    "st_mtime": 1672617600,  # One day later
                    "mimeType": "application/pdf",
                },
            },
        },
        # Similar files with different content
        {
            "name": "thesis-draft-v1.docx",
            "size": 2097152,
            "checksum": "def456",
            "Record": {
                "Attributes": {
                    "Label": "thesis-draft-v1.docx",
                    "Path": "/home/user/documents/thesis/thesis-draft-v1.docx",
                    "st_mtime": 1669852800,
                    "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                },
            },
        },
        {
            "name": "thesis-draft-v2.docx",
            "size": 2101248,  # Slightly different size
            "checksum": "ghi789",  # Different checksum
            "Record": {
                "Attributes": {
                    "Label": "thesis-draft-v2.docx",
                    "Path": "/home/user/documents/thesis/thesis-draft-v2.docx",
                    "st_mtime": 1671667200,  # Later timestamp
                    "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                },
            },
        },
        # Completely different file
        {
            "name": "presentation.pptx",
            "size": 3145728,
            "checksum": "jkl012",
            "Record": {
                "Attributes": {
                    "Label": "presentation.pptx",
                    "Path": "/home/user/documents/presentations/presentation.pptx",
                    "st_mtime": 1673827200,
                    "mimeType": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                },
            },
        },
    ]


def main():
    """Test the deduplication functionality."""
    print("Testing Indaleko Result Deduplication")
    print("=====================================\n")

    # Create sample results
    sample_results = create_sample_results()
    print(f"Original results count: {len(sample_results)}")

    # Test with different similarity thresholds
    for threshold in [0.75, 0.85, 0.95]:
        print(f"\nTesting with similarity threshold: {threshold}")

        # Deduplicate results
        deduped_results = deduplicate_results(
            sample_results, similarity_threshold=threshold,
        )

        # Print statistics
        print(f"Original count: {deduped_results.original_count}")
        print(f"Unique count: {deduped_results.unique_count}")
        print(f"Suppressed count: {deduped_results.suppressed_count}")
        print(f"Categories: {deduped_results.categories}")

        # Display results
        print("\nFormatted Results:")
        formatted_display = format_results_for_display(
            deduped_results,
            include_duplicates=True,
            max_groups=10,
            include_summary=True,
        )
        print(formatted_display)

    print("\nTest completed successfully!")


if __name__ == "__main__":
    main()
