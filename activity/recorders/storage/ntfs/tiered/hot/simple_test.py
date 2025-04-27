#!/usr/bin/env python
"""
Simple test script for the NTFS Hot Tier Recorder.

This script tests the NTFS Hot Tier Recorder using the ntfs_activities.jsonl
file, bypassing the service registration and database connection.

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

import json
import logging
import os
import sys
import time
import uuid

from collections import Counter
from datetime import UTC, datetime
from typing import Any


# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import required classes


def read_activities(file_path: str) -> list[dict[str, Any]]:
    """Read activities from a JSONL file."""
    activities = []
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            try:
                activity = json.loads(line)
                activities.append(activity)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
    return activities


def test_importance_scoring(activities: list[dict[str, Any]]) -> dict[str, Any]:
    """Test the importance scoring algorithm."""
    scores = []
    for activity in activities:
        score = calculate_importance(activity)
        activity["importance_score"] = score  # Add score to activity
        scores.append(score)

    # Calculate statistics
    avg_score = sum(scores) / len(scores) if scores else 0
    min_score = min(scores) if scores else 0
    max_score = max(scores) if scores else 0

    # Count by ranges
    ranges = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}

    for score in scores:
        if 0.0 <= score < 0.2:
            ranges["0.0-0.2"] += 1
        elif 0.2 <= score < 0.4:
            ranges["0.2-0.4"] += 1
        elif 0.4 <= score < 0.6:
            ranges["0.4-0.6"] += 1
        elif 0.6 <= score < 0.8:
            ranges["0.6-0.8"] += 1
        else:
            ranges["0.8-1.0"] += 1

    return {
        "activities": activities,  # Return activities with scores added
        "stats": {
            "average": avg_score,
            "min": min_score,
            "max": max_score,
            "ranges": ranges,
        },
    }


def calculate_importance(activity: dict[str, Any]) -> float:
    """
    Calculate importance score for an activity based on our algorithm.

    This duplicates the _calculate_initial_importance method in the
    NtfsHotTierRecorder class for testing purposes.
    """
    base_score = 0.3  # Start with modest importance

    # Factor 1: Activity type importance
    activity_type = activity.get("activity_type", "")
    if activity_type in ["create", "security_change"]:
        base_score += 0.2  # Creation events matter more
    elif activity_type in ["delete", "rename"]:
        base_score += 0.15  # Structural changes matter too

    # Factor 2: File type importance (basic version)
    file_path = activity.get("file_path", "")
    if any(file_path.lower().endswith(ext) for ext in [".docx", ".xlsx", ".pdf", ".py", ".md"]):
        base_score += 0.1  # Document types matter more

    # Factor 3: Path significance
    if any(segment in file_path for segment in ["\\Documents\\", "\\Projects\\", "\\src\\", "\\source\\"]):
        base_score += 0.1  # User document areas matter more
    elif any(segment in file_path for segment in ["\\Temp\\", "\\tmp\\", "\\Cache\\", "\\Downloaded\\"]):
        base_score -= 0.1  # Temporary areas matter less

    # Factor 4: Is directory
    if activity.get("is_directory", False):
        base_score += 0.05  # Directories slightly more important than files

    return min(1.0, max(0.1, base_score))  # Cap between 0.1 and 1.0


def test_entity_mapping(activities: list[dict[str, Any]]) -> dict[str, Any]:
    """Test entity mapping by simulating the mapping process."""
    entity_map = {}  # Maps FRN to entity UUID
    path_map = {}  # Maps path to entity UUID

    result = {
        "entity_count": 0,
        "frn_count": 0,
        "activities_with_entities": 0,
        "entity_frn_mapping": {},
    }

    for activity in activities:
        frn = activity.get("file_reference_number")
        path = activity.get("file_path")
        volume = activity.get("volume_name")

        if not frn or not volume:
            continue

        # Create a key combining volume and FRN
        frn_key = f"{volume}:{frn}"
        path_key = f"{volume}:{path}" if path else None

        # Look up entity ID or create a new one
        if frn_key in entity_map:
            entity_id = entity_map[frn_key]
        elif path_key and path_key in path_map:
            entity_id = path_map[path_key]
            # Update FRN mapping
            entity_map[frn_key] = entity_id
        else:
            # Create new entity ID
            entity_id = uuid.uuid4()
            entity_map[frn_key] = entity_id
            if path_key:
                path_map[path_key] = entity_id

        # Add entity ID to activity
        activity["entity_id"] = str(entity_id)
        result["activities_with_entities"] += 1

        # Update entity-FRN mapping for reporting
        if str(entity_id) not in result["entity_frn_mapping"]:
            result["entity_frn_mapping"][str(entity_id)] = []
        if frn not in result["entity_frn_mapping"][str(entity_id)]:
            result["entity_frn_mapping"][str(entity_id)].append(frn)

    result["entity_count"] = len(set(entity_map.values()))
    result["frn_count"] = len(entity_map)

    return result


def test_ttl_processing(
    activities: list[dict[str, Any]],
    ttl_days: int = 4,
) -> dict[str, Any]:
    """Test TTL processing by simulating expiration dates."""
    for activity in activities:
        # Add TTL timestamp
        activity_time = datetime.fromisoformat(activity["timestamp"])
        ttl_timestamp = activity_time.timestamp() + (ttl_days * 24 * 60 * 60)
        ttl_date = datetime.fromtimestamp(ttl_timestamp, tz=UTC)
        activity["ttl_timestamp"] = ttl_date.isoformat()

    # Calculate expiration statistics
    now = datetime.now(UTC)
    expired = sum(1 for a in activities if datetime.fromisoformat(a["ttl_timestamp"]) < now)
    active = len(activities) - expired

    return {
        "total": len(activities),
        "expired_count": expired,
        "active_count": active,
        "ttl_days": ttl_days,
    }


def simulate_recorder_processing(file_path: str) -> dict[str, Any]:
    """Simulate the processing done by the recorder without actually creating one."""
    print(f"Processing {file_path}...")
    start_time = time.time()

    # Read activities
    activities = read_activities(file_path)
    print(f"Read {len(activities)} activities")

    # Count activity types
    activity_types = Counter()
    for activity in activities:
        activity_type = activity.get("activity_type", "unknown")
        activity_types[activity_type] += 1

    # Test importance scoring
    importance_results = test_importance_scoring(activities)

    # Test entity mapping
    entity_results = test_entity_mapping(activities)

    # Test TTL processing
    ttl_results = test_ttl_processing(activities)

    end_time = time.time()
    processing_time = end_time - start_time

    return {
        "file_path": file_path,
        "activity_count": len(activities),
        "activity_types": dict(activity_types),
        "importance_results": importance_results["stats"],
        "entity_results": entity_results,
        "ttl_results": ttl_results,
        "processing_time": processing_time,
    }


def print_results(results: dict[str, Any]) -> None:
    """Print the simulation results."""
    print("\n=== Hot Tier Recorder Simulation Results ===")
    print(f"File: {results['file_path']}")
    print(f"Activities: {results['activity_count']}")
    print(f"Processing time: {results['processing_time']:.2f} seconds")

    print("\nActivity Types:")
    for activity_type, count in results["activity_types"].items():
        print(f"  {activity_type}: {count}")

    print("\nImportance Scores:")
    print(f"  Average: {results['importance_results']['average']:.2f}")
    print(f"  Min: {results['importance_results']['min']:.2f}")
    print(f"  Max: {results['importance_results']['max']:.2f}")
    print("  Distribution:")
    for range_name, count in results["importance_results"]["ranges"].items():
        print(f"    {range_name}: {count}")

    print("\nEntity Mapping:")
    print(f"  Unique entities: {results['entity_results']['entity_count']}")
    print(f"  Unique FRNs: {results['entity_results']['frn_count']}")
    print(
        f"  Activities with entities: {results['entity_results']['activities_with_entities']}",
    )

    print("\nTTL Processing:")
    print(f"  TTL days: {results['ttl_results']['ttl_days']}")
    print(f"  Total activities: {results['ttl_results']['total']}")
    print(f"  Active: {results['ttl_results']['active_count']}")
    print(f"  Expired: {results['ttl_results']['expired_count']}")

    print("\n=== END RESULTS ===\n")


def main():
    """Main function."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Path to the NTFS activities JSONL file
    file_path = os.path.join(
        os.environ["INDALEKO_ROOT"],
        "activity",
        "collectors",
        "storage",
        "ntfs",
        "ntfs_activities.jsonl",
    )

    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return

    # Simulate recorder processing
    results = simulate_recorder_processing(file_path)

    # Print results
    print_results(results)


if __name__ == "__main__":
    main()
