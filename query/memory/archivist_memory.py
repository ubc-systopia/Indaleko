"""
This module defines the Archivist memory model for maintaining
context across sessions in the Indaleko project.

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

import json
import os
import sys
import uuid
from datetime import UTC, datetime
from typing import Any

from icecream import ic
from pydantic import BaseModel, Field

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
from data_models.record import IndalekoRecordDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from db import IndalekoDBCollections, IndalekoDBConfig
from utils.misc.data_management import encode_binary_data

# Import Query Context Integration components if available
try:
    from query.context.data_models.query_activity import QueryActivityData

    HAS_QUERY_CONTEXT = True
except ImportError:
    HAS_QUERY_CONTEXT = False
# pylint: enable=wrong-import-position


class UserPreference(BaseModel):
    """User preference information for search and interaction."""

    category: str = Field(
        ...,
        description="Category of preference (e.g., 'search', 'display', 'organization')",
    )
    preference: str = Field(..., description="The specific preference")
    confidence: float = Field(
        default=0.5,
        description="Confidence level in this observation (0.0-1.0)",
    )
    observation_count: int = Field(
        default=1,
        description="Number of times this preference was observed",
    )
    last_observed: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this preference was last observed",
    )


class SearchPattern(BaseModel):
    """Patterns identified in the user's search behavior."""

    pattern_type: str = Field(
        ...,
        description="Type of pattern (e.g., 'query_structure', 'refinement', 'focus')",
    )
    description: str = Field(..., description="Description of the pattern")
    examples: list[str] = Field(
        default_factory=list,
        description="Example queries demonstrating this pattern",
    )
    frequency: float = Field(
        default=0.0,
        description="Relative frequency of this pattern (0.0-1.0)",
    )


class LongTermGoal(BaseModel):
    """Representation of an ongoing long-term search or organization project."""

    name: str = Field(..., description="Name of the goal")
    description: str = Field(..., description="Detailed description of the goal")
    progress: float = Field(
        default=0.0,
        description="Estimated progress toward completion (0.0-1.0)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this goal was created",
    )
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this goal was last updated",
    )
    related_queries: list[str] = Field(
        default_factory=list,
        description="Queries related to this goal",
    )
    milestones: dict[str, bool] = Field(
        default_factory=dict,
        description="Key milestones and completion status",
    )


class SearchInsight(BaseModel):
    """Insights discovered about the user's search patterns and document organization."""

    category: str = Field(
        ...,
        description="Category of insight (e.g., 'organization', 'retrieval', 'content')",
    )
    insight: str = Field(
        ...,
        description="The insight about user behavior or document patterns",
    )
    confidence: float = Field(
        default=0.5,
        description="Confidence level in this insight (0.0-1.0)",
    )
    supporting_evidence: list[str] = Field(
        default_factory=list,
        description="Evidence supporting this insight",
    )
    impact: str = Field(
        default="medium",
        description="Impact on search effectiveness (low, medium, high)",
    )


class EffectiveStrategy(BaseModel):
    """Search strategies that have proven effective for this user."""

    strategy_name: str = Field(..., description="Name of the strategy")
    description: str = Field(..., description="Detailed description of the strategy")
    applicable_contexts: list[str] = Field(
        default_factory=list,
        description="When this strategy is applicable",
    )
    success_rate: float = Field(
        default=0.5,
        description="Estimated success rate (0.0-1.0)",
    )
    example_queries: list[str] = Field(
        default_factory=list,
        description="Example queries where this strategy worked",
    )


class ArchivistMemoryData(BaseModel):
    """The core Archivist memory model that persists across sessions."""

    memory_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this memory entry",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this memory was created",
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this memory was last updated",
    )

    session_history: list[str] = Field(
        default_factory=list,
        description="List of session IDs contributing to this memory",
    )

    user_preferences: list[UserPreference] = Field(
        default_factory=list,
        description="Observed user preferences",
    )

    search_patterns: list[SearchPattern] = Field(
        default_factory=list,
        description="Identified search patterns",
    )

    long_term_goals: list[LongTermGoal] = Field(
        default_factory=list,
        description="Ongoing long-term goals",
    )

    insights: list[SearchInsight] = Field(
        default_factory=list,
        description="Insights about search and organization",
    )

    effective_strategies: list[EffectiveStrategy] = Field(
        default_factory=list,
        description="Strategies that work well for this user",
    )

    document_relationships: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Observed relationships between documents",
    )

    content_preferences: dict[str, float] = Field(
        default_factory=dict,
        description="User's preference for different content types (0.0-1.0)",
    )

    # String-based continuation context for simple continuity hints
    continuation_context: dict[str, Any] = Field(
        default_factory=lambda: {"conversations": []},
        description="Structured data for conversation continuity across sessions",
    )

    # Legacy field for backwards compatibility
    legacy_continuation_context: str | None = Field(
        default=None,
        description="Legacy string-based context from the last session for continuity",
    )

    semantic_topics: dict[str, float] = Field(
        default_factory=dict,
        description="Topic areas of interest and their importance (0.0-1.0)",
    )


class IndalekoArchivistMemoryModel(IndalekoBaseModel):
    """Indaleko data model for Archivist memory."""

    Record: IndalekoRecordDataModel = Field(
        ...,
        title="Record",
        description="The record associated with the Archivist memory data.",
    )

    ArchivistMemory: ArchivistMemoryData = Field(
        ...,
        title="ArchivistMemory",
        description="The Archivist memory data.",
    )


