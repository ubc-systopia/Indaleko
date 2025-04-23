"""
CLI integration for the Advanced Query Pattern Analysis module.

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

import argparse
import json
import logging
import os
import sys
import traceback
from datetime import UTC, datetime
from typing import Any

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db.db_config import IndalekoDBConfig
from query.memory.query_pattern_analysis import QueryPatternAnalyzer
from utils.cli.base import IndalekoBaseCLI


# Define CommandResult class for returning command results
class CommandResult:
    """Result of a command execution."""

    def __init__(self, success: bool, message: str = "", data: Any = None):
        """
        Initialize the command result.

        Args:
            success: Whether the command was successful
            message: Message to display to the user
            data: Additional data returned by the command
        """
        self.success = success
        self.message = message
        self.data = data


# pylint: enable=wrong-import-position


class QueryPatternCLIIntegration:
    """
    CLI integration for the Query Pattern Analysis module.

    This class provides command handlers for the CLI interface to interact
    with the Query Pattern Analysis functionality.
    """

    def __init__(
        self,
        cli_instance: IndalekoBaseCLI,
        db_config: IndalekoDBConfig | None = None,
    ):
        """
        Initialize the CLI integration.

        Args:
            cli_instance: The CLI instance to register commands with
            db_config: Optional database configuration
        """
        self.cli = cli_instance
        self.db_config = db_config
        self.analyzer = None
        self.logger = logging.getLogger(__name__)

        # Initialize analyzer if db_config is provided
        if self.db_config:
            self.analyzer = QueryPatternAnalyzer(self.db_config)

        # Register commands with the CLI
        self._register_commands()

    def _register_commands(self):
        """Register commands with the CLI."""
        self.cli.register_command("/patterns", self.handle_patterns_command)
        self.cli.append_help_text(
            "  /patterns          - Query pattern analysis commands",
        )

    def _initialize_analyzer(self) -> bool:
        """Initialize the analyzer if needed."""
        if self.analyzer is None:
            if self.db_config is None:
                try:
                    self.db_config = IndalekoDBConfig()
                    connected = self.db_config.connect()

                    if connected:
                        self.analyzer = QueryPatternAnalyzer(self.db_config)
                        return True
                    else:
                        return False
                except Exception as e:
                    self.logger.error(f"Failed to initialize database connection: {e}")
                    return False
            else:
                self.analyzer = QueryPatternAnalyzer(self.db_config)
                return True

        return True

    def handle_patterns_command(self, args: list[str]) -> CommandResult:
        """
        Handle the /patterns command.

        Args:
            args: Command arguments

        Returns:
            CommandResult with the command result
        """
        if not args:
            # Show help for patterns command
            return CommandResult(
                success=True,
                message="""Query Pattern Analysis Commands:
/patterns analyze [--days=N] [--max-queries=N]  - Analyze query patterns
/patterns metrics                              - Show query metrics
/patterns chains                               - Show query chains
/patterns entities                             - Show entity usage
/patterns suggestions [--context=entity_name]  - Generate suggestions
/patterns test                                 - Run with mock data
/patterns save [--file=filename.json]          - Save analysis results
""",
            )

        subcommand = args[0].lower()

        if subcommand == "analyze":
            return self._handle_analyze(args[1:])
        elif subcommand == "metrics":
            return self._handle_metrics(args[1:])
        elif subcommand == "chains":
            return self._handle_chains(args[1:])
        elif subcommand == "entities":
            return self._handle_entities(args[1:])
        elif subcommand == "suggestions":
            return self._handle_suggestions(args[1:])
        elif subcommand == "test":
            return self._handle_test(args[1:])
        elif subcommand == "save":
            return self._handle_save(args[1:])
        else:
            return CommandResult(
                success=False,
                message=f"Unknown subcommand: {subcommand}. Use /patterns for help.",
            )

    def _handle_analyze(self, args: list[str]) -> CommandResult:
        """Handle the analyze subcommand."""
        try:
            parser = argparse.ArgumentParser(prog="/patterns analyze")
            parser.add_argument(
                "--days", type=int, default=30, help="Number of days to analyze",
            )
            parser.add_argument(
                "--max-queries",
                type=int,
                default=500,
                help="Maximum number of queries to analyze",
            )

            try:
                parsed_args = parser.parse_args(args)
            except SystemExit:
                # argparse calls sys.exit() when --help is used or parsing fails
                # Capture that and return a CommandResult instead
                return CommandResult(
                    success=True,
                    message="Usage: /patterns analyze [--days=N] [--max-queries=N]",
                )

            # Initialize analyzer
            if not self._initialize_analyzer():
                return CommandResult(
                    success=False, message="Failed to initialize database connection.",
                )

            # Run the analysis
            self.cli.print_message(
                "Running query pattern analysis...", message_type="info",
            )

            summary, suggestions = self.analyzer.analyze_and_generate()

            # Format result message
            if summary.get("status") == "no_data":
                return CommandResult(
                    success=False, message="No query history data found.",
                )

            message = f"""Query Pattern Analysis Summary:
