"""
Schema analyzer module for the Indaleko database.

This module provides functions to analyze and organize collection information,
including grouping collections and identifying important indexes.

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

import logging
import re

from typing import Any


def group_collections(
    collections: list[dict[str, Any]],
    group_definitions: dict[str, list[str]],
) -> dict[str, list[str]]:
    """
    Group collections based on predefined groups or naming patterns.

    Args:
        collections: List of collection information as returned by extract_collections()
        group_definitions: Dictionary mapping group names to collection names

    Returns:
        A dictionary mapping group names to lists of collection names
    """
    logging.info("Grouping collections...")

    # Create a dictionary to store the groupings
    groups = {group_name: [] for group_name in group_definitions}

    # Track which collections have been grouped
    grouped_collections = set()

    # First, apply explicit groupings
    for group_name, collection_names in group_definitions.items():
        for collection_name in collection_names:
            # Check if this is a pattern with wildcards
            if "*" in collection_name:
                # Convert the pattern to a regex
                pattern = collection_name.replace("*", ".*")
                regex = re.compile(f"^{pattern}$")

                # Add matching collections to the group
                for collection in collections:
                    if regex.match(collection["name"]):
                        groups[group_name].append(collection["name"])
                        grouped_collections.add(collection["name"])
            else:
                # Check if this collection exists
                for collection in collections:
                    if collection["name"] == collection_name:
                        groups[group_name].append(collection_name)
                        grouped_collections.add(collection_name)
                        break

    # For collections that aren't explicitly grouped, try to infer the group
    for collection in collections:
        if collection["name"] in grouped_collections:
            continue

        # Try to infer the group based on naming conventions
        if collection["name"].startswith("ActivityProvider"):
            if "Activity Context" in groups:
                groups["Activity Context"].append(collection["name"])
                grouped_collections.add(collection["name"])

    # Create an "Other" group for any remaining collections
    ungrouped = [c["name"] for c in collections if c["name"] not in grouped_collections]
    if ungrouped:
        if "Other" not in groups:
            groups["Other"] = []
        groups["Other"].extend(ungrouped)

    # Remove empty groups
    groups = {name: members for name, members in groups.items() if members}

    logging.info(f"Collections grouped into {len(groups)} groups")
    return groups


def analyze_indexes(collections: list[dict[str, Any]], max_indexes: int = 2) -> list[dict[str, Any]]:
    """
    Analyze collection indexes and identify the most important ones.

    Args:
        collections: List of collection information as returned by extract_collections()
        max_indexes: Maximum number of indexes to include per collection

    Returns:
        The updated collections list with a new 'key_indexes' field containing
        the most important indexes for each collection
    """
    logging.info("Analyzing collection indexes...")

    for collection in collections:
        all_indexes = collection.get("indexes", [])
        key_indexes = []

        # Filter out the default primary index
        non_primary_indexes = [idx for idx in all_indexes if idx["type"] != "primary"]

        # If there are non-primary indexes, select up to max_indexes
        if non_primary_indexes:
            # Prioritize indexes based on fields and type
            # 1. Persistent indexes on commonly queried fields
            # 2. Unique constraints
            # 3. Other indexes by fields covered

            # First, look for indexes on common query fields
            common_field_indexes = [
                idx
                for idx in non_primary_indexes
                if any(field in ["LocalIdentifier", "ObjectIdentifier", "URI"] for field in idx.get("fields", []))
            ]

            # Then, consider unique indexes
            unique_indexes = [
                idx for idx in non_primary_indexes if idx.get("unique", False) and idx not in common_field_indexes
            ]

            # Finally, consider remaining indexes
            other_indexes = [
                idx for idx in non_primary_indexes if idx not in common_field_indexes and idx not in unique_indexes
            ]

            # Prioritize and select up to max_indexes
            prioritized_indexes = common_field_indexes + unique_indexes + other_indexes
            key_indexes = prioritized_indexes[:max_indexes]

        # Add the primary index if we have room
        if len(key_indexes) < max_indexes:
            primary_index = next((idx for idx in all_indexes if idx["type"] == "primary"), None)
            if primary_index:
                key_indexes.append(primary_index)

        # Add the key indexes to the collection information
        collection["key_indexes"] = key_indexes

        logging.debug(f"Selected {len(key_indexes)} key indexes for {collection['name']}")

    return collections


def identify_foreign_keys(collections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Identify potential foreign key relationships between collections.

    Args:
        collections: List of collection information as returned by extract_collections()

    Returns:
        A list of dictionaries representing potential foreign key relationships
    """
    logging.info("Identifying potential foreign key relationships...")

    foreign_keys = []
    {c["name"] for c in collections}

    # Common foreign key field patterns

    # This is a placeholder function
    # In a full implementation, we would:
    # 1. Extract schema for each collection
    # 2. Look for fields matching foreign key patterns
    # 3. Check if the base name matches an existing collection

    # For now, we'll return an empty list as relationships are
    # defined in the extract_relationships function

    return foreign_keys
