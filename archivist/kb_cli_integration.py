"""
Knowledge Base CLI integration module.

This module integrates the Knowledge Base Updating feature with the
query command-line interface.

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
import json
import logging
import os
import sys

from typing import Any
from uuid import UUID


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
import contextlib

from archivist.kb_integration import ArchivistKnowledgeIntegration
from utils.cli.base import IndalekoBaseCLI


# pylint: enable=wrong-import-position


class KnowledgeBaseCliIntegration:
    """
    Integrates the Knowledge Base Updating feature with the CLI.

    This class:
    1. Registers knowledge base commands with the CLI
    2. Handles knowledge base command execution
    3. Enhances queries with knowledge patterns
    4. Provides feedback mechanisms
    """

    def __init__(
        self,
        cli_instance: IndalekoBaseCLI,
        kb_integration: ArchivistKnowledgeIntegration | None = None,
    ) -> None:
        """
        Initialize the CLI integration.

        Args:
            cli_instance: The CLI instance to integrate with
            kb_integration: Optional existing knowledge integration instance
        """
        self.cli = cli_instance
        self.kb_integration = kb_integration or ArchivistKnowledgeIntegration()
        self.logger = logging.getLogger(__name__)

        # Register knowledge base commands
        self._register_commands()

        # Add knowledge base commands to help text
        self._update_help_text()

    def _register_commands(self) -> None:
        """Register knowledge base commands with the CLI."""
        self.cli.register_command("/kb", self.handle_kb_command)
        self.cli.register_command("/patterns", self.handle_patterns_command)
        self.cli.register_command("/entities", self.handle_entities_command)
        self.cli.register_command("/feedback", self.handle_feedback_command)
        self.cli.register_command("/insights", self.handle_insights_command)
        self.cli.register_command("/schema", self.handle_schema_command)
        self.cli.register_command("/stats", self.handle_stats_command)

    def _update_help_text(self) -> None:
        """Update CLI help text with knowledge base commands."""
        kb_help_text = (
            "\nKnowledge Base Commands:\n"
            "  /kb                 - Show knowledge base commands\n"
            "  /patterns           - Show learned query patterns\n"
            "  /patterns [id]      - Show details for a specific pattern\n"
            "  /entities           - Show entity equivalence groups\n"
            "  /entities [name]    - Show details for entities matching name\n"
            "  /feedback positive  - Give positive feedback on last query\n"
            "  /feedback negative  - Give negative feedback on last query\n"
            "  /insights           - Show knowledge base insights\n"
            "  /schema [collection] - Show schema information for a collection\n"
            "  /stats              - Show knowledge base statistics\n"
        )

        self.cli.append_help_text(kb_help_text)

    def handle_kb_command(self, args: str) -> str:
        """
        Handle the /kb command.

        Args:
            args: Command arguments

        Returns:
            Command output
        """
        return (
            "Knowledge Base Commands:\n\n"
            "/kb - Show this help text\n"
            "/patterns - Show learned query patterns\n"
            "/patterns [id] - Show details for a specific pattern\n"
            "/entities - Show entity equivalence groups\n"
            "/entities [name] - Show details for entities matching name\n"
            "/feedback positive - Give positive feedback on last query\n"
            "/feedback negative - Give negative feedback on last query\n"
            "/insights - Show knowledge base insights\n"
            "/schema [collection] - Show schema information for a collection\n"
            "/stats - Show knowledge base statistics\n"
            "\nExamples:\n"
            "/patterns - List all patterns\n"
            "/patterns a81b3522-c394-40b0-a82c-a9d7fa1f7e03 - Show details for pattern\n"
            "/entities - List all entity groups\n"
            "/entities Indaleko - Show details for 'Indaleko' entities\n"
            "/feedback positive comment='Great results!' - Give positive feedback\n"
            "/schema Objects - Show schema information for the Objects collection\n"
            "/stats - Show detailed knowledge base statistics\n"
        )


    def handle_patterns_command(self, args: str) -> str:
        """
        Handle the /patterns command.

        Args:
            args: Command arguments

        Returns:
            Command output
        """
        if not args:
            # List all patterns
            from knowledge_base import KnowledgePatternType

            query_patterns = self.kb_integration.kb_manager.get_patterns_by_type(
                KnowledgePatternType.query_pattern,
                min_confidence=0.0,
            )

            entity_patterns = self.kb_integration.kb_manager.get_patterns_by_type(
                KnowledgePatternType.entity_relationship,
                min_confidence=0.0,
            )

            schema_patterns = self.kb_integration.kb_manager.get_patterns_by_type(
                KnowledgePatternType.schema_update,
                min_confidence=0.0,
            )

            preference_patterns = self.kb_integration.kb_manager.get_patterns_by_type(
                KnowledgePatternType.user_preference,
                min_confidence=0.0,
            )

            output = f"Knowledge Patterns ({len(query_patterns) + len(entity_patterns) + len(schema_patterns) + len(preference_patterns)} total):\n\n"

            if query_patterns:
                output += f"Query Patterns ({len(query_patterns)}):\n"
                for pattern in sorted(
                    query_patterns,
                    key=lambda p: p.confidence,
                    reverse=True,
                ):
                    intent = pattern.pattern_data.get("intent", "unknown")
                    query = (
                        pattern.pattern_data.get("query_text", "")[:40] + "..."
                        if len(pattern.pattern_data.get("query_text", "")) > 40
                        else pattern.pattern_data.get("query_text", "")
                    )
                    output += f"- {pattern.pattern_id} | Conf: {pattern.confidence:.2f} | Uses: {pattern.usage_count} | {intent}: {query}\n"
                output += "\n"

            if entity_patterns:
                output += f"Entity Relationship Patterns ({len(entity_patterns)}):\n"
                for pattern in sorted(
                    entity_patterns,
                    key=lambda p: p.confidence,
                    reverse=True,
                ):
                    entity_name = pattern.pattern_data.get("entity_name", "unknown")
                    entity_type = pattern.pattern_data.get("entity_type", "unknown")
                    relations = len(pattern.pattern_data.get("relationships", []))
                    output += f"- {pattern.pattern_id} | Conf: {pattern.confidence:.2f} | {entity_name} ({entity_type}) | {relations} relationships\n"
                output += "\n"

            if schema_patterns:
                output += f"Schema Update Patterns ({len(schema_patterns)}):\n"
                for pattern in sorted(
                    schema_patterns,
                    key=lambda p: p.confidence,
                    reverse=True,
                ):
                    collection = pattern.pattern_data.get("collection", "unknown")
                    changes = len(pattern.pattern_data.get("changes", {}))
                    output += f"- {pattern.pattern_id} | Conf: {pattern.confidence:.2f} | Collection: {collection} | {changes} changes\n"
                output += "\n"

            if preference_patterns:
                output += f"User Preference Patterns ({len(preference_patterns)}):\n"
                for pattern in sorted(
                    preference_patterns,
                    key=lambda p: p.confidence,
                    reverse=True,
                ):
                    preference = pattern.pattern_data.get("preference_type", "unknown")
                    output += f"- {pattern.pattern_id} | Conf: {pattern.confidence:.2f} | {preference}\n"
                output += "\n"

            return output
        # Show details for a specific pattern
        try:
            pattern_id = UUID(args.strip())
            pattern = self.kb_integration.kb_manager.get_knowledge_pattern(
                pattern_id,
            )

            if not pattern:
                return f"Pattern with ID {pattern_id} not found."

            output = f"Pattern Details: {pattern_id}\n\n"
            output += f"Type: {pattern.pattern_type}\n"
            output += f"Confidence: {pattern.confidence:.2f}\n"
            output += f"Usage Count: {pattern.usage_count}\n"
            output += f"Created: {pattern.created_at.isoformat()}\n"
            output += f"Updated: {pattern.updated_at.isoformat()}\n\n"

            output += "Pattern Data:\n"
            for key, value in pattern.pattern_data.items():
                if isinstance(value, dict):
                    output += f"- {key}: {json.dumps(value, indent=2)}\n"
                elif isinstance(value, list):
                    if len(value) > 5:
                        output += f"- {key}: {value[:5]} (and {len(value) - 5} more)\n"
                    else:
                        output += f"- {key}: {value}\n"
                else:
                    output += f"- {key}: {value}\n"

            return output
        except ValueError:
            return f"Invalid pattern ID: {args}. Please provide a valid UUID."

    def handle_entities_command(self, args: str) -> str:
        """
        Handle the /entities command.

        Args:
            args: Command arguments

        Returns:
            Command output
        """
        if not args:
            # List all entity groups
            entity_groups = self.kb_integration.entity_equivalence.list_entity_groups()

            output = f"Entity Equivalence Groups ({len(entity_groups)}):\n\n"

            for group in entity_groups:
                canonical = group.get("canonical", {})
                entity_type = group.get("entity_type", "unknown")
                members = group.get("members", [])

                output += f"Group: {group.get('group_id')}\n"
                output += f"- Canonical: {canonical.get('name')} ({entity_type})\n"
                output += f"- Members ({len(members)}):\n"

                for i, member in enumerate(members):
                    if i >= 5 and len(members) > 6:
                        output += f"  - ... and {len(members) - 5} more\n"
                        break
                    output += f"  - {member.get('name')}{' (canonical)' if member.get('canonical') else ''}\n"

                output += "\n"

            return output
        # Search for entities by name
        search_term = args.strip()

        # Get all nodes
        all_nodes = list(
            self.kb_integration.entity_equivalence._nodes_cache.values(),
        )

        # Filter by name
        matching_nodes = [node for node in all_nodes if search_term.lower() in node.name.lower()]

        if not matching_nodes:
            return f"No entities found matching '{search_term}'."

        output = f"Entities matching '{search_term}' ({len(matching_nodes)}):\n\n"

        for node in matching_nodes:
            # Get canonical reference
            canonical = self.kb_integration.entity_equivalence.get_canonical_reference(
                node.entity_id,
            )

            output += f"Entity: {node.name} ({node.entity_type})\n"
            output += f"- ID: {node.entity_id}\n"
            output += f"- Canonical: {canonical.name if canonical else 'N/A'}\n"
            output += f"- Source: {node.source if node.source else 'N/A'}\n"
            output += f"- Context: {node.context if node.context else 'N/A'}\n"

            # Get group members
            all_refs = self.kb_integration.entity_equivalence.get_all_references(
                node.entity_id,
            )
            if len(all_refs) > 1:
                output += f"- Equivalent References ({len(all_refs)}):\n"
                for ref in all_refs:
                    if ref.entity_id != node.entity_id:
                        output += f"  - {ref.name} ({ref.entity_id})\n"

            output += "\n"

        return output

    def handle_feedback_command(self, args: str) -> str:
        """
        Handle the /feedback command.

        Args:
            args: Command arguments

        Returns:
            Command output
        """
        args_parts = args.strip().split(" ", 1)
        feedback_type = args_parts[0].lower() if args_parts else ""

        if not feedback_type or feedback_type not in ("positive", "negative"):
            return (
                "Usage: /feedback positive|negative [key=value ...]\n\n"
                "Examples:\n"
                "/feedback positive\n"
                "/feedback negative comment='Results were not relevant'\n"
                "/feedback positive relevance=0.9 completeness=0.8\n"
            )

        # Parse additional parameters
        feedback_data = {}
        strength = 0.8  # Default strength

        if len(args_parts) > 1:
            extra_args = args_parts[1].strip()

            # Parse key=value pairs
            import re

            matches = re.finditer(r"(\w+)=([^=]+?)(?=\s+\w+=|$)", extra_args)

            for match in matches:
                key, value = match.groups()

                # Remove quotes if present
                value = value.strip()
                if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
                    value = value[1:-1]

                # Special handling for strength
                if key == "strength":
                    with contextlib.suppress(ValueError):
                        strength = float(value)
                else:
                    feedback_data[key] = value

        # Get last query if available
        last_query = "Unknown query"
        if hasattr(self.cli, "last_query"):
            last_query = self.cli.last_query

        # Default comment if none provided
        if "comment" not in feedback_data:
            if feedback_type == "positive":
                feedback_data["comment"] = "Good results"
            else:
                feedback_data["comment"] = "Results could be improved"

        # Record feedback
        feedback_response = self.kb_integration.add_user_feedback(
            feedback_type=feedback_type,
            query_text=last_query,
            feedback_data=feedback_data,
            strength=strength,
        )

        output = "Feedback recorded:\n"
        output += f"- Type: {feedback_response.get('type')}\n"
        output += f"- Strength: {strength}\n"
        output += f"- Query: {last_query}\n"
        output += f"- Feedback ID: {feedback_response.get('feedback_id')}\n"

        return output

    def handle_insights_command(self, args: str) -> str:
        """
        Handle the /insights command.

        Args:
            args: Command arguments

        Returns:
            Command output
        """
        insights = self.kb_integration.get_knowledge_insights()

        output = "Knowledge Base Insights:\n\n"

        # System health
        health = insights.get("system_health", {})
        output += "System Health:\n"
        output += f"- Knowledge Confidence: {health.get('knowledge_confidence', 0.0):.2f}\n"
        output += f"- Pattern Count: {health.get('pattern_count', 0)}\n"
        output += f"- Entity Group Count: {health.get('entity_group_count', 0)}\n"
        output += f"- Memory Count: {health.get('memory_count', 0)}\n"
        output += "\n"

        # Top patterns
        top_patterns = insights.get("top_patterns", [])
        output += f"Top Patterns ({len(top_patterns)}):\n"
        for pattern in top_patterns:
            output += f"- {pattern.get('id')[:8]} | Conf: {pattern.get('confidence', 0.0):.2f} | Uses: {pattern.get('usage_count', 0)} | {pattern.get('intent', 'unknown')}\n"
        output += "\n"

        # Top entities
        top_entities = insights.get("top_entities", [])
        output += f"Top Entities ({len(top_entities)}):\n"
        for entity in top_entities:
            output += (
                f"- {entity.get('canonical_name')} ({entity.get('type')}) | Members: {entity.get('member_count', 0)}\n"
            )
        output += "\n"

        # Stats
        stats = insights.get("stats", {})
        kb_stats = stats.get("knowledge_base", {})
        output += "Knowledge Base Stats:\n"
        output += f"- Events: {kb_stats.get('event_count', 0)}\n"
        output += f"- Patterns: {kb_stats.get('pattern_count', 0)}\n"
        output += f"- Feedback: {kb_stats.get('feedback_count', 0)}\n"

        return output

    def handle_schema_command(self, args: str) -> str:
        """
        Handle the /schema command.

        Args:
            args: Command arguments

        Returns:
            Command output
        """
        if not args:
            return (
                "Usage: /schema [collection_name]\n\n"
                "Examples:\n"
                "/schema Objects - Show schema information for the Objects collection\n"
                "/schema LearningEvents - Show schema information for the LearningEvents collection\n"
            )

        collection_name = args.strip()

        # Find schema pattern for this collection
        from knowledge_base import KnowledgePatternType

        schema_patterns = self.kb_integration.kb_manager.get_patterns_by_type(
            KnowledgePatternType.schema_update,
            min_confidence=0.0,
        )

        matching_pattern = None
        for pattern in schema_patterns:
            if pattern.pattern_data.get("collection") == collection_name:
                matching_pattern = pattern
                break

        if not matching_pattern:
            return f"No schema information found for collection '{collection_name}'."

        # Build output with schema information
        output = f"Schema Information for {collection_name}:\n\n"

        # Schema version
        output += f"Schema Version: {matching_pattern.pattern_data.get('schema_version', 1)}\n"
        output += f"Last Updated: {matching_pattern.updated_at.isoformat()}\n"
        output += f"Confidence: {matching_pattern.confidence:.2f}\n\n"

        # Field types
        field_types = matching_pattern.pattern_data.get("field_types", {})
        if field_types:
            output += "Field Types:\n"
            for field, field_type in sorted(field_types.items()):
                output += f"- {field}: {field_type}\n"
            output += "\n"

        # Evolution history
        evolution_history = matching_pattern.pattern_data.get("evolution_history", [])
        if evolution_history:
            output += f"Evolution History ({len(evolution_history)} changes):\n"
            for i, evolution in enumerate(evolution_history):
                if i >= 5 and len(evolution_history) > 6:
                    output += f"- ... and {len(evolution_history) - 5} more changes\n"
                    break

                timestamp = evolution.get("timestamp", "unknown")
                changes = evolution.get("changes", {})
                backwards_compatible = evolution.get("backwards_compatible", True)

                output += f"- {timestamp}"
                if changes:
                    change_str = []
                    if "added_fields" in changes:
                        change_str.append(
                            f"{len(changes['added_fields'])} fields added",
                        )
                    if "removed_fields" in changes:
                        change_str.append(
                            f"{len(changes['removed_fields'])} fields removed",
                        )
                    if "renamed_fields" in changes:
                        change_str.append(
                            f"{len(changes['renamed_fields'])} fields renamed",
                        )
                    if "type_changes" in changes:
                        change_str.append(
                            f"{len(changes['type_changes'])} type changes",
                        )

                    if change_str:
                        output += f": {', '.join(change_str)}"

                if not backwards_compatible:
                    output += " (breaking change)"

                output += "\n"

        # Migration path
        migration_path = matching_pattern.pattern_data.get("migration_path", "")
        if migration_path:
            output += "\nMigration Path:\n"
            output += migration_path

        return output

    def handle_stats_command(self, args: str) -> str:
        """
        Handle the /stats command.

        Args:
            args: Command arguments

        Returns:
            Command output
        """
        stats = self.kb_integration.kb_manager.get_stats()

        output = "Knowledge Base Statistics:\n\n"

        # Basic counts
        output += "Event Counts:\n"
        output += f"- Total Events: {stats.get('event_count', 0)}\n"
        output += f"- Total Patterns: {stats.get('pattern_count', 0)}\n"
        output += f"- Total Feedback: {stats.get('feedback_count', 0)}\n\n"

        # Pattern type breakdown
        pattern_types = stats.get("pattern_types", {})
        if pattern_types:
            output += "Pattern Types:\n"
            for pattern_type, count in pattern_types.items():
                if count > 0:
                    output += f"- {pattern_type}: {count}\n"
            output += "\n"

        # Event type breakdown
        event_types = stats.get("event_types", {})
        if event_types:
            output += "Event Types:\n"
            for event_type, count in event_types.items():
                if count > 0:
                    output += f"- {event_type}: {count}\n"
            output += "\n"

        # Feedback type breakdown
        feedback_types = stats.get("feedback_types", {})
        if feedback_types:
            output += "Feedback Types:\n"
            for feedback_type, count in feedback_types.items():
                if count > 0:
                    output += f"- {feedback_type}: {count}\n"
            output += "\n"

        # Pattern effectiveness
        effectiveness = stats.get("effectiveness", {})
        if effectiveness:
            # Find top patterns by success rate
            top_patterns = []
            for pattern_id, pattern_stats in effectiveness.items():
                if pattern_stats.get("usage_count", 0) >= 5:  # Only consider patterns with enough usage
                    top_patterns.append((pattern_id, pattern_stats))

            top_patterns.sort(key=lambda x: x[1].get("success_rate", 0), reverse=True)

            if top_patterns:
                output += "Top Pattern Performance (min 5 uses):\n"
                for _i, (pattern_id, pattern_stats) in enumerate(top_patterns[:5]):
                    success_rate = pattern_stats.get("success_rate", 0)
                    usage_count = pattern_stats.get("usage_count", 0)
                    pattern_type = pattern_stats.get("pattern_type", "unknown")

                    output += (
                        f"- {pattern_id[:8]}: {success_rate:.2f} success rate ({usage_count} uses, {pattern_type})\n"
                    )
                output += "\n"

        return output

    def enhance_query(
        self,
        query_text: str,
        intent: str = "",
        extracted_entities: list[dict[str, Any]] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Enhance a query using the knowledge base.

        Args:
            query_text: The original query text
            intent: The query intent (if known)
            extracted_entities: Entities extracted from the query
            context: Additional context for the query (optional)

        Returns:
            Enhanced query information
        """
        # Store query for feedback commands
        self.cli.last_query = query_text

        # Process query through knowledge integration
        return self.kb_integration.process_query(
            query_text=query_text,
            query_intent=intent,
            entities=extracted_entities or [],
            context=context,
        )


    def record_query_results(
        self,
        query_text: str,
        result_info: dict[str, Any],
        query_intent: str = "",
        entities: list[dict[str, Any]] | None = None,
        context: dict[str, Any] | None = None,
        refinements: list[dict[str, Any]] | None = None,
    ) -> None:
        """
        Record query results for learning.

        Args:
            query_text: The original query text
            result_info: Information about query results
            query_intent: The query intent (if known)
            entities: Entities extracted from the query
            context: Additional context for the query (optional)
            refinements: Query refinements applied (optional)
        """
        # Enhanced: Add refinement information if available
        if refinements:
            result_info["refinements"] = refinements

        # Process query through knowledge integration
        self.kb_integration.process_query(
            query_text=query_text,
            query_intent=query_intent,
            entities=entities or [],
            result_info=result_info,
            context=context,
        )