- Processed {summary['query_count']} queries
- Detected {summary['chain_count']} query chains
- Identified {summary['pattern_count']} patterns
"""

            if summary.get("top_entities"):
                top_entities = ", ".join(summary["top_entities"][:5])
                message += f"- Top entities: {top_entities}\n"

            if summary.get("top_intents"):
                top_intents = ", ".join(summary["top_intents"][:3])
                message += f"- Top intents: {top_intents}\n"

            message += f"- Success rate: {summary['success_rate']:.1%}\n"
            message += f"- Refinement rate: {summary['refinement_rate']:.1%}\n"

            if suggestions:
                message += "\nGenerated Suggestions:\n"
                for i, suggestion in enumerate(suggestions[:3], 1):
                    message += f"{i}. {suggestion.title} (confidence: {suggestion.confidence:.2f})\n"
                    message += f"   {suggestion.content}\n"

                if len(suggestions) > 3:
                    message += f"   ... and {len(suggestions) - 3} more suggestions.\n"

            return CommandResult(success=True, message=message)

        except Exception as e:
            self.logger.error(f"Error in analyze command: {e}")
            self.logger.error(traceback.format_exc())
            return CommandResult(
                success=False, message=f"Error analyzing query patterns: {e!s}",
            )

    def _handle_metrics(self, args: list[str]) -> CommandResult:
        """Handle the metrics subcommand."""
        try:
            if not self._initialize_analyzer():
                return CommandResult(
                    success=False, message="Failed to initialize database connection.",
                )

            # Check if we have metrics
            if (
                not hasattr(self.analyzer.data, "user_metrics")
                or not self.analyzer.data.user_metrics
            ):
                # Calculate metrics
                self.cli.print_message(
                    "Calculating query metrics...", message_type="info",
                )
                metrics = self.analyzer.calculate_metrics()
            else:
                metrics = next(iter(self.analyzer.data.user_metrics.values()))

            if not metrics:
                return CommandResult(
                    success=False,
                    message="No query metrics available. Run /patterns analyze first.",
                )

            # Format the metrics
            message = f"""Query Metrics:
- Total queries: {metrics.total_queries}
- Successful queries: {metrics.successful_queries} ({metrics.success_rate:.1%})
- Empty result queries: {metrics.empty_result_queries}

Query Complexity:
- Average query length: {metrics.avg_query_length:.1f} characters
- Average entity count: {metrics.avg_entity_count:.1f} entities per query