class ConversationStateMemory(BaseModel):
    """Memory model for storing conversation state."""

    conversation_id: str = Field(..., description="The conversation ID")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this memory was created",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this memory was last updated",
    )
    summary: str = Field(..., description="Summary of the conversation")
    key_takeaways: list[str] = Field(
        default_factory=list,
        description="Key takeaways from the conversation",
    )
    topics: list[str] = Field(
        default_factory=list,
        description="Topics covered in the conversation",
    )
    entities: list[str] = Field(
        default_factory=list,
        description="Entities identified in the conversation",
    )
    importance_score: float = Field(
        default=0.5,
        description="Overall importance of the conversation",
    )
    message_count: int = Field(
        default=0,
        description="Number of messages in the conversation",
    )
    context_variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Context variables maintained across the conversation",
    )
    continuation_id: str | None = Field(
        default=None,
        description="ID for continuing this conversation",
    )


class ArchivistMemory:
    """
    Manages persistent memory for the Archivist across sessions.
    Enables long-term collaboration and goal tracking beyond context limitations.
    """

    archivist_memory_uuid_str = "e7b6f4a2-8c5d-4e9c-b3a7-f29d8a6d7e5c"
    archivist_memory_version = "2025.04.20.01"  # Updated version for conversation support
    archivist_memory_description = "Archivist persistent memory across sessions"

    def __init__(self, db_config: IndalekoDBConfig = IndalekoDBConfig()):
        """Initialize the Archivist memory manager."""
        self.db_config = db_config
        self.ensure_collection_exists()
        self.memory = self.load_latest_memory() or ArchivistMemoryData()

    def ensure_collection_exists(self) -> None:
        """Ensure the Archivist memory collection exists in the database."""
        collection_name = IndalekoDBCollections.Indaleko_Archivist_Memory_Collection

        # First try to get the collection from the centralized registry
        from db.i_collections import IndalekoCollections

        try:
            # Try to get the collection using standard IndalekoCollections mechanism
            _ = IndalekoCollections.get_collection(collection_name)
            ic(f"Found existing collection {collection_name} in registry")
            return
        except ValueError:
            # Collection not found in registry
            ic(
                f"Collection {collection_name} not in central registry, using registration service",
            )

        # Check if it exists directly in the database
        if self.db_config._arangodb.has_collection(collection_name):
            ic(f"Collection {collection_name} already exists in database")
            return

        # Collection needs to be registered, use utils.registration_service
        from utils.registration_service import IndalekoRegistrationService

        # Get basic info from collection definition if available
        schema = None
        edge = False
        indices = None
        if collection_name in IndalekoDBCollections.Collections:
            collection_def = IndalekoDBCollections.Collections[collection_name]
            schema = collection_def.get("schema")
            edge = collection_def.get("edge", False)
            indices = collection_def.get("indices")

        # Generate a deterministic UUID for this collection from its name
        import hashlib

        name_hash = hashlib.md5(collection_name.encode()).hexdigest()
        provider_id = str(uuid.UUID(name_hash))

        # Get registration service instance
        # Since this is query memory, use the archivist service type
        service_uuid = "9d3f9e5b-4567-4c1a-8e2b-2b0f3e8d3b2a"  # Fixed UUID for Archivist registration
        reg_service = IndalekoRegistrationService(
            service_uuid=service_uuid,
            service_name="Archivist Registration Service",
            service_description="Manages Archivist memory collections",
            service_version="1.0.0",
            service_type="archivist_data_registrar",
            collection_name="ArchivistProviders",
            collection_prefix="Archivist_",
        )

        # Check if provider collection already exists
        provider_collection = reg_service.lookup_provider_collection(provider_id)
        if provider_collection is None:
            # Create the collection
            ic(f"Creating collection {collection_name} via registration service")
            provider_collection = reg_service.create_provider_collection(
                identifier=provider_id,
                schema=schema,
                edge=edge,
                indices=indices,
            )
            ic(f"Successfully created collection {collection_name}")
        else:
            ic(f"Found existing collection {collection_name} via registration service")

    def load_latest_memory(self) -> ArchivistMemoryData | None:
        """Load the most recent Archivist memory from the database."""
        collection_name = IndalekoDBCollections.Indaleko_Archivist_Memory_Collection
        collection = self.db_config._arangodb.collection(collection_name)

        # Query for the most recent memory entry
        try:
            # Use AQL to sort by timestamp in descending order
            aql = "FOR doc IN @@collection SORT doc.Record.Timestamp DESC LIMIT 1 RETURN doc"
            cursor = self.db_config._arangodb.aql.execute(
                aql,
                bind_vars={"@collection": collection_name},
            )
            documents = [doc for doc in cursor]

            if not documents:
                return None

            memory_model = IndalekoArchivistMemoryModel(**documents[0])
            return memory_model.ArchivistMemory
        except Exception as e:
            ic(f"Error loading memory: {e}")
            return None

    def save_memory(self) -> None:
        """Save the current Archivist memory to the database."""
        collection_name = IndalekoDBCollections.Indaleko_Archivist_Memory_Collection
        collection = self.db_config._arangodb.collection(collection_name)

        # Update the timestamp
        self.memory.updated_at = datetime.now(UTC)

        # Create the full model
        memory_model = IndalekoArchivistMemoryModel(
            Record=IndalekoRecordDataModel(
                SourceIdentifier=IndalekoSourceIdentifierDataModel(
                    Identifier=self.archivist_memory_uuid_str,
                    Version=self.archivist_memory_version,
                    Description=self.archivist_memory_description,
                ),
                Timestamp=datetime.now(UTC),
                Data=encode_binary_data(
                    bytes(
                        self.memory.model_dump_json(
                            exclude_none=True,
                            exclude_unset=True,
                        ),
                        "utf-8",
                    ),
                ),
            ),
            ArchivistMemory=self.memory,
        )

        # Insert into database
        # Serialize to JSON and then parse back to ensure UUID handling
        doc_json = memory_model.model_dump_json(exclude_none=True)
        doc = json.loads(doc_json)

        try:
            collection.insert(doc)
            ic("Successfully saved memory to database")
        except Exception as e:
            ic(f"Error saving memory to database: {e}")

    def distill_knowledge(self, conversation_context, query_history) -> None:
        """
        Extract essential patterns and insights from recent interactions.

        Args:
            conversation_context: Recent conversation context
            query_history: History of queries and results
        """
        # Update session history
        if conversation_context and hasattr(conversation_context, "current_session_id"):
            session_id = conversation_context.current_session_id
            if session_id not in self.memory.session_history:
                self.memory.session_history.append(session_id)

        # Extract patterns from queries
        if query_history:
            self._extract_query_patterns(query_history)
            self._update_content_preferences(query_history)
            self._identify_effective_strategies(query_history)
            self._extract_semantic_topics(query_history)

    def _extract_query_patterns(self, query_history) -> None:
        """
        Extract search patterns from query history.

        This identifies common patterns in how the user structures queries.
        """
        ic("Extracting query patterns")

        # This would analyze the query history to identify patterns
        # For now, a simplified implementation that looks for basic patterns

        # Example pattern detection:
        # If we have enough queries to analyze
        if not hasattr(query_history, "get_recent_queries"):
            return

        recent_queries = query_history.get_recent_queries(10)
        if not recent_queries or len(recent_queries) < 3:
            return

        # Count queries with time-based constraints
        time_queries = 0
        file_type_queries = 0
        location_queries = 0

        for query in recent_queries:
            original_query = query.OriginalQuery.lower()

            # Simple pattern matching
            if any(term in original_query for term in ["yesterday", "today", "last week", "month", "year", "date"]):
                time_queries += 1

            if any(term in original_query for term in ["pdf", "doc", "docx", "jpg", "png", "txt", "file type"]):
                file_type_queries += 1

            if any(term in original_query for term in ["location", "folder", "directory", "path"]):
                location_queries += 1

        # If pattern frequency exceeds threshold, add or update the pattern
        if time_queries / len(recent_queries) > 0.3:
            self._add_or_update_pattern(
                "temporal_constraint",
                "User frequently includes time-based constraints in queries",
                [
                    q.OriginalQuery
                    for q in recent_queries
                    if any(
                        term in q.OriginalQuery.lower()
                        for term in [
                            "yesterday",
                            "today",
                            "last week",
                            "month",
                            "year",
                            "date",
                        ]
                    )
                ],
                time_queries / len(recent_queries),
            )

        if file_type_queries / len(recent_queries) > 0.3:
            self._add_or_update_pattern(
                "file_type_filter",
                "User often specifies file types in queries",
                [
                    q.OriginalQuery
                    for q in recent_queries
                    if any(
                        term in q.OriginalQuery.lower()
                        for term in [
                            "pdf",
                            "doc",
                            "docx",
                            "jpg",
                            "png",
                            "txt",
                            "file type",
                        ]
                    )
                ],
                file_type_queries / len(recent_queries),
            )

        if location_queries / len(recent_queries) > 0.3:
            self._add_or_update_pattern(
                "location_constraint",
                "User frequently includes location constraints in queries",
                [
                    q.OriginalQuery
                    for q in recent_queries
                    if any(term in q.OriginalQuery.lower() for term in ["location", "folder", "directory", "path"])
                ],
                location_queries / len(recent_queries),
            )

    def _add_or_update_pattern(self, pattern_type, description, examples, frequency):
        """Add a new pattern or update an existing one."""
        # Check if pattern already exists
        for pattern in self.memory.search_patterns:
            if pattern.pattern_type == pattern_type:
                # Update existing pattern
                pattern.frequency = (pattern.frequency + frequency) / 2  # Moving average
                pattern.examples = list(set(pattern.examples + examples))[:5]  # Keep up to 5 unique examples
                return

        # Add new pattern
        self.memory.search_patterns.append(
            SearchPattern(
                pattern_type=pattern_type,
                description=description,
                examples=examples[:3],  # Keep up to 3 examples
                frequency=frequency,
            ),
        )

    def _update_content_preferences(self, query_history) -> None:
        """
        Update content type preferences based on search results interaction.

        This tracks which types of content the user searches for most frequently.
        """
        ic("Updating content preferences")

        # This would analyze which content types appear in successful searches
        # For a simple implementation, we'll just count content types in the queries

        if not hasattr(query_history, "get_recent_queries"):
            return

        recent_queries = query_history.get_recent_queries(10)
        if not recent_queries:
            return

        # Dictionary to track content type mentions
        content_types = {
            "document": ["document", "doc", "docx", "pdf", "text", "txt"],
            "image": ["image", "photo", "picture", "jpg", "jpeg", "png", "gif"],
            "video": ["video", "mp4", "movie", "film"],
            "audio": ["audio", "sound", "mp3", "music", "song"],
            "email": ["email", "mail", "outlook", "gmail"],
            "code": ["code", "program", "script", "py", "js", "java", "c++", "source"],
        }

        type_counts = {t: 0 for t in content_types}

        for query in recent_queries:
            query_text = query.OriginalQuery.lower()

            for content_type, keywords in content_types.items():
                if any(keyword in query_text for keyword in keywords):
                    type_counts[content_type] += 1

        # Update content preferences
        for content_type, count in type_counts.items():
            if count > 0:
                # Calculate preference strength (0.0-1.0)
                preference = count / len(recent_queries)

                # Update or add to content preferences with exponential smoothing
                alpha = 0.3  # Smoothing factor
                if content_type in self.memory.content_preferences:
                    self.memory.content_preferences[content_type] = (
                        alpha * preference + (1 - alpha) * self.memory.content_preferences[content_type]
                    )
                else:
                    self.memory.content_preferences[content_type] = preference

    def _identify_effective_strategies(self, query_history) -> None:
        """
        Identify search strategies that led to successful outcomes.

        This analyzes which types of queries tend to produce satisfactory results.
        """
        ic("Identifying effective strategies")

        # For a simple implementation, we'll identify strategies based on basic patterns
        if not hasattr(query_history, "get_recent_queries"):
            return

        recent_queries = query_history.get_recent_queries(10)
        if not recent_queries:
            return

        # Count successful specific vs. broad queries
        specific_successful = 0
        specific_total = 0
        broad_successful = 0
        broad_total = 0

        for query in recent_queries:
            is_specific = False
            original_query = query.OriginalQuery.lower()

            # Check if query is specific (contains detailed constraints)
            if (
                len(original_query.split()) > 4
                or any(term in original_query for term in ["specific", "exact", "exactly", "named", "titled"])
                or any(
                    term in original_query
                    for term in [
                        "created",
                        "modified",
                        "accessed",
                        "on date",
                        "before",
                        "after",
                    ]
                )
            ):
                is_specific = True
                specific_total += 1
            else:
                broad_total += 1

            # Check if query was successful (had results)
            has_results = query.RankedResults is not None and len(query.RankedResults) > 0

            if is_specific and has_results:
                specific_successful += 1
            elif not is_specific and has_results:
                broad_successful += 1

        # Calculate success rates
        specific_success_rate = specific_successful / specific_total if specific_total > 0 else 0
        broad_success_rate = broad_successful / broad_total if broad_total > 0 else 0

        # Add or update strategies based on success rates
        if specific_total > 2 and specific_success_rate > 0.5:
            self._add_or_update_strategy(
                "specific_constraints",
                "Using specific constraints (e.g., dates, exact terms) improves search results",
                ["date-based searches", "exact term matching", "multiple filters"],
                specific_success_rate,
            )

        if broad_total > 2 and broad_success_rate > 0.5:
            self._add_or_update_strategy(
                "broad_queries",
                "Broader queries with fewer constraints help discover more content",
                [
                    "general topic searches",
                    "content-type filters only",
                    "short queries",
                ],
                broad_success_rate,
            )

    def _add_or_update_strategy(self, name, description, contexts, success_rate):
        """Add a new strategy or update an existing one."""
        # Check if strategy already exists
        for strategy in self.memory.effective_strategies:
            if strategy.strategy_name == name:
                # Update existing strategy
                strategy.success_rate = (strategy.success_rate + success_rate) / 2  # Moving average
                strategy.applicable_contexts = list(
                    set(strategy.applicable_contexts + contexts),
                )
                return

        # Add new strategy
        self.memory.effective_strategies.append(
            EffectiveStrategy(
                strategy_name=name,
                description=description,
                applicable_contexts=contexts,
                success_rate=success_rate,
            ),
        )

    def _extract_semantic_topics(self, query_history) -> None:
        """
        Extract and update semantic topics of interest based on recent queries.

        This identifies the general topics the user is interested in.
        """
        ic("Extracting semantic topics")

        if not hasattr(query_history, "get_recent_queries"):
            return

        recent_queries = query_history.get_recent_queries(15)
        if not recent_queries:
            return

        # Simple topic extraction based on keyword presence
        topic_keywords = {
            "work": [
                "work",
                "project",
                "business",
                "report",
                "presentation",
                "meeting",
                "client",
                "deadline",
            ],
            "personal": [
                "personal",
                "family",
                "vacation",
                "holiday",
                "trip",
                "home",
                "friend",
            ],
            "finance": [
                "finance",
                "bank",
                "money",
                "invoice",
                "payment",
                "tax",
                "budget",
                "receipt",
            ],
            "academic": [
                "research",
                "paper",
                "study",
                "academic",
                "university",
                "college",
                "course",
                "thesis",
            ],
            "media": [
                "photo",
                "video",
                "music",
                "movie",
                "song",
                "image",
                "picture",
                "album",
            ],
            "technology": [
                "code",
                "program",
                "software",
                "hardware",
                "computer",
                "app",
                "tech",
                "script",
            ],
        }

        # Count topic mentions
        topic_counts = {topic: 0 for topic in topic_keywords}

        for query in recent_queries:
            query_text = query.OriginalQuery.lower()

            for topic, keywords in topic_keywords.items():
                if any(keyword in query_text for keyword in keywords):
                    topic_counts[topic] += 1

        # Update topic importances
        alpha = 0.2  # Smoothing factor
        for topic, count in topic_counts.items():
            if count > 0:
                # Calculate importance (0.0-1.0)
                importance = count / len(recent_queries)

                # Update with exponential smoothing
                if topic in self.memory.semantic_topics:
                    self.memory.semantic_topics[topic] = (
                        alpha * importance + (1 - alpha) * self.memory.semantic_topics[topic]
                    )
                else:
                    self.memory.semantic_topics[topic] = importance

    def generate_forward_prompt(self) -> str:
        """
        Create a compact representation for the next Archivist instance.

        Returns:
            str: A forward prompt capturing essential knowledge
        """
        # Update continuation context with latest session info
        self._update_continuation_context()

        # Generate the forward prompt
        prompt = "ARCHIVIST CONTINUITY PROMPT\n"
        prompt += "------------------------\n\n"

        # Add user preferences section
        prompt += "USER PROFILE:\n"

        # Add content preferences
        if self.memory.content_preferences:
            content_prefs = sorted(
                self.memory.content_preferences.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            content_types = [f"{ctype} ({pref:.2f})" for ctype, pref in content_prefs[:3]]
            if content_types:
                prompt += f"- Preferred content types: {', '.join(content_types)}\n"

        # Add search patterns
        if self.memory.search_patterns:
            patterns = sorted(
                self.memory.search_patterns,
                key=lambda x: x.frequency,
                reverse=True,
            )
            if patterns:
                prompt += f"- Search pattern: {patterns[0].description}\n"

        # Add more user preferences if available
        for pref in self.memory.user_preferences[:3]:  # Limit to top 3
            prompt += f"- {pref.preference} (confidence: {pref.confidence:.2f})\n"
        prompt += "\n"

        # Add effective strategies
        prompt += "EFFECTIVE STRATEGIES:\n"
        for strategy in sorted(
            self.memory.effective_strategies,
            key=lambda x: x.success_rate,
            reverse=True,
        )[:3]:
            prompt += f"- {strategy.strategy_name}: {strategy.description} (success: {strategy.success_rate:.2f})\n"
        prompt += "\n"

        # Add long-term goals
        if self.memory.long_term_goals:
            prompt += "ONGOING PROJECTS:\n"
            for i, goal in enumerate(self.memory.long_term_goals[:3], 1):
                prompt += f'{i}. "{goal.name}" - {goal.description} ({goal.progress*100:.0f}% complete)\n'
            prompt += "\n"

        # Add insights
        if self.memory.insights:
            prompt += "KEY INSIGHTS:\n"
            for insight in sorted(
                self.memory.insights,
                key=lambda x: x.confidence,
                reverse=True,
            )[:5]:
                prompt += f"- {insight.insight} ({insight.impact} impact)\n"
            prompt += "\n"

        # Add continuation context
        if self.memory.continuation_context:
            prompt += "CONTINUATION CONTEXT:\n"
            prompt += self.memory.continuation_context
            prompt += "\n\n"

        # Add semantic topics of interest
        if self.memory.semantic_topics:
            prompt += "TOPICS OF INTEREST:\n"
            topics = sorted(
                self.memory.semantic_topics.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:5]
            for topic, importance in topics:
                prompt += f"- {topic} (importance: {importance:.2f})\n"

        return prompt

    def update_from_forward_prompt(self, prompt: str) -> None:
        """
        Initialize this instance from a previous generation's prompt.

        Args:
            prompt: The forward prompt from a previous session
        """
        ic("Updating from forward prompt")

        # Store the full prompt as continuation context
        self.memory.continuation_context = prompt

        # Parse the structured sections to extract information
        sections = {}
        current_section = None
        current_content = []

        for line in prompt.split("\n"):
            line = line.strip()

            # Check if this is a section header
            if line.endswith(":") and line.isupper():
                if current_section and current_content:
                    sections[current_section] = "\n".join(current_content)
                    current_content = []
                current_section = line[:-1]
            elif current_section:
                current_content.append(line)

        # Add the last section
        if current_section and current_content:
            sections[current_section] = "\n".join(current_content)

        # Process USER PROFILE section
        if "USER PROFILE" in sections:
            self._extract_user_profile(sections["USER PROFILE"])

        # Process EFFECTIVE STRATEGIES section
        if "EFFECTIVE STRATEGIES" in sections:
            self._extract_strategies(sections["EFFECTIVE STRATEGIES"])

        # Process ONGOING PROJECTS section
        if "ONGOING PROJECTS" in sections:
            self._extract_goals(sections["ONGOING PROJECTS"])

        # Process KEY INSIGHTS section
        if "KEY INSIGHTS" in sections:
            self._extract_insights(sections["KEY INSIGHTS"])

        # Process TOPICS OF INTEREST section
        if "TOPICS OF INTEREST" in sections:
            self._extract_topics(sections["TOPICS OF INTEREST"])

    def _extract_user_profile(self, profile_text):
        """Extract user preferences from profile text."""
        for line in profile_text.split("\n"):
            if line.startswith("-"):
                line = line[1:].strip()

                # Extract content preferences
                if "content types:" in line.lower():
                    types_str = line.split(":", 1)[1].strip()
                    for type_str in types_str.split(","):
                        if "(" in type_str and ")" in type_str:
                            ctype, pref_str = type_str.strip().split("(")
                            pref = float(pref_str.replace(")", ""))
                            self.memory.content_preferences[ctype.strip()] = pref

                # Add as generic user preference
                elif line:
                    # Extract confidence if available
                    confidence = 0.5
                    if "(" in line and ")" in line and "confidence" in line.lower():
                        parts = line.split("(")
                        pref_text = parts[0].strip()
                        conf_part = parts[1].split(")")[0]
                        if "confidence:" in conf_part:
                            try:
                                confidence = float(conf_part.split(":")[1].strip())
                            except ValueError:
                                pass
                    else:
                        pref_text = line

                    # Add preference
                    if pref_text:
                        self._add_or_update_preference("general", pref_text, confidence)

    def _add_or_update_preference(self, category, preference, confidence):
        """Add or update a user preference."""
        # Check if preference already exists
        for pref in self.memory.user_preferences:
            if pref.preference == preference:
                # Update existing preference
                pref.confidence = max(pref.confidence, confidence)
                pref.observation_count += 1
                pref.last_observed = datetime.now(UTC)
                return

        # Add new preference
        self.memory.user_preferences.append(
            UserPreference(
                category=category,
                preference=preference,
                confidence=confidence,
            ),
        )

    def _extract_strategies(self, strategies_text):
        """Extract effective search strategies from text."""
        for line in strategies_text.split("\n"):
            if line.startswith("-"):
                line = line[1:].strip()
                if ":" in line:
                    # Parse strategy name and description
                    name, desc = line.split(":", 1)
                    name = name.strip()
                    desc_parts = desc.strip().split("(")

                    description = desc_parts[0].strip()
                    success_rate = 0.5

                    # Extract success rate if available
                    if len(desc_parts) > 1 and "success:" in desc_parts[1]:
                        try:
                            success_str = desc_parts[1].split(":")[1].replace(")", "").strip()
                            success_rate = float(success_str)
                        except ValueError:
                            pass

                    # Add or update strategy
                    self._add_or_update_strategy(name, description, [], success_rate)

    def _extract_goals(self, goals_text):
        """Extract long-term goals from text."""
        for line in goals_text.split("\n"):
            if line and line[0].isdigit() and '. "' in line:
                # Parse goal
                try:
                    _, rest = line.split('. "', 1)
                    name, rest = rest.split('"', 1)

                    if "-" in rest:
                        description, progress_part = rest.split("-", 1)
                        description = description.strip()

                        # Extract progress percentage
                        progress = 0.0
                        if "(" in progress_part and "%" in progress_part:
                            progress_str = progress_part.split("(")[1].split("%")[0].strip()
                            try:
                                progress = float(progress_str) / 100.0
                            except ValueError:
                                pass

                        # Add or update goal
                        self.add_long_term_goal(name, description)
                        self.update_goal_progress(name, progress)
                except Exception as e:
                    ic(f"Error parsing goal: {e}")

    def _extract_insights(self, insights_text):
        """Extract search insights from text."""
        for line in insights_text.split("\n"):
            if line.startswith("-"):
                line = line[1:].strip()

                # Parse insight
                if "(" in line and ")" in line:
                    insight_text, impact_part = line.rsplit("(", 1)
                    insight_text = insight_text.strip()

                    # Extract impact
                    impact = "medium"
                    if "impact" in impact_part:
                        impact_str = impact_part.split()[0].strip()
                        impact = impact_str

                    # Add insight
                    self.add_insight("general", insight_text, 0.7)
                elif line:
                    # Simple insight without metadata
                    self.add_insight("general", line, 0.5)

    def _extract_topics(self, topics_text):
        """Extract semantic topics from text."""
        for line in topics_text.split("\n"):
            if line.startswith("-"):
                line = line[1:].strip()

                # Parse topic and importance
                if "(" in line and ")" in line and "importance:" in line:
                    topic, imp_part = line.rsplit("(", 1)
                    topic = topic.strip()

                    # Extract importance
                    importance = 0.5
                    if "importance:" in imp_part:
                        imp_str = imp_part.split(":")[1].replace(")", "").strip()
                        try:
                            importance = float(imp_str)
                        except ValueError:
                            pass

                    # Add to semantic topics
                    self.memory.semantic_topics[topic] = importance

    def _update_continuation_context(self) -> None:
        """Update the continuation context with the latest session information."""
        # Generate a concise summary of the current state
        context = "User was last working on "

        # Add information about the most recent goal activity
        if self.memory.long_term_goals:
            latest_goal = max(self.memory.long_term_goals, key=lambda g: g.last_updated)
            context += f"{latest_goal.name} ({latest_goal.progress*100:.0f}% complete). "

        # Add recent topical focus
        if self.memory.semantic_topics:
            top_topic = max(self.memory.semantic_topics.items(), key=lambda x: x[1])[0]
            context += f"Recent focus has been on {top_topic}. "

        # Add effective strategy suggestion
        if self.memory.effective_strategies:
            top_strategy = max(
                self.memory.effective_strategies,
                key=lambda s: s.success_rate,
            )
            context += f"The '{top_strategy.strategy_name}' search approach has been effective. "

        self.memory.continuation_context = context

    def add_long_term_goal(self, name: str, description: str) -> None:
        """
        Add a new long-term goal to track across sessions.

        Args:
            name: Name of the goal
            description: Detailed description of the goal
        """
        # Check if goal already exists
        for goal in self.memory.long_term_goals:
            if goal.name == name:
                # Update existing goal
                goal.description = description
                goal.last_updated = datetime.now(UTC)
                return

        # Create new goal
        self.memory.long_term_goals.append(
            LongTermGoal(name=name, description=description),
        )

    def update_goal_progress(self, name: str, progress: float) -> None:
        """
        Update the progress of a long-term goal.

        Args:
            name: Name of the goal
            progress: New progress value (0.0-1.0)
        """
        for goal in self.memory.long_term_goals:
            if goal.name == name:
                goal.progress = progress
                goal.last_updated = datetime.now(UTC)
                return

    def add_insight(self, category: str, insight: str, confidence: float = 0.5) -> None:
        """
        Add a new insight about the user's search patterns.

        Args:
            category: Category of the insight
            insight: The insight text
            confidence: Confidence level in this insight
        """
        # Check if similar insight already exists
        for existing in self.memory.insights:
            if existing.insight == insight:
                # Update confidence of existing insight
                existing.confidence = max(existing.confidence, confidence)
                return

        # Add new insight
        self.memory.insights.append(
            SearchInsight(category=category, insight=insight, confidence=confidence),
        )

    def get_most_relevant_insights(
        self,
        context: str,
        limit: int = 3,
    ) -> list[SearchInsight]:
        """
        Get the most relevant insights for the current context.

        Args:
            context: The current search context
            limit: Maximum number of insights to return

        Returns:
            List of most relevant insights
        """
        # This would use semantic matching to find relevant insights
        # For now, just return the highest confidence insights
        sorted_insights = sorted(
            self.memory.insights,
            key=lambda x: x.confidence,
            reverse=True,
        )
        return sorted_insights[:limit]

    def store_conversation_state(
        self,
        conversation_id: str,
        state_data: dict[str, Any],
    ) -> str:
        """
        Store conversation state information for cross-session continuity.

        Args:
            conversation_id: The conversation ID
            state_data: Data about the conversation state

        Returns:
            Continuation ID for retrieving this state later
        """
        # Create a continuation ID
        continuation_id = f"cont_{conversation_id}_{uuid.uuid4().hex[:8]}"

        # Create conversation state memory with required fields
        convo_state = {
            "conversation_id": conversation_id,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "summary": state_data.get(
                "summary",
                "Conversation with Indaleko Assistant",
            ),
            "key_takeaways": state_data.get("key_takeaways", []),
            "topics": state_data.get("topics", []),
            "entities": state_data.get("entities", []),
            "importance_score": state_data.get("importance_score", 0.5),
            "message_count": state_data.get("message_count", 0),
            "context_variables": state_data.get("context_variables", {}),
            "continuation_id": continuation_id,
        }

        # Ensure continuation_context is properly initialized
        if not hasattr(self.memory, "continuation_context"):
            self.memory.continuation_context = {"conversations": []}
        elif isinstance(self.memory.continuation_context, str):
            # Handle legacy string format - save it and create new dict format
            legacy_text = self.memory.continuation_context
            self.memory.legacy_continuation_context = legacy_text
            self.memory.continuation_context = {"conversations": []}
        elif self.memory.continuation_context is None:
            self.memory.continuation_context = {"conversations": []}
        elif not isinstance(self.memory.continuation_context, dict):
            # For any other type, convert to dict
            self.memory.legacy_continuation_context = str(
                self.memory.continuation_context,
            )
            self.memory.continuation_context = {"conversations": []}
        elif "conversations" not in self.memory.continuation_context:
            # Ensure conversations key exists
            self.memory.continuation_context["conversations"] = []

        # Store in memory
        # First, check if we already have this conversation
        existing_index = -1
        conversation_states = self.memory.continuation_context.get("conversations", [])

        for i, state in enumerate(conversation_states):
            if state.get("conversation_id") == conversation_id:
                existing_index = i
                break

        # Add or update
        if existing_index >= 0:
            conversation_states[existing_index] = convo_state
        else:
            conversation_states.append(convo_state)

        # Update memory
        self.memory.continuation_context["conversations"] = conversation_states

        # Save memory
        self.save_memory()

        return continuation_id

    def get_continuation_context(self, continuation_id: str) -> dict[str, Any]:
        """
        Get conversation continuation context.

        Args:
            continuation_id: The continuation ID

        Returns:
            Dict with continuation context, or empty dict if not found
        """
        # Initialize continuation context if not present
        if not hasattr(self.memory, "continuation_context"):
            return {}

        # Handle legacy string format
        if isinstance(self.memory.continuation_context, str):
            # If it's a string, we can't search it properly
            # Convert it to a dict first
            self.memory.legacy_continuation_context = self.memory.continuation_context
            self.memory.continuation_context = {"conversations": []}
            return {}

        # Look for the continuation
        conversation_states = self.memory.continuation_context.get("conversations", [])

        for state in conversation_states:
            if state.get("continuation_id") == continuation_id:
                return state

        return {}

    def search_memories(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """
        Search for relevant memories based on a query.

        Args:
            query: The search query
            max_results: Maximum number of results to return

        Returns:
            List of relevant memories
        """
        results = []

        # Search insights
        for insight in self.memory.insights:
            # Simple keyword matching
            if any(keyword in insight.insight.lower() for keyword in query.lower().split()):
                results.append(
                    {
                        "memory_id": str(uuid.uuid4()),  # Generate a unique ID
                        "memory_type": "insight",
                        "relevance": 0.7,
                        "summary": insight.insight,
                        "category": insight.category,
                        "confidence": insight.confidence,
                    },
                )

        # Search goals
        for goal in self.memory.long_term_goals:
            # Simple keyword matching
            if any(
                keyword in goal.name.lower() or keyword in goal.description.lower() for keyword in query.lower().split()
            ):
                results.append(
                    {
                        "memory_id": str(uuid.uuid4()),  # Generate a unique ID
                        "memory_type": "goal",
                        "relevance": 0.8,
                        "summary": goal.description,
                        "name": goal.name,
                        "progress": goal.progress,
                    },
                )

        # Search patterns
        for pattern in self.memory.search_patterns:
            # Simple keyword matching
            if any(keyword in pattern.description.lower() for keyword in query.lower().split()):
                results.append(
                    {
                        "memory_id": str(uuid.uuid4()),  # Generate a unique ID
                        "memory_type": "pattern",
                        "relevance": 0.6,
                        "summary": pattern.description,
                        "pattern_type": pattern.pattern_type,
                        "frequency": pattern.frequency,
                    },
                )

        # Search conversation history if available
        if hasattr(self.memory, "continuation_context"):
            conversation_states = self.memory.continuation_context.get(
                "conversations",
                [],
            )
            for state in conversation_states:
                # Check summary and takeaways
                summary = state.get("summary", "")
                takeaways = state.get("key_takeaways", [])

                if any(keyword in summary.lower() for keyword in query.lower().split()) or any(
                    any(keyword in takeaway.lower() for keyword in query.lower().split()) for takeaway in takeaways
                ):
                    results.append(
                        {
                            "memory_id": state.get(
                                "conversation_id",
                                str(uuid.uuid4()),
                            ),
                            "memory_type": "conversation",
                            "relevance": 0.9,
                            "summary": summary,
                            "key_takeaways": takeaways,
                            "continuation_id": state.get("continuation_id"),
                        },
                    )

        # Search query activities if available
        query_activities = self.memory.continuation_context.get("query_activities", [])
        for activity in query_activities:
            # Check query text
            activity_query = activity.get("query_text", "")

            if any(keyword in activity_query.lower() for keyword in query.lower().split()):
                results.append(
                    {
                        "memory_id": activity.get("query_id", str(uuid.uuid4())),
                        "memory_type": "query_activity",
                        "relevance": 0.85,
                        "summary": f"Query: {activity_query}",
                        "relationship_type": activity.get("relationship_type"),
                        "timestamp": activity.get("timestamp"),
                        "result_count": activity.get("result_count"),
                    },
                )

        # Sort by relevance
        results.sort(key=lambda x: x.get("relevance", 0), reverse=True)

        # Limit results
        return results[:max_results]

    def import_query_activities(self, activities: list[Any]) -> None:
        """
        Import query activities into the Archivist memory.

        Args:
            activities: List of query activities
        """
        if not HAS_QUERY_CONTEXT:
            ic("Query Context Integration not available, skipping import.")
            return

        # Ensure continuation_context is properly initialized
        if not hasattr(self.memory, "continuation_context"):
            self.memory.continuation_context = {
                "conversations": [],
                "query_activities": [],
            }
        elif isinstance(self.memory.continuation_context, str):
            # Handle legacy string format - save it and create new dict format
            legacy_text = self.memory.continuation_context
            self.memory.legacy_continuation_context = legacy_text
            self.memory.continuation_context = {
                "conversations": [],
                "query_activities": [],
            }
        elif self.memory.continuation_context is None:
            self.memory.continuation_context = {
                "conversations": [],
                "query_activities": [],
            }
        elif (
            isinstance(self.memory.continuation_context, dict)
            and "query_activities" not in self.memory.continuation_context
        ):
            # Ensure query_activities key exists
            self.memory.continuation_context["query_activities"] = []

        # Process each activity
        query_activities = self.memory.continuation_context.get("query_activities", [])

        for activity in activities:
            if isinstance(activity, QueryActivityData):
                # Convert to dictionary for storage
                activity_dict = {
                    "query_id": str(activity.query_id),
                    "query_text": activity.query_text,
                    "execution_time": activity.execution_time,
                    "result_count": activity.result_count,
                    "relationship_type": activity.relationship_type,
                    "previous_query_id": (str(activity.previous_query_id) if activity.previous_query_id else None),
                    "timestamp": (
                        activity.timestamp.isoformat()
                        if hasattr(activity.timestamp, "isoformat")
                        else str(activity.timestamp)
                    ),
                }

                # Check if this activity already exists
                existing = False
                for i, existing_activity in enumerate(query_activities):
                    if existing_activity.get("query_id") == activity_dict["query_id"]:
                        # Update existing activity
                        query_activities[i] = activity_dict
                        existing = True
                        break

                # Add if not existing
                if not existing:
                    query_activities.append(activity_dict)

        # Update memory with modified activities
        self.memory.continuation_context["query_activities"] = query_activities

        # Derive insights from query activities
        self._derive_query_insights(query_activities)

        # Save memory
        self.save_memory()

    def _derive_query_insights(self, query_activities: list[dict[str, Any]]) -> None:
        """
        Derive insights from query activities.

        Args:
            query_activities: List of query activity dictionaries
        """
        if not query_activities:
            return

        # Count relationship types
        relationship_counts = {}
        total_activities = len(query_activities)

        for activity in query_activities:
            rel_type = activity.get("relationship_type")
            if rel_type:
                relationship_counts[rel_type] = relationship_counts.get(rel_type, 0) + 1

        # Generate insights based on dominant patterns
        for rel_type, count in relationship_counts.items():
            if count / total_activities > 0.25:  # If more than 25% of activities have this relationship
                # Create appropriate insight based on relationship type
                if rel_type == "refinement":
                    self.add_insight(
                        "query_behavior",
                        "User frequently refines queries to narrow down results",
                        confidence=min(0.5 + (count / total_activities), 0.9),
                    )
                elif rel_type == "broadening":
                    self.add_insight(
                        "query_behavior",
                        "User often broadens queries when results are too specific",
                        confidence=min(0.5 + (count / total_activities), 0.9),
                    )
                elif rel_type == "pivot":
                    self.add_insight(
                        "query_behavior",
                        "User frequently pivots to related topics during exploration",
                        confidence=min(0.5 + (count / total_activities), 0.9),
                    )
                elif rel_type == "backtrack":
                    self.add_insight(
                        "query_behavior",
                        "User often backtracks to earlier queries in the exploration",
                        confidence=min(0.5 + (count / total_activities), 0.9),
                    )


def main():
    """Test the Archivist memory system."""
    memory = ArchivistMemory()

    # Add some test data
    memory.add_long_term_goal(
        "File Organization",
        "Organize personal documents by project and year",
    )
    memory.update_goal_progress("File Organization", 0.35)

    memory.add_insight(
        "organization",
        "User struggles with finding documents older than 6 months",
        0.8,
    )
    memory.add_insight(
        "retrieval",
        "Location data is highly valuable for narrowing searches",
        0.7,
    )

    # Generate and print a forward prompt
    forward_prompt = memory.generate_forward_prompt()
    print(forward_prompt)

    # Save to database
    memory.save_memory()


if __name__ == "__main__":
    main()
