#!/usr/bin/env python
"""
Enhanced Importance Scoring for Indaleko Tiered Memory System.

This module implements advanced importance scoring for storage activities,
which powers the tiered memory system's decisions about data retention
and transition between tiers.

Features:
- Advanced importance scoring with multiple weighted factors
- Time-decay functions for recency-based scoring
- Frequency-based importance adjustments
- Type-specific and path-based scoring rules
- Novelty detection to identify unique or rare events
- Adaptive scoring based on query feedback

The importance scoring system is inspired by cognitive models of human memory,
where "importance" is a proxy for how likely something is to be accessed
or remembered in the future.

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
import math
import os
import re
from datetime import UTC, datetime, timedelta
from typing import Any

# Document types with higher importance
IMPORTANT_DOCUMENT_EXTENSIONS = {
    # Documents
    ".docx",
    ".doc",
    ".pdf",
    ".pptx",
    ".xlsx",
    ".xls",
    ".txt",
    ".md",
    ".rtf",
    # Source code
    ".py",
    ".js",
    ".ts",
    ".html",
    ".css",
    ".c",
    ".cpp",
    ".h",
    ".java",
    ".cs",
    ".go",
    ".rs",
    ".php",
    ".rb",
    ".swift",
    # Data
    ".json",
    ".xml",
    ".yaml",
    ".yml",
    ".csv",
    ".sql",
    ".db",
}

# Paths with higher importance
IMPORTANT_PATH_SEGMENTS = {
    "Documents",
    "Projects",
    "src",
    "source",
    "repos",
    "work",
    "research",
    "thesis",
    "paper",
    "manuscript",
    "report",
}

# Paths with lower importance
TEMPORARY_PATH_SEGMENTS = {
    "temp",
    "tmp",
    "cache",
    "downloaded",
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "bin",
    "obj",
    "build",
    "dist",
}

# Activity types with higher importance
IMPORTANT_ACTIVITY_TYPES = {
    "create": 0.7,  # Creation events are significant
    "delete": 0.65,  # Deletion is significant (destructive)
    "rename": 0.65,  # Structural changes matter
    "security_change": 0.6,  # Security changes are important
    "modify": 0.55,  # Content changes matter
    "close": 0.3,  # Close events less important but still meaningful
    "attribute_change": 0.4,  # Attribute changes have medium importance
}


class ImportanceScorer:
    """
    Advanced importance scoring for storage activities.

    This class provides methods to calculate importance scores for storage activities
    based on multiple factors, with configurable weights for each factor.
    """

    def __init__(self, **kwargs):
        """
        Initialize the importance scorer with configurable weights.

        Args:
            **kwargs: Optional weights for different factors:
                - recency_weight: Weight for time-based importance (default: 0.3)
                - type_weight: Weight for activity type importance (default: 0.25)
                - content_weight: Weight for content/path importance (default: 0.2)
                - frequency_weight: Weight for access frequency (default: 0.15)
                - novelty_weight: Weight for novelty/uniqueness (default: 0.1)
                - debug: Enable debug logging (default: False)
        """
        # Configure logging
        self._debug = kwargs.get("debug", False)
        self._logger = logging.getLogger("ImportanceScorer")
        if self._debug:
            self._logger.setLevel(logging.DEBUG)

        # Factor weights (must sum to 1.0)
        self._weights = {
            "recency": kwargs.get("recency_weight", 0.3),  # Time-based importance
            "type": kwargs.get("type_weight", 0.25),  # Activity type importance
            "content": kwargs.get("content_weight", 0.2),  # Content/path importance
            "frequency": kwargs.get("frequency_weight", 0.15),  # Access frequency
            "novelty": kwargs.get("novelty_weight", 0.1),  # Novelty/uniqueness
        }

        # Normalize weights to ensure they sum to 1.0
        weight_sum = sum(self._weights.values())
        if weight_sum != 1.0:
            for key in self._weights:
                self._weights[key] /= weight_sum

        if self._debug:
            self._logger.debug(
                f"Initialized ImportanceScorer with weights: {self._weights}",
            )

        # Initialize path pattern cache for faster matching
        self._path_pattern_cache = {
            "important": re.compile(
                "|".join([rf"\\{p}\\|/{p}/" for p in IMPORTANT_PATH_SEGMENTS]),
                re.IGNORECASE,
            ),
            "temporary": re.compile(
                "|".join([rf"\\{p}\\|/{p}/" for p in TEMPORARY_PATH_SEGMENTS]),
                re.IGNORECASE,
            ),
        }

    def calculate_importance(
        self,
        activity_data: dict[str, Any],
        entity_metadata: dict[str, Any] | None = None,
        search_hits: int = 0,
    ) -> float:
        """
        Calculate the importance score for an activity.

        Args:
            activity_data: The activity data
            entity_metadata: Optional entity metadata for enhanced scoring
            search_hits: Number of times this activity has been found in search results

        Returns:
            Importance score between 0.0 and 1.0
        """
        # Calculate individual factor scores
        recency_score = self._calculate_recency_score(activity_data)
        type_score = self._calculate_type_score(activity_data)
        content_score = self._calculate_content_score(activity_data)
        frequency_score = self._calculate_frequency_score(
            activity_data, entity_metadata, search_hits,
        )
        novelty_score = self._calculate_novelty_score(activity_data, entity_metadata)

        # Apply weights to each factor
        weighted_score = (
            self._weights["recency"] * recency_score
            + self._weights["type"] * type_score
            + self._weights["content"] * content_score
            + self._weights["frequency"] * frequency_score
            + self._weights["novelty"] * novelty_score
        )

        # Cap the score between 0.1 and 1.0
        final_score = min(1.0, max(0.1, weighted_score))

        if self._debug:
            self._logger.debug(
                f"Importance calculation: recency={recency_score:.2f}, "
                f"type={type_score:.2f}, content={content_score:.2f}, "
                f"frequency={frequency_score:.2f}, novelty={novelty_score:.2f}, "
                f"final={final_score:.2f}",
            )

        return final_score

    def _calculate_recency_score(self, activity_data: dict[str, Any]) -> float:
        """
        Calculate importance based on activity recency (time decay).

        Uses an exponential decay function where newer activities have higher scores.

        Args:
            activity_data: The activity data

        Returns:
            Recency score component (0.0-1.0)
        """
        try:
            # Get timestamp from activity
            timestamp_str = activity_data.get("timestamp", "")
            if not timestamp_str:
                return 0.5  # Default score for missing timestamp

            # Parse timestamp
            if isinstance(timestamp_str, str):
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                # Assume datetime object
                timestamp = timestamp_str

            # Ensure timezone awareness
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=UTC)

            # Calculate age in days
            now = datetime.now(UTC)
            age_days = (now - timestamp).total_seconds() / (24 * 60 * 60)

            # Exponential decay function: score = exp(-age_days/half_life)
            # Where half_life is the number of days at which the score drops to 0.5
            half_life = 7.0  # Default half-life of 7 days
            recency_score = math.exp(-age_days / half_life)

            return recency_score

        except Exception as e:
            self._logger.error(f"Error calculating recency score: {e}")
            return 0.5  # Default score on error

    def _calculate_type_score(self, activity_data: dict[str, Any]) -> float:
        """
        Calculate importance based on activity type.

        Args:
            activity_data: The activity data

        Returns:
            Activity type score component (0.0-1.0)
        """
        # Get activity type
        activity_type = activity_data.get("activity_type", "").lower()

        # Check predefined importance by type
        return IMPORTANT_ACTIVITY_TYPES.get(activity_type, 0.3)

    def _calculate_content_score(self, activity_data: dict[str, Any]) -> float:
        """
        Calculate importance based on content/path characteristics.

        Args:
            activity_data: The activity data

        Returns:
            Content score component (0.0-1.0)
        """
        base_score = 0.3  # Start with modest importance

        # Get file path
        file_path = activity_data.get("file_path", "")
        if not file_path:
            return base_score

        # Normalize path separators for consistent matching
        normalized_path = file_path.replace("\\", "/")

        # Check file extension importance
        _, ext = os.path.splitext(file_path)
        if ext.lower() in IMPORTANT_DOCUMENT_EXTENSIONS:
            base_score += 0.2

        # Check path segment importance
        if self._path_pattern_cache["important"].search(file_path):
            base_score += 0.2
        elif self._path_pattern_cache["temporary"].search(file_path):
            base_score -= 0.1

        # Adjust for directories
        if activity_data.get("is_directory", False):
            base_score += 0.1

        # Check if this is a project/code metadata file
        if os.path.basename(file_path).lower() in {
            "readme.md",
            "license",
            "package.json",
            "cargo.toml",
            "pyproject.toml",
            "makefile",
            "dockerfile",
            "manifest",
            "config",
        }:
            base_score += 0.15

        # Cap the score between 0 and 1
        return min(1.0, max(0.0, base_score))

    def _calculate_frequency_score(
        self,
        activity_data: dict[str, Any],
        entity_metadata: dict[str, Any] | None = None,
        search_hits: int = 0,
    ) -> float:
        """
        Calculate importance based on access frequency.

        Args:
            activity_data: The activity data
            entity_metadata: Optional entity metadata for enhanced scoring
            search_hits: Number of times this activity has been found in search results

        Returns:
            Frequency score component (0.0-1.0)
        """
        # Start with base score
        base_score = 0.3

        # Boost by search hits
        if search_hits > 0:
            # Log scale: 1 hit → +0.1, 10 hits → +0.3, 100 hits → +0.5
            search_boost = min(0.5, 0.1 * math.log10(1 + search_hits))
            base_score += search_boost

        # Add entity frequency data if available
        if entity_metadata:
            # Get access count from entity metadata
            access_count = entity_metadata.get("access_count", 0)
            if access_count > 0:
                # Log scale: 1 access → +0.05, 10 accesses → +0.15, 100 accesses → +0.25
                access_boost = min(0.25, 0.05 * math.log10(1 + access_count))
                base_score += access_boost

            # Consider importance boost from metadata if available
            importance_boost = entity_metadata.get("importance_boost", 0.0)
            base_score += importance_boost

        # Cap the score between 0 and 1
        return min(1.0, max(0.0, base_score))

    def _calculate_novelty_score(
        self,
        activity_data: dict[str, Any],
        entity_metadata: dict[str, Any] | None = None,
    ) -> float:
        """
        Calculate importance based on novelty/uniqueness.

        Args:
            activity_data: The activity data
            entity_metadata: Optional entity metadata for enhanced scoring

        Returns:
            Novelty score component (0.0-1.0)
        """
        # Start with medium novelty
        base_score = 0.5

        # New files are more novel
        activity_type = activity_data.get("activity_type", "").lower()
        if activity_type == "create":
            base_score += 0.3

        # If we have entity metadata, check age and rarity
        if entity_metadata:
            # Newer entities are more novel
            created_at = entity_metadata.get("created_at", "")
            if created_at:
                try:
                    created_time = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00"),
                    )
                    now = datetime.now(UTC)
                    age_days = (now - created_time).total_seconds() / (24 * 60 * 60)

                    # Newer files (< 1 day) get a novelty boost
                    if age_days < 1:
                        base_score += 0.2
                    elif age_days < 7:
                        base_score += 0.1
                except Exception:
                    pass

            # Less frequently accessed entities are more novel
            access_count = entity_metadata.get("access_count", 0)
            if access_count == 0:
                base_score += 0.1  # Never accessed = more novel
            elif access_count < 5:
                base_score += 0.05  # Rarely accessed = somewhat novel

        # Cap the score between 0 and 1
        return min(1.0, max(0.0, base_score))

    def get_weights(self) -> dict[str, float]:
        """
        Get the current factor weights.

        Returns:
            Dictionary of factor weights
        """
        return self._weights.copy()

    def set_weights(self, weights: dict[str, float]) -> None:
        """
        Set new factor weights.

        Args:
            weights: Dictionary of factor weights
        """
        # Validate weights
        required_keys = {"recency", "type", "content", "frequency", "novelty"}
        if not all(key in weights for key in required_keys):
            raise ValueError(
                f"Missing required keys in weights. Required: {required_keys}",
            )

        # Set weights
        self._weights = weights.copy()

        # Normalize weights to ensure they sum to 1.0
        weight_sum = sum(self._weights.values())
        if weight_sum != 1.0:
            for key in self._weights:
                self._weights[key] /= weight_sum

        if self._debug:
            self._logger.debug(f"Updated weights: {self._weights}")


# Simple test function
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # Create scorer with default weights
    scorer = ImportanceScorer(debug=True)

    # Example activity data
    test_activity = {
        "activity_type": "create",
        "file_path": "C:/Users/Documents/Project/report.docx",
        "timestamp": datetime.now(UTC).isoformat(),
        "is_directory": False,
    }

    # Example entity metadata
    test_entity = {
        "created_at": datetime.now(UTC).isoformat(),
        "access_count": 2,
        "importance_boost": 0.1,
    }

    # Calculate score
    score = scorer.calculate_importance(test_activity, test_entity, search_hits=3)
    print(f"Importance score: {score:.2f}")

    # Test with older activity
    older_activity = test_activity.copy()
    older_activity["timestamp"] = (
        datetime.now(UTC) - timedelta(days=10)
    ).isoformat()
    score = scorer.calculate_importance(older_activity, test_entity)
    print(f"Older activity score: {score:.2f}")

    # Test with temporary path
    temp_activity = test_activity.copy()
    temp_activity["file_path"] = "C:/Users/Temp/cache/temp_file.txt"
    score = scorer.calculate_importance(temp_activity, test_entity)
    print(f"Temporary file score: {score:.2f}")