Timing:
- Average query time: {metrics.avg_query_time:.3f} seconds
- Maximum query time: {metrics.max_query_time:.3f} seconds
"""

            # Add hour distribution if available
            if metrics.queries_by_hour:
                message += "\nQuery Distribution by Hour:\n"
                max_count = (
                    max(metrics.queries_by_hour.values())
                    if metrics.queries_by_hour
                    else 0
                )

                for hour in range(24):
                    count = metrics.queries_by_hour.get(hour, 0)
                    bar = "#" * int((count / max_count) * 20) if max_count > 0 else ""
                    message += f"{hour:02d}:00: {bar} {count}\n"

            # Add top entities
            if metrics.top_entities:
                message += "\nTop Entities:\n"
                for entity, count in list(metrics.top_entities.items())[:5]:
                    message += f"- {entity}: {count}\n"

            return CommandResult(success=True, message=message)

        except Exception as e:
            self.logger.error(f"Error in metrics command: {e}")
            self.logger.error(traceback.format_exc())
            return CommandResult(
                success=False, message=f"Error retrieving metrics: {e!s}",
            )

    def _handle_chains(self, args: list[str]) -> CommandResult:
        """Handle the chains subcommand."""
        try:
            if not self._initialize_analyzer():
                return CommandResult(
                    success=False, message="Failed to initialize database connection.",
                )

            # Check if we have chains
            if (
                not hasattr(self.analyzer.data, "query_chains")
                or not self.analyzer.data.query_chains
            ):
                # Analyze chains
                self.cli.print_message("Analyzing query chains...", message_type="info")
                chains = self.analyzer.analyze_query_chains()
            else:
                chains = self.analyzer.data.query_chains

            if not chains:
                return CommandResult(
                    success=False,
                    message="No query chains detected. Run /patterns analyze first.",
                )

            # Format the chains information
            message = f"Detected {len(chains)} query chains:\n\n"

            # Group by chain type
            chains_by_type = {}
            for chain in chains:
                if chain.chain_type not in chains_by_type:
                    chains_by_type[chain.chain_type] = []
                chains_by_type[chain.chain_type].append(chain)

            # Show summary by type
            for chain_type, type_chains in chains_by_type.items():
                message += f"- {chain_type.value}: {len(type_chains)} chains\n"

            message += "\nTop Query Chains (by length):\n"

            # Sort by length and show the top 5
            top_chains = sorted(chains, key=lambda c: len(c.queries), reverse=True)[:5]

            for i, chain in enumerate(top_chains, 1):
                message += f"{i}. {chain.chain_type.value} chain with {len(chain.queries)} queries"

                if chain.shared_entities:
                    entities = ", ".join(chain.shared_entities[:3])
                    if len(chain.shared_entities) > 3:
                        entities += f" and {len(chain.shared_entities) - 3} more"
                    message += f" involving {entities}"

                message += f" (success rate: {chain.success_rate:.1%})\n"

                # Show query texts (truncated)
                for j, query_text in enumerate(chain.query_texts[:3], 1):
                    # Truncate long queries
                    if len(query_text) > 50:
                        query_text = query_text[:50] + "..."
                    message += f"   {j}. {query_text}\n"

                if len(chain.query_texts) > 3:
                    message += f"   ... and {len(chain.query_texts) - 3} more queries\n"

                message += "\n"

            return CommandResult(success=True, message=message)

        except Exception as e:
            self.logger.error(f"Error in chains command: {e}")
            self.logger.error(traceback.format_exc())
            return CommandResult(
                success=False, message=f"Error retrieving query chains: {e!s}",
            )

    def _handle_entities(self, args: list[str]) -> CommandResult:
        """Handle the entities subcommand."""
        try:
            entity_name = None
            if args and not args[0].startswith("--"):
                entity_name = args[0]

            if not self._initialize_analyzer():
                return CommandResult(
                    success=False, message="Failed to initialize database connection.",
                )

            # Check if we have entity usage data
            if (
                not hasattr(self.analyzer.data, "entity_usage")
                or not self.analyzer.data.entity_usage
            ):
                # We need to run an analysis first
                self.cli.print_message(
                    "Loading query history to analyze entities...", message_type="info",
                )
                self.analyzer.load_query_history()

                if not self.analyzer.data.entity_usage:
                    return CommandResult(
                        success=False,
                        message="No entity usage data available. Run /patterns analyze first.",
                    )

            # If a specific entity is requested
            if entity_name:
                if entity_name not in self.analyzer.data.entity_usage:
                    return CommandResult(
                        success=False,
                        message=f"Entity '{entity_name}' not found in query history.",
                    )

                # Get the entity usage
                entity_usage = self.analyzer.data.entity_usage[entity_name]

                # Format the entity information
                message = f"Entity: {entity_usage.entity_name}\n\n"
                message += f"- Mentions: {entity_usage.mention_count}\n"
                message += f"- Success rate: {entity_usage.success_rate:.1%}\n"
                message += f"- First seen: {entity_usage.first_seen.strftime('%Y-%m-%d %H:%M')}\n"
                message += f"- Last seen: {entity_usage.last_seen.strftime('%Y-%m-%d %H:%M')}\n"

                # Show intents
                if entity_usage.intents:
                    message += "\nIntents:\n"
                    for intent, count in sorted(
                        entity_usage.intents.items(), key=lambda x: x[1], reverse=True,
                    ):
                        message += f"- {intent}: {count}\n"

                # Show co-occurring entities
                if entity_usage.co_occurring_entities:
                    message += "\nCo-occurring Entities:\n"
                    co_entities = sorted(
                        entity_usage.co_occurring_entities.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )
                    for co_entity, count in co_entities[:10]:
                        message += f"- {co_entity}: {count}\n"

                    if len(co_entities) > 10:
                        message += f"... and {len(co_entities) - 10} more co-occurring entities\n"

                # Show example queries
                if entity_usage.query_examples:
                    message += "\nExample Queries:\n"
                    for i, example in enumerate(entity_usage.query_examples, 1):
                        message += f"{i}. {example}\n"

            else:
                # Show all entities summary
                entities = self.analyzer.data.entity_usage

                message = f"Found {len(entities)} entities in query history:\n\n"

                # Top entities by mention count
                message += "Top Entities by Mention Count:\n"
                top_entities = sorted(
                    entities.values(), key=lambda e: e.mention_count, reverse=True,
                )[:10]

                for i, entity in enumerate(top_entities, 1):
                    message += (
                        f"{i}. {entity.entity_name}: {entity.mention_count} mentions"
                    )
                    message += f" (success rate: {entity.success_rate:.1%})\n"

                # Entities with highest success rate (with minimum mentions)
                min_mentions = 3
                success_entities = [
                    e for e in entities.values() if e.mention_count >= min_mentions
                ]
                success_entities = sorted(
                    success_entities, key=lambda e: e.success_rate, reverse=True,
                )[:5]

                if success_entities:
                    message += f"\nEntities with Highest Success Rate (min {min_mentions} mentions):\n"
                    for i, entity in enumerate(success_entities, 1):
                        message += (
                            f"{i}. {entity.entity_name}: {entity.success_rate:.1%}"
                        )
                        message += f" ({entity.mention_count} mentions)\n"

                # Entity co-occurrence
                message += "\nStrongest Entity Co-occurrences:\n"

                # Find strong co-occurrences
                strong_cooccurrences = []

                for entity_name, entity in entities.items():
                    for co_entity, count in entity.co_occurring_entities.items():
                        if count >= 2:  # Minimum co-occurrence count
                            # Calculate co-occurrence strength
                            strength = count / entity.mention_count
                            if strength >= 0.5:  # Strong co-occurrence threshold
                                strong_cooccurrences.append(
                                    (entity_name, co_entity, count, strength),
                                )

                # Sort by strength and show top 5
                strong_cooccurrences.sort(key=lambda x: x[3], reverse=True)

                for i, (entity1, entity2, count, strength) in enumerate(
                    strong_cooccurrences[:5], 1,
                ):
                    message += (
                        f"{i}. {entity1} + {entity2}: {strength:.1%} ({count} times)\n"
                    )

                message += "\nUse /patterns entities ENTITY_NAME for detailed information about a specific entity."

            return CommandResult(success=True, message=message)

        except Exception as e:
            self.logger.error(f"Error in entities command: {e}")
            self.logger.error(traceback.format_exc())
            return CommandResult(
                success=False, message=f"Error retrieving entity information: {e!s}",
            )

    def _handle_suggestions(self, args: list[str]) -> CommandResult:
        """Handle the suggestions subcommand."""
        try:
            # Parse arguments
            parser = argparse.ArgumentParser(prog="/patterns suggestions")
            parser.add_argument("--context", type=str, help="Context entity name")

            try:
                parsed_args = parser.parse_args(args)
            except SystemExit:
                # argparse calls sys.exit() when --help is used or parsing fails
                # Capture that and return a CommandResult instead
                return CommandResult(
                    success=True,
                    message="Usage: /patterns suggestions [--context=entity_name]",
                )

            # Initialize analyzer
            if not self._initialize_analyzer():
                return CommandResult(
                    success=False, message="Failed to initialize database connection.",
                )

            # Check if we have pattern data
            if (
                not hasattr(self.analyzer.data, "query_patterns")
                or not self.analyzer.data.query_patterns
            ):
                # We need to run an analysis first
                return CommandResult(
                    success=False,
                    message="No pattern data available. Run /patterns analyze first.",
                )

            # Set up context
            context = None
            if parsed_args.context:
                context = {"entities": [parsed_args.context]}

                # Verify the entity exists
                if (
                    hasattr(self.analyzer.data, "entity_usage")
                    and parsed_args.context not in self.analyzer.data.entity_usage
                ):
                    return CommandResult(
                        success=False,
                        message=f"Entity '{parsed_args.context}' not found in query history.",
                    )

            # Generate suggestions
            suggestions = self.analyzer.generate_query_suggestions(context)

            if not suggestions:
                return CommandResult(success=False, message="No suggestions generated.")

            # Format the suggestions
            message = f"Generated {len(suggestions)} suggestions:\n\n"

            for i, suggestion in enumerate(suggestions, 1):
                message += (
                    f"{i}. {suggestion.title} ({suggestion.suggestion_type.value})\n"
                )
                message += f"   {suggestion.content}\n"
                message += f"   Confidence: {suggestion.confidence:.2f}, Priority: {suggestion.priority.value}\n"
                message += f"   Expires: {suggestion.expires_at.strftime('%Y-%m-%d %H:%M') if suggestion.expires_at else 'Never'}\n\n"

            return CommandResult(success=True, message=message)

        except Exception as e:
            self.logger.error(f"Error in suggestions command: {e}")
            self.logger.error(traceback.format_exc())
            return CommandResult(
                success=False, message=f"Error generating suggestions: {e!s}",
            )

    def _handle_test(self, args: list[str]) -> CommandResult:
        """Handle the test subcommand."""
        try:
            import query.memory.test_query_pattern_analysis as test_module

            # Create a test instance that generates mock data
            test_obj = test_module.MockQueryGeneratorTests()
            test_obj.setUp()

            # Run the test that generates mock data
            test_obj.test_with_generated_queries()

            # Use the generated data
            self.analyzer = test_obj.analyzer

            # Run analysis and generate suggestions
            summary, suggestions = self.analyzer.analyze_and_generate()

            # Format the result message
            message = f"""Query Pattern Analysis Test Results:
