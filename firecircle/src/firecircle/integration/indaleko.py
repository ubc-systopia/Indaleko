"""
Fire Circle Indaleko Integration.

This module provides the main integration between the Fire Circle
implementation and the broader Indaleko system.

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

import logging
import os
import subprocess
import sys
from typing import Any

from firecircle.entities.registry import EntityRegistry
from firecircle.integration.archivist import ArchivistIntegration
from firecircle.memory.context import CircleContext
from firecircle.memory.persistence import ConversationMemory, InsightMemory

from firecircle.protocol.orchestrator import CircleOrchestrator, ConversationPhase


class IndalekoIntegration:
    """
    Main integration class for the Fire Circle with Indaleko.

    This class provides the primary interface between the Fire Circle
    implementation and the broader Indaleko system.
    """

    def __init__(self, logger: logging.Logger | None = None):
        """
        Initialize the Indaleko integration.

        Args:
            logger: Optional logger for integration events
        """
        self.logger = logger or logging.getLogger(__name__)

        # Initialize integrations
        self.archivist = ArchivistIntegration()

        # Detect Indaleko environment
        self.indaleko_root = self._detect_indaleko_root()
        if self.indaleko_root:
            self.logger.info(f"Detected Indaleko root: {self.indaleko_root}")
            sys.path.append(self.indaleko_root)
        else:
            self.logger.warning(
                "Could not detect Indaleko root, some functionality may be limited",
            )

        # Try to import Indaleko-specific modules
        self.query_system_available = False
        try:
            from query.cli import IndalekoQueryCLI

            self.query_system_available = True
            self.logger.info("Successfully connected to Indaleko query system")
        except ImportError:
            self.logger.warning(
                "Indaleko query system not available, query functionality will be limited",
            )

    def _detect_indaleko_root(self) -> str | None:
        """
        Detect the Indaleko root directory.

        Returns:
            Path to Indaleko root if found, None otherwise
        """
        # Check if environment variable is set
        if "INDALEKO_ROOT" in os.environ:
            return os.environ["INDALEKO_ROOT"]

        # Try to find Indaleko.py in parent directories
        current_path = os.path.dirname(os.path.abspath(__file__))
        while True:
            if os.path.exists(os.path.join(current_path, "Indaleko.py")):
                return current_path

            parent_path = os.path.dirname(current_path)
            if parent_path == current_path:
                # Reached root without finding Indaleko.py
                break
            current_path = parent_path

        return None

    def execute_query(self, query: str) -> dict[str, Any]:
        """
        Execute a query using the Indaleko query system.

        Args:
            query: The query to execute

        Returns:
            Query results
        """
        if not self.query_system_available:
            self.logger.warning(
                "Indaleko query system not available, cannot execute query",
            )
            return {"error": "Query system not available"}

        try:
            from query.cli import IndalekoQueryCLI

            # Create CLI instance
            cli = IndalekoQueryCLI()

            # Execute query
            result = cli.execute_query(query)

            self.logger.info(f"Executed query: {query}")
            return result

        except Exception as e:
            self.logger.error(f"Error executing query: {e}")
            return {"error": str(e)}

    def explain_query(self, query: str) -> dict[str, Any]:
        """
        Explain a query using the Indaleko query system.

        Args:
            query: The query to explain

        Returns:
            Query explanation
        """
        if not self.query_system_available:
            self.logger.warning(
                "Indaleko query system not available, cannot explain query",
            )
            return {"error": "Query system not available"}

        try:
            from query.cli import IndalekoQueryCLI

            # Create CLI instance
            cli = IndalekoQueryCLI()

            # Explain query
            result = cli.explain_query(query)

            self.logger.info(f"Explained query: {query}")
            return result

        except Exception as e:
            self.logger.error(f"Error explaining query: {e}")
            return {"error": str(e)}

    def get_database_info(self) -> dict[str, Any]:
        """
        Get information about the Indaleko database.

        Returns:
            Database information
        """
        if not self.indaleko_root:
            self.logger.warning("Indaleko root not detected, cannot get database info")
            return {"error": "Indaleko root not detected"}

        try:
            # Try to import Indaleko database info module
            sys.path.append(self.indaleko_root)
            from db.db_info import get_database_info

            # Get database info
            info = get_database_info()

            self.logger.info("Retrieved database information")
            return info

        except ImportError:
            self.logger.error("Could not import db.db_info module")
            return {"error": "Could not import database info module"}

        except Exception as e:
            self.logger.error(f"Error getting database info: {e}")
            return {"error": str(e)}

    def export_circle_insights(
        self, insights: list[InsightMemory], store_in_archivist: bool = True,
    ) -> bool:
        """
        Export insights from the Fire Circle to Indaleko.

        Args:
            insights: The insights to export
            store_in_archivist: Whether to store in the Archivist

        Returns:
            True if successful, False otherwise
        """
        success = True

        # Store in Archivist if requested
        if store_in_archivist:
            for insight in insights:
                if not self.archivist.store_insight(insight):
                    success = False

        # Additional export methods could be added here

        return success

    def export_circle_conversation(
        self, conversation: ConversationMemory, store_in_archivist: bool = True,
    ) -> str | None:
        """
        Export a conversation from the Fire Circle to Indaleko.

        Args:
            conversation: The conversation to export
            store_in_archivist: Whether to store in the Archivist

        Returns:
            The ID of the stored conversation if successful, None otherwise
        """
        # Store in Archivist if requested
        if store_in_archivist:
            return self.archivist.store_conversation(conversation)

        return None

    def get_relevant_archivist_memories(
        self, query: str, max_results: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Get relevant memories from the Archivist.

        Args:
            query: The query to search with
            max_results: Maximum number of results to return

        Returns:
            List of relevant memories
        """
        return self.archivist.search_memories(query, max_results)

    def initialize_circle_from_continuation(
        self,
        continuation_id: str,
        entity_registry: EntityRegistry,
        orchestrator: CircleOrchestrator,
        context: CircleContext,
    ) -> bool:
        """
        Initialize a circle from a continuation context.

        Args:
            continuation_id: The continuation ID
            entity_registry: The entity registry
            orchestrator: The circle orchestrator
            context: The circle context

        Returns:
            True if successful, False otherwise
        """
        # Get continuation context from Archivist
        continuation_data = self.archivist.get_continuation_context(continuation_id)

        if not continuation_data:
            self.logger.warning(f"No continuation data found for ID: {continuation_id}")
            return False

        try:
            # Apply context variables
            for key, value in continuation_data.get("context_variables", {}).items():
                # Assume the first entity is the creator for simplicity
                entities = entity_registry.get_all_entities()
                if entities:
                    context.set_variable(key, value, entities[0].entity_id)

            # Set topics if available
            topics = continuation_data.get("topics", [])
            if topics and orchestrator.current_phase == ConversationPhase.OPENING:
                # Force transition to EXPLORATION with the first topic
                orchestrator.force_phase_transition(ConversationPhase.EXPLORATION)

            self.logger.info(
                f"Initialized circle from continuation ID: {continuation_id}",
            )
            return True

        except Exception as e:
            self.logger.error(f"Error initializing from continuation: {e}")
            return False

    def run_indaleko_command(self, command: list[str]) -> tuple[int, str, str]:
        """
        Run an Indaleko command.

        Args:
            command: The command to run

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        if not self.indaleko_root:
            self.logger.warning("Indaleko root not detected, cannot run command")
            return (1, "", "Indaleko root not detected")

        try:
            # Convert to string for logging
            cmd_str = " ".join(command)
            self.logger.info(f"Running Indaleko command: {cmd_str}")

            # Run command
            process = subprocess.Popen(
                command,
                cwd=self.indaleko_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Get output
            stdout, stderr = process.communicate()
            return_code = process.returncode

            if return_code == 0:
                self.logger.info(f"Command completed successfully: {cmd_str}")
            else:
                self.logger.warning(
                    f"Command failed with code {return_code}: {cmd_str}",
                )

            return (return_code, stdout, stderr)

        except Exception as e:
            self.logger.error(f"Error running command: {e}")
            return (1, "", str(e))
