"""
CLI integration for the Archivist memory system.

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
import sys
import uuid

from datetime import datetime


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.memory.archivist_memory import ArchivistMemory


# Import Query Context Integration components if available
try:
    from query.context.activity_provider import QueryActivityProvider
    from query.context.navigation import QueryNavigator
    from query.context.relationship import QueryRelationshipDetector, RelationshipType

    HAS_QUERY_CONTEXT = True
except ImportError:
    HAS_QUERY_CONTEXT = False
# pylint: enable=wrong-import-position


class ArchivistCliIntegration:
    """Integrates Archivist memory capabilities with the Indaleko Query CLI."""

    def __init__(self, cli_instance, archivist_memory=None) -> None:
        """
        Initialize the CLI integration for Archivist memory.

        Args:
            cli_instance: The CLI instance to integrate with
            archivist_memory: An existing ArchivistMemory instance, or None to create a new one
        """
        self.cli = cli_instance
        self.memory = archivist_memory or ArchivistMemory(self.cli.db_config)

        # Initialize Query Context components if available
        self.query_context_provider = None
        self.query_navigator = None
        self.query_relationship_detector = None

        if HAS_QUERY_CONTEXT:
            # Check if CLI already has these components
            if hasattr(self.cli, "query_context_integration") and self.cli.query_context_integration:
                self.query_context_provider = self.cli.query_context_integration
            elif hasattr(self.cli, "args") and hasattr(self.cli.args, "debug"):
                self.query_context_provider = QueryActivityProvider(
                    debug=self.cli.args.debug,
                )

            if hasattr(self.cli, "query_navigator") and self.cli.query_navigator:
                self.query_navigator = self.cli.query_navigator
            elif hasattr(self.cli, "args") and hasattr(self.cli.args, "debug"):
                self.query_navigator = QueryNavigator(debug=self.cli.args.debug)

            if hasattr(self.cli, "query_relationship_detector") and self.cli.query_relationship_detector:
                self.query_relationship_detector = self.cli.query_relationship_detector
            elif hasattr(self.cli, "args") and hasattr(self.cli.args, "debug"):
                self.query_relationship_detector = QueryRelationshipDetector(
                    debug=self.cli.args.debug,
                )

        # Add the memory commands to the CLI
        self.commands = {
            "/memory": self.show_memory_help,
            "/forward": self.generate_forward_prompt,
            "/load": self.load_forward_prompt,
            "/goals": self.manage_goals,
            "/insights": self.view_insights,
            "/topics": self.view_topics,
            "/strategies": self.view_strategies,
            "/save": self.save_memory,
            "/query-insights": self.view_query_insights,
        }

    def handle_command(self, command) -> bool:
        """
        Handle a memory-related command.

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

    def show_memory_help(self, args) -> None:
        """Show help for memory commands."""
        if HAS_QUERY_CONTEXT:
            pass

    def generate_forward_prompt(self, args) -> None:
        """Generate and display a forward prompt."""
        # Update memory with recent query history first
        if hasattr(self.cli, "query_history"):
            self.memory.distill_knowledge(
                self.cli.query_history,
                self.cli.query_history,
            )

        # Generate and display prompt
        prompt = self.memory.generate_forward_prompt()

        # Save to file if requested
        if args and args.lower().startswith("save"):
            filename = args.split(maxsplit=1)[1] if len(args.split()) > 1 else "archivist_prompt.txt"
            with open(filename, "w") as f:
                f.write(prompt)

    def load_forward_prompt(self, args) -> None:
        """Load a forward prompt."""
        if args:
            # Load from file
            try:
                with open(args) as f:
                    prompt = f.read()
                self.memory.update_from_forward_prompt(prompt)
                self.memory.save_memory()
            except Exception:
                pass
        else:
            # Interactive load
            lines = []
            while True:
                line = input()
                if line == "---":
                    break
                lines.append(line)

            if lines:
                prompt = "\n".join(lines)
                self.memory.update_from_forward_prompt(prompt)
                self.memory.save_memory()

    def manage_goals(self, args) -> None:
        """Interface for managing long-term goals."""
        if args:
            # Handle sub-commands
            parts = args.split(maxsplit=1)
            subcmd = parts[0].lower()

            if subcmd == "add" and len(parts) > 1:
                # Add a new goal
                goal_parts = parts[1].split(" - ", 1)
                if len(goal_parts) == 2:
                    name, description = goal_parts
                    self.memory.add_long_term_goal(name, description)
                    self.memory.save_memory()
                else:
                    pass

            elif subcmd == "progress" and len(parts) > 1:
                # Update goal progress
                goal_parts = parts[1].split(maxsplit=1)
                if len(goal_parts) == 2:
                    name, progress_str = goal_parts
                    try:
                        progress = float(progress_str) / 100.0
                        self.memory.update_goal_progress(name, progress)
                        self.memory.save_memory()
                    except ValueError:
                        pass
                else:
                    pass
            else:
                pass
        else:
            # Display goals
            goals = self.memory.memory.long_term_goals
            if not goals:
                return

            for _i, _goal in enumerate(goals, 1):
                pass


    def view_insights(self, args) -> None:
        """View insights about search patterns."""
        insights = self.memory.memory.insights
        if not insights:
            return

        insights = sorted(insights, key=lambda x: x.confidence, reverse=True)

        for _i, insight in enumerate(insights, 1):
            if insight.supporting_evidence:
                pass

    def view_topics(self, args) -> None:
        """View topics of interest."""
        topics = self.memory.memory.semantic_topics
        if not topics:
            return

        for _topic, _importance in sorted(
            topics.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            pass

    def view_strategies(self, args) -> None:
        """View effective search strategies."""
        strategies = self.memory.memory.effective_strategies
        if not strategies:
            return

        for strategy in sorted(strategies, key=lambda x: x.success_rate, reverse=True):
            if strategy.applicable_contexts:
                pass

    def save_memory(self, args) -> None:
        """Save the current memory state."""
        self.memory.save_memory()

    def view_query_insights(self, args) -> None:
        """View insights from Query Context Integration."""
        if not HAS_QUERY_CONTEXT:
            return

        if not self.query_context_provider or not self.query_navigator:
            return

        # Get recent query activities
        recent_activities = self.query_context_provider.get_recent_query_activities(
            limit=10,
        )
        if not recent_activities:
            return

        # Display query history summary
        for _i, activity in enumerate(recent_activities, 1):
            activity.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            if activity.result_count is not None:
                str(activity.result_count)



            # If this query has a previous query, show the relationship
            if activity.previous_query_id:
                prev_activity = self.query_context_provider.get_query_activity(
                    activity.previous_query_id,
                )
                if prev_activity:
                    pass


        # Check if query paths should be analyzed
        if self.query_navigator and args and "analyze" in args:

            # Get the most recent query activity
            latest_activity = recent_activities[0]

            # Get the query path
            path = self.query_navigator.get_query_path(
                latest_activity.query_id,
                max_depth=5,
            )
            if path:
                for _i, step in enumerate(path, 1):
                    step.get("relationship_type", "initial")
                    step.get("query_text", "Unknown")
                    datetime.fromisoformat(
                        step.get("timestamp", datetime.now().isoformat()),
                    ).strftime("%H:%M:%S")


                # Get branches if any
                if len(path) > 1:
                    pivot_point = path[1].get("query_id")  # Get second query in path
                    if pivot_point:
                        branches = self.query_navigator.get_query_branches(
                            uuid.UUID(pivot_point),
                            max_depth=3,
                        )
                        if len(branches) > 1:  # If there are multiple branches
                            for _i, branch in enumerate(branches, 1):
                                if branch:  # Ensure branch is not empty
                                    pass

            # Add query patterns to Archivist memory
            if self.memory:
                for activity in recent_activities:
                    # Check for relationship patterns
                    if activity.relationship_type:
                        # Create search pattern based on relationship type
                        pattern_type = f"query_{activity.relationship_type}"
                        description = f"User tends to {activity.relationship_type} queries when exploring"
                        examples = [activity.query_text]
                        frequency = 0.7  # Default frequency

                        # Add pattern to memory
                        self._add_query_pattern_to_memory(
                            pattern_type,
                            description,
                            examples,
                            frequency,
                        )

                # Save memory updates
                self.memory.save_memory()

        # Show help for analysis options
        if not args:
            pass

    def _add_query_pattern_to_memory(
        self,
        pattern_type,
        description,
        examples,
        frequency,
    ) -> None:
        """Add a query pattern to the Archivist memory."""
        if not self.memory:
            return

        # Check if pattern already exists
        for pattern in self.memory.memory.search_patterns:
            if pattern.pattern_type == pattern_type:
                # Update existing pattern
                pattern.frequency = (pattern.frequency + frequency) / 2  # Moving average
                pattern.examples = list(set(pattern.examples + examples))[:5]  # Keep up to 5 unique examples
                return

        # Add new pattern
        self.memory.memory.search_patterns.append(
            {
                "pattern_type": pattern_type,
                "description": description,
                "examples": examples[:3],  # Keep up to 3 examples
                "frequency": frequency,
            },
        )

        # Also add as insight
        self.memory.add_insight("query_behavior", description, confidence=0.7)

    def update_from_session(self, query_history) -> None:
        """
        Update the memory with information from the current session.

        Args:
            query_history: The query history from the current session
        """
        self.memory.distill_knowledge(query_history, query_history)

        # Also integrate with Query Context data if available
        if HAS_QUERY_CONTEXT and self.query_context_provider:
            recent_activities = self.query_context_provider.get_recent_query_activities(
                limit=20,
            )

            if recent_activities:
                # Analyze query patterns
                refinement_count = 0
                broadening_count = 0
                pivot_count = 0

                for activity in recent_activities:
                    if activity.relationship_type == RelationshipType.REFINEMENT.value:
                        refinement_count += 1
                    elif activity.relationship_type == RelationshipType.BROADENING.value:
                        broadening_count += 1
                    elif activity.relationship_type == RelationshipType.PIVOT.value:
                        pivot_count += 1

                total = len(recent_activities)
                if total > 0:
                    # Add insights based on dominant patterns
                    if refinement_count / total > 0.3:
                        self.memory.add_insight(
                            "query_behavior",
                            "User frequently refines queries to narrow down results",
                            confidence=min(0.5 + (refinement_count / total), 0.9),
                        )

                    if broadening_count / total > 0.3:
                        self.memory.add_insight(
                            "query_behavior",
                            "User often broadens queries when results are too specific",
                            confidence=min(0.5 + (broadening_count / total), 0.9),
                        )

                    if pivot_count / total > 0.3:
                        self.memory.add_insight(
                            "query_behavior",
                            "User frequently pivots to related topics during exploration",
                            confidence=min(0.5 + (pivot_count / total), 0.9),
                        )

        self.memory.save_memory()
