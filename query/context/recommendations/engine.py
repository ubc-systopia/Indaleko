"""
Recommendation engine for the Contextual Query Recommendation Engine.

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

import uuid

from typing import Any

from icecream import ic

from query.context.activity_provider import QueryActivityProvider
from query.context.data_models.recommendation import (
    FeedbackType,
    QuerySuggestion,
    RecommendationFeedback,
    RecommendationSettings,
    RecommendationSource,
)
from query.context.navigation import QueryNavigator
from query.context.recommendations.activity_context import ActivityContextRecommender
from query.context.recommendations.base import RecommendationProvider
from query.context.recommendations.entity_relationship import (
    EntityRelationshipRecommender,
)
from query.context.recommendations.query_history import QueryHistoryRecommender
from query.context.recommendations.temporal_pattern import TemporalPatternRecommender
from query.context.relationship import QueryRelationshipDetector


class RecommendationEngine:
    """
    Central coordinator for generating contextual query recommendations.

    This engine collects suggestions from multiple recommendation sources,
    ranks them based on relevance and confidence, and provides a unified
    interface for generating and managing recommendations.
    """

    def __init__(
        self,
        settings: RecommendationSettings | None = None,
        debug: bool = False,
    ) -> None:
        """
        Initialize the recommendation engine.

        Args:
            settings: Settings for the recommendation engine
            debug: Whether to enable debug output
        """
        self.settings = settings or RecommendationSettings()
        self.debug = debug

        # Initialize recommendation providers
        self.providers = {}
        self._initialize_providers()

        # Storage for feedback
        self.feedback_history = {}  # {suggestion_id: RecommendationFeedback}

        # Cache for recent suggestions
        self.recent_suggestions = {}  # {suggestion_id: QuerySuggestion}

        # Statistics
        self.suggestion_counts = dict.fromkeys(RecommendationSource, 0)
        self.acceptance_counts = dict.fromkeys(RecommendationSource, 0)

    def _initialize_providers(self) -> None:
        """Initialize recommendation providers."""
        # Create shared components
        query_provider = QueryActivityProvider(debug=self.debug)
        query_navigator = QueryNavigator(debug=self.debug)
        relationship_detector = QueryRelationshipDetector(debug=self.debug)

        # Initialize query history recommender
        self.providers[RecommendationSource.QUERY_HISTORY] = QueryHistoryRecommender(
            query_provider=query_provider,
            query_navigator=query_navigator,
            relationship_detector=relationship_detector,
            debug=self.debug,
        )

        # Initialize activity context recommender
        self.providers[RecommendationSource.ACTIVITY_CONTEXT] = ActivityContextRecommender(
            db_config=None,
            debug=self.debug,  # Use default config
        )

        # Initialize entity relationship recommender
        self.providers[RecommendationSource.ENTITY_RELATIONSHIP] = EntityRelationshipRecommender(
            db_config=None,
            debug=self.debug,  # Use default config
        )

        # Initialize temporal pattern recommender
        self.providers[RecommendationSource.TEMPORAL_PATTERN] = TemporalPatternRecommender(
            db_config=None,
            debug=self.debug,  # Use default config
        )

    def register_provider(self, provider: RecommendationProvider) -> None:
        """
        Register a recommendation provider.

        Args:
            provider: The provider to register
        """
        self.providers[provider.get_source_type()] = provider

    def get_recommendations(
        self,
        current_query: str | None = None,
        context_data: dict[str, Any] | None = None,
        max_results: int | None = None,
    ) -> list[QuerySuggestion]:
        """
        Generate recommendations based on current context.

        Args:
            current_query: The current query, if any
            context_data: Additional context data
            max_results: Maximum number of results to return (default: from settings)

        Returns:
            List of query suggestions
        """
        if not self.settings.enabled:
            return []

        max_results = max_results or self.settings.max_suggestions
        context_data = context_data or {}

        # Collect suggestions from all providers
        all_suggestions = []

        for source_type, provider in self.providers.items():
            # Check if this source is enabled
            if source_type not in self.settings.source_weights or self.settings.source_weights[source_type] <= 0:
                continue

            # Get suggestions from this provider
            suggestions = provider.generate_suggestions(
                current_query=current_query,
                context_data=context_data,
                max_suggestions=max_results * 2,  # Request more for ranking
            )

            # Apply source weight to confidence
            for suggestion in suggestions:
                source_weight = self.settings.source_weights.get(source_type, 1.0)
                suggestion.confidence *= source_weight

                # Track this suggestion
                self.recent_suggestions[suggestion.suggestion_id] = suggestion
                self.suggestion_counts[source_type] += 1

            all_suggestions.extend(suggestions)

        # Rank suggestions
        ranked_suggestions = self._rank_suggestions(all_suggestions, context_data)

        # Filter by confidence threshold
        filtered_suggestions = [s for s in ranked_suggestions if s.confidence >= self.settings.min_confidence]

        # Limit to max results
        return filtered_suggestions[:max_results]

    def _rank_suggestions(
        self,
        suggestions: list[QuerySuggestion],
        context_data: dict[str, Any],
    ) -> list[QuerySuggestion]:
        """
        Rank suggestions based on confidence and diversity.

        Args:
            suggestions: List of suggestions to rank
            context_data: Additional context data

        Returns:
            Ranked list of suggestions
        """
        if not suggestions:
            return []

        # First sort by confidence
        sorted_suggestions = sorted(
            suggestions,
            key=lambda x: x.confidence,
            reverse=True,
        )

        # Then ensure diversity by limiting same-source suggestions
        diversified_suggestions = []
        source_counts = dict.fromkeys(RecommendationSource, 0)

        for suggestion in sorted_suggestions:
            source = suggestion.source

            # Allow more suggestions from higher-weighted sources
            max_per_source = int(
                max(1, 2 * self.settings.source_weights.get(source, 1.0)),
            )

            if source_counts[source] < max_per_source:
                diversified_suggestions.append(suggestion)
                source_counts[source] += 1

                # If we have enough diverse suggestions, stop
                if len(diversified_suggestions) >= self.settings.max_suggestions:
                    break

        return diversified_suggestions

    def record_feedback(
        self,
        suggestion_id: uuid.UUID,
        feedback: FeedbackType,
        result_count: int | None = None,
    ) -> None:
        """
        Record user feedback about a suggestion.

        Args:
            suggestion_id: ID of the suggestion that received feedback
            feedback: The type of feedback provided
            result_count: Number of results from the suggested query, if applicable
        """
        # Find the suggestion
        suggestion = self.recent_suggestions.get(suggestion_id)
        if not suggestion:
            if self.debug:
                ic(f"Suggestion with ID {suggestion_id} not found")
            return

        # Record feedback
        feedback_record = RecommendationFeedback(
            suggestion_id=suggestion_id,
            feedback_type=feedback,
            result_count=result_count,
        )

        self.feedback_history[suggestion_id] = feedback_record

        # Update provider
        provider = self.providers.get(suggestion.source)
        if provider and self.settings.enable_learning:
            provider.update_from_feedback(suggestion, feedback, result_count)

        # Update statistics
        if feedback in [FeedbackType.ACCEPTED, FeedbackType.HELPFUL]:
            self.acceptance_counts[suggestion.source] += 1

    def get_acceptance_rate(
        self,
        source_type: RecommendationSource | None = None,
    ) -> float:
        """
        Get the acceptance rate for recommendations.

        Args:
            source_type: Optional source type to get rate for (None for overall)

        Returns:
            Acceptance rate as a float (0.0-1.0)
        """
        if source_type:
            suggestions = self.suggestion_counts.get(source_type, 0)
            acceptances = self.acceptance_counts.get(source_type, 0)

            return acceptances / suggestions if suggestions > 0 else 0.0
        total_suggestions = sum(self.suggestion_counts.values())
        total_acceptances = sum(self.acceptance_counts.values())

        return total_acceptances / total_suggestions if total_suggestions > 0 else 0.0

    def get_feedback_stats(self) -> dict[str, Any]:
        """
        Get statistics about feedback.

        Returns:
            Dictionary with feedback statistics
        """
        total_feedback = len(self.feedback_history)
        feedback_types = {}

        for feedback in self.feedback_history.values():
            feedback_type = feedback.feedback_type.value
            feedback_types[feedback_type] = feedback_types.get(feedback_type, 0) + 1

        return {
            "total_feedback": total_feedback,
            "feedback_types": feedback_types,
            "acceptance_rate": self.get_acceptance_rate(),
            "source_acceptance_rates": {
                source.value: self.get_acceptance_rate(source)
                for source in RecommendationSource
                if self.suggestion_counts.get(source, 0) > 0
            },
        }

    def update_settings(self, settings: RecommendationSettings) -> None:
        """
        Update recommendation engine settings.

        Args:
            settings: New settings
        """
        self.settings = settings

    def clear_cache(self) -> None:
        """Clear the suggestion cache."""
        self.recent_suggestions = {}

    def save_state(self, file_path: str) -> None:
        """
        Save the engine state to a file.

        Args:
            file_path: Path to save the state to
        """
        # Create the state dictionary
        state = {
            "settings": self.settings.model_dump() if self.settings else {},
            "suggestion_counts": {s.value: c for s, c in self.suggestion_counts.items()},
            "acceptance_counts": {s.value: c for s, c in self.acceptance_counts.items()},
            "feedback_history": {str(k): v.model_dump() for k, v in self.feedback_history.items()},
        }

        # Save to file
        import json

        with open(file_path, "w") as f:
            json.dump(state, f, indent=2, default=str)

    def load_state(self, file_path: str) -> None:
        """
        Load the engine state from a file.

        Args:
            file_path: Path to load the state from
        """
        import json

        with open(file_path) as f:
            state = json.load(f)

        # Load settings
        if "settings" in state:
            self.settings = RecommendationSettings(**state["settings"])

        # Load statistics
        if "suggestion_counts" in state:
            self.suggestion_counts = {RecommendationSource(s): c for s, c in state["suggestion_counts"].items()}

        if "acceptance_counts" in state:
            self.acceptance_counts = {RecommendationSource(s): c for s, c in state["acceptance_counts"].items()}

        # Load feedback history
        if "feedback_history" in state:
            self.feedback_history = {
                uuid.UUID(k): RecommendationFeedback(**v) for k, v in state["feedback_history"].items()
            }