- Generated {summary['query_count']} mock queries
- Detected {summary['chain_count']} query chains
- Identified {summary['pattern_count']} patterns

Detected Patterns:
"""
            for i, pattern in enumerate(self.analyzer.data.query_patterns, 1):
                message += f"{i}. {pattern.pattern_name} ({pattern.pattern_type}, confidence: {pattern.confidence:.2f})\n"
                message += f"   {pattern.description}\n"

            if suggestions:
                message += "\nGenerated Suggestions:\n"
                for i, suggestion in enumerate(suggestions, 1):
                    message += f"{i}. {suggestion.title} ({suggestion.suggestion_type}, confidence: {suggestion.confidence:.2f})\n"
                    message += f"   {suggestion.content}\n"

            return CommandResult(success=True, message=message)

        except Exception as e:
            self.logger.error(f"Error in test command: {e}")
            self.logger.error(traceback.format_exc())
            return CommandResult(success=False, message=f"Error running test: {e!s}")

    def _handle_save(self, args: list[str]) -> CommandResult:
        """Handle the save subcommand."""
        try:
            # Parse arguments
            parser = argparse.ArgumentParser(prog="/patterns save")
            parser.add_argument(
                "--file",
                type=str,
                default="query_patterns.json",
                help="Output file name",
            )

            try:
                parsed_args = parser.parse_args(args)
            except SystemExit:
                # argparse calls sys.exit() when --help is used or parsing fails
                # Capture that and return a CommandResult instead
                return CommandResult(
                    success=True, message="Usage: /patterns save [--file=filename.json]",
                )

            if not self.analyzer or not hasattr(self.analyzer, "data"):
                return CommandResult(
                    success=False,
                    message="No analysis data available. Run /patterns analyze first.",
                )

            # Prepare results for serialization
            results = {
                "timestamp": datetime.now(UTC).isoformat(),
                "query_count": (
                    len(self.analyzer.data.queries)
                    if hasattr(self.analyzer.data, "queries")
                    else 0
                ),
                "patterns": (
                    [p.model_dump() for p in self.analyzer.data.query_patterns]
                    if hasattr(self.analyzer.data, "query_patterns")
                    else []
                ),
                "chains": (
                    [c.model_dump() for c in self.analyzer.data.query_chains]
                    if hasattr(self.analyzer.data, "query_chains")
                    else []
                ),
                "entity_usage": (
                    {
                        k: v.model_dump()
                        for k, v in self.analyzer.data.entity_usage.items()
                    }
                    if hasattr(self.analyzer.data, "entity_usage")
                    else {}
                ),
                "metrics": (
                    next(iter(self.analyzer.data.user_metrics.values())).model_dump()
                    if hasattr(self.analyzer.data, "user_metrics")
                    and self.analyzer.data.user_metrics
                    else None
                ),
            }

            # Save to file
            with open(parsed_args.file, "w") as f:
                json.dump(results, f, indent=2, default=str)

            return CommandResult(
                success=True, message=f"Analysis results saved to {parsed_args.file}",
            )

        except Exception as e:
            self.logger.error(f"Error in save command: {e}")
            self.logger.error(traceback.format_exc())
            return CommandResult(
                success=False, message=f"Error saving results: {e!s}",
            )


def register_query_pattern_commands(
    cli_instance: IndalekoBaseCLI, db_config: IndalekoDBConfig | None = None,
) -> QueryPatternCLIIntegration:
    """
    Register query pattern analysis commands with a CLI instance.

    Args:
        cli_instance: The CLI instance to register commands with
        db_config: Optional database configuration

    Returns:
        The created QueryPatternCLIIntegration instance
    """
    integration = QueryPatternCLIIntegration(cli_instance, db_config)
    return integration


def main():
    """Run a standalone CLI demo."""
    # Set up CLI
    from utils.cli.base import IndalekoBaseCLI

    cli = IndalekoBaseCLI(
        prompt="Indaleko> ",
        intro="Indaleko Query Pattern Analysis CLI Demo\nType /help for help, /exit to exit.",
        default_handler=lambda cmd: print(
            f"Unknown command: {cmd}. Type /help for help.",
        ),
    )

    # Try to connect to the database
    try:
        db_config = IndalekoDBConfig()
        connected = db_config.connect()

        if connected:
            print("Connected to database.")
            integration = register_query_pattern_commands(cli, db_config)
        else:
            print("Failed to connect to database. Running in mock mode.")
            integration = register_query_pattern_commands(cli)
    except Exception as e:
        print(f"Database connection error: {e}")
        print("Running in mock mode.")
        integration = register_query_pattern_commands(cli)

    # Run the CLI
    cli.run()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    main()
