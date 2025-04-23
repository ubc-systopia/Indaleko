"""
Test script for the Contextual Query Recommendation Engine.

This module provides tests for the recommendation engine components,
including individual recommendation providers and the main engine.

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

import argparse
import logging
import os
import sys

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
    RecommendationSettings,
    RecommendationSource,
)
from query.context.recommendations.activity_context import ActivityContextRecommender
from query.context.recommendations.engine import RecommendationEngine
from query.context.recommendations.entity_relationship import (
    EntityRelationshipRecommender,
)
from query.context.recommendations.query_history import QueryHistoryRecommender
from query.context.recommendations.temporal_pattern import TemporalPatternRecommender

# pylint: enable=wrong-import-position


def test_query_history_recommender():
    """Test the QueryHistoryRecommender."""
    print("\n===== Testing QueryHistoryRecommender =====")
    recommender = QueryHistoryRecommender(debug=True)

    # Test with a current query
    suggestions = recommender.generate_suggestions(
        current_query="Find documents about Indaleko", max_suggestions=3,
    )

    print(f"Generated {len(suggestions)} suggestions:")
    for i, suggestion in enumerate(suggestions):
        print(
            f"{i+1}. {suggestion.query_text} (confidence: {suggestion.confidence:.2f})",
        )
        print(f"   Rationale: {suggestion.rationale}")
        print(f"   Tags: {suggestion.tags}")
        print()

    # Test feedback
    if suggestions:
        print("Testing feedback:")
        recommender.update_from_feedback(
            suggestion=suggestions[0], feedback=FeedbackType.ACCEPTED, result_count=5,
        )
        print("Feedback recorded")


def test_activity_context_recommender():
    """Test the ActivityContextRecommender."""
    print("\n===== Testing ActivityContextRecommender =====")

    # Initialize database config for the recommender
    try:
        from db.db_config import IndalekoDBConfig

        db_config = IndalekoDBConfig()
        print("Database connection established")
    except Exception as e:
        print(f"Failed to establish database connection: {e}")
        print("Continuing with mock data...")
        db_config = None

    # Create the recommender with actual database connection
    recommender = ActivityContextRecommender(db_config=db_config, debug=True)

    # Generate suggestions
    print("Generating suggestions from activities...")
    suggestions = recommender.generate_suggestions(max_suggestions=5)

    print(f"Generated {len(suggestions)} suggestions:")
    for i, suggestion in enumerate(suggestions):
        print(
            f"{i+1}. {suggestion.query_text} (confidence: {suggestion.confidence:.2f})",
        )
        print(f"   Rationale: {suggestion.rationale}")
        print(
            f"   Source context: {suggestion.source_context.get('activity_type', 'unknown')}",
        )
        print(f"   Tags: {suggestion.tags}")
        print()

    # Test feedback
    if suggestions:
        print("Testing feedback:")
        recommender.update_from_feedback(
            suggestion=suggestions[0], feedback=FeedbackType.HELPFUL, result_count=7,
        )
        print("Feedback recorded")

        # Generate new suggestions to see effect of feedback
        print("\nGenerating new suggestions after feedback:")
        new_suggestions = recommender.generate_suggestions(max_suggestions=5)

        print(f"Generated {len(new_suggestions)} suggestions after feedback:")
        for i, suggestion in enumerate(new_suggestions):
            print(
                f"{i+1}. {suggestion.query_text} (confidence: {suggestion.confidence:.2f})",
            )
            print(f"   Rationale: {suggestion.rationale}")
            print(
                f"   Source context: {suggestion.source_context.get('activity_type', 'unknown')}",
            )
            print()

        # Check if feedback affected confidence scores
        for i, new_suggestion in enumerate(new_suggestions):
            if (
                i < len(suggestions)
                and new_suggestion.query_text == suggestions[i].query_text
            ):
                confidence_change = (
                    new_suggestion.confidence - suggestions[i].confidence
                )
                if abs(confidence_change) > 0.01:
                    print(f"Suggestion confidence changed by {confidence_change:.2f}")
                    print(f"   From: {suggestions[i].confidence:.2f}")
                    print(f"   To: {new_suggestion.confidence:.2f}")
                    print()


def test_entity_relationship_recommender():
    """Test the EntityRelationshipRecommender."""
    print("\n===== Testing EntityRelationshipRecommender =====")

    # Create recommender
    recommender = EntityRelationshipRecommender(debug=True)

    # Test with a query and context
    current_query = "Find files shared with Alice"
    context_data = {
        "entities": [
            {
                "id": str(uuid.uuid4()),
                "name": "Quarterly Report",
                "type": "file",
                "confidence": 0.9,
                "source": "recent_activity",
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Marketing",
                "type": "project",
                "confidence": 0.8,
                "source": "recent_activity",
            },
        ],
    }

    print(f"Generating suggestions for query: '{current_query}'")
    print(f"Context entities: {len(context_data['entities'])}")

    # Generate suggestions
    suggestions = recommender.generate_suggestions(
        current_query=current_query, context_data=context_data, max_suggestions=5,
    )

    print(f"Generated {len(suggestions)} suggestions:")
    for i, suggestion in enumerate(suggestions):
        print(
            f"{i+1}. {suggestion.query_text} (confidence: {suggestion.confidence:.2f})",
        )
        print(f"   Rationale: {suggestion.rationale}")
        print(
            f"   Entity type: {suggestion.source_context.get('entity_type', 'unknown')}",
        )
        if "relationship" in suggestion.source_context:
            print(
                f"   Relationship: {suggestion.source_context['relationship']} with {suggestion.source_context.get('source_entity', 'unknown')}",
            )
        print(f"   Tags: {suggestion.tags}")
        print()

    # Test feedback
    if suggestions:
        print("Testing feedback:")
        recommender.update_from_feedback(
            suggestion=suggestions[0], feedback=FeedbackType.ACCEPTED, result_count=5,
        )
        print("Feedback recorded")

        # Generate new suggestions to see effect of feedback
        print("\nGenerating new suggestions after feedback:")
        new_suggestions = recommender.generate_suggestions(
            current_query=current_query, context_data=context_data, max_suggestions=5,
        )

        print(f"Generated {len(new_suggestions)} suggestions after feedback:")
        for i, suggestion in enumerate(new_suggestions):
            print(
                f"{i+1}. {suggestion.query_text} (confidence: {suggestion.confidence:.2f})",
            )
            print(f"   Rationale: {suggestion.rationale}")

            # Check if confidence changed
            for orig in suggestions:
                if suggestion.query_text == orig.query_text:
                    confidence_change = suggestion.confidence - orig.confidence
                    if abs(confidence_change) > 0.01:
                        print(f"   Confidence change: {confidence_change:+.2f}")
            print()


def test_temporal_pattern_recommender():
    """Test the TemporalPatternRecommender."""
    print("\n===== Testing TemporalPatternRecommender =====")

    # Create recommender
    recommender = TemporalPatternRecommender(debug=True)

    # Test specific times
    test_times = [
        # Weekday morning
        datetime(2025, 4, 21, 9, 0, tzinfo=timezone.utc),  # Monday 9 AM
        # Weekday end of day
        datetime(2025, 4, 21, 17, 0, tzinfo=timezone.utc),  # Monday 5 PM
        # Friday afternoon
        datetime(2025, 4, 25, 16, 0, tzinfo=timezone.utc),  # Friday 4 PM
    ]

    for test_time in test_times:
        print(f"\nTesting time: {test_time.strftime('%A, %I:%M %p')}")

        # Create context with current time
        context_data = {"current_time": test_time.isoformat()}

        # Generate suggestions
        suggestions = recommender.generate_suggestions(
            context_data=context_data, max_suggestions=3,
        )

        print(f"Generated {len(suggestions)} suggestions:")
        for i, suggestion in enumerate(suggestions):
            print(
                f"{i+1}. {suggestion.query_text} (confidence: {suggestion.confidence:.2f})",
            )
            print(f"   Rationale: {suggestion.rationale}")

            # Show time window
            time_window = suggestion.source_context.get("time_window", {})
            if "days_of_week" in time_window:
                days = [calendar.day_name[d] for d in time_window["days_of_week"]]
                print(f"   Days: {', '.join(days)}")
            if "hour_range" in time_window:
                hr = time_window["hour_range"]
                print(f"   Hours: {hr[0]}:00 - {hr[1]}:00")

            print(
                f"   Match score: {suggestion.source_context.get('match_score', 0):.2f}",
            )
            print(f"   Tags: {suggestion.tags}")
            print()

    # Test feedback
    if suggestions:
        print("Testing feedback:")
        recommender.update_from_feedback(
            suggestion=suggestions[0], feedback=FeedbackType.ACCEPTED, result_count=7,
        )
        print("Feedback recorded")

        # Generate new suggestions to see effect of feedback
        print("\nGenerating suggestions after feedback:")
        new_suggestions = recommender.generate_suggestions(
            context_data=context_data, max_suggestions=3,
        )

        print(f"Generated {len(new_suggestions)} suggestions after feedback:")
        for i, suggestion in enumerate(new_suggestions):
            print(
                f"{i+1}. {suggestion.query_text} (confidence: {suggestion.confidence:.2f})",
            )
            print(f"   Rationale: {suggestion.rationale}")

            # Check if this matches an original suggestion to see confidence change
            for orig in suggestions:
                if suggestion.query_text == orig.query_text:
                    confidence_change = suggestion.confidence - orig.confidence
                    if abs(confidence_change) > 0.01:
                        print(f"   Confidence change: {confidence_change:+.2f}")
            print()


def test_recommendation_engine():
    """Test the RecommendationEngine."""
    print("\n===== Testing RecommendationEngine =====")
    engine = RecommendationEngine(debug=True)

    # Generate recommendations
    recommendations = engine.get_recommendations(
        current_query="Find documents about Indaleko", max_results=5,
    )

    print(f"Generated {len(recommendations)} recommendations:")
    for i, recommendation in enumerate(recommendations):
        print(
            f"{i+1}. {recommendation.query_text} (confidence: {recommendation.confidence:.2f})",
        )
        print(f"   Source: {recommendation.source.value}")
        print(f"   Rationale: {recommendation.rationale}")
        print()

    # Test feedback
    if recommendations:
        print("Testing feedback:")
        engine.record_feedback(
            suggestion_id=recommendations[0].suggestion_id,
            feedback=FeedbackType.ACCEPTED,
            result_count=3,
        )
        print("Feedback recorded")

    # Check acceptance rate
    print("\nAcceptance rates:")
    for source in RecommendationSource:
        rate = engine.get_acceptance_rate(source)
        print(f"{source.value}: {rate:.2f}")

    # Test updating settings
    print("\nUpdating settings:")
    new_settings = RecommendationSettings(
        max_suggestions=10,
        min_confidence=0.6,
        source_weights={
            RecommendationSource.QUERY_HISTORY: 0.8,
            RecommendationSource.ACTIVITY_CONTEXT: 1.2,
        },
    )
    engine.update_settings(new_settings)
    print("Settings updated")

    # Generate recommendations again
    print("\nGenerating recommendations with new settings:")
    new_recommendations = engine.get_recommendations(
        current_query="Find documents about Indaleko", max_results=5,
    )

    print(f"Generated {len(new_recommendations)} recommendations:")
    for i, recommendation in enumerate(new_recommendations):
        print(
            f"{i+1}. {recommendation.query_text} (confidence: {recommendation.confidence:.2f})",
        )
        print(f"   Source: {recommendation.source.value}")
        print(f"   Rationale: {recommendation.rationale}")
        print()


def main():
    """Main entry point for testing."""
    parser = argparse.ArgumentParser(
        description="Test the recommendation engine components",
    )
    parser.add_argument(
        "--history", action="store_true", help="Test query history recommender",
    )
    parser.add_argument(
        "--activity", action="store_true", help="Test activity context recommender",
    )
    parser.add_argument(
        "--entity", action="store_true", help="Test entity relationship recommender",
    )
    parser.add_argument(
        "--temporal", action="store_true", help="Test temporal pattern recommender",
    )
    parser.add_argument(
        "--engine", action="store_true", help="Test recommendation engine",
    )
    parser.add_argument("--all", action="store_true", help="Test all components")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level)

    # If no specific tests are requested, run all tests
    run_all = args.all or not (
        args.history or args.activity or args.entity or args.temporal or args.engine
    )

    if args.history or run_all:
        test_query_history_recommender()

    if args.activity or run_all:
        test_activity_context_recommender()

    if args.entity or run_all:
        test_entity_relationship_recommender()

    if args.temporal or run_all:
        test_temporal_pattern_recommender()

    if args.engine or run_all:
        test_recommendation_engine()


if __name__ == "__main__":
    main()
