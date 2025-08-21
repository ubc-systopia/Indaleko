"""
Temporal Pattern Recommender for the Contextual Query Recommendation Engine.

This module provides the TemporalPatternRecommender class, which generates
query suggestions based on temporal patterns in user behavior and queries.

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

import calendar
import logging
import math
import os
import sys
import uuid

from datetime import UTC, datetime
from typing import Any


# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.context.data_models.recommendation import (
    FeedbackType,
    QuerySuggestion,
    RecommendationSource,
)
from query.context.recommendations.base import RecommendationProvider


# pylint: enable=wrong-import-position


class TemporalPattern:
    """Class representing a detected temporal pattern."""

    def __init__(
        self,
        pattern_id: str,
        description: str,
        query_template: str,
        time_window: dict[str, Any],
        confidence: float = 0.5,
        observation_count: int = 1,
    ) -> None:
        """
        Initialize the temporal pattern.

        Args:
            pattern_id: Unique identifier for the pattern
            description: Human-readable description of the pattern
            query_template: Query template for this pattern
            time_window: Dictionary defining when this pattern is active
            confidence: Confidence score (0.0-1.0)
            observation_count: Number of times this pattern has been observed
        """
        self.pattern_id = pattern_id
        self.description = description
        self.query_template = query_template
        self.time_window = time_window
        self.confidence = confidence
        self.observation_count = observation_count
        self.successful_uses = 0
        self.unsuccessful_uses = 0
        self.last_used = None
        self.created_at = datetime.now(UTC)

    def is_active(self, current_time: datetime | None = None) -> bool:
        """
        Check if this pattern is active for the given time.

        Args:
            current_time: Time to check (defaults to now)

        Returns:
            True if pattern is active, False otherwise
        """
        if not current_time:
            current_time = datetime.now(UTC)

        # Handle timezone awareness
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=UTC)

        # Check day of week match
        if "days_of_week" in self.time_window:
            day_of_week = current_time.weekday()  # 0=Monday, 6=Sunday
            if day_of_week not in self.time_window["days_of_week"]:
                return False

        # Check hour range match
        if "hour_range" in self.time_window:
            hour = current_time.hour
            hour_range = self.time_window["hour_range"]
            if not (hour_range[0] <= hour <= hour_range[1]):
                return False

        # Check date range match
        if "date_range" in self.time_window:
            date_range = self.time_window["date_range"]
            start_date = datetime.fromisoformat(date_range[0])
            end_date = datetime.fromisoformat(date_range[1])

            if current_time < start_date or current_time > end_date:
                return False

        # Check month match
        if "months" in self.time_window:
            month = current_time.month
            if month not in self.time_window["months"]:
                return False

        return True

    def match_score(self, current_time: datetime | None = None) -> float:
        """
        Calculate how well current time matches this pattern.

        Args:
            current_time: Time to check (defaults to now)

        Returns:
            Score from 0.0 (no match) to 1.0 (perfect match)
        """
        if not current_time:
            current_time = datetime.now(UTC)

        # Handle timezone awareness
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=UTC)

        scores = []

        # Check day of week match
        if "days_of_week" in self.time_window:
            day_of_week = current_time.weekday()  # 0=Monday, 6=Sunday
            if day_of_week in self.time_window["days_of_week"]:
                scores.append(1.0)
            else:
                # Calculate proximity to next matching day
                days = self.time_window["days_of_week"]
                days.sort()

                # Find closest day
                min_distance = 7  # Worst case
                for d in days:
                    distance = (d - day_of_week) % 7
                    min_distance = min(min_distance, distance)

                day_score = max(0.0, 1.0 - (min_distance / 7.0))
                scores.append(day_score)

        # Check hour range match
        if "hour_range" in self.time_window:
            hour = current_time.hour
            hour_range = self.time_window["hour_range"]

            if hour_range[0] <= hour <= hour_range[1]:
                # Within range, perfect score
                scores.append(1.0)
            else:
                # Outside range, calculate distance to range
                distance = hour_range[0] - hour if hour < hour_range[0] else hour - hour_range[1]

                # Normalize distance (max possible distance is 12 hours)
                hour_score = max(0.0, 1.0 - (distance / 12.0))
                scores.append(hour_score)

        # If no time constraints, it's considered a universal pattern
        if not scores:
            return 0.5  # Neutral score for universal patterns

        return sum(scores) / len(scores)

    def update_from_feedback(self, feedback: FeedbackType) -> None:
        """
        Update pattern statistics based on feedback.

        Args:
            feedback: The type of feedback provided
        """
        self.last_used = datetime.now(UTC)

        if feedback in [FeedbackType.ACCEPTED, FeedbackType.HELPFUL]:
            self.successful_uses += 1
        elif feedback in [
            FeedbackType.REJECTED,
            FeedbackType.NOT_HELPFUL,
            FeedbackType.IRRELEVANT,
        ]:
            self.unsuccessful_uses += 1


class TemporalPatternRecommender(RecommendationProvider):
    """
    Generates query suggestions based on temporal patterns.

    This recommender analyzes time-based patterns in user behavior and queries
    to generate contextually relevant suggestions. It identifies recurring
    information needs and suggests queries based on time of day, day of week,
    and other temporal factors.
    """

    def __init__(self, db_config=None, debug: bool = False) -> None:
        """
        Initialize the temporal pattern recommender.

        Args:
            db_config: Optional database configuration
            debug: Whether to enable debug output
        """
        super().__init__(RecommendationSource.TEMPORAL_PATTERN, debug)

        # Set up logging
        self._logger = logging.getLogger("TemporalPatternRecommender")
        if debug:
            self._logger.setLevel(logging.DEBUG)

        # Initialize database connection
        self._db_config = db_config

        # Initialize pattern storage
        self._patterns = {}

        # Create some default patterns
        self._initialize_default_patterns()

        # Flag to indicate patterns were loaded from database
        self._patterns_loaded = False

    def _initialize_default_patterns(self) -> None:
        """Initialize default temporal patterns."""
        # Morning patterns
        morning_pattern = TemporalPattern(
            pattern_id=str(uuid.uuid4()),
            description="Morning overview pattern",
            query_template="Show me activities from yesterday",
            time_window={
                "days_of_week": [0, 1, 2, 3, 4],  # Weekdays only
                "hour_range": [8, 10],  # 8 AM to 10 AM
            },
            confidence=0.8,
            observation_count=5,
        )
        self._patterns[morning_pattern.pattern_id] = morning_pattern

        # Start of week pattern
        monday_pattern = TemporalPattern(
            pattern_id=str(uuid.uuid4()),
            description="Week planning pattern",
            query_template="Show me upcoming deadlines this week",
            time_window={
                "days_of_week": [0],  # Monday
                "hour_range": [9, 11],  # 9 AM to 11 AM
            },
            confidence=0.85,
            observation_count=4,
        )
        self._patterns[monday_pattern.pattern_id] = monday_pattern

        # End of day review
        eod_pattern = TemporalPattern(
            pattern_id=str(uuid.uuid4()),
            description="End of day review pattern",
            query_template="Show files I modified today",
            time_window={
                "days_of_week": [0, 1, 2, 3, 4],  # Weekdays only
                "hour_range": [16, 18],  # 4 PM to 6 PM
            },
            confidence=0.75,
            observation_count=6,
        )
        self._patterns[eod_pattern.pattern_id] = eod_pattern

        # End of week review
        friday_pattern = TemporalPattern(
            pattern_id=str(uuid.uuid4()),
            description="End of week review pattern",
            query_template="Show me what I accomplished this week",
            time_window={
                "days_of_week": [4],  # Friday
                "hour_range": [15, 17],  # 3 PM to 5 PM
            },
            confidence=0.85,
            observation_count=3,
        )
        self._patterns[friday_pattern.pattern_id] = friday_pattern

        # Lunch time check
        lunch_pattern = TemporalPattern(
            pattern_id=str(uuid.uuid4()),
            description="Lunch break pattern",
            query_template="Show me recent communications",
            time_window={
                "days_of_week": [0, 1, 2, 3, 4],  # Weekdays only
                "hour_range": [12, 13],  # 12 PM to 1 PM
            },
            confidence=0.7,
            observation_count=5,
        )
        self._patterns[lunch_pattern.pattern_id] = lunch_pattern

        # Weekend catch-up
        weekend_pattern = TemporalPattern(
            pattern_id=str(uuid.uuid4()),
            description="Weekend catch-up pattern",
            query_template="Show me unread documents",
            time_window={
                "days_of_week": [5, 6],  # Saturday and Sunday
                "hour_range": [10, 16],  # 10 AM to 4 PM
            },
            confidence=0.65,
            observation_count=2,
        )
        self._patterns[weekend_pattern.pattern_id] = weekend_pattern

        self._logger.info(
            f"Initialized {len(self._patterns)} default temporal patterns",
        )

    def _load_patterns_from_database(self) -> None:
        """
        Load temporal patterns from database.

        In a real implementation, this would query the database for saved patterns.
        For demonstration, we'll just use the default patterns.
        """
        # Mark patterns as loaded to avoid multiple attempts
        self._patterns_loaded = True
        self._logger.info(
            "Using default temporal patterns (database load not implemented)",
        )

    def _detect_patterns(self, query_history: list[dict[str, Any]]) -> None:
        """
        Analyze query history to detect temporal patterns.

        Args:
            query_history: List of historical queries with timestamps
        """
        # Group queries by hour of day
        hour_groups = {}
        # Group queries by day of week
        day_groups = {}

        for query in query_history:
            # Parse timestamp
            timestamp_str = query.get("timestamp")
            if not timestamp_str:
                continue

            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=UTC)

                # Group by hour
                hour = timestamp.hour
                if hour not in hour_groups:
                    hour_groups[hour] = []
                hour_groups[hour].append(query)

                # Group by day of week
                day = timestamp.weekday()
                if day not in day_groups:
                    day_groups[day] = []
                day_groups[day].append(query)

            except (ValueError, TypeError):
                continue

        # Analyze hour patterns
        for hour, queries in hour_groups.items():
            if len(queries) < 3:
                continue  # Too few queries to establish a pattern

            # Look for recurring query patterns in this hour
            self._analyze_query_group(queries, {"hour_range": [hour, hour]})

        # Analyze day patterns
        for day, queries in day_groups.items():
            if len(queries) < 3:
                continue  # Too few queries to establish a pattern

            # Look for recurring query patterns on this day
            self._analyze_query_group(queries, {"days_of_week": [day]})

    def _analyze_query_group(
        self,
        queries: list[dict[str, Any]],
        time_window: dict[str, Any],
    ) -> None:
        """
        Analyze a group of queries to detect patterns.

        Args:
            queries: List of queries in this time window
            time_window: Time constraints for this group
        """
        # This is a simplified implementation
        # A more advanced implementation would use ML/clustering to identify actual patterns

        # Count query templates
        template_counts = {}

        for query in queries:
            query_text = query.get("query_text", "")

            # Skip empty queries
            if not query_text:
                continue

            # Normalize query by removing specific values
            normalized = self._normalize_query(query_text)

            if normalized in template_counts:
                template_counts[normalized] += 1
            else:
                template_counts[normalized] = 1

        # Find templates that occur frequently
        min_count = max(2, len(queries) * 0.2)  # At least 20% of queries

        for template, count in template_counts.items():
            if count >= min_count:
                # This is a potential pattern
                confidence = min(0.9, 0.5 + (count / len(queries)) * 0.5)

                # Create pattern
                pattern_id = str(uuid.uuid4())
                description = f"Auto-detected pattern ({time_window})"

                pattern = TemporalPattern(
                    pattern_id=pattern_id,
                    description=description,
                    query_template=template,
                    time_window=time_window,
                    confidence=confidence,
                    observation_count=count,
                )

                self._patterns[pattern_id] = pattern
                self._logger.info(
                    f"Detected new pattern: {template} with confidence {confidence:.2f}",
                )

    def _normalize_query(self, query_text: str) -> str:
        """
        Normalize a query to identify patterns.

        Args:
            query_text: Raw query text

        Returns:
            Normalized query template
        """
        # This is a simple implementation
        # A more advanced implementation would use NLP to extract query templates

        # Replace dates with placeholders
        date_keywords = [
            "today",
            "yesterday",
            "last week",
            "this week",
            "next week",
            "last month",
            "this month",
            "next month",
        ]

        normalized = query_text.lower()

        for keyword in date_keywords:
            if keyword in normalized:
                normalized = normalized.replace(keyword, "{date}")

        # Replace specific times
        time_pattern = r"\d{1,2}:\d{2}"
        import re

        normalized = re.sub(time_pattern, "{time}", normalized)

        # Replace numbers
        return re.sub(r"\b\d+\b", "{number}", normalized)


    def generate_suggestions(
        self,
        current_query: str | None = None,
        context_data: dict[str, Any] | None = None,
        max_suggestions: int = 10,
    ) -> list[QuerySuggestion]:
        """
        Generate query suggestions based on temporal patterns.

        Args:
            current_query: The current query, if any
            context_data: Additional context data
            max_suggestions: Maximum number of suggestions to generate

        Returns:
            List of query suggestions based on temporal patterns
        """
        # Load patterns if not already loaded
        if not self._patterns_loaded:
            self._load_patterns_from_database()

        # Get current time
        current_time = datetime.now(UTC)
        context_data = context_data or {}

        # Override current time for testing if provided
        if "current_time" in context_data:
            try:
                current_time = datetime.fromisoformat(context_data["current_time"])
                if current_time.tzinfo is None:
                    current_time = current_time.replace(tzinfo=UTC)
            except (ValueError, TypeError):
                pass

        self._logger.info(
            f"Generating suggestions for current time: {current_time.isoformat()}",
        )

        # Find active patterns
        active_patterns = []
        for pattern in self._patterns.values():
            match_score = pattern.match_score(current_time)

            # Consider patterns with a match score above threshold
            if match_score >= 0.5:
                active_patterns.append((pattern, match_score))

        if not active_patterns:
            self._logger.info("No active patterns found for current time")
            return []

        # Sort by match score and confidence
        active_patterns.sort(key=lambda x: x[1] * x[0].confidence, reverse=True)

        # Process query history if available
        if "query_history" in context_data and not self._patterns_loaded:
            self._detect_patterns(context_data["query_history"])

        # Generate suggestions from active patterns
        suggestions = []

        for pattern, match_score in active_patterns[:max_suggestions]:
            # Calculate confidence based on pattern confidence and match score
            confidence = pattern.confidence * match_score

            # Adjust confidence based on usage history
            if pattern.successful_uses + pattern.unsuccessful_uses > 0:
                success_ratio = pattern.successful_uses / (pattern.successful_uses + pattern.unsuccessful_uses)
                confidence = (confidence + success_ratio) / 2

            # Calculate recency boost if recently successful
            recency_boost = 0.0
            if pattern.last_used and pattern.successful_uses > 0:
                time_since_last_use = (current_time - pattern.last_used).total_seconds() / 3600  # hours
                if time_since_last_use < 24:
                    recency_boost = 0.1 * math.exp(-time_since_last_use / 24)

            confidence = min(1.0, confidence + recency_boost)

            # Generate suggestion
            suggestion = self.create_suggestion(
                query_text=pattern.query_template,
                rationale=f"Based on temporal pattern: {pattern.description}",
                confidence=confidence,
                source_context={
                    "pattern_id": pattern.pattern_id,
                    "time_window": pattern.time_window,
                    "match_score": match_score,
                    "current_time": current_time.isoformat(),
                },
                relevance_factors={
                    "temporal_match": match_score,
                    "pattern_confidence": pattern.confidence,
                    "observation_count": min(1.0, pattern.observation_count / 10),
                    "success_ratio": (
                        pattern.successful_uses / (pattern.successful_uses + pattern.unsuccessful_uses)
                        if pattern.successful_uses + pattern.unsuccessful_uses > 0
                        else 0.5
                    ),
                    "recency_boost": recency_boost,
                },
                tags=[
                    "temporal",
                    f"day:{calendar.day_name[current_time.weekday()]}",
                    f"hour:{current_time.hour}",
                ],
            )

            suggestions.append(suggestion)

        return suggestions

    def update_from_feedback(
        self,
        suggestion: QuerySuggestion,
        feedback: FeedbackType,
        result_count: int | None = None,
    ) -> None:
        """
        Update internal models based on feedback.

        Args:
            suggestion: The suggestion that received feedback
            feedback: The type of feedback provided
            result_count: Number of results from the suggested query, if applicable
        """
        # Extract pattern ID from source context
        source_context = suggestion.source_context
        pattern_id = source_context.get("pattern_id")

        if not pattern_id or pattern_id not in self._patterns:
            self._logger.warning(f"Pattern ID {pattern_id} not found")
            return

        # Update pattern with feedback
        pattern = self._patterns[pattern_id]
        pattern.update_from_feedback(feedback)

        # Add bonus for highly successful queries
        if self.is_positive_feedback(feedback) and result_count and result_count > 5:
            pattern.successful_uses += 1

        self._logger.info(
            f"Updated feedback for pattern {pattern_id}: {pattern.successful_uses} successes, {pattern.unsuccessful_uses} failures",
        )

    def get_patterns(self) -> list[TemporalPattern]:
        """
        Get all registered temporal patterns.

        Returns:
            List of temporal patterns
        """
        return list(self._patterns.values())

    def add_pattern(self, pattern: TemporalPattern) -> None:
        """
        Add a new temporal pattern.

        Args:
            pattern: The pattern to add
        """
        self._patterns[pattern.pattern_id] = pattern
        self._logger.info(f"Added new pattern: {pattern.description}")

    def remove_pattern(self, pattern_id: str) -> bool:
        """
        Remove a temporal pattern.

        Args:
            pattern_id: ID of the pattern to remove

        Returns:
            True if pattern was removed, False otherwise
        """
        if pattern_id in self._patterns:
            del self._patterns[pattern_id]
            self._logger.info(f"Removed pattern: {pattern_id}")
            return True
        return False

    def save_patterns_to_database(self) -> bool:
        """
        Save patterns to database.

        Returns:
            True if successful, False otherwise
        """
        # In a real implementation, this would save patterns to the database
        # For demonstration, we'll just log the number of patterns
        self._logger.info(f"Would save {len(self._patterns)} patterns to database")
        return True


def main() -> None:
    """Test the TemporalPatternRecommender."""
    logging.basicConfig(level=logging.DEBUG)


    # Create recommender
    recommender = TemporalPatternRecommender(debug=True)

    # Test specific times
    test_times = [
        # Weekday morning
        datetime(2025, 4, 21, 9, 0, tzinfo=UTC),  # Monday 9 AM
        # Weekday lunch
        datetime(2025, 4, 21, 12, 30, tzinfo=UTC),  # Monday 12:30 PM
        # Weekday end of day
        datetime(2025, 4, 21, 17, 0, tzinfo=UTC),  # Monday 5 PM
        # Friday afternoon
        datetime(2025, 4, 25, 16, 0, tzinfo=UTC),  # Friday 4 PM
        # Weekend
        datetime(2025, 4, 26, 11, 0, tzinfo=UTC),  # Saturday 11 AM
    ]

    for test_time in test_times:

        # Create context with current time
        context_data = {"current_time": test_time.isoformat()}

        # Generate suggestions
        suggestions = recommender.generate_suggestions(
            context_data=context_data,
            max_suggestions=3,
        )

        for _i, suggestion in enumerate(suggestions):

            # Show time window
            time_window = suggestion.source_context.get("time_window", {})
            if "days_of_week" in time_window:
                [calendar.day_name[d] for d in time_window["days_of_week"]]
            if "hour_range" in time_window:
                time_window["hour_range"]


    # Test feedback
    if suggestions:
        recommender.update_from_feedback(
            suggestion=suggestions[0],
            feedback=FeedbackType.ACCEPTED,
            result_count=7,
        )

        # Generate new suggestions to see effect of feedback
        new_suggestions = recommender.generate_suggestions(
            context_data=context_data,
            max_suggestions=3,
        )

        for _i, suggestion in enumerate(new_suggestions):

            # Check if this matches an original suggestion to see confidence change
            for orig in suggestions:
                if suggestion.query_text == orig.query_text:
                    confidence_change = suggestion.confidence - orig.confidence
                    if abs(confidence_change) > 0.01:
                        pass


if __name__ == "__main__":
    main()
