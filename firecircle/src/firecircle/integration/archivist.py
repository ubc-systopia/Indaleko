"""
Fire Circle Archivist Integration.

This module provides integration between the Fire Circle and the
Indaleko Archivist memory system.

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
from typing import Any

from firecircle.memory.persistence import ConversationMemory, InsightMemory


class ArchivistIntegration:
    """
    Integrates the Fire Circle with the Indaleko Archivist.

    This class provides bidirectional communication between the
    Fire Circle and the Archivist memory system, allowing circle
    insights to be stored in long-term memory and relevant memories
    to be retrieved for circle discussions.
    """

    def __init__(self, logger: logging.Logger | None = None):
        """
        Initialize the Archivist integration.

        Args:
            logger: Optional logger for integration events
        """
        self.logger = logger or logging.getLogger(__name__)

        # Attempt to import the Archivist memory system
        try:
            from query.memory.archivist_memory import ArchivistMemory

            self.archivist_memory = ArchivistMemory()
            self.available = True
            self.logger.info("Successfully connected to Archivist memory system")
        except ImportError:
            self.archivist_memory = None
            self.available = False
            self.logger.warning(
                "Archivist memory system not available, integration will be limited",
            )

    def store_conversation(
        self,
        conversation_memory: ConversationMemory,
    ) -> str | None:
        """
        Store a conversation from the Fire Circle in the Archivist.

        Args:
            conversation_memory: The conversation memory to store

        Returns:
            The ID of the stored memory if successful, None otherwise
        """
        if not self.available:
            self.logger.warning("Archivist not available, cannot store conversation")
            return None

        try:
            # Convert to format expected by Archivist
            conversation_data = {
                "conversation_id": conversation_memory.conversation_id,
                "summary": conversation_memory.summary,
                "key_takeaways": [f"Fire Circle: {conversation_memory.topic}"],
                "topics": ([conversation_memory.topic] if conversation_memory.topic else []),
                "entities": conversation_memory.participants,
                "importance_score": conversation_memory.importance,
                "message_count": len(conversation_memory.messages),
                "context_variables": conversation_memory.context_snapshot,
            }

            # Store in Archivist
            continuation_id = self.archivist_memory.store_conversation_state(
                conversation_memory.conversation_id,
                conversation_data,
            )

            self.logger.info(
                f"Stored Fire Circle conversation in Archivist with ID: {continuation_id}",
            )
            return continuation_id

        except Exception as e:
            self.logger.error(f"Error storing conversation in Archivist: {e}")
            return None

    def store_insight(self, insight_memory: InsightMemory) -> bool:
        """
        Store an insight from the Fire Circle in the Archivist.

        Args:
            insight_memory: The insight memory to store

        Returns:
            True if successful, False otherwise
        """
        if not self.available:
            self.logger.warning("Archivist not available, cannot store insight")
            return False

        try:
            # Add insight to Archivist
            self.archivist_memory.add_insight(
                category=(insight_memory.categories[0] if insight_memory.categories else "general"),
                insight=insight_memory.insight,
                confidence=insight_memory.confidence,
            )

            self.logger.info("Stored Fire Circle insight in Archivist")
            return True

        except Exception as e:
            self.logger.error(f"Error storing insight in Archivist: {e}")
            return False

    def search_memories(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """
        Search the Archivist for relevant memories.

        Args:
            query: The search query
            max_results: Maximum number of results to return

        Returns:
            List of relevant memories
        """
        if not self.available:
            self.logger.warning("Archivist not available, cannot search memories")
            return []

        try:
            # Search Archivist
            memories = self.archivist_memory.search_memories(query, max_results)

            self.logger.info(f"Found {len(memories)} relevant memories in Archivist")
            return memories

        except Exception as e:
            self.logger.error(f"Error searching Archivist memories: {e}")
            return []

    def get_continuation_context(self, continuation_id: str) -> dict[str, Any]:
        """
        Get continuation context from the Archivist.

        Args:
            continuation_id: The continuation ID

        Returns:
            The continuation context
        """
        if not self.available:
            self.logger.warning(
                "Archivist not available, cannot get continuation context",
            )
            return {}

        try:
            # Get continuation context
            context = self.archivist_memory.get_continuation_context(continuation_id)

            self.logger.info(
                f"Retrieved continuation context for ID: {continuation_id}",
            )
            return context

        except Exception as e:
            self.logger.error(f"Error getting continuation context: {e}")
            return {}

    def retrieve_relevant_insights(
        self,
        topic: str,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Get relevant insights from the Archivist.

        Args:
            topic: The topic to get insights for
            limit: Maximum number of insights to return

        Returns:
            List of relevant insights
        """
        if not self.available:
            self.logger.warning("Archivist not available, cannot retrieve insights")
            return []

        try:
            # Get insights from Archivist
            insights = self.archivist_memory.get_most_relevant_insights(topic, limit)

            self.logger.info(
                f"Retrieved {len(insights)} insights from Archivist for topic: {topic}",
            )
            return insights

        except Exception as e:
            self.logger.error(f"Error retrieving insights from Archivist: {e}")
            return []
