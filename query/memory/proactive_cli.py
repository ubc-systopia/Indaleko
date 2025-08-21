"""
CLI integration for the Proactive Archivist system.

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

from datetime import UTC, datetime


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.memory.archivist_memory import ArchivistMemory
from query.memory.proactive_archivist import (
    ProactiveArchivist,
    ProactiveSuggestion,
    SuggestionType,
)


# pylint: enable=wrong-import-position


class ProactiveCliIntegration:
    """Integrates the Proactive Archivist capabilities with the Indaleko CLI."""

    def __init__(self, cli_instance, archivist_memory=None, proactive_archivist=None) -> None:
        """
        Initialize the CLI integration for Proactive Archivist.

        Args:
            cli_instance: The CLI instance to integrate with
            archivist_memory: An existing ArchivistMemory instance, or None to create a new one
            proactive_archivist: An existing ProactiveArchivist instance, or None to create a new one
        """
        self.cli = cli_instance
        self.memory = archivist_memory or ArchivistMemory(self.cli.db_config)
        self.proactive = proactive_archivist or ProactiveArchivist(self.memory)

        # Suggestion display settings
        self.show_suggestions = True
        self.suggestion_limit = 3
        self.last_suggestions_time = None
        self.suggestion_cooldown_minutes = 30

        # Record context information
        self.context = {
            "session_start": datetime.now(UTC),
            "last_queries": [],
            "current_goal": None,
            "current_topics": [],
        }

        # Add commands to CLI
        self.commands = {
            "/proactive": self.show_proactive_help,
            "/suggest": self.show_suggestions_cmd,
            "/feedback": self.provide_feedback,
            "/patterns": self.view_patterns,
            "/insights": self.view_insights,
            "/priorities": self.manage_priorities,
            "/disable": self.disable_suggestions,
            "/enable": self.enable_suggestions,
            "/cross-source": self.show_cross_source_status,
            "/cross-enable": self.enable_cross_source,
            "/cross-disable": self.disable_cross_source,
            "/cross-analyze": self.force_cross_source_analysis,
        }

    def handle_command(self, command) -> bool:
        """
        Handle a proactive-related command.

        Args:
            command: The command to handle

        Returns:
            bool: True if the command was handled, False otherwise
        """
        parts = command.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd in self.commands:
            self.commands[cmd](args)
            return True

        return False

    def show_proactive_help(self, args) -> None:
        """Show help for proactive commands."""

    def check_suggestions(self, context_update=None) -> None:
        """
        Check if it's time to show suggestions and display them if appropriate.

        Args:
            context_update: Optional updated context information
        """
        if not self.show_suggestions:
            return

        # Update context if provided
        if context_update:
            self.context.update(context_update)

        # Only show suggestions once per cooldown period
        now = datetime.now(UTC)
        if (
            self.last_suggestions_time
            and (now - self.last_suggestions_time).total_seconds() < self.suggestion_cooldown_minutes * 60
        ):
            return

        # Generate new suggestions
        suggestions = self.proactive.generate_suggestions(self.context)

        # Show top suggestions
        if suggestions:
            self._display_suggestions(suggestions[: self.suggestion_limit])
            self.last_suggestions_time = now

    def _display_suggestions(self, suggestions: list[ProactiveSuggestion]) -> None:
        """
        Display suggestions to the user.

        Args:
            suggestions: List of suggestions to display
        """
        if not suggestions:
            return


        for i, suggestion in enumerate(suggestions, 1):
            {
                "low": "📌",
                "medium": "⭐",
                "high": "🔥",
                "critical": "⚠️",
            }.get(suggestion.priority, "📌")


            # Add a tip about the feedback command
            if i == len(suggestions):
                pass

    def show_suggestions_cmd(self, args) -> None:
        """Force display of suggestions."""
        suggestions = self.proactive.generate_suggestions(self.context)

        if not suggestions:
            return

        self._display_suggestions(
            suggestions[:5],
        )  # Show more when explicitly requested
        self.last_suggestions_time = datetime.now(UTC)

    def provide_feedback(self, args) -> None:
        """
        Process feedback on a suggestion.

        Args:
            args: Format should be "<suggestion_number> <positive|negative>"
        """
        if not args:
            return

        parts = args.split(maxsplit=1)
        if len(parts) != 2:
            return

        try:
            num = int(parts[0]) - 1  # Convert to 0-based index
            feedback_type = parts[1].lower()

            if feedback_type not in ["positive", "negative"]:
                return

            if not self.proactive.data.active_suggestions or num >= len(
                self.proactive.data.active_suggestions,
            ):
                return

            suggestion = self.proactive.data.active_suggestions[num]

            # Apply feedback
            feedback_value = 1.0 if feedback_type == "positive" else -1.0
            self.proactive.record_user_feedback(
                suggestion.suggestion_id,
                feedback_value,
            )

            # Confirm to user
            if feedback_type == "positive":

                # If it's a query suggestion, offer to run it
                if suggestion.suggestion_type == SuggestionType.QUERY and suggestion.related_queries:
                    suggestion.related_queries[0]
            else:
                pass

        except ValueError:
            pass

    def view_patterns(self, args) -> None:
        """View detected temporal patterns."""
        patterns = self.proactive.data.temporal_patterns

        if not patterns:
            return


        for _i, pattern in enumerate(
            sorted(patterns, key=lambda p: p.confidence, reverse=True),
            1,
        ):

            # Print timeframe details
            if pattern.pattern_type == "daily":
                pass
            elif pattern.pattern_type == "weekly":
                [
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                    "Sunday",
                ][pattern.timeframe.get("day_of_week", 0)]
            elif pattern.pattern_type == "monthly":
                pass

            if pattern.associated_actions:
                pass


    def view_insights(self, args) -> None:
        """View insights derived from proactive analysis."""
        # Get insights from archivist memory
        insights = self.memory.get_most_relevant_insights(
            "",
            10,
        )  # Get up to 10 insights

        if not insights:
            return

        # Filter for insights from proactive analysis
        proactive_insights = [i for i in insights if i.category in ["temporal", "sequential", "pattern"]]

        if not proactive_insights:
            return


        for _i, _insight in enumerate(proactive_insights, 1):
            pass

    def manage_priorities(self, args) -> None:
        """Manage suggestion type priorities."""
        if args:
            # Handle sub-commands
            parts = args.split(maxsplit=2)
            if len(parts) >= 2:
                suggestion_type = parts[0].upper()
                threshold_str = parts[1]

                # Validate suggestion type
                try:
                    suggestion_type = SuggestionType(suggestion_type.lower())
                except ValueError:
                    return

                # Update threshold
                try:
                    threshold = float(threshold_str)
                    if 0.0 <= threshold <= 1.0:
                        self.proactive.data.suggestion_thresholds[suggestion_type] = threshold
                    else:
                        pass
                except ValueError:
                    pass

                return

        # Display current thresholds

        for suggestion_type, threshold in sorted(
            self.proactive.data.suggestion_thresholds.items(),
        ):
            pass


    def disable_suggestions(self, args) -> None:
        """Disable proactive suggestions."""
        self.show_suggestions = False

    def enable_suggestions(self, args) -> None:
        """Enable proactive suggestions."""
        self.show_suggestions = True
        self.last_suggestions_time = None  # Reset cooldown

        # Show suggestions immediately
        self.show_suggestions_cmd("")

    def show_cross_source_status(self, args) -> None:
        """Show the status of cross-source pattern detection."""
        # Show last analysis time if available
        if self.proactive.data.last_cross_source_analysis:
            last_time = self.proactive.data.last_cross_source_analysis
            now = datetime.now(UTC)
            time_diff = now - last_time
            hours_ago = time_diff.total_seconds() / 3600

            if hours_ago < 1:
                f"{int(time_diff.total_seconds() / 60)} minutes ago"
            elif hours_ago < 24:
                f"{int(hours_ago)} hours ago"
            else:
                int(hours_ago / 24)

        else:
            pass

        # Show patterns and correlations if available
        if hasattr(self.proactive, "cross_source_detector"):
            len(self.proactive.cross_source_detector.data.patterns)
            len(self.proactive.cross_source_detector.data.correlations)

            # Show data sources with events
            sources = self.proactive.cross_source_detector.data.source_statistics
            if sources:
                for stats in sources.values():
                    if stats["event_count"] > 0:
                        pass

    def enable_cross_source(self, args) -> None:
        """Enable cross-source pattern detection."""
        self.proactive.data.cross_source_enabled = True

    def disable_cross_source(self, args) -> None:
        """Disable cross-source pattern detection."""
        self.proactive.data.cross_source_enabled = False

    def force_cross_source_analysis(self, args) -> None:
        """Force a cross-source pattern analysis."""
        try:
            # Run the analysis
            self.proactive.analyze_cross_source_patterns()

            # Show results
            self.show_cross_source_status("")

            # Show new suggestions if any
            cross_source_suggestions = [
                s
                for s in self.proactive.data.active_suggestions
                if "correlation_id" in s.context or "pattern_id" in s.context
            ]

            if cross_source_suggestions:
                self._display_suggestions(cross_source_suggestions[:3])
            else:
                pass

        except Exception:
            pass

    def update_context_with_query(self, query_text, results=None) -> None:
        """
        Update context with a new query.

        Args:
            query_text: The query text
            results: Optional results information
        """
        # Update recent queries list
        self.context["last_queries"] = [query_text, *self.context.get("last_queries", [])[:4]]

        # Extract topics from query
        topics = self._extract_topics_from_query(query_text)
        if topics:
            self.context["current_topics"] = topics

        # Update context with results info if provided
        if results:
            self.context["last_results_count"] = len(results) if hasattr(results, "__len__") else 0

        # Check if we should show suggestions after this query
        # Don't show after every query to avoid being annoying
        if random.random() < 0.3:  # 30% chance to show suggestions after a query
            self.check_suggestions(self.context)

    def _extract_topics_from_query(self, query_text):
        """
        Extract potential topics from a query.

        Args:
            query_text: The query text

        Returns:
            List of potential topics
        """
        # Simple keyword extraction (this could be more sophisticated)
        topics = []

        # Check against known topics
        for topic in self.memory.memory.semantic_topics:
            if topic.lower() in query_text.lower():
                topics.append(topic)

        return topics

    def analyze_session(self, query_history=None) -> None:
        """
        Analyze the current session and update patterns.

        Args:
            query_history: Optional query history to analyze
        """
        if query_history:
            self.proactive.analyze_session(query_history, self.context)

        # Reset context for next session
        self.context = {
            "session_start": datetime.now(UTC),
            "last_queries": [],
            "current_goal": self.context.get("current_goal"),
            "current_topics": self.context.get("current_topics", []),
        }

    def get_initial_suggestions(self):
        """
        Get initial suggestions to show at the start of a session.

        Returns:
            List of suggestions
        """
        # Generate suggestions based on current context
        suggestions = self.proactive.generate_suggestions(self.context)

        # Filter to only show high-priority or goal-related suggestions
        important_suggestions = [
            s
            for s in suggestions
            if s.priority in ["high", "critical"] or s.suggestion_type == SuggestionType.GOAL_PROGRESS
        ]

        # Only show a limited number to avoid overwhelming the user
        return important_suggestions[:2]


def main() -> None:
    """Test the Proactive CLI integration."""
    # This would normally be integrated with the main CLI
    from query.memory.archivist_memory import ArchivistMemory

    # Create a simple mock CLI class
    class MockCLI:
        def __init__(self) -> None:
            from db import IndalekoDBConfig

            self.db_config = IndalekoDBConfig()
            self.query_history = None

    # Initialize components
    cli = MockCLI()
    memory = ArchivistMemory(cli.db_config)
    proactive = ProactiveArchivist(memory)
    cli_integration = ProactiveCliIntegration(cli, memory, proactive)

    # Add some test data
    memory.add_long_term_goal(
        "Document Organization",
        "Organize and tag work documents",
    )
    memory.add_insight(
        "temporal",
        "User typically searches for work documents on Monday mornings",
        0.8,
    )

    # Test commands
    cli_integration.show_proactive_help("")

    # Show initial suggestions
    initial_suggestions = cli_integration.get_initial_suggestions()
    if initial_suggestions:
        cli_integration._display_suggestions(initial_suggestions)
    else:
        pass

    # Simulate a query
    cli_integration.update_context_with_query(
        "Find recent work documents about budgets",
    )

    # Show suggestions
    cli_integration.show_suggestions_cmd("")


if __name__ == "__main__":
    main()