def register_kb_integration(
    cli_instance: IndalekoBaseCLI,
) -> KnowledgeBaseCliIntegration:
    """
    Register the Knowledge Base Integration with a CLI instance.

    Args:
        cli_instance: The CLI instance to integrate with

    Returns:
        The created KnowledgeBaseCliIntegration instance
    """
    # Create integration
    kb_integration = KnowledgeBaseCliIntegration(cli_instance)

    # Store integration in CLI instance for use by command handlers
    cli_instance.kb_integration = kb_integration

    return kb_integration


def main() -> None:
    """Main function for testing the CLI integration."""

    # Create a sample CLI for testing
    class TestCLI(IndalekoBaseCLI):
        """Test CLI implementation."""

        def __init__(self) -> None:
            """Initialize the test CLI."""
            self.commands = {}
            self.help_text = "Test CLI Help\n"
            self.last_query = ""

        def register_command(self, command, handler) -> None:
            """Register a command."""
            self.commands[command] = handler

        def append_help_text(self, text) -> None:
            """Append to help text."""
            self.help_text += text

        def execute_command(self, command, args):
            """Execute a command."""
            if command in self.commands:
                return self.commands[command](args)
            return f"Unknown command: {command}"

    # Create CLI
    cli = TestCLI()

    # Register KB integration
    register_kb_integration(cli)

    # Parse arguments
    parser = argparse.ArgumentParser(description="Test Knowledge Base CLI Integration")
    parser.add_argument("--command", help="Command to execute", default="/kb")
    parser.add_argument("--args", help="Command arguments", default="")

    args = parser.parse_args()

    # Execute command
    cli.execute_command(args.command, args.args)


if __name__ == "__main__":
    main()
