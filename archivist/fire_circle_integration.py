"""
Integration between Indaleko's Archivist and Fire Circle.

This module provides integration between Indaleko's Archivist component
and the Fire Circle entity roles, enabling collaborative analysis of
knowledge patterns and query insights.

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
import os
import sys
from typing import Any

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
try:
    from src.firecircle.orchestrator import FireCircleOrchestrator
    from src.firecircle.protocol import EntityRole

    HAS_FIRE_CIRCLE = True
except ImportError:
    HAS_FIRE_CIRCLE = False

from archivist.knowledge_base.data_models.knowledge_pattern import KnowledgePattern
from archivist.knowledge_base.data_models.learning_event import (
    LearningEvent,
    LearningEventType,
)
from archivist.knowledge_base.knowledge_manager import KnowledgeBaseManager
from utils.cli.base import IndalekoBaseCLI

# pylint: enable=wrong-import-position


class FireCircleArchivistIntegration:
    """Integration between Indaleko's Archivist and Fire Circle."""

    def __init__(
        self,
        kb_manager: KnowledgeBaseManager | None = None,
        orchestrator: Any | None = None,
    ):
        """
        Initialize a new Fire Circle Archivist integration.

        Args:
            kb_manager: Optional knowledge base manager
            orchestrator: Optional Fire Circle orchestrator
        """
        if not HAS_FIRE_CIRCLE:
            raise ImportError(
                "Fire Circle is not available. "
                "Please ensure the firecircle package is installed.",
            )

        self.kb_manager = kb_manager or KnowledgeBaseManager()
        self.orchestrator = orchestrator or FireCircleOrchestrator()

    def analyze_pattern(self, pattern: KnowledgePattern) -> dict[str, Any]:
        """
        Analyze a knowledge pattern using multiple perspectives from Fire Circle.

        Args:
            pattern: The knowledge pattern to analyze

        Returns:
            A dictionary containing the analysis results
        """
        # Create a session with all entity roles
        session = self.orchestrator.create_session()

        # Prepare a message describing the knowledge pattern
        message = f"""
        Please analyze this knowledge pattern discovered in the Indaleko knowledge base:

        Pattern ID: {pattern.pattern_id}
        Pattern Type: {pattern.pattern_type}
        Confidence: {pattern.confidence}

        Description: {pattern.description}

        Source Events:
        {json.dumps(pattern.source_events, indent=2)}

        Application Context:
        {json.dumps(pattern.application_context, indent=2)}

        Please provide insights about this pattern, potential applications,
        and suggestions for how it might be used to improve the system's
        understanding of user behavior or data relationships.
        """

        # Process the message through the Fire Circle
        result = self.orchestrator.process_message(
            session_id=session.session_id, message=message, gather_all_perspectives=True,
        )

        # Record the analysis as a learning event
        learning_event = LearningEvent(
            event_type=LearningEventType.pattern_analysis,
            source="fire_circle",
            content={
                "pattern_id": pattern.pattern_id,
                "analysis": {
                    "storyteller": result["perspectives"].get("storyteller"),
                    "analyst": result["perspectives"].get("analyst"),
                    "critic": result["perspectives"].get("critic"),
                    "synthesis": result.get("synthesis"),
                },
            },
            confidence=0.8,
            metadata={
                "session_id": session.session_id,
                "entities_used": list(result["perspectives"].keys()),
            },
        )

        self.kb_manager.record_learning_event(learning_event)

        # Return the analysis results
        return {
            "pattern_id": pattern.pattern_id,
            "perspectives": result["perspectives"],
            "synthesis": result.get("synthesis"),
            "learning_event_id": learning_event.event_id,
        }

    def evaluate_system_effectiveness(self) -> dict[str, Any]:
        """
        Evaluate the overall effectiveness of the knowledge base system.

        Returns:
            A dictionary containing the evaluation results
        """
        # Get recent patterns and learning events
        recent_patterns = self.kb_manager.get_recent_patterns(limit=10)
        recent_events = self.kb_manager.get_recent_learning_events(limit=20)

        # Create a session with all entity roles
        session = self.orchestrator.create_session()

        # Prepare a message for system evaluation
        message = f"""
        Please evaluate the overall effectiveness of the Indaleko knowledge base system
        based on these recent knowledge patterns and learning events:

        Recent Knowledge Patterns:
        {json.dumps([p.dict() for p in recent_patterns], indent=2)}

        Recent Learning Events:
        {json.dumps([e.dict() for e in recent_events], indent=2)}

        Please consider:
        1. Are the patterns being detected meaningful and useful?
        2. Is the system learning appropriate lessons from interactions?
        3. What areas show promising progress or room for improvement?
        4. Are there any blind spots or biases in the knowledge acquisition?
        5. What recommendations would you make for improving the system?
        """

        # Process the message through the Fire Circle
        result = self.orchestrator.process_message(
            session_id=session.session_id, message=message, gather_all_perspectives=True,
        )

        # Record the evaluation as a learning event
        learning_event = LearningEvent(
            event_type=LearningEventType.system_reflection,
            source="fire_circle",
            content={
                "evaluation": {
                    "storyteller": result["perspectives"].get("storyteller"),
                    "analyst": result["perspectives"].get("analyst"),
                    "critic": result["perspectives"].get("critic"),
                    "synthesis": result.get("synthesis"),
                },
            },
            confidence=0.8,
            metadata={
                "session_id": session.session_id,
                "entities_used": list(result["perspectives"].keys()),
                "patterns_evaluated": len(recent_patterns),
                "events_evaluated": len(recent_events),
            },
        )

        self.kb_manager.record_learning_event(learning_event)

        # Return the evaluation results
        return {
            "perspectives": result["perspectives"],
            "synthesis": result.get("synthesis"),
            "learning_event_id": learning_event.event_id,
        }

    def suggest_knowledge_patterns(
        self, query_history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Suggest potential knowledge patterns based on query history.

        Args:
            query_history: History of user queries

        Returns:
            A dictionary containing suggested knowledge patterns
        """
        # Create a session with all entity roles
        session = self.orchestrator.create_session()

        # Prepare a message for pattern suggestion
        message = f"""
        Based on this user query history, please suggest potential knowledge patterns
        that might be useful for the Indaleko system to track and learn from:

        Query History:
        {json.dumps(query_history, indent=2)}

        For each suggested pattern, please provide:
        1. A name/identifier for the pattern
        2. A description of what the pattern represents
        3. How it could be detected in query or user behavior data
        4. What actions or optimizations it might enable
        5. Why this pattern would be valuable to the system and user
        """

        # Process the message through the Fire Circle
        result = self.orchestrator.process_message(
            session_id=session.session_id, message=message, gather_all_perspectives=True,
        )

        # Create knowledge patterns from the suggestions
        # (This is a simplified implementation; in practice, we'd
        # want to parse the responses more carefully)
        suggested_patterns = []

        # Use the synthesis if available, otherwise use analyst perspective
        pattern_source = result.get("synthesis")
        if not pattern_source and "analyst" in result["perspectives"]:
            pattern_source = result["perspectives"]["analyst"]

        if pattern_source:
            # Record suggestions as a learning event
            learning_event = LearningEvent(
                event_type=LearningEventType.pattern_suggestion,
                source="fire_circle",
                content={
                    "suggestion_source": "query_history_analysis",
                    "suggestions": pattern_source,
                    "perspectives": result["perspectives"],
                },
                confidence=0.7,
                metadata={
                    "session_id": session.session_id,
                    "queries_analyzed": len(query_history),
                },
            )

            self.kb_manager.record_learning_event(learning_event)

        # Return the suggestions
        return {
            "perspectives": result["perspectives"],
            "synthesis": result.get("synthesis"),
            "suggested_patterns": suggested_patterns,
        }


class FireCircleCliIntegration:
    """Integration between Fire Circle and Indaleko CLI."""

    def __init__(
        self,
        cli_instance: IndalekoBaseCLI,
        fc_integration: FireCircleArchivistIntegration | None = None,
    ):
        """
        Initialize a new Fire Circle CLI integration.

        Args:
            cli_instance: The CLI instance to integrate with
            fc_integration: Optional Fire Circle integration
        """
        if not HAS_FIRE_CIRCLE:
            raise ImportError(
                "Fire Circle is not available. "
                "Please ensure the firecircle package is installed.",
            )

        self.cli = cli_instance
        self.fc_integration = fc_integration or FireCircleArchivistIntegration()

        # Register command handlers
        self._register_commands()

    def _register_commands(self) -> None:
        """Register Fire Circle commands with the CLI."""
        self.cli.register_command("/firecircle", self._handle_firecircle_command)
        self.cli.register_command("/fc", self._handle_firecircle_command)  # Alias

        # Add help text
        self.cli.append_help_text(
            "  /firecircle           - Fire Circle management and analysis commands",
        )
        self.cli.append_help_text("  /fc                   - Alias for /firecircle")

    def _handle_firecircle_command(self, args: str) -> None:
        """
        Handle Fire Circle commands.

        Args:
            args: Command arguments
        """
        args = args.strip()

        if not args or args == "help":
            self._show_firecircle_help()
            return

        # Split args into command and remaining args
        parts = args.split(maxsplit=1)
        subcommand = parts[0]
        subargs = parts[1] if len(parts) > 1 else ""

        # Dispatch to appropriate handler
        if subcommand == "analyze":
            self._handle_analyze_command(subargs)
        elif subcommand == "evaluate":
            self._handle_evaluate_command(subargs)
        elif subcommand == "suggest":
            self._handle_suggest_command(subargs)
        elif subcommand == "status":
            self._handle_status_command(subargs)
        else:
            self.cli.display_error(f"Unknown Fire Circle command: {subcommand}")
            self._show_firecircle_help()

    def _show_firecircle_help(self) -> None:
        """Show help for Fire Circle commands."""
        help_text = """
Fire Circle Commands:
  analyze <pattern_id>    - Analyze a knowledge pattern with multiple perspectives
  evaluate                - Evaluate the effectiveness of the knowledge base system
  suggest                 - Suggest potential knowledge patterns based on query history
  status                  - Show the status of the Fire Circle integration
        """
        self.cli.display_info(help_text)

    def _handle_analyze_command(self, args: str) -> None:
        """
        Handle the 'analyze' command.

        Args:
            args: Command arguments
        """
        args = args.strip()
        if not args:
            self.cli.display_error("Please specify a pattern ID to analyze")
            return

        try:
            # Get the pattern from the knowledge base
            pattern = self.fc_integration.kb_manager.get_pattern(args)

            if not pattern:
                self.cli.display_error(f"Pattern not found: {args}")
                return

            # Analyze the pattern
            self.cli.display_info(f"Analyzing pattern {args} with Fire Circle...")
            result = self.fc_integration.analyze_pattern(pattern)

            # Display results
            self.cli.display_info("=== Fire Circle Analysis ===")

            if "storyteller" in result["perspectives"]:
                self.cli.display_info("\n== Storyteller Perspective ==")
                self.cli.display_info(result["perspectives"]["storyteller"])

            if "analyst" in result["perspectives"]:
                self.cli.display_info("\n== Analyst Perspective ==")
                self.cli.display_info(result["perspectives"]["analyst"])

            if "critic" in result["perspectives"]:
                self.cli.display_info("\n== Critic Perspective ==")
                self.cli.display_info(result["perspectives"]["critic"])

            if result.get("synthesis"):
                self.cli.display_info("\n== Synthesized Analysis ==")
                self.cli.display_info(result["synthesis"])

            self.cli.display_info(
                f"\nAnalysis saved as learning event: {result['learning_event_id']}",
            )

        except Exception as e:
            self.cli.display_error(f"Error analyzing pattern: {e!s}")

    def _handle_evaluate_command(self, args: str) -> None:
        """
        Handle the 'evaluate' command.

        Args:
            args: Command arguments
        """
        try:
            self.cli.display_info(
                "Evaluating knowledge base system with Fire Circle...",
            )
            result = self.fc_integration.evaluate_system_effectiveness()

            # Display results
            self.cli.display_info("=== System Evaluation ===")

            if "storyteller" in result["perspectives"]:
                self.cli.display_info("\n== Narrative Perspective ==")
                self.cli.display_info(result["perspectives"]["storyteller"])

            if "analyst" in result["perspectives"]:
                self.cli.display_info("\n== Analytical Perspective ==")
                self.cli.display_info(result["perspectives"]["analyst"])

            if "critic" in result["perspectives"]:
                self.cli.display_info("\n== Critical Perspective ==")
                self.cli.display_info(result["perspectives"]["critic"])

            if result.get("synthesis"):
                self.cli.display_info("\n== Synthesized Evaluation ==")
                self.cli.display_info(result["synthesis"])

            self.cli.display_info(
                f"\nEvaluation saved as learning event: {result['learning_event_id']}",
            )

        except Exception as e:
            self.cli.display_error(f"Error evaluating system: {e!s}")

    def _handle_suggest_command(self, args: str) -> None:
        """
        Handle the 'suggest' command.

        Args:
            args: Command arguments
        """
        try:
            # Get recent query history
            query_history = (
                self.cli.get_query_history()
                if hasattr(self.cli, "get_query_history")
                else []
            )

            if not query_history:
                self.cli.display_warning("No query history available for analysis")
                return

            limit = 20  # Default limit
            if args:
                try:
                    limit = int(args)
                except ValueError:
                    self.cli.display_warning(
                        f"Invalid limit: {args}, using default: {limit}",
                    )

            # Limit the history
            query_history = query_history[-limit:]

            self.cli.display_info(
                f"Suggesting patterns based on {len(query_history)} recent queries...",
            )
            result = self.fc_integration.suggest_knowledge_patterns(query_history)

            # Display results
            self.cli.display_info("=== Pattern Suggestions ===")

            if "storyteller" in result["perspectives"]:
                self.cli.display_info("\n== Narrative Patterns ==")
                self.cli.display_info(result["perspectives"]["storyteller"])

            if "analyst" in result["perspectives"]:
                self.cli.display_info("\n== Analytical Patterns ==")
                self.cli.display_info(result["perspectives"]["analyst"])

            if "critic" in result["perspectives"]:
                self.cli.display_info("\n== Alternative Patterns ==")
                self.cli.display_info(result["perspectives"]["critic"])

            if result.get("synthesis"):
                self.cli.display_info("\n== Synthesized Suggestions ==")
                self.cli.display_info(result["synthesis"])

        except Exception as e:
            self.cli.display_error(f"Error suggesting patterns: {e!s}")

    def _handle_status_command(self, args: str) -> None:
        """
        Handle the 'status' command.

        Args:
            args: Command arguments
        """
        try:
            # Get capabilities of available entities
            capabilities = {}

            orchestrator = self.fc_integration.orchestrator
            session = orchestrator.create_session()

            for entity in session.entities:
                adapter = entity.adapter
                capabilities[entity.role.value] = adapter.get_capabilities()

            # Display status
            self.cli.display_info("=== Fire Circle Status ===")
            self.cli.display_info(
                f"Available entities: {', '.join([e.role.value for e in session.entities])}",
            )

            self.cli.display_info("\n== Entity Capabilities ==")
            for role, caps in capabilities.items():
                self.cli.display_info(f"\n{role.capitalize()}:")
                self.cli.display_info(f"  Provider: {caps.get('provider', 'unknown')}")
                self.cli.display_info(f"  Model: {caps.get('model', 'unknown')}")

                if "features" in caps:
                    features = caps["features"]
                    self.cli.display_info("  Features:")
                    for feature, value in features.items():
                        self.cli.display_info(f"    {feature}: {value}")

            # Clean up
            orchestrator.delete_session(session.session_id)

        except Exception as e:
            self.cli.display_error(f"Error getting Fire Circle status: {e!s}")


def initialize_firecircle_for_cli(
    cli_instance: IndalekoBaseCLI,
) -> FireCircleCliIntegration | None:
    """
    Initialize the Fire Circle integration for the CLI.

    Args:
        cli_instance: The CLI instance to integrate with

    Returns:
        FireCircleCliIntegration instance if available, None otherwise
    """
    if not HAS_FIRE_CIRCLE:
        logging.warning("Fire Circle features are not available")
        return None

    try:
        # Create integration
        fc_integration = FireCircleCliIntegration(cli_instance)

        # Store integration in CLI instance
        cli_instance.fc_integration = fc_integration

        # Log success
        logging.info("Fire Circle integration initialized successfully")

        return fc_integration
    except Exception as e:
        logging.exception(f"Failed to initialize Fire Circle integration: {e!s}")
        return None


def add_firecircle_arguments(parser) -> None:
    """
    Add Fire Circle arguments to a command-line parser.

    Args:
        parser: The argument parser to add arguments to
    """
    fc_group = parser.add_argument_group("Fire Circle")
    fc_group.add_argument(
        "--fc", "--fire-circle", action="store_true", help="Enable Fire Circle features",
    )
    fc_group.add_argument(
        "--fc-all-perspectives",
        action="store_true",
        help="Always use all perspectives for Fire Circle analysis",
    )
