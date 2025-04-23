#!/usr/bin/env python
"""
Importance Scorer for the Indaleko Cognitive Memory System.

This module implements an importance scoring system that evaluates NTFS file system
activities to determine their relative importance for memory consolidation and retention.
The scoring algorithm considers multiple factors including activity recency, file type,
path significance, access patterns, and more.

The ImportanceScorer is part of the Indaleko Cognitive Memory System, which models human
memory processes in handling file system activities. The importance scores determine how
long information is retained in each memory tier and guide the consolidation process.

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
import math
import os
import re
from datetime import UTC, datetime, timedelta
from typing import Any

# pylint: disable=wrong-import-position
# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    import sys

    sys.path.append(current_path)

from utils.i_logging import get_logger

# pylint: enable=wrong-import-position


class ImportanceScorer:
    """
    Evaluates the importance of file system activities for memory consolidation.

    This class implements a multi-factor importance scoring system that considers
    various aspects of file system activities to determine their cognitive importance,
    mirroring how human memory prioritizes information for retention and recall.

    The ImportanceScorer is used throughout the Indaleko Cognitive Memory System
    to guide retention, consolidation, and retrieval processes across memory tiers.
    """

    # Activity type importance weights
    ACTIVITY_TYPE_WEIGHTS = {
        "create": 0.8,  # Creating files is highly important
        "delete": 0.7,  # Deletion is significant but less than creation
        "rename": 0.7,  # Renaming indicates important structural changes
        "modify": 0.6,  # Modification is moderately important
        "security_change": 0.6,  # Security changes are moderately important
        "read": 0.4,  # Reading is somewhat important
        "close": 0.3,  # Closing is less important
        "info_change": 0.3,  # Info changes are less important
        "unknown": 0.2,  # Unknown activities receive low importance
    }

    # Extension importance weights
    EXTENSION_WEIGHTS = {
        # Documents
        "doc": 0.8,
        "docx": 0.8,
        "pdf": 0.8,
        "ppt": 0.8,
        "pptx": 0.8,
        "xls": 0.8,
        "xlsx": 0.8,
        "odt": 0.7,
        "ods": 0.7,
        "odp": 0.7,
        "rtf": 0.7,
        "tex": 0.7,
        "md": 0.7,
        # Source code
        "py": 0.8,
        "js": 0.8,
        "java": 0.8,
        "c": 0.8,
        "cpp": 0.8,
        "h": 0.8,
        "hpp": 0.8,
        "cs": 0.8,
        "php": 0.8,
        "rb": 0.8,
        "go": 0.8,
        "rs": 0.8,
        "ts": 0.8,
        "sql": 0.8,
        # Data files
        "json": 0.7,
        "xml": 0.7,
        "csv": 0.7,
        "yml": 0.7,
        "yaml": 0.7,
        "ini": 0.7,
        "conf": 0.7,
        # Media files
        "jpg": 0.6,
        "jpeg": 0.6,
        "png": 0.6,
        "gif": 0.6,
        "mp3": 0.6,
        "mp4": 0.6,
        "avi": 0.6,
        "mov": 0.6,
        "wav": 0.6,
        "svg": 0.6,
        "bmp": 0.5,
        "tiff": 0.5,
        "flac": 0.5,
        # Executable files
        "exe": 0.6,
        "dll": 0.6,
        "so": 0.6,
        "dylib": 0.6,
        "bat": 0.6,
        "sh": 0.6,
        "cmd": 0.6,
        # Archive files
        "zip": 0.5,
        "tar": 0.5,
        "gz": 0.5,
        "rar": 0.5,
        "7z": 0.5,
        "bz2": 0.5,
        # System files
        "sys": 0.4,
        "msi": 0.4,
        "inf": 0.4,
        "log": 0.4,
        "tmp": 0.3,
        "bak": 0.3,
        "cache": 0.2,
    }

    # Path significance patterns and weights
    PATH_SIGNIFICANCE_PATTERNS = [
        # User-created content (high importance)
        (r"(?i)\\Documents\\", 0.9),
        (r"(?i)\\Desktop\\", 0.9),
        (r"(?i)\\Projects\\", 0.9),
        (r"(?i)\\Work\\", 0.9),
        (r"(?i)\\Source\\", 0.8),
        (r"(?i)\\src\\", 0.8),
        (r"(?i)\\dev\\", 0.8),
        # User application data (moderate importance)
        (r"(?i)\\AppData\\Local\\", 0.5),
        (r"(?i)\\AppData\\Roaming\\", 0.5),
        (r"(?i)\\Application Data\\", 0.5),
        (r"(?i)\\Library\\Application Support\\", 0.5),
        # Temporary or cache data (low importance)
        (r"(?i)\\Temp\\", 0.2),
        (r"(?i)\\Temporary\\", 0.2),
        (r"(?i)\\Cache\\", 0.2),
        (r"(?i)\\Windows\\", 0.3),
        (r"(?i)\\Program Files\\", 0.3),
        (r"(?i)\\ProgramData\\", 0.3),
        (r"(?i)\\System32\\", 0.3),
        # Downloads (moderate-low importance)
        (r"(?i)\\Downloads\\", 0.4),
        # Default baseline if no other patterns match
        (r".*", 0.5),
    ]

    def __init__(self, **kwargs):
        """
        Initialize the importance scorer.

        Args:
            time_decay_rate: Rate at which importance decays with time (default: 0.05)
            extensions_weight: Weight of file extension factor (default: 0.25)
            activity_type_weight: Weight of activity type factor (default: 0.30)
            path_weight: Weight of path significance factor (default: 0.20)
            recency_weight: Weight of recency factor (default: 0.15)
            metadata_weight: Weight of additional metadata factor (default: 0.10)
            debug: Whether to enable debug logging (default: False)
        """
        # Configure logging
        self._debug = kwargs.get("debug", False)
        self._logger = get_logger(__name__)
        if self._debug:
            self._logger.setLevel(logging.DEBUG)
        else:
            self._logger.setLevel(logging.INFO)

        # Set importance factor weights
        self._extensions_weight = kwargs.get("extensions_weight", 0.25)
        self._activity_type_weight = kwargs.get("activity_type_weight", 0.30)
        self._path_weight = kwargs.get("path_weight", 0.20)
        self._recency_weight = kwargs.get("recency_weight", 0.15)
        self._metadata_weight = kwargs.get("metadata_weight", 0.10)

        # Set time decay parameters
        self._time_decay_rate = kwargs.get("time_decay_rate", 0.05)

        # Compile path significance patterns
        self._compiled_patterns = [
            (re.compile(pattern), weight)
            for pattern, weight in self.PATH_SIGNIFICANCE_PATTERNS
        ]

    def calculate_importance(self, activity_data: dict[str, Any]) -> float:
        """
        Calculate an importance score for an activity.

        Args:
            activity_data: Activity data from collector

        Returns:
            Importance score between 0.0 and 1.0
        """
        if not activity_data:
            return 0.0

        # Calculate individual factors
        extension_score = self._calculate_extension_importance(activity_data)
        activity_type_score = self._calculate_activity_type_importance(activity_data)
        path_score = self._calculate_path_importance(activity_data)
        recency_score = self._calculate_recency_importance(activity_data)
        metadata_score = self._calculate_metadata_importance(activity_data)

        # Log individual scores if debug is enabled
        if self._debug:
            self._logger.debug(f"Extension score: {extension_score:.2f}")
            self._logger.debug(f"Activity type score: {activity_type_score:.2f}")
            self._logger.debug(f"Path score: {path_score:.2f}")
            self._logger.debug(f"Recency score: {recency_score:.2f}")
            self._logger.debug(f"Metadata score: {metadata_score:.2f}")

        # Combine scores with their respective weights
        combined_score = (
            (extension_score * self._extensions_weight)
            + (activity_type_score * self._activity_type_weight)
            + (path_score * self._path_weight)
            + (recency_score * self._recency_weight)
            + (metadata_score * self._metadata_weight)
        )

        # Ensure score is between 0.0 and 1.0
        importance = max(0.1, min(1.0, combined_score))

        # Apply any external boost from user feedback
        importance_boost = activity_data.get("importance_boost", 0.0)
        if importance_boost > 0:
            # Apply boost in a way that can't exceed 1.0
            importance = min(1.0, importance + (importance_boost * (1.0 - importance)))
            if self._debug:
                self._logger.debug(
                    f"Applied importance boost of {importance_boost}: {importance:.2f}",
                )

        return importance

    def _calculate_extension_importance(self, activity_data: dict[str, Any]) -> float:
        """
        Calculate importance based on file extension.

        Args:
            activity_data: Activity data

        Returns:
            Extension importance score
        """
        # Default importance for directories or unknown extensions
        if activity_data.get("is_directory", False):
            return 0.7  # Directories are generally important

        # Get file path and extract extension
        file_path = activity_data.get("file_path", "")
        _, ext = os.path.splitext(file_path)

        # Clean extension and convert to lowercase
        ext = ext.lstrip(".").lower()

        # Get importance from extension weights, default to 0.4 if not found
        return self.EXTENSION_WEIGHTS.get(ext, 0.4)

    def _calculate_activity_type_importance(
        self, activity_data: dict[str, Any],
    ) -> float:
        """
        Calculate importance based on activity type.

        Args:
            activity_data: Activity data

        Returns:
            Activity type importance score
        """
        activity_type = activity_data.get("activity_type", "unknown").lower()

        # Handle specific USN reason codes if available
        if (
            "attributes" in activity_data
            and "usn_reason" in activity_data["attributes"]
        ):
            usn_reason = activity_data["attributes"]["usn_reason"]

            # Check for particularly important combinations
            if "DATA_EXTEND" in usn_reason and "DATA_OVERWRITE" in usn_reason:
                return 0.9  # Heavy modification is very important

            if "FILE_CREATE" in usn_reason:
                return 0.85  # File creation is very important

        # Use activity type weights for general cases
        return self.ACTIVITY_TYPE_WEIGHTS.get(activity_type, 0.2)

    def _calculate_path_importance(self, activity_data: dict[str, Any]) -> float:
        """
        Calculate importance based on file path.

        Args:
            activity_data: Activity data

        Returns:
            Path importance score
        """
        file_path = activity_data.get("file_path", "")

        # Special handling for certain path patterns
        if activity_data.get("is_directory", False):
            # Top-level directories are more important
            depth = file_path.count("\\") + file_path.count("/")
            if depth <= 2:
                return 0.8  # Higher importance for shallow directories

        # Apply path significance patterns
        for pattern, weight in self._compiled_patterns:
            if pattern.search(file_path):
                return weight

        # Default score if no patterns match
        return 0.5

    def _calculate_recency_importance(self, activity_data: dict[str, Any]) -> float:
        """
        Calculate importance based on activity recency.

        Args:
            activity_data: Activity data

        Returns:
            Recency importance score
        """
        timestamp_str = activity_data.get("timestamp")
        if not timestamp_str:
            return 0.5  # Default if no timestamp

        try:
            # Parse timestamp
            if isinstance(timestamp_str, str):
                activity_time = datetime.fromisoformat(timestamp_str)
            else:
                activity_time = timestamp_str

            # Ensure timezone-aware
            if activity_time.tzinfo is None:
                activity_time = activity_time.replace(tzinfo=UTC)

            # Calculate age in days
            age_days = (datetime.now(UTC) - activity_time).total_seconds() / (
                24 * 60 * 60
            )

            # Apply exponential decay based on age
            recency_score = math.exp(-self._time_decay_rate * age_days)

            return min(1.0, max(0.1, recency_score))

        except Exception as e:
            self._logger.error(f"Error calculating recency score: {e}")
            return 0.5  # Default on error

    def _calculate_metadata_importance(self, activity_data: dict[str, Any]) -> float:
        """
        Calculate importance based on additional metadata.

        Args:
            activity_data: Activity data

        Returns:
            Metadata importance score
        """
        # Start with a baseline score
        score = 0.5

        # Boost score for files with search hits (indicates user interest)
        search_hits = activity_data.get("search_hits", 0)
        if search_hits > 0:
            search_boost = min(0.3, search_hits * 0.03)  # Cap at 0.3
            score += search_boost

        # Adjust for size (larger files may be more important, but with diminishing returns)
        file_size = activity_data.get("file_size", 0)
        if file_size > 0:
            # Use logarithmic scaling for file size importance
            size_factor = min(0.2, math.log10(max(1, file_size) / 1024) * 0.05)
            score += size_factor

        # Adjust for rename-related attributes
        if "attributes" in activity_data:
            attrs = activity_data["attributes"]
            if attrs.get("rename_type") == "new_name":
                score += 0.1  # Boost for new names after rename

            # Additional USN-specific boosts
            if attrs.get("usn_reason_simplified") in [
                "security_change",
                "named_data_extend",
            ]:
                score += 0.05

        # Cap at 1.0
        return min(1.0, score)

    def calculate_importance_decay(
        self, original_importance: float, age_days: float, access_count: int = 0,
    ) -> float:
        """
        Calculate importance decay based on age and access patterns.

        Args:
            original_importance: Original importance score
            age_days: Age in days
            access_count: Number of times item was accessed (boosts importance)

        Returns:
            Updated importance score
        """
        # Base decay from age (more important items decay more slowly)
        decay_rate = self._time_decay_rate * (1.0 - (original_importance * 0.5))
        time_factor = math.exp(-decay_rate * age_days)

        # Access count boosts importance retention
        access_factor = 1.0 + (min(10, access_count) * 0.05)

        # Combine factors (access partially counteracts time decay)
        adjusted_importance = original_importance * time_factor * access_factor

        # Ensure minimum importance
        return max(0.1, min(1.0, adjusted_importance))

    def estimate_retention_days(
        self, importance: float, memory_type: str = "short_term",
    ) -> int:
        """
        Estimate recommended retention days based on importance and memory type.

        Args:
            importance: Importance score (0.0 to 1.0)
            memory_type: Type of memory (sensory, short_term, long_term, archival)

        Returns:
            Recommended retention days
        """
        # Base retention days by memory type
        base_retention = {
            "sensory": 7,  # Sensory memory: ~1 week
            "short_term": 90,  # Short-term: ~3 months
            "long_term": 365,  # Long-term: ~1 year
            "archival": 3650,  # Archival: ~10 years
        }

        # Get base retention for this memory type
        base_days = base_retention.get(memory_type, 30)

        # Scale by importance (higher importance = longer retention)
        importance_factor = 0.5 + (importance * 1.5)  # 0.5 to 2.0 range

        # Calculate estimated retention
        retention_days = int(base_days * importance_factor)

        return max(1, retention_days)

    def combine_importance_scores(self, scores: list[float]) -> float:
        """
        Combine multiple importance scores into a single score.

        Args:
            scores: List of importance scores

        Returns:
            Combined importance score
        """
        if not scores:
            return 0.0

        # Average the scores, but bias toward higher values
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)

        # Weighted average with 70% weight to average, 30% to maximum
        combined = (avg_score * 0.7) + (max_score * 0.3)

        return min(1.0, combined)

    def should_consolidate(
        self, importance: float, age_hours: float, from_memory: str, to_memory: str,
    ) -> bool:
        """
        Determine if an item should be consolidated to the next memory tier.

        Args:
            importance: Item importance score
            age_hours: Age of the item in hours
            from_memory: Source memory type
            to_memory: Target memory type

        Returns:
            True if the item should be consolidated, False otherwise
        """
        # Base thresholds by memory tier transition
        thresholds = {
            # from → to: (min_importance, min_age_hours)
            "sensory→short_term": (0.3, 12),
            "short_term→long_term": (0.6, 168),  # 1 week
            "long_term→archival": (0.8, 8760),  # 1 year
        }

        # Get threshold for this transition
        transition_key = f"{from_memory}→{to_memory}"
        min_importance, min_age = thresholds.get(transition_key, (0.5, 24))

        # Higher importance items can consolidate earlier
        adjusted_age_threshold = min_age * (
            1.0 - (importance * 0.5)
        )  # 50% to 100% of threshold

        return (importance >= min_importance) and (age_hours >= adjusted_age_threshold)


# If run directly, perform a simple test
if __name__ == "__main__":
    import argparse

    # Create argument parser
    parser = argparse.ArgumentParser(
        description="Importance Scorer for Indaleko Cognitive Memory System",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Add arguments
    parser.add_argument("--input", type=str, help="Input JSONL file with activities")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    # Parse arguments
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format="%(message)s")

    # Create scorer
    scorer = ImportanceScorer(debug=args.debug)

    # Process input file if provided
    if args.input:
        results = []
        with open(args.input, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    activity = json.loads(line)
                    score = scorer.calculate_importance(activity)

                    # Add result
                    results.append(
                        {
                            "file_path": activity.get("file_path", "Unknown"),
                            "activity_type": activity.get("activity_type", "Unknown"),
                            "importance_score": score,
                            "retention_days": {
                                "sensory": scorer.estimate_retention_days(
                                    score, "sensory",
                                ),
                                "short_term": scorer.estimate_retention_days(
                                    score, "short_term",
                                ),
                                "long_term": scorer.estimate_retention_days(
                                    score, "long_term",
                                ),
                            },
                        },
                    )
                except Exception as e:
                    logging.exception(f"Error processing line {line_num}: {e}")

        # Sort by importance score
        results.sort(key=lambda x: x["importance_score"], reverse=True)

        # Display results
        print("\n=== Importance Scoring Results ===")
        for i, result in enumerate(results[:20], 1):
            print(f"\n{i}. {result['file_path']} ({result['activity_type']})")
            print(f"   Importance Score: {result['importance_score']:.2f}")
            print("   Retention Days:")
            print(f"     Sensory:     {result['retention_days']['sensory']}")
            print(f"     Short-Term:  {result['retention_days']['short_term']}")
            print(f"     Long-Term:   {result['retention_days']['long_term']}")

        # Print summary
        print(f"\nProcessed {len(results)} activities")
        avg_score = sum(r["importance_score"] for r in results) / max(1, len(results))
        print(f"Average importance score: {avg_score:.2f}")
    else:
        # Run demo test
        print("\n=== Importance Scorer Demo ===")

        # Sample activities
        test_activities = [
            {
                "file_path": "C:\\Users\\Documents\\Project\\report.docx",
                "activity_type": "modify",
                "timestamp": datetime.now(UTC).isoformat(),
                "is_directory": False,
                "attributes": {"usn_reason": ["DATA_OVERWRITE", "DATA_EXTEND"]},
            },
            {
                "file_path": "C:\\Users\\Downloads\\setup.exe",
                "activity_type": "create",
                "timestamp": (
                    datetime.now(UTC) - timedelta(days=1)
                ).isoformat(),
                "is_directory": False,
            },
            {
                "file_path": "C:\\Windows\\Temp\\temp12345.dat",
                "activity_type": "delete",
                "timestamp": (
                    datetime.now(UTC) - timedelta(days=3)
                ).isoformat(),
                "is_directory": False,
            },
            {
                "file_path": "C:\\Users\\Projects\\Source\\main.py",
                "activity_type": "create",
                "timestamp": datetime.now(UTC).isoformat(),
                "is_directory": False,
                "search_hits": 5,
            },
        ]

        # Score each activity
        print("\nScoring sample activities:")
        for activity in test_activities:
            score = scorer.calculate_importance(activity)
            path = activity["file_path"]
            activity_type = activity["activity_type"]

            print(f"\n- {path} ({activity_type})")
            print(f"  Importance Score: {score:.2f}")
            print(
                f"  Retention (Sensory): {scorer.estimate_retention_days(score, 'sensory')} days",
            )
            print(
                f"  Retention (Short-Term): {scorer.estimate_retention_days(score, 'short_term')} days",
            )

        # Test consolidation decision
        print("\nConsolidation Decisions:")
        activities_with_ages = [
            (test_activities[0], 6),  # 6 hours old
            (test_activities[1], 24),  # 24 hours old
            (test_activities[2], 72),  # 72 hours old
            (test_activities[3], 4),  # 4 hours old
        ]

        for activity, age_hours in activities_with_ages:
            score = scorer.calculate_importance(activity)
            decision = scorer.should_consolidate(
                score, age_hours, "sensory", "short_term",
            )
            path = activity["file_path"]

            print(f"- {path} (Age: {age_hours}h, Score: {score:.2f})")
            print(f"  Consolidate to Short-Term Memory: {'Yes' if decision else 'No'}")

        print("\nDemo completed successfully!")
