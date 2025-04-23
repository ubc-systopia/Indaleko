"""
Main CLI integration module for the Archivist system.

This module provides a unified interface for initializing and registering
all Archivist components with the Indaleko CLI.

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

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from archivist.cli_integration import DatabaseOptimizerCliIntegration
from archivist.database_optimizer import DatabaseOptimizer
from query.memory.archivist_memory import ArchivistMemory
from query.memory.cli_integration import ArchivistCliIntegration
from query.memory.proactive_archivist import ProactiveArchivist
from query.memory.proactive_cli import ProactiveCliIntegration

# Import Query Context Integration if available
try:
    from query.context.activity_provider import QueryActivityProvider
    from query.context.navigation import QueryNavigator
    from query.context.relationship import QueryRelationshipDetector

    HAS_QUERY_CONTEXT = True
except ImportError:
    HAS_QUERY_CONTEXT = False

# Import Recommendation Engine Integration if available
try:
    from query.context.recommendations.archivist_integration import (
        RecommendationArchivistIntegration,
    )
    from query.context.recommendations.engine import RecommendationEngine

    HAS_RECOMMENDATIONS = True
except ImportError:
    HAS_RECOMMENDATIONS = False
# pylint: enable=wrong-import-position


def register_archivist_components(
    cli_instance, enable_proactive=True, enable_recommendations=True,
):
    """
    Register all Archivist components with the CLI.

    Args:
        cli_instance: The CLI instance to register with
        enable_proactive: Whether to enable proactive features
        enable_recommendations: Whether to enable query recommendations

    Returns:
        Dict containing the initialized components
    """
    # Initialize components
    archivist_memory = ArchivistMemory(cli_instance.db_config)

    # Connect to Query Context Integration if available
    query_context_provider = None
    query_navigator = None

    if HAS_QUERY_CONTEXT:
        # Check if CLI already has Query Context components
        if (
            hasattr(cli_instance, "query_context_integration")
            and cli_instance.query_context_integration
        ):
            query_context_provider = cli_instance.query_context_integration

            # Import recent query activities into Archivist memory
            if query_context_provider:
                recent_activities = query_context_provider.get_recent_query_activities(
                    limit=20,
                )
                if recent_activities:
                    archivist_memory.import_query_activities(recent_activities)

        if hasattr(cli_instance, "query_navigator") and cli_instance.query_navigator:
            query_navigator = cli_instance.query_navigator

    # Create memory integration with Query Context awareness
    memory_integration = ArchivistCliIntegration(cli_instance, archivist_memory)

    # Initialize database optimizer
    database_optimizer = DatabaseOptimizer(
        cli_instance.db_config.db,
        archivist_memory,
        cli_instance.query_history if hasattr(cli_instance, "query_history") else None,
    )
    optimizer_integration = DatabaseOptimizerCliIntegration(
        cli_instance, archivist_memory, database_optimizer,
    )

    # Initialize proactive components if enabled
    proactive_archivist = None
    proactive_integration = None
    if enable_proactive:
        proactive_archivist = ProactiveArchivist(archivist_memory)
        proactive_integration = ProactiveCliIntegration(
            cli_instance, archivist_memory, proactive_archivist,
        )

    # Initialize recommendation components if enabled
    recommendation_engine = None
    recommendation_integration = None
    if enable_recommendations and HAS_RECOMMENDATIONS:
        recommendation_engine = RecommendationEngine(
            debug=hasattr(cli_instance, "debug") and cli_instance.debug,
        )
        recommendation_integration = RecommendationArchivistIntegration(
            cli_instance, archivist_memory, proactive_archivist, recommendation_engine,
        )

    # Register memory commands
    for cmd, handler in memory_integration.commands.items():
        cli_instance.register_command(cmd, memory_integration.handle_command)

    # Register optimizer commands
    for cmd, handler in optimizer_integration.commands.items():
        cli_instance.register_command(cmd, optimizer_integration.handle_command)

    # Register proactive commands if enabled
    if enable_proactive and proactive_integration:
        for cmd, handler in proactive_integration.commands.items():
            cli_instance.register_command(cmd, proactive_integration.handle_command)

    # Register recommendation commands if enabled
    if enable_recommendations and recommendation_integration:
        recommendation_integration.register_commands()

    # Add help text
    cli_instance.append_help_text("\nArchivist Commands:")
    cli_instance.append_help_text(
        "  /memory              - Show archivist memory commands",
    )
    cli_instance.append_help_text(
        "  /forward             - Generate a forward prompt for the next session",
    )
    cli_instance.append_help_text(
        "  /load                - Load a forward prompt from a previous session",
    )
    cli_instance.append_help_text("  /goals               - Manage long-term goals")
    cli_instance.append_help_text(
        "  /insights            - View insights about search patterns",
    )
    cli_instance.append_help_text("  /topics              - View topics of interest")
    cli_instance.append_help_text(
        "  /strategies          - View effective search strategies",
    )
    cli_instance.append_help_text(
        "  /save                - Save the current memory state",
    )

    # Add Query Context Integration help text if available
    if HAS_QUERY_CONTEXT:
        cli_instance.append_help_text(
            "  /query-insights       - View insights from Query Context Integration",
        )

    cli_instance.append_help_text("\nDatabase Optimization Commands:")
    cli_instance.append_help_text(
        "  /optimize            - Show database optimization commands",
    )
    cli_instance.append_help_text(
        "  /analyze             - Analyze query patterns and suggest optimizations",
    )
    cli_instance.append_help_text(
        "  /index               - Manage index recommendations",
    )
    cli_instance.append_help_text(
        "  /view                - Manage view recommendations",
    )
    cli_instance.append_help_text("  /query               - Manage query optimizations")
    cli_instance.append_help_text(
        "  /impact              - Show impact of applied optimizations",
    )

    # Add proactive help text if enabled
    if enable_proactive:
        cli_instance.append_help_text("\nProactive Commands:")
        cli_instance.append_help_text(
            "  /proactive           - Show proactive archivist commands",
        )
        cli_instance.append_help_text(
            "  /suggest             - Show current suggestions",
        )
        cli_instance.append_help_text(
            "  /feedback            - Provide feedback on suggestions",
        )
        cli_instance.append_help_text(
            "  /patterns            - View detected temporal patterns",
        )
        cli_instance.append_help_text(
            "  /priorities          - Manage suggestion priorities",
        )
        cli_instance.append_help_text(
            "  /enable              - Enable proactive suggestions",
        )
        cli_instance.append_help_text(
            "  /disable             - Disable proactive suggestions",
        )

    result = {
        "memory": archivist_memory,
        "memory_integration": memory_integration,
        "database_optimizer": database_optimizer,
        "optimizer_integration": optimizer_integration,
    }

    if enable_proactive:
        result.update(
            {
                "proactive_archivist": proactive_archivist,
                "proactive_integration": proactive_integration,
            },
        )

    if enable_recommendations and recommendation_integration:
        result.update(
            {
                "recommendation_engine": recommendation_engine,
                "recommendation_integration": recommendation_integration,
            },
        )

    # Include Query Context components if available
    if HAS_QUERY_CONTEXT:
        result.update(
            {
                "query_context_provider": query_context_provider,
                "query_navigator": query_navigator,
            },
        )

    return result


def register_with_cli(cli_instance, enable_proactive=True, enable_recommendations=True):
    """
    Register the Archivist with the CLI.

    Args:
        cli_instance: The CLI instance to register with
        enable_proactive: Whether to enable proactive features
        enable_recommendations: Whether to enable query recommendations

    Returns:
        The initialized components
    """
    return register_archivist_components(
        cli_instance, enable_proactive, enable_recommendations,
    )
