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
from archivist.database_optimizer import DatabaseOptimizer
from archivist.cli_integration import DatabaseOptimizerCliIntegration
from query.memory.archivist_memory import ArchivistMemory
from query.memory.cli_integration import ArchivistCliIntegration
# pylint: enable=wrong-import-position


def register_archivist_components(cli_instance):
    """
    Register all Archivist components with the CLI.
    
    Args:
        cli_instance: The CLI instance to register with
        
    Returns:
        Dict containing the initialized components
    """
    # Initialize components
    archivist_memory = ArchivistMemory(cli_instance.db_config)
    memory_integration = ArchivistCliIntegration(cli_instance, archivist_memory)
    
    # Initialize database optimizer
    database_optimizer = DatabaseOptimizer(
        cli_instance.db_config.db,
        archivist_memory,
        cli_instance.query_history if hasattr(cli_instance, "query_history") else None
    )
    optimizer_integration = DatabaseOptimizerCliIntegration(
        cli_instance, 
        archivist_memory, 
        database_optimizer
    )
    
    # Register memory commands
    for cmd, handler in memory_integration.commands.items():
        cli_instance.register_command(cmd, memory_integration.handle_command)
    
    # Register optimizer commands
    for cmd, handler in optimizer_integration.commands.items():
        cli_instance.register_command(cmd, optimizer_integration.handle_command)
    
    # Add help text
    cli_instance.append_help_text("\nArchivist Commands:")
    cli_instance.append_help_text("  /memory              - Show archivist memory commands")
    cli_instance.append_help_text("  /forward             - Generate a forward prompt for the next session")
    cli_instance.append_help_text("  /load                - Load a forward prompt from a previous session")
    cli_instance.append_help_text("  /goals               - Manage long-term goals")
    cli_instance.append_help_text("  /insights            - View insights about search patterns")
    cli_instance.append_help_text("  /topics              - View topics of interest")
    cli_instance.append_help_text("  /strategies          - View effective search strategies")
    cli_instance.append_help_text("  /save                - Save the current memory state")
    
    cli_instance.append_help_text("\nDatabase Optimization Commands:")
    cli_instance.append_help_text("  /optimize            - Show database optimization commands")
    cli_instance.append_help_text("  /analyze             - Analyze query patterns and suggest optimizations")
    cli_instance.append_help_text("  /index               - Manage index recommendations")
    cli_instance.append_help_text("  /view                - Manage view recommendations")
    cli_instance.append_help_text("  /query               - Manage query optimizations")
    cli_instance.append_help_text("  /impact              - Show impact of applied optimizations")
    
    return {
        "memory": archivist_memory,
        "memory_integration": memory_integration,
        "database_optimizer": database_optimizer,
        "optimizer_integration": optimizer_integration
    }


def register_with_cli(cli_instance):
    """
    Register the Archivist with the CLI.
    
    Args:
        cli_instance: The CLI instance to register with
        
    Returns:
        The initialized components
    """
    return register_archivist_components(cli_instance)