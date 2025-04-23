"""
Result formatting and deduplication utilities for Indaleko.

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
from collections import defaultdict
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
from utils.misc.identity_resolution import resolve_indaleko_objects


class ResultGroup(IndalekoBaseModel):
    """Represents a group of similar results with a primary result and duplicates."""

    primary: dict[str, Any] = Field(
        ..., description="The primary (representative) result",
    )
    duplicates: list[dict[str, Any]] = Field(
        default_factory=list, description="Duplicate results",
    )
    similarity_scores: list[float] = Field(
        default_factory=list, description="Similarity scores of duplicates to primary",
    )
    last_modified: datetime | None = Field(
        default=None, description="Last modification time of primary item",
    )
    item_count: int = Field(
        default=1, description="Total number of items in this group",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "primary": {"name": "document.pdf", "size": 1024},
                "duplicates": [{"name": "document_backup.pdf", "size": 1024}],
                "similarity_scores": [0.95],
                "last_modified": "2023-09-21T10:30:00Z",
                "item_count": 2,
            },
        }


class FormattedResults(IndalekoBaseModel):
    """Formatted results with grouping, statistics, and summary information."""

    result_groups: list[ResultGroup] = Field(
        default_factory=list, description="Groups of similar results",
    )
    original_count: int = Field(
        default=0, description="Original number of results before deduplication",
    )
    unique_count: int = Field(
        default=0, description="Number of unique results after deduplication",
    )
    suppressed_count: int = Field(
        default=0, description="Number of suppressed duplicate results",
    )
    summary: str = Field(default="", description="Summary of the results")
    query_time: float | None = Field(
        default=None, description="Query execution time in seconds",
    )
    categories: dict[str, int] = Field(
        default_factory=dict, description="Counts of result categories",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "result_groups": [
                    {
                        "primary": {"name": "document.pdf", "size": 1024},
                        "duplicates": [{"name": "document_backup.pdf", "size": 1024}],
                        "similarity_scores": [0.95],
                        "last_modified": "2023-09-21T10:30:00Z",
                        "item_count": 2,
                    },
                ],
                "original_count": 10,
                "unique_count": 9,
                "suppressed_count": 1,
                "summary": "Found 9 unique items (1 duplicate suppressed)",
                "query_time": 0.123,
                "categories": {"pdf": 3, "docx": 4, "txt": 2},
            },
        }


def extract_timestamp(result: dict[str, Any]) -> datetime | None:
    """
    Extract the timestamp from a result item.

    Tries various common timestamp fields and formats.

    Args:
        result: Result item dictionary

    Returns:
        Extracted timestamp as datetime or None if not found
    """
    timestamp = None

    # Check for timestamp in different possible locations and formats
    if "Record" in result and "Attributes" in result["Record"]:
        attrs = result["Record"]["Attributes"]

        # Try modification time first (most common)
        if "st_mtime" in attrs:
            try:
                timestamp = datetime.fromtimestamp(float(attrs["st_mtime"]))
                return timestamp
            except (ValueError, TypeError):
                pass

        # Try other POSIX timestamp fields
        for field in ["st_ctime", "st_atime", "st_birthtime"]:
            if field in attrs:
                try:
                    timestamp = datetime.fromtimestamp(float(attrs[field]))
                    return timestamp
                except (ValueError, TypeError):
                    pass

    # Check for direct timestamp fields
    for field in ["Timestamp", "timestamp", "modified", "created", "accessed"]:
        if field in result:
            value = result[field]

            # Handle string timestamps
            if isinstance(value, str):
                try:
                    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    return timestamp
                except ValueError:
                    pass

            # Handle numeric timestamps
            elif isinstance(value, (int, float)):
                try:
                    timestamp = datetime.fromtimestamp(value)
                    return timestamp
                except (ValueError, TypeError, OverflowError):
                    pass

    return timestamp


def extract_categorization_info(result: dict[str, Any]) -> list[str]:
    """
    Extract information useful for categorizing a result.

    Args:
        result: Result item dictionary

    Returns:
        List of category tags for the result
    """
    categories = []

    # Extract file extension if available
    if "name" in result:
        _, ext = os.path.splitext(result["name"])
        if ext:
            categories.append(ext[1:].lower())  # Remove leading dot

    # Extract MIME type if available
    if "Record" in result and "Attributes" in result["Record"]:
        attrs = result["Record"]["Attributes"]
        if "mimeType" in attrs:
            mime = attrs["mimeType"]
            categories.append(f"mime:{mime}")

            # Add general content type
            main_type = mime.split("/")[0]
            categories.append(main_type)

    # Extract semantic categories if available
    if "SemanticAttributes" in result:
        for attr in result["SemanticAttributes"]:
            if "Identifier" in attr and "Label" in attr["Identifier"]:
                label = attr["Identifier"]["Label"]
                if label in ["FileType", "ContentType", "Category"]:
                    if "Value" in attr:
                        categories.append(f"semantic:{attr['Value']}")

    return categories


def deduplicate_results(
    results: list[dict[str, Any]],
    similarity_threshold: float = 0.85,
    max_results: int | None = None,
) -> FormattedResults:
    """
    Deduplicate results and group similar items together.

    Args:
        results: List of result items to deduplicate
        similarity_threshold: Threshold for considering items as duplicates
        max_results: Maximum number of results to return (None for all)

    Returns:
        FormattedResults with deduplicated and grouped results
    """
    if not results:
        return FormattedResults(
            result_groups=[],
            original_count=0,
            unique_count=0,
            suppressed_count=0,
            summary="No results found",
            categories={},
        )

    # Sort results by modification time (newest first) if available
    # This ensures we prefer newer versions as the primary result
    timed_results = []
    for result in results:
        timestamp = extract_timestamp(result)
        timed_results.append((result, timestamp))

    # Sort by timestamp (most recent first), handling None timestamps
    timed_results.sort(
        key=lambda x: (x[1] is None, x[1] if x[1] is not None else datetime.min),
        reverse=True,
    )

    # Extract categories for statistics
    category_counts = defaultdict(int)
    for result, _ in timed_results:
        categories = extract_categorization_info(result)
        for category in categories:
            category_counts[category] += 1

    # First pass: group exact duplicates (same checksum/object identifier if available)
    exact_groups = {}
    processed_indices = set()

    for i, (result, _) in enumerate(timed_results):
        if i in processed_indices:
            continue

        # Extract identifier for exact matching
        identifier = None

        # Try checksum first
        if "checksum" in result:
            identifier = f"checksum:{result['checksum']}"
        elif "Record" in result and "Attributes" in result["Record"]:
            attrs = result["Record"]["Attributes"]
            if "ObjectIdentifier" in attrs:
                identifier = f"id:{attrs['ObjectIdentifier']}"

        # If we found an identifier, use it to group exact duplicates
        if identifier:
            group = [i]

            # Find all other results with the same identifier
            for j, (other_result, _) in enumerate(timed_results):
                if j != i and j not in processed_indices:
                    other_id = None

                    if "checksum" in other_result:
                        other_id = f"checksum:{other_result['checksum']}"
                    elif (
                        "Record" in other_result
                        and "Attributes" in other_result["Record"]
                    ):
                        other_attrs = other_result["Record"]["Attributes"]
                        if "ObjectIdentifier" in other_attrs:
                            other_id = f"id:{other_attrs['ObjectIdentifier']}"

                    if identifier == other_id:
                        group.append(j)
                        processed_indices.add(j)

            exact_groups[i] = group
            processed_indices.add(i)

    # Second pass: apply Jaro-Winkler similarity on remaining items
    remaining = [i for i in range(len(timed_results)) if i not in processed_indices]

    # Process each remaining result
    for i in remaining:
        if i in processed_indices:
            continue

        result, _ = timed_results[i]
        group = [i]
        processed_indices.add(i)

        # Find similar results
        for j in remaining:
            if j != i and j not in processed_indices:
                other_result, _ = timed_results[j]

                # Use identity resolution to determine if items are similar
                is_same, score = resolve_indaleko_objects(
                    result, other_result, threshold=similarity_threshold,
                )

                if is_same:
                    group.append(j)
                    processed_indices.add(j)

        exact_groups[i] = group

    # Create result groups
    result_groups = []
    for primary_idx, group_indices in exact_groups.items():
        primary_result, primary_timestamp = timed_results[primary_idx]

        duplicates = []
        similarity_scores = []

        for idx in group_indices:
            if idx != primary_idx:
                dup_result, _ = timed_results[idx]

                # Calculate similarity score if not already identical
                _, score = resolve_indaleko_objects(
                    primary_result, dup_result, threshold=0.0,
                )

                duplicates.append(dup_result)
                similarity_scores.append(score)

        # Create the result group
        result_group = ResultGroup(
            primary=primary_result,
            duplicates=duplicates,
            similarity_scores=similarity_scores,
            last_modified=primary_timestamp,
            item_count=len(group_indices),
        )

        result_groups.append(result_group)

    # Apply result limit if specified
    if max_results is not None and max_results > 0:
        result_groups = result_groups[:max_results]

    # Sort by most duplicates (can be adjusted to sort by relevance or timestamp later)
    result_groups.sort(key=lambda g: g.item_count, reverse=True)

    # Count original and suppressed items
    original_count = len(results)
    unique_count = len(result_groups)
    suppressed_count = original_count - unique_count

    # Generate summary
    summary = f"Found {unique_count} unique items"
    if suppressed_count > 0:
        summary += f" ({suppressed_count} duplicates suppressed)"

    # Return the formatted results
    return FormattedResults(
        result_groups=result_groups,
        original_count=original_count,
        unique_count=unique_count,
        suppressed_count=suppressed_count,
        summary=summary,
        categories=dict(category_counts),
    )


def format_result_for_display(
    result: dict[str, Any], include_details: bool = True,
) -> str:
    """
    Format a result item for display in the console.

    Args:
        result: Result item to format
        include_details: Whether to include all details or just summary

    Returns:
        Formatted string representation of the result
    """
    formatted = []

    # Extract name or identifier
    name = "Unknown"
    if "name" in result:
        name = result["name"]
    elif "Record" in result and "Attributes" in result["Record"]:
        attrs = result["Record"]["Attributes"]
        if "Label" in attrs:
            name = attrs["Label"]
        elif "Name" in attrs:
            name = attrs["Name"]
        elif "Path" in attrs:
            path = attrs["Path"]
            name = os.path.basename(path) if path else "Unknown"

    formatted.append(f"Name: {name}")

    # Extract size
    size = None
    if "size" in result:
        size = result["size"]
    elif "Record" in result and "Attributes" in result["Record"]:
        attrs = result["Record"]["Attributes"]
        if "Size" in attrs:
            size = attrs["Size"]
        elif "st_size" in attrs:
            size = attrs["st_size"]

    if size is not None:
        # Format size in human-readable form
        if isinstance(size, (int, float)) and size >= 1024:
            if size >= 1024 * 1024 * 1024:
                formatted.append(f"Size: {size / (1024 * 1024 * 1024):.2f} GB")
            elif size >= 1024 * 1024:
                formatted.append(f"Size: {size / (1024 * 1024):.2f} MB")
            elif size >= 1024:
                formatted.append(f"Size: {size / 1024:.2f} KB")
            else:
                formatted.append(f"Size: {size} bytes")
        else:
            formatted.append(f"Size: {size} bytes")

    # Extract timestamp
    timestamp = extract_timestamp(result)
    if timestamp:
        formatted.append(f"Modified: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

    # Include additional details if requested
    if include_details:
        # Extract path
        path = None
        if "path" in result:
            path = result["path"]
        elif "Record" in result and "Attributes" in result["Record"]:
            attrs = result["Record"]["Attributes"]
            if "Path" in attrs:
                path = attrs["Path"]
            elif "LocalPath" in attrs:
                path = attrs["LocalPath"]

        if path:
            formatted.append(f"Path: {path}")

        # Extract MIME type
        mime_type = None
        if "Record" in result and "Attributes" in result["Record"]:
            attrs = result["Record"]["Attributes"]
            if "mimeType" in attrs:
                mime_type = attrs["mimeType"]

        if mime_type:
            formatted.append(f"Type: {mime_type}")

    return "\n".join(formatted)


def format_result_group_for_display(
    group: ResultGroup, include_duplicates: bool = True,
) -> str:
    """
    Format a result group for display in the console.

    Args:
        group: Result group to format
        include_duplicates: Whether to include duplicate items

    Returns:
        Formatted string representation of the group
    """
    formatted = []

    # Format primary result
    formatted.append(format_result_for_display(group.primary))

    # Include duplicate count
    if group.duplicates:
        dup_count = len(group.duplicates)
        formatted.append(f"\nDuplicates: {dup_count} similar items")

        # Include duplicate details if requested
        if include_duplicates:
            for i, (duplicate, score) in enumerate(
                zip(group.duplicates, group.similarity_scores, strict=False), 1,
            ):
                formatted.append(f"\n  Duplicate {i} (similarity: {score:.2f}):")

                # Format with less detail for duplicates
                dup_formatted = format_result_for_display(
                    duplicate, include_details=False,
                )

                # Indent the duplicate details
                dup_formatted = "\n  ".join(dup_formatted.split("\n"))
                formatted.append(f"  {dup_formatted}")

    return "\n".join(formatted)


def format_results_for_display(
    formatted_results: FormattedResults,
    include_duplicates: bool = True,
    max_groups: int = 10,
    include_summary: bool = True,
) -> str:
    """
    Format the complete results for display in the console.

    Args:
        formatted_results: FormattedResults to display
        include_duplicates: Whether to include duplicate items
        max_groups: Maximum number of groups to display
        include_summary: Whether to include summary information

    Returns:
        Formatted string representation of the results
    """
    display = []

    # Include summary if requested
    if include_summary:
        display.append(formatted_results.summary)

        if formatted_results.query_time:
            display.append(f"Query time: {formatted_results.query_time:.3f} seconds")

        # Add category distribution
        if formatted_results.categories:
            display.append("\nCategories:")

            # Sort categories by count (descending)
            sorted_categories = sorted(
                formatted_results.categories.items(), key=lambda x: x[1], reverse=True,
            )

            for category, count in sorted_categories[:5]:
                display.append(f"  {category}: {count} items")

            if len(sorted_categories) > 5:
                display.append(
                    f"  ... and {len(sorted_categories) - 5} more categories",
                )

        display.append("")  # Empty line before results

    # Format each result group
    groups = formatted_results.result_groups[:max_groups]
    for i, group in enumerate(groups, 1):
        if i > 1:
            display.append("\n" + "-" * 50 + "\n")  # Separator between groups

        display.append(f"Result {i} of {len(groups)}:")
        display.append(format_result_group_for_display(group, include_duplicates))

    # Include indication if there are more results
    if len(formatted_results.result_groups) > max_groups:
        remaining = len(formatted_results.result_groups) - max_groups
        display.append(f"\n... and {remaining} more results not shown")

    return "\n".join(display)


def main():
    """Test the result formatting functionality with sample data."""
    # Sample results for testing (similar to real Indaleko results)
    sample_results = [
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

    # Test deduplication and grouping
    print("Testing result deduplication and grouping...")
    formatted_results = deduplicate_results(sample_results)

    # Display results
    print("\nFormatted results:")
    print(format_results_for_display(formatted_results))

    # Display statistics
    print("\nStatistics:")
    print(f"Original count: {formatted_results.original_count}")
    print(f"Unique count: {formatted_results.unique_count}")
    print(f"Suppressed count: {formatted_results.suppressed_count}")
    print(f"Categories: {formatted_results.categories}")

    print("\nResult formatting and deduplication is working!")


if __name__ == "__main__":
    main()
