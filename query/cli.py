"""
This module provides a CLI based interface for querying Indaleko.

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
import configparser
import os
import sys

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from arango.aql import AQLQueryExplainError
from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
import contextlib

from data_models.collection_metadata_data_model import (
    IndalekoCollectionMetadataDataModel,
)
from data_models.db_index import IndalekoCollectionIndexDataModel
from data_models.named_entity import IndalekoNamedEntityDataModel, NamedEntityCollection
from db import IndalekoDBCollections, IndalekoDBConfig
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from query.history.data_models.query_history import QueryHistoryData
from query.memory.kb_integration import (
    enhance_query_with_kb,
    initialize_kb_for_cli,
    record_query_results,
)
from query.query_processing.data_models.parser_data import ParserResults
from query.query_processing.data_models.query_input import StructuredQuery
from query.query_processing.data_models.translator_input import TranslatorInput
from query.query_processing.enhanced_nl_parser import EnhancedNLParser
from query.query_processing.nl_parser import NLParser
from query.query_processing.query_history import QueryHistory
from query.query_processing.query_translator.aql_translator import AQLTranslator
from query.query_processing.query_translator.enhanced_aql_translator import (
    EnhancedAQLTranslator,
)
from query.result_analysis.data_models.facet_data_model import DynamicFacets
from query.result_analysis.facet_generator import FacetGenerator
from query.result_analysis.metadata_analyzer import MetadataAnalyzer
from query.result_analysis.query_refiner import QueryRefiner
from query.result_analysis.result_formatter import (
    FormattedResults,
    format_results_for_display,
)
from query.result_analysis.result_ranker import ResultRanker
from query.search_execution.query_executor.aql_executor import AQLExecutor
from query.search_execution.query_visualizer import PlanVisualizer
from query.utils.llm_connector.openai_connector import OpenAIConnector
from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel


# Import Query Context Integration components
try:
    from query.context.activity_provider import QueryActivityProvider
    from query.context.navigation import QueryNavigator
    from query.context.relationship import QueryRelationshipDetector
    from query.context.visualization import QueryPathVisualizer

    HAS_QUERY_CONTEXT = True
except ImportError:
    HAS_QUERY_CONTEXT = False

# Import archivist components if available
try:
    from archivist.cli_integration_main import register_with_cli as register_archivist

    HAS_ARCHIVIST = True
except ImportError:
    HAS_ARCHIVIST = False

# Import Fire Circle components if available
try:
    from archivist.fire_circle_integration import (
        add_firecircle_arguments,
        initialize_firecircle_for_cli,
    )

    HAS_FIRE_CIRCLE = True
except ImportError:
    HAS_FIRE_CIRCLE = False

# Import semantic performance monitoring components if available
try:
    from semantic.cli_integration import register_semantic_performance_cli

    HAS_SEMANTIC_PERFORMANCE = True
except ImportError:
    HAS_SEMANTIC_PERFORMANCE = False

# Import query pattern analysis components
try:
    from query.cli_query_pattern_integration import register_query_pattern_commands

    HAS_QUERY_PATTERN_ANALYSIS = True
except ImportError:
    HAS_QUERY_PATTERN_ANALYSIS = False

# Import analytics integration
try:
    from query.analytics_integration import (
        register_analytics_commands,
    )

    HAS_ANALYTICS = True
except ImportError:
    HAS_ANALYTICS = False

# pylint: enable=wrong-import-position


class IndalekoQueryCLI(IndalekoBaseCLI):
    """This class represents the base class for Indaleko Queries."""

    service_name = "IndalekoQueryCLI"

    def __init__(self) -> None:
        """Create an instance of the IndalekoQueryCLI class."""
        cli_data = IndalekoBaseCliDataModel(
            RegistrationServiceName=IndalekoQueryCLI.service_name,
            FileServiceName=IndalekoQueryCLI.service_name,
        )
        handler_mixin = IndalekoQueryCLI.query_handler_mixin
        features = IndalekoBaseCLI.cli_features(
            machine_config=False,
            input=False,
            output=False,
            offline=False,
            logging=False,
            performance=False,
            platform=False,
        )
        super().__init__(
            cli_data=cli_data,
            handler_mixin=handler_mixin,
            features=features,
        )
        config_data = self.get_config_data()
        config_file_path = os.path.join(
            config_data["ConfigDirectory"],
            config_data["DBConfigFile"],
        )
        self.db_config = IndalekoDBConfig(config_file=config_file_path)
        self.archivist_components = None
        self.collections_metadata = IndalekoDBCollectionsMetadata(self.db_config)
        self.openai_key = self.get_api_key()
        self.llm_connector = OpenAIConnector(
            api_key=self.openai_key,
            model="gpt-4o-mini",
        )

        # Initialize a dictionary to store command handlers
        self.commands = {}
        # Initialize parsers based on args
        use_enhanced = hasattr(self.args, "enhanced_nl") and self.args.enhanced_nl
        if use_enhanced:
            self.nl_parser = EnhancedNLParser(
                llm_connector=self.llm_connector,
                collections_metadata=self.collections_metadata,
            )
            self.query_translator = EnhancedAQLTranslator(self.collections_metadata)
        else:
            self.nl_parser = NLParser(
                llm_connector=self.llm_connector,
                collections_metadata=self.collections_metadata,
            )
            self.query_translator = AQLTranslator(self.collections_metadata)
        self.query_history = QueryHistory()
        self.query_executor = AQLExecutor()
        self.metadata_analyzer = MetadataAnalyzer()
        self.prompt = "Indaleko Search> "

        # Initialize facet generator with CLI args
        conversational = hasattr(self.args, "conversational") and self.args.conversational
        self.facet_generator = FacetGenerator(
            max_facets=5,
            min_facet_coverage=0.2,
            min_value_count=2,
            conversational=conversational,
        )

        # Initialize query refiner for interactive facet refinement
        self.query_refiner = QueryRefiner()

        # Initialize query plan visualizer
        colorize = not (hasattr(self.args, "no_color") and self.args.no_color)
        self.plan_visualizer = PlanVisualizer(colorize=colorize)

        self.result_ranker = ResultRanker()
        self.schema = self.build_schema_table()
        self.args = self.get_args()

    class query_handler_mixin(IndalekoBaseCLI.default_handler_mixin):
        """Handler mixin for the CLI."""

        @staticmethod
        def get_pre_parser() -> argparse.ArgumentParser | None:
            """
            Build extended pre-parser for the CLI.

            This method is used to get the pre-parser.  Callers can
            set up switches/parameters before we add the common ones.
            """
            parser = argparse.ArgumentParser(add_help=False)

            # Add debug flag
            parser.add_argument(
                "--debug",
                action="store_true",
                default=False,
                help="Enable debug output",
            )

            parser.add_argument(
                "--explain",
                action="store_true",
                help="Explain query execution plans instead of executing queries",
            )
            parser.add_argument(
                "--show-plan",
                action="store_true",
                help="Show query execution plan before executing the query",
            )
            parser.add_argument(
                "--perf",
                action="store_true",
                help="Collect and display performance metrics for query execution",
            )
            parser.add_argument(
                "--all-plans",
                action="store_true",
                help="Show all possible execution plans when using --explain or --show-plan",
            )
            parser.add_argument(
                "--max-plans",
                type=int,
                default=5,
                help="Maximum number of plans to show when using --all-plans (default: 5)",
            )
            parser.add_argument(
                "--verbose",
                action="store_true",
                help="Show detailed execution plan information including all plan nodes",
            )
            parser.add_argument(
                "--deduplicate",
                action="store_true",
                help="Enable deduplication of similar results using Jaro-Winkler similarity",
            )
            parser.add_argument(
                "--similarity-threshold",
                type=float,
                default=0.85,
                help="Threshold for considering items as duplicates when using --deduplicate (0.0-1.0, default: 0.85)",
            )
            parser.add_argument(
                "--show-duplicates",
                action="store_true",
                help="Show duplicate items in results when using --deduplicate",
            )
            parser.add_argument(
                "--dynamic-facets",
                action="store_true",
                help="Enable enhanced dynamic facets for result exploration",
            )

            parser.add_argument(
                "--no-color",
                action="store_true",
                help="Disable colorized output for query plans and other displays",
            )
            parser.add_argument(
                "--enhanced-nl",
                action="store_true",
                help="Use enhanced natural language understanding for queries",
            )
            parser.add_argument(
                "--context-aware",
                action="store_true",
                help="Enable context-aware queries using query history",
            )
            parser.add_argument(
                "--archivist",
                action="store_true",
                help="Enable the Archivist memory system for maintaining context across sessions",
            )
            parser.add_argument(
                "--optimizer",
                action="store_true",
                help="Enable the database optimizer for analyzing and improving query performance",
            )
            parser.add_argument(
                "--proactive",
                action="store_true",
                help="Enable proactive suggestions based on patterns and context",
            )

            # Add Knowledge Base arguments
            parser.add_argument(
                "--kb",
                "--knowledge-base",
                action="store_true",
                help="Enable Knowledge Base features for learning from interactions",
            )
            parser.add_argument(
                "--kb-confidence",
                type=float,
                default=0.7,
                help="Minimum confidence threshold for knowledge patterns (0-1)",
            )

            # Add Fire Circle arguments
            parser.add_argument(
                "--fc",
                "--fire-circle",
                action="store_true",
                help="Enable Fire Circle features with specialized entity roles",
            )
            parser.add_argument(
                "--fc-all-perspectives",
                action="store_true",
                help="Always use all perspectives for Fire Circle analysis",
            )

            # Add semantic performance monitoring arguments
            parser.add_argument(
                "--semantic-performance",
                action="store_true",
                help="Enable semantic performance monitoring features",
            )

            # Add query pattern analysis arguments
            parser.add_argument(
                "--query-patterns",
                action="store_true",
                help="Enable advanced query pattern analysis and suggestions",
            )

            # Add Query Context Integration arguments
            parser.add_argument(
                "--query-context",
                action="store_true",
                help="Enable Query Context Integration for recording queries as activities",
            )
            parser.add_argument(
                "--query-visualization",
                action="store_true",
                help="Enable visualization of query paths and relationships",
            )

            parser.add_argument(
                "--conversational",
                action="store_true",
                help="Enable conversational suggestions for search refinement",
            )

            # Add analytics integration arguments
            parser.add_argument(
                "--analytics",
                action="store_true",
                help="Enable analytics capabilities for file statistics",
            )
            args = parser.parse_known_args()
            if (len(args[1]) == 1 and
                Path(args[1][0]).exists() and
                Path(args[1][0]).is_file()):
                # If only one argument is passed and it is a file
                # if it is, this is a batch request.
                parser.add_argument(
                    "input_file",
                    nargs=1,
                    type=Path,
                    default=Path(args[1][0]),
                    help="Input file containing queries to process (one per line)."
                    " Runs in batch mode.",
                )
            else:
                # Add interactive only options
                parser.add_argument(
                    "--interactive",
                    action="store_true",
                    help="Enable interactive facet refinement mode",
                )

            return parser

    query_cli_handler_mixin = query_handler_mixin

    def get_api_key(self, api_key_file: str | None = None) -> str:
        """Get the API key from the config file."""
        if api_key_file is None:
            api_key_file = os.path.join(
                self.config_data["ConfigDirectory"],
                "openai-key.ini",
            )
        assert os.path.exists(api_key_file), f"API key file ({api_key_file}) not found"
        config = configparser.ConfigParser()
        config.read(api_key_file, encoding="utf-8-sig")
        openai_key = config["openai"]["api_key"]
        if openai_key is None:
            raise ValueError("OpenAI API key not found in config file")
        if openai_key[0] == '"' or openai_key[0] == "'":
            openai_key = openai_key[1:]
        if openai_key[-1] == '"' or openai_key[-1] == "'":
            openai_key = openai_key[:-1]
        return openai_key

    def register_command(self, command: str, handler_function) -> None:
        """
        Register a command handler function.

        Args:
            command: The command to register (e.g., "/analytics")
            handler_function: The function to call when the command is invoked
        """
        # Make sure we have a commands dictionary
        if not hasattr(self, "commands"):
            self.commands = {}

        self.commands[command] = handler_function
        ic(f"Registered command handler for: {command}")

    def append_help_text(self, text: str) -> None:
        """
        Append text to the help message.

        Args:
            text: The text to append to the help message
        """
        # Make sure we have a help_text list
        if not hasattr(self, "help_text"):
            self.help_text = []

        self.help_text.append(text)
        ic(f"Added help text: {text}")

    def run(self) -> None:
        """Runs the CLI query tool."""
        if not self.args:
            # If no arguments are provided, show help and exit
            self.args = self.pre_parser.parse_args()
        ic(self.args)

        batch_file = None
        if hasattr(self.args, "input_file"):
            input_file = Path(self.args.input_file[0])
            batch_file = input_file.open("r", encoding="utf-8")

        # self.archivist_components is already initialized in __init__
        self.archivist_components = None
        if HAS_ARCHIVIST and hasattr(self.args, "archivist") and self.args.archivist:
            # Check if proactive mode is enabled
            enable_proactive = hasattr(self.args, "proactive") and self.args.proactive
            self.archivist_components = register_archivist(self, enable_proactive)
            memory_integration = self.archivist_components.get("memory_integration")

            # Get proactive integration if available
            self.proactive_integration = self.archivist_components.get(
                "proactive_integration",
            )

            # Show initial suggestions if proactive mode is enabled
            if enable_proactive and self.proactive_integration:
                initial_suggestions = self.proactive_integration.get_initial_suggestions()
                if initial_suggestions:
                    self.proactive_integration._display_suggestions(initial_suggestions)

        # Initialize Knowledge Base integration
        self.kb_integration = None
        if hasattr(self.args, "kb") and self.args.kb:
            self.kb_integration = initialize_kb_for_cli(self)
            if self.kb_integration:
                pass

        # Initialize Fire Circle integration
        self.fire_circle_integration = None
        if HAS_FIRE_CIRCLE and hasattr(self.args, "fc") and self.args.fc:
            self.fire_circle_integration = initialize_firecircle_for_cli(self)
            if self.fire_circle_integration:
                pass

        # Initialize Semantic Performance Monitoring
        self.semantic_performance_integration = None
        if HAS_SEMANTIC_PERFORMANCE and hasattr(
            self.args,
            "semantic_performance"
        ) and self.args.semantic_performance:
            self.semantic_performance_integration = register_semantic_performance_cli(
                self,
            )

        # Initialize Query Pattern Analysis
        self.query_pattern_integration = None
        if HAS_QUERY_PATTERN_ANALYSIS and hasattr(self.args, "query_patterns") and self.args.query_patterns:
            self.query_pattern_integration = register_query_pattern_commands(
                self,
                self.db_config,
            )

        # Initialize Query Context Integration
        self.query_context_integration = None
        self.query_navigator = None
        self.query_relationship_detector = None
        self.query_path_visualizer = None

        if HAS_QUERY_CONTEXT and hasattr(self.args, "query_context") and self.args.query_context:
            # Initialize QueryActivityProvider
            self.query_context_integration = QueryActivityProvider(
                debug=hasattr(self.args, "debug") and self.args.debug,
            )

            # Initialize related components if available
            self.query_navigator = QueryNavigator(
                debug=hasattr(self.args, "debug") and self.args.debug,
            )
            self.query_relationship_detector = QueryRelationshipDetector(
                debug=hasattr(self.args, "debug") and self.args.debug,
            )

            # Initialize visualization if requested
            if hasattr(self.args, "query_visualization") and self.args.query_visualization:
                self.query_path_visualizer = QueryPathVisualizer(
                    debug=hasattr(self.args, "debug") and self.args.debug,
                )


        # Initialize Analytics Integration
        self.analytics_integration = None
        if HAS_ANALYTICS and hasattr(self.args, "analytics") and self.args.analytics:
            self.analytics_integration = register_analytics_commands(
                self,
                self.db_config,
                debug=hasattr(self.args, "debug") and self.args.debug,
            )

        while True:
            # Need UPI information about the database
            #

            if batch_file:
                # read the next line from the batch file
                user_query = batch_file.readline().strip()
                if not user_query:
                    break
            else:
                # Get query from user
                user_query = self.get_query()

                # Handle exit commands in interactive mode
                if user_query.lower() in ["exit", "quit", "bye", "leave"]:
                    return
                # Special processing for interactive mode
                if user_query in {"!status", "!help"}:
                    # Reuse the last query if this is just a status check or help request
                    if hasattr(self, "current_refined_query"):
                        user_query = self.current_refined_query

                # Check for registered commands first (direct command handling)
                if user_query.startswith("/"):
                    command = user_query.split()[0]
                    if hasattr(self, "commands") and command in self.commands:
                        # Extract arguments for the command handler
                        args = user_query.split(maxsplit=1)[1] if len(user_query.split()) > 1 else ""
                        try:
                            result = self.commands[command](args)
                            if result:
                                print(result)
                            continue
                        except OSError as e:
                            print(f"Error executing command {command}: {e!s}")
                            continue

                # Check for Archivist commands if no direct handler was found
                # Handle Knowledge Base commands
                if (
                    hasattr(self, "kb_integration")
                    and self.kb_integration
                    and user_query.startswith(
                        ("/kb", "/patterns", "/entities", "/feedback", "/insights"),
                    )
                ):
                    command_handler = self.kb_integration.commands.get(
                        user_query.split()[0],
                        None,
                    )
                    if command_handler:
                        # Extract arguments for the command handler
                        args = user_query.split(maxsplit=1)[1] if len(user_query.split()) > 1 else ""
                        result = command_handler(args)
                        print(result)
                        continue

                # Handle Archivist commands if Archivist is enabled
                if self.archivist_components:
                    # Try to handle commands with the appropriate component
                    if user_query.startswith(
                        (
                            "/memory",
                            "/forward",
                            "/load",
                            "/goals",
                            "/topics",
                            "/strategies",
                            "/save",
                        ),
                    ):
                        memory_integration = self.archivist_components.get(
                            "memory_integration",
                        )
                        if memory_integration and memory_integration.handle_command(
                            user_query,
                        ):
                            continue

                elif user_query.startswith(("/optimize", "/analyze", "/index", "/view", "/query", "/impact")):
                    optimizer_integration = self.archivist_components.get("optimizer_integration")
                    if optimizer_integration and optimizer_integration.handle_command(user_query):
                        continue

                    if user_query.startswith(
                        (
                            "/proactive",
                            "/suggest",
                            "/priorities",
                            "/enable",
                            "/disable",
                        ),
                    ):
                        if (
                            hasattr(self, "proactive_integration")
                            and self.proactive_integration
                            and self.proactive_integration.handle_command(user_query)
                        ):
                            continue

                    # Handle Semantic Performance Monitoring commands
                    elif user_query.startswith(("/perf", "/experiments", "/report")):
                        if hasattr(self, "semantic_performance_integration") and self.semantic_performance_integration:
                            command_parts = user_query.split(maxsplit=1)
                            command = command_parts[0]
                            args = command_parts[1] if len(command_parts) > 1 else ""

                            if command == "/perf":
                                self.semantic_performance_integration.handle_perf_command(
                                    args.split(),
                                )
                                continue
                            if command == "/experiments":
                                self.semantic_performance_integration.handle_experiments_command(
                                    args.split(),
                                )
                                continue
                            if command == "/report":
                                self.semantic_performance_integration.handle_report_command(
                                    args.split(),
                                )
                                continue

                    # Handle Query Pattern Analysis commands
                    elif user_query.startswith("/patterns"):
                        if hasattr(self, "query_pattern_integration") and self.query_pattern_integration:
                            command_parts = user_query.split(maxsplit=1)
                            args = command_parts[1].split() if len(command_parts) > 1 else []
                            result = self.query_pattern_integration.handle_patterns_command(
                                args,
                            )
                            if result:
                                continue

                    # Handle Fire Circle commands
                    elif user_query.startswith(("/firecircle", "/fc")):
                        if hasattr(self, "fire_circle_integration") and self.fire_circle_integration:
                            # The Fire Circle CLI integration handles its own command parsing
                            handled = self.fire_circle_integration._handle_firecircle_command(
                                (user_query.split(maxsplit=1)[1] if len(user_query.split()) > 1 else ""),
                            )
                            if handled:
                                continue

                    # Handle Query Context commands
                    elif user_query.startswith("/query-path"):
                        if hasattr(self, "query_path_visualizer") and self.query_path_visualizer:
                            # Parse the command
                            args = user_query.split(maxsplit=1)[1] if len(user_query.split()) > 1 else ""

                            # Process different visualization options
                            if args.startswith("recent"):
                                # Show the most recent query path
                                limit = 5  # Default to 5 recent queries
                                if len(args.split()) > 1:
                                    with contextlib.suppress(ValueError):
                                        limit = int(args.split()[1])

                                # Get recent activities from the context provider
                                recent_activities = self.query_context_integration.get_recent_query_activities(
                                    limit=limit,
                                )
                                if recent_activities:
                                    # Generate visualization
                                    self.query_path_visualizer.generate_path_graph(
                                        query_id=recent_activities[0].query_id,
                                        include_branches=True,
                                        max_depth=limit,
                                    )
                                else:
                                    pass

                            elif args.startswith("type"):
                                # Show queries by relationship type
                                relationship_type = args.split()[1] if len(args.split()) > 1 else "refinement"

                                # Generate visualization for the specified relationship type
                                self.query_path_visualizer.generate_relationship_graph(
                                    relationship_type=relationship_type,
                                )

                            elif args.startswith("help") or args == "":
                                # Show help information
                                pass

                            else:
                                pass

                            continue

                    # Handle Analytics commands
                    elif user_query.startswith("/analytics"):
                        if hasattr(self, "analytics_integration") and self.analytics_integration:
                            # Extract arguments for the analytics command
                            args = user_query.split(maxsplit=1)[1] if len(user_query.split()) > 1 else ""

                            # Process the analytics command
                            result = self.analytics_integration.handle_analytics_command(
                                args,
                            )
                            continue

                    elif user_query.startswith(
                        (
                            "/proactive",
                            "/suggest",
                            "/priorities",
                            "/enable",
                            "/disable",
                        ),
                    ):
                        if (
                            hasattr(self, "proactive_integration")
                            and self.proactive_integration
                            and self.proactive_integration.handle_command(user_query)
                        ):
                            continue

                    # Handle Semantic Performance Monitoring commands
                    elif user_query.startswith(("/perf", "/experiments", "/report")):
                        if hasattr(self, "semantic_performance_integration") and self.semantic_performance_integration:
                            command_parts = user_query.split(maxsplit=1)
                            command = command_parts[0]
                            args = command_parts[1] if len(command_parts) > 1 else ""

                            if command == "/perf":
                                self.semantic_performance_integration.handle_perf_command(
                                    args.split(),
                                )
                                continue
                            if command == "/experiments":
                                self.semantic_performance_integration.handle_experiments_command(
                                    args.split(),
                                )
                                continue
                            if command == "/report":
                                self.semantic_performance_integration.handle_report_command(
                                    args.split(),
                                )
                                continue

                    # Handle Query Pattern Analysis commands
                    elif user_query.startswith("/patterns"):
                        if hasattr(self,
                                   "query_pattern_integration",
                                   ) and self.query_pattern_integration:
                            command_parts = user_query.split(maxsplit=1)
                            args = command_parts[1].split() if len(command_parts) > 1 else []
                            result = self.query_pattern_integration.handle_patterns_command(
                                args,
                            )
                            if result:
                                continue

                    # Handle Fire Circle commands
                    elif user_query.startswith(("/firecircle", "/fc")):
                        if hasattr(
                            self,
                            "fire_circle_integration") and self.fire_circle_integration:
                            # The Fire Circle CLI integration handles its own command parsing
                            self.fire_circle_integration._handle_firecircle_command(
                                (user_query.split(maxsplit=1)[1]
                                 if len(user_query.split()) > 1 else ""),
                            )

                    # Handle Query Context commands
                    elif user_query.startswith("/query-path"):
                        if hasattr(self, "query_path_visualizer") and self.query_path_visualizer:
                            # Parse the command
                            args = user_query.split(maxsplit=1)[1] if len(user_query.split()) > 1 else ""

                            # Process different visualization options
                            if args.startswith("recent"):
                                # Show the most recent query path
                                limit = 5  # Default to 5 recent queries
                                if len(args.split()) > 1:
                                    with contextlib.suppress(ValueError):
                                        limit = int(args.split()[1])

                                # Get recent activities from the context provider
                                recent_activities = self.query_context_integration.get_recent_query_activities(
                                    limit=limit,
                                )
                                if recent_activities:
                                    # Generate visualization
                                    self.query_path_visualizer.generate_path_graph(
                                        query_id=recent_activities[0].query_id,
                                        include_branches=True,
                                        max_depth=limit,
                                    )
                                else:
                                    pass

                            elif args.startswith("type"):
                                # Show queries by relationship type
                                relationship_type = args.split()[1] if len(args.split()) > 1 else "refinement"

                                # Generate visualization for the specified relationship type
                                self.query_path_visualizer.generate_relationship_graph(
                                    relationship_type=relationship_type,
                                )

                            elif args.startswith("help") or args == "":
                                # Show help information
                                pass

                            else:
                                pass

                            continue

                    # Handle Analytics commands
                    elif user_query.startswith("/analytics"):
                        if hasattr(self, "analytics_integration") and self.analytics_integration:
                            # Extract arguments for the analytics command
                            args = user_query.split(maxsplit=1)[1] if len(user_query.split()) > 1 else ""

                            # Process the analytics command
                            result = self.analytics_integration.handle_analytics_command(
                                args,
                            )
                            continue

            # Log the query
            # self.logging_service.log_query(user_query)
            start_time = datetime.now(UTC)

            # Check if we should use enhanced NL parsing
            use_enhanced = hasattr(self.args, "enhanced_nl") and self.args.enhanced_nl
            use_context = hasattr(self.args, "context_aware") and self.args.context_aware

            # Apply Knowledge Base enhancement if enabled
            kb_enabled = (
                hasattr(self.args, "kb") and self.args.kb and hasattr(self, "kb_integration") and self.kb_integration
            )

            if kb_enabled:
                # Extract entities from the query with minimal parsing
                # Just to get some entity context for the KB
                basic_entities = []
                try:
                    # Try to extract some basic entities for context
                    temp_parsed = self.nl_parser.parse(query=user_query)
                    for entity in temp_parsed.Entities.entities:
                        basic_entities.append(
                            {
                                "name": entity.name,
                                "type": (entity.category if hasattr(entity, "category") else "unknown"),
                                "original_text": entity.name,
                            },
                        )
                except OSError as e:
                    # If entity extraction fails, proceed without entities
                    ic(f"Failed to extract entities for KB: {e}")

                # Enhance query using Knowledge Base
                kb_enhanced = enhance_query_with_kb(
                    self,
                    user_query,
                    intent="search",
                    entities=basic_entities,
                )

                # If KB successfully enhanced the query, use the enhanced version
                if kb_enhanced.get("enhancements_applied", False):
                    ic(f"KB enhanced query: {kb_enhanced.get('enhanced_query')}")
                    # Use the enhanced query for further processing
                    enhanced_query = kb_enhanced.get("enhanced_query", user_query)
                    # Keep original query for reference
                    user_query = enhanced_query

            if use_enhanced:
                # Use enhanced natural language parser
                ic(f"Enhanced parsing of query: {user_query}")

                # Get dynamic facets for context if available
                facet_context = (
                    self.facet_generator.last_facets if hasattr(self.facet_generator, "last_facets") else None
                )

                # Check if the enhanced parser has the necessary method
                if hasattr(self.nl_parser, "parse_enhanced"):
                    # Parse with enhanced understanding
                    enhanced_understanding = self.nl_parser.parse_enhanced(
                        query=user_query,
                        facet_context=facet_context,
                        include_history=use_context,
                    )

                    # Create input for enhanced translator
                    query_data = TranslatorInput(
                        Query=enhanced_understanding,
                        Connector=self.llm_connector,
                    )

                    # Translate using enhanced translator if available
                    if hasattr(self.query_translator, "translate_enhanced"):
                        translated_query = self.query_translator.translate_enhanced(
                            enhanced_understanding,
                            query_data,
                        )
                    else:
                        # Fall back to regular translation
                        ic("Enhanced translator not available, falling back to regular translator")
                        # Convert to structured query format expected by regular translator
                        parsed_query = self.nl_parser.parse(query=user_query)
                        structured_query = self._create_structured_query(parsed_query, user_query)
                        query_data = TranslatorInput(
                            Query=structured_query,
                            Connector=self.llm_connector,
                        )
                        translated_query = self.query_translator.translate(query_data)
                else:
                    # Fall back to regular parsing
                    ic("Enhanced NL parser not available, falling back to regular parser")
                    parsed_query = self.nl_parser.parse(query=user_query)

                    # Map to structured query
                    structured_query = self._create_structured_query(parsed_query, user_query)

                    # Create input for standard translator
                    query_data = TranslatorInput(
                        Query=structured_query,
                        Connector=self.llm_connector,
                    )

                    # Translate using standard translator
                    translated_query = self.query_translator.translate(query_data)

                # Store for history and facet context
                self.last_query_understanding = enhanced_understanding

            else:
                # Standard parsing flow
                ic(f"Parsing query: {user_query}")
                parsed_query = self.nl_parser.parse(query=user_query)
                ParserResults.model_validate(parsed_query)

                # Only support search for now.
                if parsed_query.Intent.intent != "search":
                    pass
                ic(f"Query Type: {parsed_query.Intent.intent}")

                # Map entities to database attributes
                entity_mappings = self.map_entities(parsed_query.Entities)

                # Use the categories to obtain the metadata attributes
                # of the corresponding collection
                collection_categories = [
                    entity.collection for entity in parsed_query.Categories.category_map
                ]
                collection_metadata = self.get_collection_metadata(
                    collection_categories,
                )

                # Let's get the index data
                indices = {}
                for category in collection_categories:
                    collection_indices = self.db_config.get_arangodb().collection(
                        category,
                    ).indexes()
                    for index in collection_indices:
                        if category not in indices:
                            indices[category] = []
                        if index["type"] != "primary":
                            kwargs = {
                                "Name": index["name"],
                                "Type": index["type"],
                                "Fields": index["fields"],
                            }
                            if "unique" in index:
                                kwargs["Unique"] = index["unique"]
                            if "sparse" in index:
                                kwargs["Sparse"] = index["sparse"]
                            if "deduplicate" in index:
                                kwargs["Deduplicate"] = index["deduplicate"]
                            indices[category].append(
                                IndalekoCollectionIndexDataModel(**kwargs),
                            )

                # Create structured query
                structured_query = StructuredQuery(
                    original_query=user_query,
                    intent=parsed_query.Intent.intent,
                    entities=entity_mappings,
                    db_info=collection_metadata,
                    db_indices=indices,
                )
                query_data = TranslatorInput(
                    Query=structured_query,
                    Connector=self.llm_connector,
                )

                # Standard translation
                translated_query = self.query_translator.translate(query_data)

            ic(translated_query.bind_vars)

            # Always get the query execution plan first
            try:
                explain_results = self.query_executor.explain_query(
                    translated_query.aql_query,
                    self.db_config,
                    bind_vars=translated_query.bind_vars,
                    all_plans=(self.args.all_plans if hasattr(self.args, "all_plans") else False),
                    max_plans=self.args.max_plans if hasattr(self.args, "max_plans") else 5,
                )
            except AQLQueryExplainError as err:
                # seen it happen for collections that exist!
                explain_results = None
                ic('explain_query failure', err)


            # Execute the query or only display the execution plan
            if hasattr(self.args, "explain") and self.args.explain:
                # Display the execution plan
                self.display_execution_plan(explain_results, translated_query.aql_query)

                # In EXPLAIN mode, we don't process results further
                raw_results = explain_results
                analyzed_results = explain_results
                facets = []
                ranked_results = [{"original": {"result": explain_results}}]
            else:
                # Execute the query with performance metrics and deduplication if requested
                collect_perf = hasattr(self.args, "perf") and self.args.perf
                deduplicate = hasattr(self.args, "deduplicate") and self.args.deduplicate
                similarity_threshold = (
                    self.args.similarity_threshold if hasattr(self.args, "similarity_threshold") else 0.85
                )

                # Use the bind variables from the translated query
                bind_vars = getattr(translated_query, "bind_vars", {})

                ic("cli", bind_vars)

                raw_results = self.query_executor.execute(
                    translated_query.aql_query,
                    self.db_config,
                    bind_vars=bind_vars,
                    collect_performance=collect_perf,
                    deduplicate=deduplicate,
                    similarity_threshold=similarity_threshold,
                )

                # If requested, display the execution plan
                if hasattr(self.args, "show_plan") and self.args.show_plan:
                    self.display_execution_plan(
                        explain_results,
                        translated_query.aql_query,
                    )

                # Handle results based on whether they're deduplicated or not
                if isinstance(raw_results, FormattedResults):
                    # For deduplicated results, we already have analyzed data
                    analyzed_results = raw_results

                    # Extract the primary results for facet generation
                    primary_results = [group.primary for group in raw_results.result_groups]
                    facets = self.facet_generator.generate(primary_results)

                    # No need for further ranking since deduplication handles this
                    ranked_results = raw_results
                else:
                    # For regular results, proceed with analysis and ranking
                    analyzed_results = self.metadata_analyzer.analyze(raw_results)
                    facets = self.facet_generator.generate(analyzed_results)
                    ranked_results = self.result_ranker.rank(analyzed_results)

            # Display results to user
            self.display_results(ranked_results, facets)
            ic(facets)

            # Prepare query history entry, capping result sizes to avoid huge payloads
            MAX_HISTORY_RESULTS = 10
            # RawResults may be a list or FormattedResults; truncate to primaries if needed
            if isinstance(raw_results, FormattedResults):
                [grp.primary for grp in raw_results.result_groups[:MAX_HISTORY_RESULTS]]
            else:
                raw_results[:MAX_HISTORY_RESULTS]
            # AnalyzedResults is a list of dicts or None; truncate list
            if isinstance(analyzed_results, list):
                analyzed_results[:MAX_HISTORY_RESULTS]
            else:
                pass
            # RankedResults should be a list of dicts; truncate or extract primaries
            if isinstance(ranked_results, FormattedResults):
                [grp.primary for grp in ranked_results.result_groups[:MAX_HISTORY_RESULTS]]
            elif isinstance(ranked_results, list):
                ranked_results[:MAX_HISTORY_RESULTS]
            else:
                pass
            # Build history record
            end_time = datetime.now(UTC)
            time_diference = end_time - start_time

            # Convert facets to the right format for QueryHistoryData
            facets_data = facets
            # Check if facets is a DynamicFacets object and convert to dict
            if hasattr(facets, "model_dump"):
                facets_data = facets.model_dump()

            # Convert ranked results if needed
            ranked_data = ranked_results
            if hasattr(ranked_results, "model_dump"):
                ranked_data = ranked_results.model_dump()

            query_history = QueryHistoryData(
                OriginalQuery=user_query,
                ParsedResults=parsed_query,
                LLMName=self.llm_connector.get_llm_name(),
                LLMQuery=structured_query,
                TranslatedOutput=translated_query,
                ExecutionPlan=explain_results,
                RawResults=raw_results,
                AnalyzedResults=analyzed_results,
                Facets=facets_data,
                RankedResults=ranked_data,
                StartTimestamp=start_time,
                EndTimestamp=end_time,
                ElapsedTime=time_diference.total_seconds(),
            )
            self.query_history.add(query_history)

            # Record query in activity context if enabled
            if hasattr(self, "query_context_integration") and self.query_context_integration:
                # Extract result count
                result_count = 0
                if isinstance(ranked_results, FormattedResults):
                    result_count = len(ranked_results.result_groups)
                elif isinstance(ranked_results, list):
                    result_count = len(ranked_results)

                # Get relationship type if available and a previous query exists
                relationship_type = None
                previous_query_id = None

                if (
                    hasattr(self, "query_relationship_detector")
                    and self.query_relationship_detector
                    and len(self.query_history.get_query_history()) > 1
                ):
                    previous_query = self.query_history.get_query_history()[-2].OriginalQuery
                    current_query = user_query

                    # Detect relationship between current and previous query
                    relationship = self.query_relationship_detector.detect_relationship(
                        previous_query,
                        current_query,
                    )

                    if relationship:
                        relationship_type = relationship.value
                        # Get the previous query ID from our activity provider if available
                        previous_activities = self.query_context_integration.get_recent_query_activities(
                            limit=1,
                        )
                        if previous_activities:
                            previous_query_id = previous_activities[0].query_id

                # Record the query as an activity
                query_activity = self.query_context_integration.record_query(
                    query_text=user_query,
                    results={"count": result_count},
                    execution_time=time_diference.total_seconds(),
                    relationship_type=relationship_type,
                    previous_query_id=previous_query_id,
                )

                # Store the query ID in the query history for reference
                if query_activity:
                    query_history.query_activity_id = str(query_activity.query_id)

            # Update proactive archivist with query context if enabled
            if hasattr(self, "proactive_integration") and self.proactive_integration:
                # Create context with query results information
                results_count = 0
                if isinstance(ranked_results, FormattedResults):
                    results_count = len(ranked_results.result_groups)
                elif isinstance(ranked_results, list):
                    results_count = len(ranked_results)

                # Update proactive context with this query
                self.proactive_integration.update_context_with_query(
                    user_query,
                    results={"count": results_count},
                )

            # Record query results with Knowledge Base if enabled
            if hasattr(self.args, "kb") and self.args.kb and hasattr(
                self, "kb_integration") and self.kb_integration:
                # Prepare result info for KB
                result_info = {
                    "count": 0,
                    "quality": 0.8,  # Default quality
                    "collections": [],
                    "execution_time": 0.0,
                }

                # Extract result count
                if isinstance(ranked_results, FormattedResults):
                    result_info["count"] = len(ranked_results.result_groups)
                elif isinstance(ranked_results, list):
                    result_info["count"] = len(ranked_results)

                # Extract collections from the query
                if hasattr(translated_query, "collections"):
                    result_info["collections"] = translated_query.collections

                # Extract any entities if available
                entities = []
                try:
                    if use_enhanced and hasattr(self, "last_query_understanding"):
                        # Use entities from enhanced understanding
                        for entity in self.last_query_understanding.entities:
                            entities.append(
                                {
                                    "name": entity.name,
                                    "type": (entity.type if hasattr(entity, "type") else "unknown"),
                                    "original_text": entity.name,
                                },
                            )
                    else:
                        # Use entities from standard parsing
                        for entity in parsed_query.Entities.entities:
                            entities.append(
                                {
                                    "name": entity.name,
                                    "type": (entity.category if hasattr(entity, "category") else "unknown"),
                                    "original_text": entity.name,
                                },
                            )
                except OSError as e:
                    # If entity extraction fails, proceed without entities
                    ic(f"Failed to extract entities for KB recording: {e}")

                # Record results with Knowledge Base
                record_query_results(
                    self,
                    user_query,
                    result_info=result_info,
                    intent="search",
                    entities=entities,
                )

    def map_entities(
        self,
        entity_list: NamedEntityCollection,
    ) -> list[NamedEntityCollection]:
        """
        Construct a new list that maps the entities into values from the NER collection.

        Args:
            entities (List[NamedEntityCollection]): The list of named entities to try mapping.

        Returns:
            List[NamedEntityCollection]: The list of named entities with mapped values.

        If a named entity cannot be mapped, it is omitted from the returned list.  If it
        can be mapped, the entry is replaced with the mapped value from the NER collection.
        """
        mapped_entities = []
        collection = self.db_config.get_arangodb().collection(
            IndalekoDBCollections.Indaleko_Named_Entity_Collection,
        )
        if collection is None:
            return NamedEntityCollection(entities=mapped_entities)
        for entity in entity_list.entities:
            if entity.name is None:
                continue
            docs = list(collection.find({"name": entity.name}))
            if docs is None or len(docs) == 0:
                ic(f"NER mapping: Could not find entity: {entity.name}")
                continue
            if len(docs) > 1:
                ic(f"NER mapping: Multiple entities found for: {entity.name}")
                raise NotImplementedError("Multiple entities found, not handled yet")
            doc = docs[0]
            ic(docs)
            ic(doc)

            mapped_entities.append(
                IndalekoNamedEntityDataModel(
                    name=entity.name,
                    uuid=doc.uuid,
                    category=doc.category,
                    description=doc.description,
                    gis_location=doc.gis_location,
                    device_id=doc.device_id,
                ),
            )
        return NamedEntityCollection(entities=mapped_entities)

    def _create_structured_query(self, parsed_query, original_query_text):
        """Create a structured query from parsed query data.

        Args:
            parsed_query: The parsed query result from the NL parser
            original_query_text: The original query text

        Returns:
            StructuredQuery: A structured query ready for the translator
        """
        from query.query_processing.data_models.query_input import StructuredQuery

        # Map entities
        entity_mappings = self.map_entities(parsed_query.Entities)

        # Use the categories to obtain the metadata attributes
        collection_categories = [
            entity.collection for entity in parsed_query.Categories.category_map
        ]

        # Get collection metadata
        collection_metadata = self.get_collection_metadata(collection_categories)

        # Get collection indices
        indices = {}
        for category in collection_categories:
            try:
                collection_indices = self.db_config.get_arangodb().collection(
                    category,
                ).indexes()

                for index in collection_indices:
                    if category not in indices:
                        indices[category] = []
                    if index["type"] != "primary":
                        kwargs = {
                            "Name": index["name"],
                            "Type": index["type"],
                            "Fields": index["fields"],
                        }
                        if "unique" in index:
                            kwargs["Unique"] = index["unique"]
                        if "sparse" in index:
                            kwargs["Sparse"] = index["sparse"]
                        if "deduplicate" in index:
                            kwargs["Deduplicate"] = index["deduplicate"]
                        indices[category].append(
                            IndalekoCollectionIndexDataModel(**kwargs),
                        )
            except (GeneratorExit , RecursionError , MemoryError , NotImplementedError ) as e:
                ic(f"Error getting indices for {category}: {str(e)}")

        # Create structured query
        structured_query = StructuredQuery(
            original_query=original_query_text,
            intent=parsed_query.Intent.intent,
            entities=entity_mappings,
            db_info=collection_metadata,
            db_indices=indices,
        )

        return structured_query

    def get_collection_metadata(
        self,
        categories: list[str],
    ) -> list[IndalekoCollectionMetadataDataModel]:
        """Get the metadata for the collections based upon the selected categories."""
        if self.collections_metadata is None:
            return []
        collection_metadata = []

        # Check if get_collection_metadata method exists
        if hasattr(self.collections_metadata, "get_collection_metadata"):
            # Use the existing method
            for category in categories:
                metadata = self.collections_metadata.get_collection_metadata(category)
                if metadata is None:
                    ic(f"Failed to get metadata for category: {category}")
                else:
                    collection_metadata.append(metadata)
        else:
            # Fallback implementation
            collections_metadata = getattr(
                self.collections_metadata,
                "collections_metadata",
                {},
            )
            for category in categories:
                if category in collections_metadata:
                    # Use the metadata from the collections_metadata dictionary
                    metadata = collections_metadata[category]
                    collection_metadata.append(metadata)
                else:
                    ic(f"Failed to get metadata for category: {category}")
                    # Create a default metadata object
                    from data_models.collection_metadata_data_model import (
                        IndalekoCollectionMetadataDataModel,
                    )

                    default_metadata = IndalekoCollectionMetadataDataModel(
                        key=category,
                        Description=f"Collection for {category}",
                        QueryGuidelines=[f"Search for {category}"],
                        Schema={},
                    )
                    collection_metadata.append(default_metadata)

        return collection_metadata

    def get_query(self) -> str:
        """Get a query from the user."""
        query = input(self.prompt).strip()

        # Special commands for interactive refinement
        if query.startswith("!refine "):
            if hasattr(self, "last_facet_options") and self.last_facet_options:
                # Parse the refinement selection
                try:
                    selection = query.split(" ", 1)[1].strip()
                    if selection in self.last_facet_options:
                        option = self.last_facet_options[selection]
                        # Apply the refinement
                        if hasattr(self, "original_query"):
                            refined_query, _ = self.query_refiner.apply_refinement(
                                option["facet"],
                                option["value"],
                            )
                            return refined_query
                except OSError as e:
                    print(f"Error applying refinement: {e}")

            # If we couldn't apply refinement, return the original query
            if hasattr(self, "current_refined_query"):
                return self.current_refined_query

        # Special command to clear refinements
        if query == "!clear":
            if hasattr(self, "original_query") and self.query_refiner.current_state:
                original, _ = self.query_refiner.clear_refinements()
                self.current_refined_query = original
                return original

        # Special command to show active refinements
        if query == "!status" and self.query_refiner.current_state:
            if hasattr(self, "current_refined_query"):
                return "!status"  # Special marker to reuse last query

        # Special command to remove a refinement
        if query.startswith("!remove "):
            if self.query_refiner.current_state:
                try:
                    index = int(query.split(" ", 1)[1].strip())
                    refinement = self.query_refiner.get_active_refinement_by_index(
                        index,
                    )
                    if refinement:
                        refined_query, _ = self.query_refiner.remove_refinement(
                            refinement.facet_name,
                            refinement.value,
                        )
                        print(
                            f"Removed refinement: {refinement.facet_name}: {refinement.value}",
                        )
                        print(f"Refined query: {refined_query}")
                        self.current_refined_query = refined_query
                        return refined_query
                except OSError as e:
                    print(f"Error removing refinement: {e}")

        # Special command to show help for interactive mode
        if query == "!help":
            self._print_interactive_help()
            if hasattr(self, "current_refined_query"):
                return "!help"  # Special marker to reuse last query

        # Store the original query for refinement
        if not query.startswith("!"):
            self.original_query = query
            self.current_refined_query = query
            # Initialize refinement state with this query
            self.query_refiner.initialize_state(query)

        return query

    def _print_interactive_help(self) -> None:
        """Print help information for interactive refinement mode."""

    def display_results(
        self,
        results: list[dict[str, Any]] | FormattedResults,
        facets: list[str] | DynamicFacets,
    ) -> None:
        """
        Displays the search results and suggested facets to the user.

        Args:
            results: The search results, either as a list of ranked results or a FormattedResults object
            facets: Facet suggestions, either as a list of strings or a DynamicFacets object
        """
        if not results:
            return

        # Handle deduplicated results (FormattedResults object)
        if isinstance(results, FormattedResults):
            # Display formatted results using the formatter
            include_duplicates = hasattr(self.args, "show_duplicates") and self.args.show_duplicates
            format_results_for_display(
                results,
                include_duplicates=include_duplicates,
                max_groups=10,
                include_summary=True,
            )

            # Display facets after results
            self._display_facets(facets)
            return

        # Handle regular results (list of dictionaries)
        # Check if this is an EXPLAIN result
        if (
            len(results) == 1
            and isinstance(results[0]["original"]["result"], dict)
            and "plan" in results[0]["original"]["result"]
        ):
            # This is already displayed by display_execution_plan
            return

        ic(len(results))
        for result in results:
            ic(result)
        if len(results) < 10:
            for i, result in enumerate(results, 1):
                assert isinstance(result, dict), "Result should be a dictionary"
                doc = result.get("original")
                if doc is None:
                    ic("Skipping ", result)
                if isinstance(doc, int):
                    ic(f"Result {i}: {doc}")
                elif isinstance(doc, dict) and "performance" in doc:
                    # Display performance metrics if available
                    doc["performance"]
                elif (
                    isinstance(doc, dict)
                    and "Record" in doc
                    and "Attributes" in doc["Record"]
                    and "Path" in doc["Record"]["Attributes"]
                ):
                    ic(doc["Record"]["Attributes"]["Path"])
                else:
                    ic(f"Result {i}: {doc}")

        # Display facets after results
        self._display_facets(facets)

    def _display_facets(self, facets: list[str] | DynamicFacets) -> None:
        """
        Display facets to the user.

        Args:
            facets: Either a list of string facets or a DynamicFacets object
        """
        # Handle dynamic facets
        if isinstance(facets, DynamicFacets):
            # Check if dynamic facets or interactive mode are enabled
            use_dynamic = hasattr(self.args, "dynamic_facets") and self.args.dynamic_facets
            conversational = hasattr(self.args, "conversational") and self.args.conversational
            interactive = hasattr(self.args, "interactive") and self.args.interactive

            # Generate facet options for interactive mode
            if interactive:
                self.last_facet_options = self.query_refiner.get_facet_options(facets)

            # Show active refinements if there are any
            if interactive and self.query_refiner.current_state and self.query_refiner.current_state.active_refinements:
                pass

            if use_dynamic or interactive:
                # Display enhanced facets

                # Display statistics
                if facets.facet_statistics:
                    for key, value in sorted(facets.facet_statistics.items()):
                        # Format the key for display
                        key.replace("_", " ").capitalize()

                        # Format values appropriately
                        if isinstance(value, int) and key.endswith("size"):
                            # Format file sizes
                            if value >= 1024 * 1024 * 1024:
                                f"{value / (1024 * 1024 * 1024):.2f} GB"
                            elif value >= 1024 * 1024:
                                f"{value / (1024 * 1024):.2f} MB"
                            elif value >= 1024:
                                f"{value / 1024:.2f} KB"
                            else:
                                pass
                        elif isinstance(value, float) and key.endswith("coverage"):
                            # Format coverage percentages
                            f"{value * 100:.1f}%"
                        else:
                            str(value)


                # Display facets with interactive options if enabled
                option_count = 1
                for facet in facets.facets:

                    # Print facet metadata
                    facet.coverage * 100

                    # Print facet values
                    for _i, value in enumerate(facet.values[:5], 1):
                        if interactive:
                            # Show with numbered options for interactive mode
                            option_count += 1
                        else:
                            # Show regular format for non-interactive mode
                            pass

                    # If there are more values, indicate this
                    if len(facet.values) > 5:
                        len(facet.values) - 5

                # Display conversational hints if enabled
                if conversational and facets.conversational_hints:
                    for _hint in facets.conversational_hints:
                        pass

                # Display interactive mode help if enabled
                if interactive:
                    pass

            elif facets.suggestions:
                for _suggestion in facets.suggestions:
                    pass

        # Handle legacy string facets
        elif facets:
            for facet in facets:
                pass

    def display_execution_plan(self, plan_data: dict, query: str) -> None:
        """
        Displays the query execution plan in a formatted way.

        Args:
            plan_data (Dict): The execution plan from ArangoDB
            query (str): The original AQL query
        """
        # Add the query to the plan data if not present
        if "query" not in plan_data:
            plan_data["query"] = query

        # Use our enhanced plan visualizer
        verbose = hasattr(self.args, "verbose") and self.args.verbose

        # Parse the plan and visualize it as text
        self.plan_visualizer.visualize_text(plan_data, verbose=verbose)

        # Print the visualization

    def continue_session(self) -> bool:
        """Check if the user wants to continue the session."""
        continue_session = input("Do you want to continue? [Y/N] ").strip().lower() in [
            "y",
            "yes",
        ]

        # If ending the session and Archivist is enabled, update memory
        if not continue_session and self.archivist_components:
            memory_integration = self.archivist_components.get("memory_integration")
            if memory_integration:
                memory_integration.update_from_session(self.query_history)

            # Update proactive archivist if enabled
            if hasattr(self, "proactive_integration") and self.proactive_integration:
                self.proactive_integration.analyze_session(self.query_history)

        # If ending the session and Fire Circle is enabled, update pattern suggestions
        if not continue_session and hasattr(self, "fire_circle_integration") and self.fire_circle_integration:
            # Get Fire Circle integration through Fire Circle CLI
            fc_integration = getattr(
                self.fire_circle_integration,
                "fc_integration",
                None,
            )
            if fc_integration:
                # Convert query history to a format that Fire Circle can use
                query_history_data = []
                for entry in self.query_history.get_query_history():
                    query_data = {
                        "query": entry.OriginalQuery,
                        "timestamp": entry.StartTimestamp.timestamp(),
                        "result_count": 0,
                    }

                    # Try to extract result count if available
                    if isinstance(entry.RankedResults, list):
                        query_data["result_count"] = len(entry.RankedResults)
                    elif hasattr(entry.RankedResults, "result_groups"):
                        query_data["result_count"] = len(
                            entry.RankedResults.result_groups,
                        )

                    query_history_data.append(query_data)

                # Suggest patterns if we have query history
                if query_history_data:
                    fc_integration.suggest_knowledge_patterns(query_history_data)

        return continue_session

    def build_schema_table(self) -> dict:
        """Build the schema table."""
        schema = {}
        for collection in self.db_config.get_arangodb().collections():
            name = collection["name"]
            if name.startswith("_"):
                continue
            doc = self.db_config.get_arangodb().collection(name)
            properties = doc.properties()
            schema[name] = properties["schema"]
        return schema


def main() -> None:
    """A CLI based query tool for Indaleko."""
    ic("Starting Indaleko Query CLI")

    # Quick check for batch mode with a very simple parse

    IndalekoQueryCLI().run()


    # Only show exit message in interactive mode
    print("Thank you for using Indaleko Query CLI")  # noqa: T201
    print("Have a lovely day!")   # noqa: T201


if __name__ == "__main__":
    main()
