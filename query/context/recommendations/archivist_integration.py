"""
Archivist integration for the Contextual Query Recommendation Engine.

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
from datetime import UTC, datetime, timedelta
from typing import Any

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
from query.context.recommendations.engine import RecommendationEngine
from query.memory.archivist_memory import ArchivistMemory
from query.memory.proactive_archivist import (
    ProactiveArchivist,
    ProactiveSuggestion,
    SuggestionPriority,
    SuggestionType,
)

# pylint: enable=wrong-import-position


class RecommendationArchivistIntegration:
    """
    Integrates the Contextual Query Recommendation Engine with the Archivist memory system.

    This class serves as a bridge between the recommendation engine and the Archivist,
    allowing recommendations to be surfaced through the Archivist interface and benefit
    from the Archivist's memory and context awareness.
    """

    def __init__(
        self,
        cli_instance,
        archivist_memory=None,
        proactive_archivist=None,
        recommendation_engine=None,
        debug=False,
    ):
        """
        Initialize the CLI integration for Recommendations with Archivist.

        Args:
            cli_instance: The CLI instance to integrate with
            archivist_memory: An existing ArchivistMemory instance, or None to create a new one
            proactive_archivist: An existing ProactiveArchivist instance, or None to create a new one
            recommendation_engine: An existing RecommendationEngine instance, or None to create a new one
            debug: Whether to enable debug output
        """
        self.cli = cli_instance
        self.debug = debug

        # Initialize or use provided components
        self.memory = archivist_memory or ArchivistMemory(self.cli.db_config)
        self.proactive = proactive_archivist or ProactiveArchivist(self.memory)
        self.recommendation_engine = recommendation_engine or RecommendationEngine(
            debug=self.debug,
        )

        # Settings for integration
        self.settings = {
            "enabled": True,
            "show_on_startup": True,
            "show_with_proactive": True,
            "convert_to_proactive": True,
            "max_display": 5,
            "feedback_to_insights": True,
            "min_confidence": 0.6,
        }

        # Tracking for recommendations
        self.last_recommendations_time = None
        self.recommendation_cooldown_minutes = 15

        # Context information
        self.context = {
            "session_start": datetime.now(UTC),
            "session_queries": [],
            "current_topics": [],
            "entity_counts": {},
        }

        # Register commands
        self.commands = {
            "/recommend": self.show_recommendations,
            "/rconfig": self.configure_recommendations,
            "/rstats": self.show_recommendation_stats,
            "/rfeedback": self.provide_recommendation_feedback,
            "/rtest": self.test_recommendations,
            "/rhelp": self.show_recommendation_help,
        }

    def register_commands(self):
        """Register all recommendation commands with the CLI."""
        for cmd, handler in self.commands.items():
            self.cli.register_command(
                cmd, lambda args, cmd=cmd: self.handle_command(cmd, args),
            )

        # Add help text
        self.cli.append_help_text("\nRecommendation Commands:")
        self.cli.append_help_text("  /recommend           - Show query recommendations")
        self.cli.append_help_text(
            "  /rconfig             - Configure recommendation settings",
        )
        self.cli.append_help_text(
            "  /rstats              - Show recommendation statistics",
        )
        self.cli.append_help_text(
            "  /rfeedback           - Provide feedback on recommendations",
        )
        self.cli.append_help_text(
            "  /rtest               - Test recommendation generation",
        )
        self.cli.append_help_text("  /rhelp               - Show recommendation help")

    def handle_command(self, command, args):
        """
        Handle a recommendation-related command.

        Args:
            command: The command to handle
            args: The command arguments

        Returns:
            The result of the command handler
        """
        if command in self.commands:
            result = self.commands[command](args)
            return result

        return False

    def show_recommendation_help(self, args):
        """Show help for recommendation commands."""
        print("\nRecommendation Engine Commands:")
        print("-----------------------------")
        print("/recommend           - Show current query recommendations")
        print("/rconfig             - Configure recommendation settings")
        print("/rstats              - Show recommendation statistics")
        print("/rfeedback           - Provide feedback on a recommendation")
        print("/rtest               - Test recommendation generation")
        print("/rhelp               - Show this help message")
        print("\nUsage Examples:")
        print(
            "  /recommend                     - Show recommendations based on current context",
        )
        print(
            "  /recommend <query>             - Show recommendations for a specific query",
        )
        print("  /rconfig show                  - Show current configuration")
        print("  /rconfig enabled true|false    - Enable or disable recommendations")
        print("  /rfeedback <num> accept|reject - Provide feedback on a recommendation")

    def show_recommendations(self, args):
        """
        Show recommendations based on the current context or specified query.

        Args:
            args: Optional specific query to get recommendations for
        """
        if not self.settings["enabled"]:
            print(
                "Recommendations are currently disabled. Use /rconfig enabled true to enable.",
            )
            return

        # Use provided query or empty string
        query = args.strip() if args else ""

        # Add query to context if provided
        if query:
            self.context["session_queries"].append(
                {"query": query, "timestamp": datetime.now(UTC)},
            )

        # Generate recommendations
        recommendations = self.recommendation_engine.get_recommendations(
            current_query=query,
            context_data=self._prepare_context_data(),
            max_results=self.settings["max_display"],
        )

        if not recommendations:
            print("No recommendations available at this time.")
            return

        # Display recommendations
        self._display_recommendations(recommendations)

        # Update last recommendations time
        self.last_recommendations_time = datetime.now(UTC)

        # If enabled, convert to proactive suggestions
        if self.settings["convert_to_proactive"]:
            self._convert_to_proactive_suggestions(recommendations)

    def _prepare_context_data(self) -> dict[str, Any]:
        """
        Prepare context data for recommendation generation.

        Returns:
            Dictionary with context data
        """
        # Get Archivist insights
        insights = self.memory.get_most_relevant_insights("", 10)

        # Get topics from Archivist
        topics = self.memory.semantic_topics

        # Prepare context
        context_data = {
            "archivist_insights": [i.model_dump() for i in insights],
            "archivist_topics": topics,
            "recent_queries": [
                q["query"] for q in self.context["session_queries"][-10:]
            ],
            "entity_counts": self.context["entity_counts"],
            "current_topics": self.context["current_topics"],
        }

        # Add effective strategies if available
        if hasattr(self.memory, "effective_strategies"):
            context_data["effective_strategies"] = [
                s.model_dump() for s in self.memory.effective_strategies
            ]

        # Add long-term goals if available
        if hasattr(self.memory, "long_term_goals"):
            context_data["long_term_goals"] = [
                g.model_dump() for g in self.memory.long_term_goals
            ]

        # If proactive is available, add active suggestions
        if (
            self.proactive
            and hasattr(self.proactive, "data")
            and hasattr(self.proactive.data, "active_suggestions")
        ):
            context_data["proactive_suggestions"] = [
                s.model_dump() for s in self.proactive.data.active_suggestions
            ]

        # Handle integration with cross-source patterns if available
        if (
            self.proactive
            and hasattr(self.proactive, "cross_source_detector")
            and self.proactive.cross_source_detector is not None
        ):

            # Add cross-source patterns
            context_data["cross_source_patterns"] = [
                p.model_dump()
                for p in self.proactive.cross_source_detector.data.patterns
            ]

            # Add cross-source correlations
            context_data["cross_source_correlations"] = [
                c.model_dump()
                for c in self.proactive.cross_source_detector.data.correlations
            ]

        return context_data

    def _display_recommendations(self, recommendations: list[QuerySuggestion]):
        """
        Display recommendations to the user.

        Args:
            recommendations: List of recommendations to display
        """
        if not recommendations:
            return

        print("\n🔍 Query Recommendations:")
        print("------------------------")

        for i, recommendation in enumerate(recommendations, 1):
            # Choose icon based on source
            icon = {
                RecommendationSource.QUERY_HISTORY: "📜",
                RecommendationSource.ACTIVITY_CONTEXT: "🏃",
                RecommendationSource.ENTITY_RELATIONSHIP: "🔗",
                RecommendationSource.TEMPORAL_PATTERN: "⏰",
            }.get(recommendation.source, "💡")

            # Display recommendation
            print(f"{i}. {icon} {recommendation.query}")
            print(f"   {recommendation.description}")
            print(
                f"   Source: {recommendation.source.value}, Confidence: {recommendation.confidence:.2f}",
            )

        # Add a tip about the feedback command
        print("\nTip: Use /rfeedback <number> accept|reject to provide feedback")

    def _convert_to_proactive_suggestions(self, recommendations: list[QuerySuggestion]):
        """
        Convert recommendations to proactive suggestions for the Proactive Archivist.

        Args:
            recommendations: List of recommendations to convert
        """
        if not self.proactive or not hasattr(self.proactive, "data"):
            return

        # Map recommendation sources to suggestion types
        source_to_type = {
            RecommendationSource.QUERY_HISTORY: SuggestionType.QUERY,
            RecommendationSource.ACTIVITY_CONTEXT: SuggestionType.QUERY,
            RecommendationSource.ENTITY_RELATIONSHIP: SuggestionType.RELATED_CONTENT,
            RecommendationSource.TEMPORAL_PATTERN: SuggestionType.REMINDER,
        }

        # Convert each recommendation to a proactive suggestion
        for recommendation in recommendations:
            suggestion_type = source_to_type.get(
                recommendation.source, SuggestionType.QUERY,
            )

            # Create ProactiveSuggestion
            suggestion = ProactiveSuggestion(
                suggestion_type=suggestion_type,
                title=f"Suggested search: {recommendation.query}",
                content=recommendation.description,
                expires_at=datetime.now(UTC) + timedelta(days=1),
                priority=SuggestionPriority.MEDIUM,
                confidence=recommendation.confidence,
                context={
                    "from_recommendation": True,
                    "recommendation_id": str(recommendation.suggestion_id),
                    "recommendation_source": recommendation.source.value,
                },
                related_queries=[recommendation.query],
            )

            # Add to proactive suggestions if not a duplicate
            existing_queries = [
                q
                for s in self.proactive.data.active_suggestions
                for q in (s.related_queries or [])
            ]

            if recommendation.query not in existing_queries:
                self.proactive.data.active_suggestions.append(suggestion)

    def configure_recommendations(self, args):
        """
        Configure recommendation settings.

        Args:
            args: Configuration arguments
        """
        if not args:
            print("Usage: /rconfig <setting> <value>")
            print("Available settings: " + ", ".join(self.settings.keys()))
            return

        parts = args.split(maxsplit=1)
        setting = parts[0].lower()

        # Show current configuration
        if setting == "show":
            print("\nRecommendation Configuration:")
            print("--------------------------")
            for key, value in self.settings.items():
                print(f"{key}: {value}")
            return

        # Update a setting
        if len(parts) == 2:
            value = parts[1].lower()

            # Check if setting exists
            if setting not in self.settings:
                print(f"Unknown setting: {setting}")
                print("Available settings: " + ", ".join(self.settings.keys()))
                return

            # Handle boolean settings
            if isinstance(self.settings[setting], bool):
                if value in ["true", "1", "yes", "on"]:
                    self.settings[setting] = True
                    print(f"Setting {setting} enabled")
                elif value in ["false", "0", "no", "off"]:
                    self.settings[setting] = False
                    print(f"Setting {setting} disabled")
                else:
                    print(f"Invalid value for {setting}. Use true or false.")
                    return

            # Handle numeric settings
            elif isinstance(self.settings[setting], (int, float)):
                try:
                    if setting == "min_confidence":
                        num_value = float(value)
                        if 0 <= num_value <= 1:
                            self.settings[setting] = num_value
                            print(f"Setting {setting} set to {num_value}")
                        else:
                            print(f"Value for {setting} must be between 0 and 1")
                    else:
                        num_value = int(value)
                        if num_value > 0:
                            self.settings[setting] = num_value
                            print(f"Setting {setting} set to {num_value}")
                        else:
                            print(f"Value for {setting} must be greater than 0")
                except ValueError:
                    print(f"Invalid numeric value for {setting}")
                    return

            # Update engine settings if needed
            if setting == "min_confidence":
                self.recommendation_engine.settings.min_confidence = self.settings[
                    "min_confidence"
                ]

            return

        # If we got here, show usage
        print("Usage: /rconfig <setting> <value>")
        print("Example: /rconfig enabled true")
        print("Available settings: " + ", ".join(self.settings.keys()))

    def show_recommendation_stats(self, args):
        """
        Show statistics about recommendations.

        Args:
            args: Command arguments
        """
        # Get stats from engine
        stats = self.recommendation_engine.get_feedback_stats()

        print("\nRecommendation Statistics:")
        print("------------------------")

        print(
            f"Total suggestions: {sum(self.recommendation_engine.suggestion_counts.values())}",
        )
        print(f"Total feedback: {stats['total_feedback']}")
        print(f"Overall acceptance rate: {stats['acceptance_rate']:.2f}")

        print("\nBy source:")
        for source, count in self.recommendation_engine.suggestion_counts.items():
            if count > 0:
                acceptance = self.recommendation_engine.acceptance_counts.get(source, 0)
                rate = acceptance / count if count > 0 else 0
                print(
                    f"  {source.value}: {count} suggestions, {acceptance} accepted ({rate:.2f})",
                )

        print("\nFeedback types:")
        for feedback_type, count in stats.get("feedback_types", {}).items():
            print(f"  {feedback_type}: {count}")

    def provide_recommendation_feedback(self, args):
        """
        Process feedback for a recommendation.

        Args:
            args: Format should be "<recommendation_number> <accept|reject>"
        """
        if not args:
            print("Usage: /rfeedback <recommendation_number> accept|reject")
            return

        parts = args.split(maxsplit=1)
        if len(parts) != 2:
            print("Usage: /rfeedback <recommendation_number> accept|reject")
            return

        try:
            num = int(parts[0]) - 1  # Convert to 0-based index
            feedback_type = parts[1].lower()

            if feedback_type not in ["accept", "reject"]:
                print("Feedback must be either 'accept' or 'reject'")
                return

            # Get suggestions from the engine
            suggestions = list(self.recommendation_engine.recent_suggestions.values())
            if not suggestions or num >= len(suggestions):
                print("Invalid recommendation number")
                return

            suggestion = suggestions[num]

            # Record feedback
            feedback = (
                FeedbackType.ACCEPTED
                if feedback_type == "accept"
                else FeedbackType.REJECTED
            )
            self.recommendation_engine.record_feedback(
                suggestion.suggestion_id, feedback,
            )

            # Confirm to user
            if feedback_type == "accept":
                print(
                    "Thanks for accepting the recommendation! I'll show more like this.",
                )

                # Add recommended query to history
                self.context["session_queries"].append(
                    {
                        "query": suggestion.query,
                        "timestamp": datetime.now(UTC),
                        "from_recommendation": True,
                    },
                )

                # Add as insight if enabled
                if self.settings["feedback_to_insights"]:
                    insight_text = (
                        f"User found '{suggestion.query}' to be a valuable query"
                    )
                    self.memory.add_insight("recommendation", insight_text, 0.8)

                # Execute the query if it's an accept
                print(
                    f"\nWould you like to run the recommended query? Type: {suggestion.query}",
                )

            else:
                print(
                    "Thanks for the feedback. I'll show fewer recommendations like this.",
                )

                # Add as insight if enabled
                if self.settings["feedback_to_insights"]:
                    insight_text = (
                        f"User did not find '{suggestion.query}' to be a relevant query"
                    )
                    self.memory.add_insight("recommendation", insight_text, 0.6)

        except ValueError:
            print("Invalid recommendation number")

    def test_recommendations(self, args):
        """
        Test recommendation generation with various sources.

        Args:
            args: Command arguments
        """
        # Parse arguments
        source_filter = None
        if args:
            try:
                source_filter = RecommendationSource(args.lower())
                print(f"Testing recommendations from source: {source_filter.value}")
            except ValueError:
                print(f"Invalid source type: {args}")
                print(
                    f"Valid sources: {', '.join(s.value for s in RecommendationSource)}",
                )
                return

        # Prepare context with enhanced data for testing
        context = self._prepare_context_data()

        # Add test topics if not present
        if not context.get("archivist_topics"):
            context["archivist_topics"] = {"work": 0.8, "personal": 0.7, "finance": 0.5}

        # Add test insights if not present
        if not context.get("archivist_insights"):
            context["archivist_insights"] = [
                {
                    "category": "organization",
                    "insight": "User struggles with finding documents older than 6 months",
                    "confidence": 0.8,
                },
                {
                    "category": "temporal",
                    "insight": "User typically searches for work documents on Monday mornings",
                    "confidence": 0.7,
                },
            ]

        # Add test queries if not present
        if not context.get("recent_queries"):
            context["recent_queries"] = [
                "important documents",
                "project plans",
                "financial reports",
            ]

        # Generate recommendations from all sources or filtered source
        all_recommendations = []

        for source_type, provider in self.recommendation_engine.providers.items():
            if source_filter and source_type != source_filter:
                continue

            print(f"\nTesting {source_type.value} recommendations...")

            try:
                recommendations = provider.generate_suggestions(
                    current_query="", context_data=context, max_suggestions=3,
                )

                if recommendations:
                    print(f"Generated {len(recommendations)} recommendations:")
                    for i, rec in enumerate(recommendations, 1):
                        print(f"  {i}. {rec.query} (confidence: {rec.confidence:.2f})")
                        print(f"     {rec.description}")

                    all_recommendations.extend(recommendations)
                else:
                    print(f"No recommendations generated from {source_type.value}")
            except Exception as e:
                print(f"Error generating recommendations from {source_type.value}: {e}")

        # Display combined recommendations
        if all_recommendations:
            print("\nCombined Recommendations:")
            ranked = sorted(
                all_recommendations, key=lambda x: x.confidence, reverse=True,
            )
            self._display_recommendations(ranked[:5])
        else:
            print("\nNo recommendations were generated from any source.")

    def update_context_with_query(self, query_text, results=None):
        """
        Update context with query information.

        Args:
            query_text: The query text
            results: Optional query results
        """
        # Add to query history
        self.context["session_queries"].append(
            {
                "query": query_text,
                "timestamp": datetime.now(UTC),
                "result_count": len(results) if results is not None else 0,
            },
        )

        # Update entity counts (simple extraction)
        entities = self._extract_entities_from_query(query_text)
        for entity in entities:
            self.context["entity_counts"][entity] = (
                self.context["entity_counts"].get(entity, 0) + 1
            )

        # Extract potential topics
        topics = self._extract_topics_from_query(query_text)
        if topics:
            self.context["current_topics"] = list(
                set(self.context["current_topics"] + topics),
            )

    def _extract_entities_from_query(self, query_text):
        """
        Extract potential entities from a query (simplified).

        Args:
            query_text: The query text

        Returns:
            List of extracted entities
        """
        # Simple extraction - in a real implementation, this would use NLP
        entities = []

        # Extract quoted phrases
        import re

        quoted = re.findall(r'"([^"]*)"', query_text)
        entities.extend(quoted)

        # Extract capitalized words (likely names)
        words = query_text.split()
        for word in words:
            if word and word[0].isupper() and len(word) > 1 and word not in entities:
                entities.append(word)

        return entities

    def _extract_topics_from_query(self, query_text):
        """
        Extract potential topics from a query.

        Args:
            query_text: The query text

        Returns:
            List of potential topics
        """
        # Check against common topics
        common_topics = [
            "work",
            "personal",
            "finance",
            "project",
            "report",
            "presentation",
            "email",
            "document",
            "photo",
            "video",
            "music",
            "code",
        ]

        query_lower = query_text.lower()
        return [topic for topic in common_topics if topic in query_lower]

    def check_show_recommendations(self, query_text=None):
        """
        Check if recommendations should be shown based on current context.

        Args:
            query_text: Optional current query text

        Returns:
            True if recommendations should be shown, False otherwise
        """
        if not self.settings["enabled"]:
            return False

        # Check cooldown period
        now = datetime.now(UTC)
        if (
            self.last_recommendations_time
            and (now - self.last_recommendations_time).total_seconds()
            < self.recommendation_cooldown_minutes * 60
        ):
            return False

        # Update context if query provided
        if query_text:
            self.update_context_with_query(query_text)

        # Simple logic for when to show recommendations:
        # - Show on third query in a session
        # - Show when a topic appears multiple times
        # - Show when we have multiple queries about the same entity

        # Check query count
        if len(self.context["session_queries"]) == 3:
            return True

        # Check for repeated topics
        topic_counts = {}
        for query in self.context["session_queries"]:
            topics = self._extract_topics_from_query(query["query"])
            for topic in topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

        if any(count >= 2 for count in topic_counts.values()):
            return True

        # Check for repeated entities
        if any(count >= 2 for count in self.context["entity_counts"].values()):
            return True

        return False

    def get_recommendations_for_context(self):
        """
        Get recommendations based on the current context.

        Returns:
            List of query suggestions
        """
        return self.recommendation_engine.get_recommendations(
            current_query="",
            context_data=self._prepare_context_data(),
            max_results=self.settings["max_display"],
        )

    def get_startup_recommendations(self):
        """
        Get recommendations to show at startup.

        Returns:
            List of query suggestions
        """
        if not self.settings["enabled"] or not self.settings["show_on_startup"]:
            return []

        # Get recommendations with enhanced context
        context = self._prepare_context_data()

        # Add indicator this is for startup
        context["is_startup"] = True

        return self.recommendation_engine.get_recommendations(
            current_query="",
            context_data=context,
            max_results=2,  # Limit to just a couple for startup
        )

    def add_recommendation_insights_to_archivist(self):
        """Add insights from the recommendation engine to the Archivist memory."""
        if not self.memory:
            return

        # Get acceptance statistics
        for source_type, count in self.recommendation_engine.suggestion_counts.items():
            if count >= 10:  # Only add insights if we have sufficient data
                acceptance = self.recommendation_engine.acceptance_counts.get(
                    source_type, 0,
                )
                acceptance_rate = acceptance / count

                if acceptance_rate >= 0.7:
                    insight = f"User finds {source_type.value} recommendations highly valuable (acceptance rate: {acceptance_rate:.2f})"
                    self.memory.add_insight("recommendation_preferences", insight, 0.8)
                elif acceptance_rate <= 0.3:
                    insight = f"User rarely finds {source_type.value} recommendations valuable (acceptance rate: {acceptance_rate:.2f})"
                    self.memory.add_insight("recommendation_preferences", insight, 0.7)
