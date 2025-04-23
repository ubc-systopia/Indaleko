"""
This module implements proactive capabilities for the Archivist memory system.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason and contributors

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
import random
import sys
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from icecream import ic
from pydantic import BaseModel, Field

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.memory.archivist_memory import ArchivistMemory
from query.memory.pattern_types import (
    ProactiveSuggestion,
    SuggestionPriority,
    SuggestionType,
)

# We'll import the detector by name only to avoid circular imports
# pylint: enable=wrong-import-position


class SuggestionHistory(BaseModel):
    """History of suggestions and user interactions."""

    suggestions: list[ProactiveSuggestion] = Field(
        default_factory=list, description="All suggestions generated",
    )
    positive_interactions: dict[SuggestionType, int] = Field(
        default_factory=dict, description="Count of positive interactions by type",
    )
    negative_interactions: dict[SuggestionType, int] = Field(
        default_factory=dict, description="Count of negative interactions by type",
    )

    def record_interaction(
        self, suggestion: ProactiveSuggestion, feedback_value: float,
    ) -> None:
        """
        Record user interaction with a suggestion.

        Args:
            suggestion: The suggestion that received feedback
            feedback_value: The feedback value (-1.0 to 1.0)
        """
        suggestion_type = suggestion.suggestion_type

        # Initialize counts if not present
        if suggestion_type not in self.positive_interactions:
            self.positive_interactions[suggestion_type] = 0
        if suggestion_type not in self.negative_interactions:
            self.negative_interactions[suggestion_type] = 0

        # Update counts based on feedback
        if feedback_value > 0:
            self.positive_interactions[suggestion_type] += 1
        elif feedback_value < 0:
            self.negative_interactions[suggestion_type] += 1

    def get_acceptance_rate(
        self, suggestion_type: SuggestionType | None = None,
    ) -> float:
        """
        Calculate the acceptance rate for a suggestion type or overall.

        Args:
            suggestion_type: Specific suggestion type or None for overall

        Returns:
            float: Acceptance rate between 0.0 and 1.0
        """
        if suggestion_type:
            positive = self.positive_interactions.get(suggestion_type, 0)
            negative = self.negative_interactions.get(suggestion_type, 0)
            total = positive + negative
            return positive / total if total > 0 else 0.5
        else:
            total_positive = sum(self.positive_interactions.values())
            total_negative = sum(self.negative_interactions.values())
            total = total_positive + total_negative
            return total_positive / total if total > 0 else 0.5


class TemporalPattern(BaseModel):
    """Representation of a temporal pattern in user behavior."""

    pattern_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this pattern",
    )
    pattern_type: str = Field(
        ..., description="Type of temporal pattern (e.g., 'daily', 'weekly', 'monthly')",
    )
    description: str = Field(..., description="Description of the pattern")
    confidence: float = Field(
        default=0.5, description="Confidence in this pattern (0.0-1.0)",
    )
    timeframe: dict[str, Any] = Field(
        ..., description="Timeframe specification for the pattern",
    )
    associated_actions: list[str] = Field(
        default_factory=list, description="Actions associated with this pattern",
    )

    def matches_current_time(self) -> bool:
        """Check if the current time matches this pattern."""
        now = datetime.now(UTC)
        pattern_type = self.pattern_type

        if pattern_type == "daily":
            # Check hour range
            if "hour_start" in self.timeframe and "hour_end" in self.timeframe:
                start_hour = self.timeframe["hour_start"]
                end_hour = self.timeframe["hour_end"]
                current_hour = now.hour
                return start_hour <= current_hour <= end_hour

        elif pattern_type == "weekly":
            # Check day of week
            if "day_of_week" in self.timeframe:
                target_day = self.timeframe["day_of_week"]
                current_day = now.weekday()  # 0-6 (Monday-Sunday)
                return target_day == current_day

        elif pattern_type == "monthly":
            # Check day of month
            if "day_of_month" in self.timeframe:
                target_day = self.timeframe["day_of_month"]
                current_day = now.day
                return target_day == current_day

        # No match by default
        return False


class ProactiveArchivistData(BaseModel):
    """Data model for the proactive capabilities of the Archivist memory system."""

    suggestion_history: SuggestionHistory = Field(
        default_factory=SuggestionHistory,
        description="History of suggestions and interactions",
    )
    active_suggestions: list[ProactiveSuggestion] = Field(
        default_factory=list, description="Currently active suggestions",
    )
    temporal_patterns: list[TemporalPattern] = Field(
        default_factory=list, description="Detected temporal patterns",
    )
    sequential_patterns: dict[str, list[str]] = Field(
        default_factory=dict, description="Detected sequential patterns in queries",
    )
    context_triggers: dict[str, list[str]] = Field(
        default_factory=dict, description="Context triggers for proactive suggestions",
    )
    suggestion_thresholds: dict[SuggestionType, float] = Field(
        default_factory=dict,
        description="Confidence thresholds for different suggestion types",
    )
    cross_source_enabled: bool = Field(
        default=True, description="Whether cross-source pattern detection is enabled",
    )
    last_cross_source_analysis: datetime | None = Field(
        default=None, description="When cross-source patterns were last analyzed",
    )

    def __init__(self, **data):
        super().__init__(**data)
        # Set default suggestion thresholds if not provided
        if not self.suggestion_thresholds:
            self.suggestion_thresholds = {
                SuggestionType.QUERY: 0.6,
                SuggestionType.CONTENT: 0.7,
                SuggestionType.ORGANIZATION: 0.7,
                SuggestionType.REMINDER: 0.5,
                SuggestionType.RELATED_CONTENT: 0.6,
                SuggestionType.SEARCH_STRATEGY: 0.7,
                SuggestionType.GOAL_PROGRESS: 0.6,
            }


class ProactiveArchivist:
    """
    Enhances the Archivist memory system with proactive capabilities.

    This component analyzes patterns in user behavior and anticipates information
    needs, generating suggestions before they're explicitly requested.
    """

    proactive_archivist_uuid_str = "f5a3e7b1-9c6d-4e8a-b7f2-c9d4e6f3a2b1"
    proactive_archivist_version = "2025.04.11.02"
    proactive_archivist_description = (
        "Proactive Archivist enhancement with cross-source pattern detection"
    )

    def __init__(self, archivist_memory: ArchivistMemory):
        """
        Initialize the Proactive Archivist.

        Args:
            archivist_memory: The base Archivist memory system to enhance
        """
        self.archivist = archivist_memory
        self.data = ProactiveArchivistData()

        # We'll initialize the cross-source pattern detector on demand to avoid circular imports
        self._cross_source_detector = None

    @property
    def cross_source_detector(self):
        """Lazy-load the cross-source pattern detector when needed."""
        if self._cross_source_detector is None:
            # Import here to avoid circular imports
            from query.memory.cross_source_patterns import CrossSourcePatternDetector

            self._cross_source_detector = CrossSourcePatternDetector(
                self.archivist.db_config,
            )
        return self._cross_source_detector

    def generate_suggestions(
        self, context: dict[str, Any] | None = None,
    ) -> list[ProactiveSuggestion]:
        """
        Generate proactive suggestions based on memory and context.

        Args:
            context: Current context information (optional)

        Returns:
            List of suggestions to present to the user
        """
        # Clean up expired suggestions
        self._remove_expired_suggestions()

        # Generate suggestions from different sources
        suggestions = []
        suggestions.extend(self._generate_goal_based_suggestions(context))
        suggestions.extend(self._generate_topic_based_suggestions(context))
        suggestions.extend(self._generate_temporal_pattern_suggestions(context))
        suggestions.extend(self._generate_strategy_suggestions(context))

        # Add cross-source suggestions if enabled and analysis has been run
        if self.data.cross_source_enabled and self.data.last_cross_source_analysis:
            # Check if we need to refresh cross-source suggestions
            now = datetime.now(UTC)
            time_since_analysis = (
                now - self.data.last_cross_source_analysis
            ).total_seconds()

            # If it's been more than 24 hours since the last analysis, run it again
            if time_since_analysis > 24 * 60 * 60:
                try:
                    self.analyze_cross_source_patterns()
                except Exception as e:
                    ic(f"Error refreshing cross-source analysis: {e}")

            # Add existing cross-source suggestions from active suggestions
            cross_source_suggestions = [
                s
                for s in self.data.active_suggestions
                if "correlation_id" in s.context or "pattern_id" in s.context
            ]
            suggestions.extend(cross_source_suggestions)

        # Filter suggestions based on confidence thresholds
        filtered_suggestions = [
            s
            for s in suggestions
            if s.confidence
            >= self.data.suggestion_thresholds.get(s.suggestion_type, 0.7)
        ]

        # Sort by priority and confidence
        sorted_suggestions = sorted(
            filtered_suggestions,
            key=lambda s: (
                {"critical": 3, "high": 2, "medium": 1, "low": 0}[s.priority],
                s.confidence,
            ),
            reverse=True,
        )

        # Add to active suggestions (avoiding duplicates)
        existing_ids = {s.suggestion_id for s in self.data.active_suggestions}
        new_suggestions = [
            s for s in sorted_suggestions if s.suggestion_id not in existing_ids
        ]
        self.data.active_suggestions.extend(new_suggestions)

        return sorted_suggestions

    def _remove_expired_suggestions(self) -> None:
        """Remove expired suggestions from the active list."""
        self.data.active_suggestions = [
            s
            for s in self.data.active_suggestions
            if not s.is_expired() and not s.dismissed
        ]

    def _generate_goal_based_suggestions(
        self, context: dict[str, Any] | None = None,
    ) -> list[ProactiveSuggestion]:
        """
        Generate suggestions related to long-term goals.

        Args:
            context: Current context information

        Returns:
            List of goal-related suggestions
        """
        suggestions = []

        # Check if there are any goals with low progress updates
        for goal in self.archivist.memory.long_term_goals:
            # Check for stalled goals (no updates in over 2 weeks)
            if goal.last_updated < datetime.now(UTC) - timedelta(days=14):
                confidence = min(
                    0.5
                    + (0.1 * (datetime.now(UTC) - goal.last_updated).days / 7),
                    0.9,
                )

                suggestion = ProactiveSuggestion(
                    suggestion_type=SuggestionType.GOAL_PROGRESS,
                    title=f"Continue work on {goal.name}",
                    content=f"You haven't made progress on '{goal.name}' recently. Current progress is {goal.progress*100:.0f}%. Would you like to continue work on this goal?",
                    expires_at=datetime.now(UTC) + timedelta(days=7),
                    priority=SuggestionPriority.MEDIUM,
                    confidence=confidence,
                    context={"goal_name": goal.name, "goal_progress": goal.progress},
                )
                suggestions.append(suggestion)

            # For goals in progress (between 25% and 75% complete)
            elif 0.25 <= goal.progress <= 0.75:
                # Check if we have specific milestones
                incomplete_milestones = [k for k, v in goal.milestones.items() if not v]

                if incomplete_milestones:
                    # Suggest next milestone
                    next_milestone = incomplete_milestones[0]

                    suggestion = ProactiveSuggestion(
                        suggestion_type=SuggestionType.GOAL_PROGRESS,
                        title=f"Next step for {goal.name}",
                        content=f"Next milestone for '{goal.name}': {next_milestone}. Would you like to work on this now?",
                        expires_at=datetime.now(UTC) + timedelta(days=3),
                        priority=SuggestionPriority.MEDIUM,
                        confidence=0.75,
                        context={"goal_name": goal.name, "milestone": next_milestone},
                    )
                    suggestions.append(suggestion)

        return suggestions

    def _generate_topic_based_suggestions(
        self, context: dict[str, Any] | None = None,
    ) -> list[ProactiveSuggestion]:
        """
        Generate suggestions based on topics of interest.

        Args:
            context: Current context information

        Returns:
            List of topic-related suggestions
        """
        suggestions = []

        # Get top topics of interest
        topics = self.archivist.memory.semantic_topics
        if not topics:
            return suggestions

        top_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:3]

        # Generate query suggestions for top topics
        for topic, importance in top_topics:
            if importance > 0.7:  # Only for high-importance topics
                # Generate suggested queries for this topic
                suggested_queries = self._generate_queries_for_topic(topic)

                if suggested_queries:
                    query = random.choice(suggested_queries)

                    suggestion = ProactiveSuggestion(
                        suggestion_type=SuggestionType.QUERY,
                        title=f"Suggested search: {topic}",
                        content=f"Based on your interests, you might want to try: '{query}'",
                        expires_at=datetime.now(UTC) + timedelta(days=1),
                        priority=SuggestionPriority.LOW,
                        confidence=importance,
                        context={"topic": topic, "suggested_query": query},
                        related_queries=[query],
                    )
                    suggestions.append(suggestion)

        return suggestions

    def _generate_queries_for_topic(self, topic: str) -> list[str]:
        """
        Generate suggested queries for a given topic.

        Args:
            topic: The topic to generate queries for

        Returns:
            List of suggested queries
        """
        # This could be enhanced with an LLM for more sophisticated query generation
        topic_query_templates = {
            "work": [
                f"recent {topic} documents",
                f"important {topic} files from last month",
                f"{topic} presentations",
            ],
            "personal": [
                f"recent {topic} photos",
                f"{topic} documents from last year",
                f"{topic} planning files",
            ],
            "finance": [
                f"recent {topic} receipts",
                f"{topic} budget documents",
                f"{topic} tax forms from this year",
            ],
            "academic": [
                f"recent {topic} research papers",
                f"{topic} notes from this semester",
                f"important {topic} references",
            ],
            "media": [
                f"recent {topic} photos",
                f"{topic} videos from last month",
                f"shared {topic} albums",
            ],
            "technology": [
                f"recent {topic} code",
                f"{topic} projects",
                f"{topic} documentation",
            ],
        }

        # Return templates for the specific topic, or general ones if not found
        return topic_query_templates.get(
            topic.lower(),
            [
                f"recent {topic} files",
                f"important {topic} documents",
                f"{topic} information from last month",
            ],
        )

    def _generate_temporal_pattern_suggestions(
        self, context: dict[str, Any] | None = None,
    ) -> list[ProactiveSuggestion]:
        """
        Generate suggestions based on temporal patterns.

        Args:
            context: Current context information

        Returns:
            List of time-based suggestions
        """
        suggestions = []

        # Check for matching temporal patterns
        matching_patterns = [
            p for p in self.data.temporal_patterns if p.matches_current_time()
        ]

        for pattern in matching_patterns:
            if pattern.associated_actions:
                action = random.choice(pattern.associated_actions)

                suggestion = ProactiveSuggestion(
                    suggestion_type=SuggestionType.REMINDER,
                    title=f"Scheduled activity: {pattern.description}",
                    content=f"Based on your usual patterns, it's time for: {action}",
                    expires_at=datetime.now(UTC) + timedelta(hours=2),
                    priority=SuggestionPriority.MEDIUM,
                    confidence=pattern.confidence,
                    context={"pattern_type": pattern.pattern_type, "action": action},
                )
                suggestions.append(suggestion)

        return suggestions

    def _generate_strategy_suggestions(
        self, context: dict[str, Any] | None = None,
    ) -> list[ProactiveSuggestion]:
        """
        Generate suggestions for effective search strategies.

        Args:
            context: Current context information

        Returns:
            List of strategy suggestions
        """
        suggestions = []

        # Only suggest strategies if we have high-confidence ones
        effective_strategies = [
            s
            for s in self.archivist.memory.effective_strategies
            if s.success_rate > 0.7
        ]

        if effective_strategies and context and "recent_queries" in context:
            # Try to suggest a strategy based on recent queries
            strategy = max(effective_strategies, key=lambda s: s.success_rate)

            suggestion = ProactiveSuggestion(
                suggestion_type=SuggestionType.SEARCH_STRATEGY,
                title=f"Try search strategy: {strategy.strategy_name}",
                content=f"This search approach might improve your results: {strategy.description}",
                expires_at=datetime.now(UTC) + timedelta(days=1),
                priority=SuggestionPriority.LOW,
                confidence=strategy.success_rate,
                context={"strategy_name": strategy.strategy_name},
            )
            suggestions.append(suggestion)

        return suggestions

    def detect_temporal_patterns(self, query_history) -> None:
        """
        Detect temporal patterns in user query behavior.

        Args:
            query_history: Query history to analyze
        """
        if not hasattr(query_history, "get_recent_queries"):
            return

        queries = query_history.get_recent_queries(
            30,
        )  # Get more history for pattern detection
        if not queries or len(queries) < 10:  # Need sufficient data
            return

        # Group queries by hour of day
        hour_counts = {}
        for query in queries:
            if hasattr(query, "Timestamp"):
                hour = query.Timestamp.hour
                hour_counts[hour] = hour_counts.get(hour, 0) + 1

        # Group queries by day of week
        day_counts = {}
        for query in queries:
            if hasattr(query, "Timestamp"):
                day = query.Timestamp.weekday()
                day_counts[day] = day_counts.get(day, 0) + 1

        # Detect daily patterns (active hours)
        if hour_counts:
            active_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
            if (
                active_hours and active_hours[0][1] > len(queries) * 0.2
            ):  # At least 20% in peak hour
                peak_hour = active_hours[0][0]
                # Define a 3-hour window around the peak
                hour_start = max(0, peak_hour - 1)
                hour_end = min(23, peak_hour + 1)

                # Create or update temporal pattern
                self._add_or_update_temporal_pattern(
                    pattern_type="daily",
                    description="Daily active time",
                    confidence=min(0.5 + (active_hours[0][1] / len(queries)), 0.9),
                    timeframe={"hour_start": hour_start, "hour_end": hour_end},
                )

        # Detect weekly patterns
        if day_counts:
            active_days = sorted(day_counts.items(), key=lambda x: x[1], reverse=True)
            if (
                active_days and active_days[0][1] > len(queries) * 0.3
            ):  # At least 30% on peak day
                peak_day = active_days[0][0]

                # Create or update temporal pattern
                self._add_or_update_temporal_pattern(
                    pattern_type="weekly",
                    description=f"Weekly active day ({['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][peak_day]})",
                    confidence=min(0.5 + (active_days[0][1] / len(queries)), 0.9),
                    timeframe={"day_of_week": peak_day},
                )

    def _add_or_update_temporal_pattern(
        self, pattern_type, description, confidence, timeframe,
    ):
        """Add a new temporal pattern or update an existing one."""
        # Check if similar pattern already exists
        for pattern in self.data.temporal_patterns:
            if pattern.pattern_type == pattern_type and pattern.timeframe == timeframe:
                # Update confidence (moving average)
                pattern.confidence = (pattern.confidence + confidence) / 2
                return

        # Add new pattern
        self.data.temporal_patterns.append(
            TemporalPattern(
                pattern_type=pattern_type,
                description=description,
                confidence=confidence,
                timeframe=timeframe,
            ),
        )

    def detect_sequential_patterns(self, query_history) -> None:
        """
        Detect sequential patterns in queries (what queries tend to follow others).

        Args:
            query_history: Query history to analyze
        """
        if not hasattr(query_history, "get_recent_queries"):
            return

        queries = query_history.get_recent_queries(20)
        if not queries or len(queries) < 5:
            return

        # Analyze consecutive query pairs
        for i in range(len(queries) - 1):
            current = queries[i].OriginalQuery
            next_query = queries[i + 1].OriginalQuery

            # Skip if they're the same query
            if current == next_query:
                continue

            # Add to sequential patterns
            if current not in self.data.sequential_patterns:
                self.data.sequential_patterns[current] = []

            if next_query not in self.data.sequential_patterns[current]:
                self.data.sequential_patterns[current].append(next_query)

    def extract_insights_from_patterns(self) -> None:
        """Extract insights from detected patterns and add them to the Archivist."""
        # Add insights from temporal patterns
        for pattern in self.data.temporal_patterns:
            if pattern.confidence > 0.7:
                if pattern.pattern_type == "daily":
                    hours = f"{pattern.timeframe['hour_start']}:00-{pattern.timeframe['hour_end']}:00"
                    insight = f"User is most active during {hours} hours"
                    self.archivist.add_insight("temporal", insight, pattern.confidence)
                elif pattern.pattern_type == "weekly":
                    day = [
                        "Monday",
                        "Tuesday",
                        "Wednesday",
                        "Thursday",
                        "Friday",
                        "Saturday",
                        "Sunday",
                    ][pattern.timeframe["day_of_week"]]
                    insight = f"User is most active on {day}s"
                    self.archivist.add_insight("temporal", insight, pattern.confidence)

        # Add insights from sequential patterns
        common_sequences = []
        for first_query, next_queries in self.data.sequential_patterns.items():
            if (
                len(next_queries) >= 3
            ):  # If a query is frequently followed by specific others
                common_sequences.append((first_query, next_queries[:3]))

        if common_sequences:
            for first, seconds in common_sequences[:3]:  # Limit to top 3
                insight = f"Search for '{first}' is often followed by searches for: {', '.join(seconds)}"
                self.archivist.add_insight("sequential", insight, 0.7)

    def record_user_feedback(self, suggestion_id: str, feedback_value: float) -> None:
        """
        Record user feedback on a suggestion.

        Args:
            suggestion_id: ID of the suggestion receiving feedback
            feedback_value: Feedback value between -1.0 (negative) and 1.0 (positive)
        """
        # Find the suggestion
        for suggestion in self.data.active_suggestions:
            if suggestion.suggestion_id == suggestion_id:
                # Record feedback
                suggestion.provide_feedback(feedback_value)

                # Update history
                self.data.suggestion_history.record_interaction(
                    suggestion, feedback_value,
                )

                # If negative feedback, dismiss the suggestion
                if feedback_value < 0:
                    suggestion.mark_dismissed()
                # If positive feedback, mark as acted upon
                elif feedback_value > 0:
                    suggestion.mark_acted_upon()

                # Adjust threshold based on feedback
                suggestion_type = suggestion.suggestion_type
                current_threshold = self.data.suggestion_thresholds.get(
                    suggestion_type, 0.7,
                )

                if feedback_value > 0:
                    # Slightly lower threshold for types with positive feedback
                    self.data.suggestion_thresholds[suggestion_type] = max(
                        0.5, current_threshold - 0.05,
                    )
                elif feedback_value < 0:
                    # Slightly raise threshold for types with negative feedback
                    self.data.suggestion_thresholds[suggestion_type] = min(
                        0.9, current_threshold + 0.05,
                    )

                break

    def get_suggested_query(
        self, context: dict[str, Any] | None = None,
    ) -> str | None:
        """
        Get a query suggestion based on current context.

        Args:
            context: Current context information

        Returns:
            Suggested query or None
        """
        # Generate suggestions if we don't have active ones
        if not self.data.active_suggestions:
            self.generate_suggestions(context)

        # Look for query suggestions
        query_suggestions = [
            s
            for s in self.data.active_suggestions
            if s.suggestion_type == SuggestionType.QUERY and not s.dismissed
        ]

        if query_suggestions:
            # Return the highest confidence query suggestion
            suggestion = max(query_suggestions, key=lambda s: s.confidence)
            return suggestion.related_queries[0] if suggestion.related_queries else None

        return None

    def analyze_session(self, query_history, context=None) -> None:
        """
        Analyze session data to update patterns and generate new insights.

        Args:
            query_history: Query history from the session
            context: Additional context information
        """
        # Detect patterns
        self.detect_temporal_patterns(query_history)
        self.detect_sequential_patterns(query_history)

        # Extract insights
        self.extract_insights_from_patterns()

        # Run cross-source pattern analysis if enabled and due
        if self.data.cross_source_enabled:
            now = datetime.now(UTC)
            # Run analysis if never run before or not run in the last 24 hours
            if (
                self.data.last_cross_source_analysis is None
                or (now - self.data.last_cross_source_analysis).total_seconds()
                > 24 * 60 * 60
            ):
                self.analyze_cross_source_patterns()

        # Clean up expired suggestions
        self._remove_expired_suggestions()

        # Update statistics based on user interactions
        # (This would analyze which suggestions were acted upon)

    def analyze_cross_source_patterns(self) -> None:
        """
        Analyze patterns across different data sources to generate holistic insights.

        This method collects data from various sources, detects patterns and correlations,
        and generates suggestions based on the findings.
        """
        try:
            ic("Running cross-source pattern analysis")

            # Run the cross-source pattern detector
            event_count, patterns, correlations, suggestions = (
                self.cross_source_detector.analyze_and_generate()
            )

            ic(
                f"Cross-source analysis: Found {len(patterns)} patterns, {len(correlations)} correlations",
            )

            # Convert any generated suggestions to our format and add them
            for suggestion in suggestions:
                # Create a ProactiveSuggestion from the cross-source suggestion
                proactive_suggestion = ProactiveSuggestion(
                    suggestion_type=suggestion.suggestion_type,
                    title=suggestion.title,
                    content=suggestion.content,
                    expires_at=suggestion.expires_at,
                    priority=suggestion.priority,
                    confidence=suggestion.confidence,
                    context=suggestion.context,
                )

                # Add to active suggestions if confidence meets threshold
                if (
                    proactive_suggestion.confidence
                    >= self.data.suggestion_thresholds.get(
                        proactive_suggestion.suggestion_type, 0.7,
                    )
                ):
                    self.data.active_suggestions.append(proactive_suggestion)

            # Add insights from patterns
            for pattern in patterns:
                if (
                    pattern.confidence >= 0.65
                ):  # Only add high-confidence patterns as insights
                    insight_category = "cross_source_pattern"
                    insight_text = pattern.description
                    self.archivist.add_insight(
                        insight_category, insight_text, pattern.confidence,
                    )

            # Add insights from correlations
            for correlation in correlations:
                if (
                    correlation.confidence >= 0.7
                ):  # Only add high-confidence correlations as insights
                    insight_category = "cross_source_correlation"
                    insight_text = correlation.description
                    self.archivist.add_insight(
                        insight_category, insight_text, correlation.confidence,
                    )

            # Update last analysis timestamp
            self.data.last_cross_source_analysis = datetime.now(UTC)

        except Exception as e:
            ic(f"Error in cross-source pattern analysis: {e}")


def main():
    """Test the Proactive Archivist capabilities."""
    # Initialize base Archivist memory
    archivist = ArchivistMemory()

    # Add some test data
    archivist.add_long_term_goal(
        "File Organization", "Organize personal documents by project and year",
    )
    archivist.update_goal_progress("File Organization", 0.35)

    archivist.add_insight(
        "organization", "User struggles with finding documents older than 6 months", 0.8,
    )
    archivist.add_insight(
        "retrieval", "Location data is highly valuable for narrowing searches", 0.7,
    )

    # Initialize Proactive Archivist
    proactive = ProactiveArchivist(archivist)

    # Generate suggestions
    suggestions = proactive.generate_suggestions()

    # Display suggestions
    print("\nProactive Suggestions:")
    print("=====================")
    for suggestion in suggestions:
        print(f"\n{suggestion.title}")
        print(f"Type: {suggestion.suggestion_type}, Priority: {suggestion.priority}")
        print(f"Confidence: {suggestion.confidence:.2f}")
        print(f"Content: {suggestion.content}")


if __name__ == "__main__":
    main()
