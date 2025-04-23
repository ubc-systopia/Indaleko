"""
Base classes for recommendation sources in the Contextual Query Recommendation Engine.

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
from abc import ABC, abstractmethod
from typing import Any

from query.context.data_models.recommendation import (
    FeedbackType,
    QuerySuggestion,
    RecommendationSource,
)


class RecommendationProvider(ABC):
    """
    Abstract base class for recommendation sources.

    Each provider is responsible for generating query suggestions
    based on a specific source of information (query history,
    activity context, entity relationships, etc.).
    """

    def __init__(self, source_type: RecommendationSource, debug: bool = False):
        """
        Initialize the recommendation provider.

        Args:
            source_type: The type of recommendation source
            debug: Whether to enable debug output
        """
        self.source_type = source_type
        self.debug = debug

    @abstractmethod
    def generate_suggestions(
        self,
        current_query: str | None = None,
        context_data: dict[str, Any] | None = None,
        max_suggestions: int = 10,
    ) -> list[QuerySuggestion]:
        """
        Generate query suggestions based on the given context.

        Args:
            current_query: The current query, if any
            context_data: Additional context data
            max_suggestions: Maximum number of suggestions to generate

        Returns:
            List of query suggestions
        """

    @abstractmethod
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

    def get_source_type(self) -> RecommendationSource:
        """
        Get the source type for this provider.

        Returns:
            The source type
        """
        return self.source_type

    def calculate_confidence(
        self, factors: dict[str, float], weights: dict[str, float] | None = None,
    ) -> float:
        """
        Calculate confidence score based on weighted factors.

        Args:
            factors: Dictionary of factors and their values (0.0-1.0)
            weights: Optional dictionary of factor weights (defaults to equal weights)

        Returns:
            Confidence score (0.0-1.0)
        """
        if not factors:
            return 0.0

        # Use provided weights or equal weights
        if weights is None:
            weights = {k: 1.0 for k in factors}

        # Ensure all factors have weights
        for k in factors:
            if k not in weights:
                weights[k] = 1.0

        # Calculate weighted sum
        weighted_sum = sum(factors[k] * weights[k] for k in factors if k in weights)
        total_weight = sum(weights[k] for k in factors if k in weights)

        if total_weight == 0:
            return 0.0

        # Return normalized score (0.0-1.0)
        return min(1.0, max(0.0, weighted_sum / total_weight))

    def create_suggestion(
        self,
        query_text: str,
        rationale: str,
        confidence: float,
        source_context: dict[str, Any] | None = None,
        relevance_factors: dict[str, float] | None = None,
        tags: list[str] | None = None,
    ) -> QuerySuggestion:
        """
        Create a query suggestion with the appropriate source type.

        Args:
            query_text: The suggested query text
            rationale: Explanation of why this query is suggested
            confidence: Confidence score (0.0-1.0)
            source_context: Context information from the source
            relevance_factors: Factors contributing to relevance score
            tags: Tags for categorization

        Returns:
            A QuerySuggestion object
        """
        return QuerySuggestion(
            suggestion_id=uuid.uuid4(),
            query_text=query_text,
            rationale=rationale,
            confidence=confidence,
            source=self.source_type,
            source_context=source_context or {},
            relevance_factors=relevance_factors or {},
            tags=tags or [],
        )

    def is_positive_feedback(self, feedback: FeedbackType) -> bool:
        """
        Determine if feedback is positive.

        Args:
            feedback: The feedback type

        Returns:
            True if the feedback is positive, False otherwise
        """
        return feedback in [FeedbackType.ACCEPTED, FeedbackType.HELPFUL]

    def is_negative_feedback(self, feedback: FeedbackType) -> bool:
        """
        Determine if feedback is negative.

        Args:
            feedback: The feedback type

        Returns:
            True if the feedback is negative, False otherwise
        """
        return feedback in [
            FeedbackType.REJECTED,
            FeedbackType.NOT_HELPFUL,
            FeedbackType.IRRELEVANT,
        ]
