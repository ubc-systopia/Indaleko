"""
This module implements advanced query pattern analysis for the Indaleko system.

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
import logging
import os
import sys
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher
from typing import Any

from pydantic import BaseModel, Field

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
# pylint: enable=wrong-import-position
from enum import Enum

from data_models.base import IndalekoBaseModel
from query.memory.cross_source_patterns import CrossSourcePatternDetector
from query.memory.pattern_types import (
    ProactiveSuggestion,
    SuggestionPriority,
    SuggestionType,
)


class QueryIntentType(str, Enum):
    """Types of query intents."""

    SEARCH = "search"
    LIST = "list"
    COUNT = "count"
    ANALYZE = "analyze"
    RECOMMEND = "recommend"
    EXPLAIN = "explain"
    COMPARE = "compare"
    TRACK = "track"
    OTHER = "other"


class QueryEntityUsage(BaseModel):
    """Analysis of an entity's usage across queries."""

    entity_name: str = Field(..., description="Name of the entity")
    mention_count: int = Field(
        default=0,
        description="Number of times this entity appears in queries",
    )
    first_seen: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this entity was first seen",
    )
    last_seen: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this entity was last seen",
    )
    co_occurring_entities: dict[str, int] = Field(
        default_factory=dict,
        description="Entities that co-occur with this one",
    )
    intents: dict[str, int] = Field(
        default_factory=dict,
        description="Intents associated with this entity",
    )
    success_rate: float = Field(
        default=0.0,
        description="Percentage of successful queries with this entity",
    )
    query_examples: list[str] = Field(
        default_factory=list,
        description="Example queries containing this entity",
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional attributes",
    )


class QuerySequence(BaseModel):
    """A sequence of related queries."""

    sequence_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this sequence",
    )
    sequence_signature: str = Field(
        ...,
        description="Signature identifying this query sequence",
    )
    queries: list[str] = Field(
        default_factory=list,
        description="IDs of queries in this sequence",
    )
    timestamps: list[datetime] = Field(
        default_factory=list,
        description="Timestamps of queries in sequence",
    )
    frequency: int = Field(
        default=1,
        description="Number of times this sequence has been observed",
    )
    avg_time_between: float | None = Field(
        None,
        description="Average time between queries in seconds",
    )
    success_rate: float = Field(
        default=0.0,
        description="Percentage of successful queries in this sequence",
    )
    common_entities: list[str] = Field(
        default_factory=list,
        description="Entities common across queries",
    )
    refinement_pattern: str | None = Field(
        None,
        description="Pattern of query refinement if present",
    )
    is_refinement: bool = Field(
        default=False,
        description="Whether this is a refinement sequence",
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional attributes",
    )


class QueryPattern(BaseModel):
    """A pattern detected in query behavior."""

    pattern_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this pattern",
    )
    pattern_name: str = Field(..., description="Name of the pattern")
    description: str = Field(..., description="Description of the pattern")
    pattern_type: str = Field(
        ...,
        description="Type of pattern (time-based, entity-based, etc.)",
    )
    confidence: float = Field(
        default=0.5,
        description="Confidence in this pattern (0.0-1.0)",
    )
    observation_count: int = Field(
        default=1,
        description="Number of times this pattern was observed",
    )
    first_observed: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this pattern was first observed",
    )
    last_observed: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this pattern was last observed",
    )
    supporting_evidence: list[str] = Field(
        default_factory=list,
        description="Query IDs supporting this pattern",
    )
    entities_involved: list[str] = Field(
        default_factory=list,
        description="Entities involved in this pattern",
    )
    intents_involved: list[str] = Field(
        default_factory=list,
        description="Intents involved in this pattern",
    )
    temporal_factors: dict[str, Any] = Field(
        default_factory=dict,
        description="Temporal factors in this pattern",
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional attributes",
    )


class QueryChainType(str, Enum):
    """Types of query chains."""

    REFINEMENT = "refinement"  # Refining a previous query with added filters
    EXPANSION = "expansion"  # Expanding a previous query to be more general
    PIVOT = "pivot"  # Switching focus while keeping some context
    EXPLORATION = "exploration"  # Exploring related but different aspects
    REPETITION = "repetition"  # Similar queries repeated over time
    COMPARISON = "comparison"  # Comparing different entities
    DRILL_DOWN = "drill_down"  # Progressive narrowing to specific information
    OTHER = "other"  # Other types of chains


class QueryChain(BaseModel):
    """A chain of related queries that form a logical sequence."""

    chain_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this chain",
    )
    chain_type: QueryChainType = Field(..., description="Type of query chain")
    queries: list[str] = Field(
        default_factory=list,
        description="IDs of queries in this chain",
    )
    query_texts: list[str] = Field(
        default_factory=list,
        description="Texts of queries in this chain",
    )
    start_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this chain started",
    )
    end_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this chain ended",
    )
    duration: float = Field(default=0.0, description="Duration of the chain in seconds")
    shared_entities: list[str] = Field(
        default_factory=list,
        description="Entities shared across the chain",
    )
    transition_patterns: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Patterns in transitions between queries",
    )
    outcome: str | None = Field(None, description="Final outcome of the chain")
    success_rate: float = Field(
        default=0.0,
        description="Success rate of queries in the chain",
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional attributes",
    )


class QueryRefinementType(str, Enum):
    """Types of query refinements."""

    ADD_FILTER = "add_filter"  # Adding a filter condition
    REMOVE_FILTER = "remove_filter"  # Removing a filter condition
    CHANGE_ENTITY = "change_entity"  # Changing the focus entity
    SPECIFY_ATTRIBUTE = "specify_attribute"  # Specifying an attribute
    TEMPORAL_REFINEMENT = "temporal_refinement"  # Adding time constraints
    LOCATION_REFINEMENT = "location_refinement"  # Adding location constraints
    RESTATE = "restate"  # Restating the query differently
    CORRECT = "correct"  # Correcting an error
    BROADEN = "broaden"  # Making the query broader
    NARROW = "narrow"  # Making the query more specific
    OTHER = "other"  # Other types of refinements


class QueryRefinement(BaseModel):
    """A refinement relationship between two queries."""

    refinement_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this refinement",
    )
    original_query_id: str = Field(..., description="ID of the original query")
    refined_query_id: str = Field(..., description="ID of the refined query")
    refinement_type: QueryRefinementType = Field(..., description="Type of refinement")
    time_between: float = Field(..., description="Time between queries in seconds")
    similarity: float = Field(
        default=0.0,
        description="Similarity measure between the queries",
    )
    added_terms: list[str] = Field(
        default_factory=list,
        description="Terms added in the refinement",
    )
    removed_terms: list[str] = Field(
        default_factory=list,
        description="Terms removed in the refinement",
    )
    added_entities: list[str] = Field(
        default_factory=list,
        description="Entities added in the refinement",
    )
    removed_entities: list[str] = Field(
        default_factory=list,
        description="Entities removed in the refinement",
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional attributes",
    )


class UserQueryHistoryMetrics(BaseModel):
    """Metrics on a user's query behavior."""

    user_id: str = Field(..., description="Identifier for the user")
    time_period: str = Field(
        default="all_time",
        description="Time period for these metrics",
    )
    start_date: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Start of the time period",
    )
    end_date: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="End of the time period",
    )
    total_queries: int = Field(default=0, description="Total number of queries")

    # Query success metrics
    successful_queries: int = Field(
        default=0,
        description="Number of queries with results",
    )
    empty_result_queries: int = Field(
        default=0,
        description="Number of queries with no results",
    )
    success_rate: float = Field(
        default=0.0,
        description="Percentage of successful queries",
    )

    # Query complexity metrics
    avg_query_length: float = Field(
        default=0.0,
        description="Average length of queries in characters",
    )
    avg_entity_count: float = Field(
        default=0.0,
        description="Average number of entities per query",
    )

    # Temporal metrics
    queries_by_hour: dict[int, int] = Field(
        default_factory=dict,
        description="Distribution of queries by hour",
    )
    queries_by_day: dict[int, int] = Field(
        default_factory=dict,
        description="Distribution of queries by day of week",
    )

    # Content metrics
    top_entities: dict[str, int] = Field(
        default_factory=dict,
        description="Most frequently queried entities",
    )
    top_intents: dict[str, int] = Field(
        default_factory=dict,
        description="Most frequent query intents",
    )

    # Chain metrics
    avg_chain_length: float = Field(
        default=0.0,
        description="Average number of queries in a chain",
    )
    refinement_rate: float = Field(default=0.0, description="Rate of query refinement")

    # Performance metrics
    avg_query_time: float = Field(
        default=0.0,
        description="Average query execution time in seconds",
    )
    max_query_time: float = Field(
        default=0.0,
        description="Maximum query execution time in seconds",
    )


class QueryAssociationRule(BaseModel):
    """An association rule between query elements."""

    rule_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this rule",
    )
    antecedent: list[str] = Field(..., description="Antecedent elements")
    consequent: list[str] = Field(..., description="Consequent elements")
    support: float = Field(
        ...,
        description="Support for this rule (frequency of antecedent and consequent together)",
    )
    confidence: float = Field(
        ...,
        description="Confidence in this rule (frequency of consequent given antecedent)",
    )
    lift: float = Field(..., description="Lift of this rule (how much above chance)")
    conviction: float | None = Field(None, description="Conviction of this rule")
    rule_type: str = Field(..., description="Type of rule (entity, intent, etc.)")
    observed_count: int = Field(
        default=0,
        description="Number of times this rule has been observed",
    )
    examples: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Example occurrences of this rule",
    )


class QueryPatternAnalysisData(IndalekoBaseModel):
    """Data model for the Query Pattern Analysis system."""

    # Basic query tracking
    queries: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Query history records",
    )
    query_timeline: list[tuple[str, datetime]] = Field(
        default_factory=list,
        description="Chronological timeline of queries",
    )

    # Entity analysis
    entity_usage: dict[str, QueryEntityUsage] = Field(
        default_factory=dict,
        description="Analysis of entity usage",
    )

    # Pattern detection
    query_patterns: list[QueryPattern] = Field(
        default_factory=list,
        description="Detected query patterns",
    )
    query_sequences: list[QuerySequence] = Field(
        default_factory=list,
        description="Detected query sequences",
    )

    # Query chains and refinements
    query_chains: list[QueryChain] = Field(
        default_factory=list,
        description="Detected query chains",
    )
    query_refinements: list[QueryRefinement] = Field(
        default_factory=list,
        description="Detected query refinements",
    )

    # Association rules
    association_rules: list[QueryAssociationRule] = Field(
        default_factory=list,
        description="Association rules between query elements",
    )

    # User metrics
    user_metrics: dict[str, UserQueryHistoryMetrics] = Field(
        default_factory=dict,
        description="Metrics on user query behavior",
    )

    # Cross-source integration
    cross_source_events: list[str] = Field(
        default_factory=list,
        description="IDs of related cross-source events",
    )

    # System metadata
    last_update: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this data was last updated",
    )
    version: str = Field(default="1.0.0", description="Version of the data model")


class QueryPatternAnalyzer:
    """
    Advanced query pattern analyzer for detecting sophisticated patterns in search behavior.

    This component enables:
    1. Detection of temporal patterns in query behavior
    2. Analysis of query refinement sequences
    3. Identification of entity co-occurrence patterns
    4. Discovery of successful search strategies
    5. Prediction of related queries based on context
    6. Integration with cross-source pattern detection
    """

    def __init__(self, db_config=None, cross_source_detector=None):
        """
        Initialize the query pattern analyzer.

        Args:
            db_config: Database configuration for accessing data
            cross_source_detector: Optional cross-source pattern detector for integration
        """
        self.db_config = db_config
        self.cross_source_detector = cross_source_detector
        if cross_source_detector is None and db_config is not None:
            self.cross_source_detector = CrossSourcePatternDetector(db_config)

        self.data = QueryPatternAnalysisData()
        self.logger = logging.getLogger(__name__)

        # Configuration parameters
        self.similarity_threshold = 0.7  # Threshold for query similarity
        self.chain_time_threshold = 3600  # Maximum time between queries in a chain (1 hour)
        self.min_pattern_support = 3  # Minimum observations for a pattern
        self.temporal_window_size = 7  # Days to look back for temporal patterns

    def load_query_history(self, max_queries: int = 1000, days_back: int = 30) -> int:
        """
        Load query history from the database.

        Args:
            max_queries: Maximum number of queries to load
            days_back: Number of days to look back

        Returns:
            Number of queries loaded
        """
        if not self.db_config or not self.db_config.db:
            self.logger.warning(
                "No database connection available for loading query history",
            )
            return 0

        loaded_count = 0
        try:
            # Get the collection
            collection_name = "QueryHistory"
            if not self.db_config.db.has_collection(collection_name):
                self.logger.warning(f"Collection {collection_name} not found")
                return 0

            collection = self.db_config.db.collection(collection_name)

            # Get query history from the last N days
            cutoff_date = datetime.now(UTC) - timedelta(days=days_back)

            cursor = collection.find(
                {"Record.Timestamp": {"$gt": cutoff_date.isoformat()}},
                sort=[("Record.Timestamp", 1)],
                limit=max_queries,
            )

            # Process each query
            self.data.queries = {}
            self.data.query_timeline = []

            for doc in cursor:
                try:
                    query_id = str(doc.get("_key", uuid.uuid4()))
                    timestamp = datetime.fromisoformat(doc["Record"]["Timestamp"])

                    # Store the query
                    self.data.queries[query_id] = doc
                    self.data.query_timeline.append((query_id, timestamp))

                    # Process entities
                    self._process_query_entities(query_id, doc)

                    loaded_count += 1

                except Exception as e:
                    self.logger.error(
                        f"Error processing query {doc.get('_key', 'unknown')}: {e}",
                    )

            # Sort the timeline
            self.data.query_timeline.sort(key=lambda x: x[1])

            self.logger.info(f"Loaded {loaded_count} queries from history")

        except Exception as e:
            self.logger.error(f"Error loading query history: {e}")

        return loaded_count

    def _process_query_entities(
        self,
        query_id: str,
        query_data: dict[str, Any],
    ) -> None:
        """
        Process and analyze entities in a query.

        Args:
            query_id: ID of the query
            query_data: Query data dictionary
        """
        try:
            # Extract query text and timestamp
            query_text = query_data.get("QueryHistory", {}).get("OriginalQuery", "")
            if not query_text and "OriginalQuery" in query_data:
                query_text = query_data["OriginalQuery"]

            timestamp = datetime.fromisoformat(query_data["Record"]["Timestamp"])

            # Extract entities
            entities = []

            # Try to get entities from parsed results
            if "QueryHistory" in query_data and "ParsedResults" in query_data["QueryHistory"]:
                parsed = query_data["QueryHistory"]["ParsedResults"]
                if "Entities" in parsed:
                    for entity in parsed["Entities"]:
                        if isinstance(entity, dict) and "name" in entity:
                            entities.append(entity["name"])

            # Check alternative paths
            elif "ParsedResults" in query_data and "Entities" in query_data["ParsedResults"]:
                for entity in query_data["ParsedResults"]["Entities"]:
                    if isinstance(entity, dict) and "name" in entity:
                        entities.append(entity["name"])

            # Determine success/failure
            has_results = False
            if "QueryHistory" in query_data and "RawResults" in query_data["QueryHistory"]:
                has_results = len(query_data["QueryHistory"]["RawResults"]) > 0
            elif "RawResults" in query_data:
                has_results = len(query_data["RawResults"]) > 0

            # Extract execution time
            execution_time = None
            if "QueryHistory" in query_data and "ElapsedTime" in query_data["QueryHistory"]:
                execution_time = query_data["QueryHistory"]["ElapsedTime"]
            elif "ElapsedTime" in query_data:
                execution_time = query_data["ElapsedTime"]

            # Extract intent
            intent = "search"  # Default intent
            if "QueryHistory" in query_data and "ParsedResults" in query_data["QueryHistory"]:
                parsed = query_data["QueryHistory"]["ParsedResults"]
                if "Intent" in parsed:
                    intent = parsed["Intent"]
            elif "ParsedResults" in query_data and "Intent" in query_data["ParsedResults"]:
                intent = query_data["ParsedResults"]["Intent"]

            # Update entity usage statistics
            for entity_name in entities:
                if entity_name not in self.data.entity_usage:
                    self.data.entity_usage[entity_name] = QueryEntityUsage(
                        entity_name=entity_name,
                        first_seen=timestamp,
                        last_seen=timestamp,
                        mention_count=1,
                        query_examples=[query_text[:100]],  # Store truncated example
                        intents={intent: 1},
                        success_rate=1.0 if has_results else 0.0,
                    )
                else:
                    # Update existing entity
                    entity_usage = self.data.entity_usage[entity_name]
                    entity_usage.mention_count += 1
                    entity_usage.last_seen = timestamp

                    # Update intent counts
                    if intent in entity_usage.intents:
                        entity_usage.intents[intent] += 1
                    else:
                        entity_usage.intents[intent] = 1

                    # Update success rate
                    total_queries = entity_usage.mention_count
                    successful_queries = int(
                        entity_usage.success_rate * (total_queries - 1),
                    )
                    successful_queries += 1 if has_results else 0
                    entity_usage.success_rate = successful_queries / total_queries

                    # Add example if we don't have many
                    if len(entity_usage.query_examples) < 5:
                        entity_usage.query_examples.append(query_text[:100])

                # Track co-occurring entities
                for co_entity in entities:
                    if co_entity != entity_name:
                        entity_usage = self.data.entity_usage[entity_name]
                        if co_entity in entity_usage.co_occurring_entities:
                            entity_usage.co_occurring_entities[co_entity] += 1
                        else:
                            entity_usage.co_occurring_entities[co_entity] = 1

        except Exception as e:
            self.logger.error(f"Error processing entities for query {query_id}: {e}")

    def analyze_query_chains(self) -> list[QueryChain]:
        """
        Analyze query history to identify chains of related queries.

        Returns:
            List of detected query chains
        """
        chains = []

        # Timeline should be sorted by timestamp
        timeline = self.data.query_timeline
        if not timeline or len(timeline) < 2:
            return chains

        # Track chains being built
        current_chains = []

        # Process the timeline
        for i in range(1, len(timeline)):
            prev_id, prev_time = timeline[i - 1]
            curr_id, curr_time = timeline[i]

            time_diff = (curr_time - prev_time).total_seconds()

            if time_diff > self.chain_time_threshold:
                # Too much time passed, close any open chains
                for chain in current_chains:
                    if len(chain.queries) > 1:
                        chain.end_time = prev_time
                        chain.duration = (chain.end_time - chain.start_time).total_seconds()
                        chains.append(chain)

                # Reset current chains
                current_chains = []
                continue

            # Get query data
            prev_query = self.data.queries[prev_id]
            curr_query = self.data.queries[curr_id]

            # Extract texts
            prev_text = prev_query.get("QueryHistory", {}).get("OriginalQuery", "")
            if not prev_text and "OriginalQuery" in prev_query:
                prev_text = prev_query["OriginalQuery"]

            curr_text = curr_query.get("QueryHistory", {}).get("OriginalQuery", "")
            if not curr_text and "OriginalQuery" in curr_query:
                curr_text = curr_query["OriginalQuery"]

            # Extract entities
            prev_entities = self._extract_entities(prev_query)
            curr_entities = self._extract_entities(curr_query)

            # Find shared entities
            shared_entities = [e for e in prev_entities if e in curr_entities]

            # Calculate text similarity
            similarity = self._calculate_query_similarity(prev_text, curr_text)

            # Determine if this is a refinement
            is_refinement = similarity > self.similarity_threshold and len(shared_entities) > 0
            refinement_type = self._determine_refinement_type(
                prev_text,
                curr_text,
                prev_entities,
                curr_entities,
            )

            # Check if these queries can be part of the same chain
            chain_match = False
            for chain in current_chains:
                # If the last query in the chain is the previous query
                if chain.queries and chain.queries[-1] == prev_id:
                    # Extend the chain
                    chain.queries.append(curr_id)
                    chain.query_texts.append(curr_text)

                    # Add transition pattern
                    transition = {
                        "from": prev_id,
                        "to": curr_id,
                        "time_diff": time_diff,
                        "similarity": similarity,
                        "shared_entities": shared_entities,
                        "refinement_type": (refinement_type.value if refinement_type else None),
                    }
                    chain.transition_patterns.append(transition)

                    # Update shared entities across the chain
                    if not chain.shared_entities:
                        chain.shared_entities = shared_entities
                    else:
                        chain.shared_entities = [e for e in chain.shared_entities if e in shared_entities]

                    chain_match = True
                    break

            # If no matching chain, create a new one
            if not chain_match and (is_refinement or (shared_entities and len(shared_entities) > 0)):
                # Determine chain type
                chain_type = QueryChainType.OTHER
                if is_refinement:
                    if refinement_type == QueryRefinementType.NARROW:
                        chain_type = QueryChainType.REFINEMENT
                    elif refinement_type == QueryRefinementType.BROADEN:
                        chain_type = QueryChainType.EXPANSION
                    elif refinement_type == QueryRefinementType.CHANGE_ENTITY:
                        chain_type = QueryChainType.PIVOT

                # Create transition pattern
                transition = {
                    "from": prev_id,
                    "to": curr_id,
                    "time_diff": time_diff,
                    "similarity": similarity,
                    "shared_entities": shared_entities,
                    "refinement_type": (refinement_type.value if refinement_type else None),
                }

                # Create new chain
                chain = QueryChain(
                    chain_type=chain_type,
                    queries=[prev_id, curr_id],
                    query_texts=[prev_text, curr_text],
                    start_time=prev_time,
                    end_time=curr_time,
                    shared_entities=shared_entities,
                    transition_patterns=[transition],
                )

                current_chains.append(chain)

        # Close any remaining chains
        for chain in current_chains:
            if len(chain.queries) > 1:
                last_id, last_time = next(
                    (id_time for id_time in timeline if id_time[0] == chain.queries[-1]),
                    (None, None),
                )
                if last_time:
                    chain.end_time = last_time
                    chain.duration = (chain.end_time - chain.start_time).total_seconds()
                    chains.append(chain)

        # Calculate success rates for each chain
        for chain in chains:
            successful = 0
            for query_id in chain.queries:
                query = self.data.queries.get(query_id, {})
                if self._query_has_results(query):
                    successful += 1

            chain.success_rate = successful / len(chain.queries) if chain.queries else 0.0

        # Store in the data model
        self.data.query_chains = chains

        return chains

    def _extract_entities(self, query_data: dict[str, Any]) -> list[str]:
        """Extract entities from query data."""
        entities = []

        # Try to get entities from parsed results
        if "QueryHistory" in query_data and "ParsedResults" in query_data["QueryHistory"]:
            parsed = query_data["QueryHistory"]["ParsedResults"]
            if "Entities" in parsed:
                for entity in parsed["Entities"]:
                    if isinstance(entity, dict) and "name" in entity:
                        entities.append(entity["name"])

        # Check alternative paths
        elif "ParsedResults" in query_data and "Entities" in query_data["ParsedResults"]:
            for entity in query_data["ParsedResults"]["Entities"]:
                if isinstance(entity, dict) and "name" in entity:
                    entities.append(entity["name"])

        return entities

    def _query_has_results(self, query_data: dict[str, Any]) -> bool:
        """Check if a query has results."""
        if "QueryHistory" in query_data and "RawResults" in query_data["QueryHistory"]:
            return len(query_data["QueryHistory"]["RawResults"]) > 0
        elif "RawResults" in query_data:
            return len(query_data["RawResults"]) > 0
        return False

    def _calculate_query_similarity(self, query1: str, query2: str) -> float:
        """Calculate similarity between two queries."""
        if not query1 or not query2:
            return 0.0

        # Use SequenceMatcher for similarity
        return SequenceMatcher(None, query1.lower(), query2.lower()).ratio()

    def _determine_refinement_type(
        self,
        query1: str,
        query2: str,
        entities1: list[str],
        entities2: list[str],
    ) -> QueryRefinementType | None:
        """Determine the type of refinement between two queries."""
        if not query1 or not query2:
            return None

        # Check if this is a complete rewrite
        similarity = self._calculate_query_similarity(query1, query2)
        if similarity < 0.3:
            return None

        # Check for entity changes
        entity_diff = set(entities2) - set(entities1)
        if entity_diff and not all(e in entities1 for e in entities2):
            return QueryRefinementType.CHANGE_ENTITY

        # Check for temporal refinements (added date/time terms)
        temporal_terms = [
            "today",
            "yesterday",
            "last week",
            "month",
            "year",
            "before",
            "after",
            "between",
        ]
        has_new_temporal = any(term in query2.lower() and term not in query1.lower() for term in temporal_terms)
        if has_new_temporal:
            return QueryRefinementType.TEMPORAL_REFINEMENT

        # Check for location refinements
        location_terms = ["in", "at", "near", "location", "where"]
        has_new_location = any(term in query2.lower() and term not in query1.lower() for term in location_terms)
        if has_new_location:
            return QueryRefinementType.LOCATION_REFINEMENT

        # Check for narrowing vs broadening
        if len(query2) > len(query1) and all(e in entities2 for e in entities1):
            return QueryRefinementType.NARROW
        elif len(query2) < len(query1) and all(e in entities1 for e in entities2):
            return QueryRefinementType.BROADEN

        # Default to adding a filter
        return QueryRefinementType.ADD_FILTER

    def detect_query_patterns(self) -> list[QueryPattern]:
        """
        Detect patterns in query behavior.

        Returns:
            List of detected patterns
        """
        patterns = []

        # Detect temporal patterns
        temporal_patterns = self._detect_temporal_patterns()
        patterns.extend(temporal_patterns)

        # Detect entity patterns
        entity_patterns = self._detect_entity_patterns()
        patterns.extend(entity_patterns)

        # Detect refinement patterns
        refinement_patterns = self._detect_refinement_patterns()
        patterns.extend(refinement_patterns)

        # Store in data model
        self.data.query_patterns = patterns

        return patterns

    def _detect_temporal_patterns(self) -> list[QueryPattern]:
        """Detect temporal patterns in query behavior."""
        patterns = []

        # Check if we have enough data
        if len(self.data.query_timeline) < self.min_pattern_support:
            return patterns

        # Analyze queries by hour of day
        hour_counts = defaultdict(list)
        for query_id, timestamp in self.data.query_timeline:
            hour_counts[timestamp.hour].append(query_id)

        # Find hours with consistent query behavior
        for hour, query_ids in hour_counts.items():
            if len(query_ids) < self.min_pattern_support:
                continue

            # Check for entity patterns at this hour
            entity_counts = defaultdict(int)
            intent_counts = defaultdict(int)

            for query_id in query_ids:
                query_data = self.data.queries.get(query_id, {})

                # Count entities
                entities = self._extract_entities(query_data)
                for entity in entities:
                    entity_counts[entity] += 1

                # Count intents
                intent = self._extract_intent(query_data)
                intent_counts[intent] += 1

            # Find dominant entities and intents
            dominant_entities = [e for e, c in entity_counts.items() if c >= self.min_pattern_support]
            dominant_intents = [i for i, c in intent_counts.items() if c >= self.min_pattern_support]

            if dominant_entities or dominant_intents:
                # We have a temporal pattern
                pattern_name = f"Hour-{hour} Query Pattern"

                # Create description
                description = f"Consistent queries at {hour}:00"
                if dominant_entities:
                    entity_str = ", ".join(dominant_entities[:3])
                    if len(dominant_entities) > 3:
                        entity_str += f" and {len(dominant_entities)-3} more"
                    description += f" involving {entity_str}"

                if dominant_intents:
                    intent_str = ", ".join(dominant_intents[:2])
                    description += f" with {intent_str} intent"

                # Calculate confidence based on consistency
                confidence = min(
                    0.5 + (len(query_ids) / 20),
                    0.95,
                )  # Scales up with more observations

                # Create pattern
                pattern = QueryPattern(
                    pattern_name=pattern_name,
                    description=description,
                    pattern_type="temporal_hour",
                    confidence=confidence,
                    observation_count=len(query_ids),
                    supporting_evidence=query_ids[:10],  # Limit to 10 examples
                    entities_involved=dominant_entities,
                    intents_involved=dominant_intents,
                    temporal_factors={"hour": hour},
                )

                patterns.append(pattern)

        # Similar analysis could be done for day of week patterns

        return patterns

    def _extract_intent(self, query_data: dict[str, Any]) -> str:
        """Extract intent from query data."""
        # Try to get intent from parsed results
        if "QueryHistory" in query_data and "ParsedResults" in query_data["QueryHistory"]:
            parsed = query_data["QueryHistory"]["ParsedResults"]
            if "Intent" in parsed:
                return parsed["Intent"]

        # Check alternative paths
        elif "ParsedResults" in query_data and "Intent" in query_data["ParsedResults"]:
            return query_data["ParsedResults"]["Intent"]

        # Default intent
        return "search"

    def _detect_entity_patterns(self) -> list[QueryPattern]:
        """Detect patterns in entity usage."""
        patterns = []

        # Check entity co-occurrence
        for entity_name, entity_usage in self.data.entity_usage.items():
            # Skip if not mentioned enough
            if entity_usage.mention_count < self.min_pattern_support:
                continue

            # Find strongly co-occurring entities
            strong_cooccurrence = []
            for co_entity, count in entity_usage.co_occurring_entities.items():
                # Calculate co-occurrence strength
                if count >= self.min_pattern_support:
                    co_entity_usage = self.data.entity_usage.get(co_entity)
                    if co_entity_usage:
                        # Calculate conditional probability: P(co_entity | entity)
                        conditional_prob = count / entity_usage.mention_count

                        if conditional_prob >= 0.5:  # Strong co-occurrence
                            strong_cooccurrence.append((co_entity, conditional_prob))

            # If we have strong co-occurrences, create a pattern
            if strong_cooccurrence:
                pattern_name = f"Entity Co-occurrence: {entity_name}"

                # Sort by strength
                strong_cooccurrence.sort(key=lambda x: x[1], reverse=True)
                top_cooccur = strong_cooccurrence[:3]  # Top 3

                # Create description
                cooccur_str = ", ".join(f"{e} ({p:.1%})" for e, p in top_cooccur)
                description = f"When querying about {entity_name}, users often also query about {cooccur_str}"

                # Calculate confidence based on strength and consistency
                avg_strength = sum(p for _, p in top_cooccur) / len(top_cooccur)
                confidence = min(0.6 + (avg_strength * 0.3), 0.9)

                # Create pattern
                pattern = QueryPattern(
                    pattern_name=pattern_name,
                    description=description,
                    pattern_type="entity_cooccurrence",
                    confidence=confidence,
                    observation_count=entity_usage.mention_count,
                    entities_involved=[entity_name] + [e for e, _ in top_cooccur],
                    attributes={
                        "co_occurrence_strengths": {e: p for e, p in strong_cooccurrence},
                        "success_rate": entity_usage.success_rate,
                    },
                )

                patterns.append(pattern)

        return patterns

    def _detect_refinement_patterns(self) -> list[QueryPattern]:
        """Detect patterns in query refinement behavior."""
        patterns = []

        # Check if we have chains
        if not self.data.query_chains:
            return patterns

        # Analyze refinement chains
        refinement_chains = [c for c in self.data.query_chains if c.chain_type == QueryChainType.REFINEMENT]

        # Skip if not enough data
        if len(refinement_chains) < self.min_pattern_support:
            return patterns

        # Analyze refinement types
        refinement_type_counts = defaultdict(int)
        for chain in refinement_chains:
            for transition in chain.transition_patterns:
                if transition.get("refinement_type"):
                    refinement_type_counts[transition["refinement_type"]] += 1

        # Find common refinement types
        for ref_type, count in refinement_type_counts.items():
            if count < self.min_pattern_support:
                continue

            # Create a pattern for this refinement type
            pattern_name = f"Query Refinement: {ref_type}"

            # Get example chains with this refinement type
            examples = []
            for chain in refinement_chains:
                for transition in chain.transition_patterns:
                    if transition.get("refinement_type") == ref_type:
                        examples.append(chain.chain_id)
                        break
                if len(examples) >= 5:  # Limit to 5 examples
                    break

            # Create description
            description = f"Users frequently refine queries by {ref_type.replace('_', ' ')}"

            # Add success rate information if available
            success_rates = [
                chain.success_rate
                for chain in refinement_chains
                if any(t.get("refinement_type") == ref_type for t in chain.transition_patterns)
            ]

            if success_rates:
                avg_success = sum(success_rates) / len(success_rates)
                confidence = min(
                    0.5 + (count / 10) * 0.4,
                    0.9,
                )  # Scale confidence with observation count

                if avg_success > 0.7:
                    description += f", with high success rate ({avg_success:.1%})"
                    confidence = min(
                        confidence + 0.1,
                        0.95,
                    )  # Boost confidence for successful patterns
            else:
                confidence = min(0.5 + (count / 10) * 0.3, 0.8)

            # Create pattern
            pattern = QueryPattern(
                pattern_name=pattern_name,
                description=description,
                pattern_type="query_refinement",
                confidence=confidence,
                observation_count=count,
                supporting_evidence=examples,
                attributes={
                    "refinement_type": ref_type,
                    "avg_success_rate": (sum(success_rates) / len(success_rates) if success_rates else None),
                },
            )

            patterns.append(pattern)

        return patterns

    def calculate_metrics(self) -> UserQueryHistoryMetrics:
        """
        Calculate comprehensive metrics on query behavior.

        Returns:
            UserQueryHistoryMetrics object with calculated metrics
        """
        if not self.data.queries or not self.data.query_timeline:
            return None

        # Initialize metrics
        metrics = UserQueryHistoryMetrics(
            user_id="current_user",  # Default user
            start_date=(self.data.query_timeline[0][1] if self.data.query_timeline else datetime.now(UTC)),
            end_date=(self.data.query_timeline[-1][1] if self.data.query_timeline else datetime.now(UTC)),
        )

        # Calculate basic metrics
        metrics.total_queries = len(self.data.queries)

        # Count successful queries
        successful = 0
        query_lengths = []
        entity_counts = []
        query_times = []
        intent_counts = defaultdict(int)
        hour_counts = defaultdict(int)
        day_counts = defaultdict(int)
        entity_counts_agg = defaultdict(int)

        for query_id, timestamp in self.data.query_timeline:
            query_data = self.data.queries.get(query_id, {})

            # Success count
            if self._query_has_results(query_data):
                successful += 1

            # Get query text for length
            query_text = self._extract_query_text(query_data)
            if query_text:
                query_lengths.append(len(query_text))

            # Count entities
            entities = self._extract_entities(query_data)
            entity_counts.append(len(entities))

            # Track top entities
            for entity in entities:
                entity_counts_agg[entity] += 1

            # Extract intent
            intent = self._extract_intent(query_data)
            intent_counts[intent] += 1

            # Temporal distribution
            hour_counts[timestamp.hour] += 1
            day_counts[timestamp.weekday()] += 1

            # Performance metrics
            execution_time = self._extract_execution_time(query_data)
            if execution_time is not None:
                query_times.append(execution_time)

        # Calculate derived metrics
        metrics.successful_queries = successful
        metrics.empty_result_queries = metrics.total_queries - successful
        metrics.success_rate = successful / metrics.total_queries if metrics.total_queries > 0 else 0.0

        # Complexity metrics
        metrics.avg_query_length = sum(query_lengths) / len(query_lengths) if query_lengths else 0.0
        metrics.avg_entity_count = sum(entity_counts) / len(entity_counts) if entity_counts else 0.0

        # Temporal metrics
        metrics.queries_by_hour = dict(hour_counts)
        metrics.queries_by_day = dict(day_counts)

        # Content metrics
        metrics.top_entities = dict(
            sorted(entity_counts_agg.items(), key=lambda x: x[1], reverse=True)[:10],
        )
        metrics.top_intents = dict(
            sorted(intent_counts.items(), key=lambda x: x[1], reverse=True),
        )

        # Chain metrics
        if self.data.query_chains:
            chain_lengths = [len(chain.queries) for chain in self.data.query_chains]
            metrics.avg_chain_length = sum(chain_lengths) / len(chain_lengths) if chain_lengths else 0.0

            # Count refinements
            refinement_chains = [c for c in self.data.query_chains if c.chain_type == QueryChainType.REFINEMENT]
            metrics.refinement_rate = (
                len(refinement_chains) / len(self.data.query_chains) if self.data.query_chains else 0.0
            )

        # Performance metrics
        if query_times:
            metrics.avg_query_time = sum(query_times) / len(query_times)
            metrics.max_query_time = max(query_times)

        # Store in data model
        self.data.user_metrics["current_user"] = metrics

        return metrics

    def _extract_query_text(self, query_data: dict[str, Any]) -> str:
        """Extract query text from query data."""
        query_text = query_data.get("QueryHistory", {}).get("OriginalQuery", "")
        if not query_text and "OriginalQuery" in query_data:
            query_text = query_data["OriginalQuery"]
        return query_text

    def _extract_execution_time(self, query_data: dict[str, Any]) -> float | None:
        """Extract execution time from query data."""
        if "QueryHistory" in query_data and "ElapsedTime" in query_data["QueryHistory"]:
            return query_data["QueryHistory"]["ElapsedTime"]
        elif "ElapsedTime" in query_data:
            return query_data["ElapsedTime"]
        return None

    def generate_query_suggestions(
        self,
        context: dict[str, Any] = None,
    ) -> list[ProactiveSuggestion]:
        """
        Generate query suggestions based on detected patterns.

        Args:
            context: Optional context to influence suggestions

        Returns:
            List of query suggestions
        """
        suggestions = []

        # Get current time context
        now = datetime.now(UTC)
        current_hour = now.hour

        # Check if we have enough data for meaningful suggestions
        if not self.data.query_patterns:
            return suggestions

        # 1. Temporal suggestions
        for pattern in self.data.query_patterns:
            if pattern.pattern_type == "temporal_hour" and pattern.temporal_factors.get("hour") == current_hour:
                # This is a pattern matching the current hour

                # Only suggest high confidence patterns
                if pattern.confidence >= 0.7:
                    # Create suggestion with relevant entities
                    entities_str = ", ".join(pattern.entities_involved[:2])
                    if len(pattern.entities_involved) > 2:
                        entities_str += f" and {len(pattern.entities_involved)-2} more"

                    content = f"Based on your patterns, you might want to search for information about {entities_str} at this time."

                    suggestion = ProactiveSuggestion(
                        suggestion_type=SuggestionType.QUERY,
                        title="Search suggestion based on your patterns",
                        content=content,
                        expires_at=now + timedelta(hours=1),
                        priority=SuggestionPriority.MEDIUM,
                        confidence=pattern.confidence,
                        context={"pattern_id": pattern.pattern_id},
                    )

                    suggestions.append(suggestion)

        # 2. Entity-based suggestions (if context contains entities)
        if context and "entities" in context and context["entities"]:
            mentioned_entity = context["entities"][0]

            # Look for entity co-occurrence patterns
            for pattern in self.data.query_patterns:
                if pattern.pattern_type == "entity_cooccurrence" and mentioned_entity in pattern.entities_involved:
                    # Find the other entities that co-occur with this one
                    related_entities = [e for e in pattern.entities_involved if e != mentioned_entity]

                    if related_entities:
                        # Check if this is a confident pattern
                        if pattern.confidence >= 0.6:
                            related_str = ", ".join(related_entities[:2])

                            content = f"Since you're interested in '{mentioned_entity}', you might also want to explore '{related_str}'."

                            suggestion = ProactiveSuggestion(
                                suggestion_type=SuggestionType.RELATED_CONTENT,
                                title="Related search suggestion",
                                content=content,
                                expires_at=now + timedelta(hours=2),
                                priority=SuggestionPriority.MEDIUM,
                                confidence=pattern.confidence,
                                context={
                                    "pattern_id": pattern.pattern_id,
                                    "related_to": mentioned_entity,
                                },
                            )

                            suggestions.append(suggestion)

        # 3. Search strategy suggestions
        refinement_patterns = [p for p in self.data.query_patterns if p.pattern_type == "query_refinement"]
        if refinement_patterns and len(refinement_patterns) >= 2:
            # Pick a high-confidence refinement pattern
            successful_patterns = [
                p for p in refinement_patterns if p.confidence >= 0.7 and p.attributes.get("avg_success_rate", 0) > 0.7
            ]

            if successful_patterns:
                pattern = successful_patterns[0]

                # Create a suggestion based on successful refinement strategies
                refinement_type = pattern.attributes.get("refinement_type", "").replace(
                    "_",
                    " ",
                )

                content = f"When searching, try {refinement_type} to refine your queries. This approach has been successful in similar searches."

                suggestion = ProactiveSuggestion(
                    suggestion_type=SuggestionType.SEARCH_STRATEGY,
                    title="Search strategy tip",
                    content=content,
                    expires_at=now + timedelta(days=7),  # Longer expiration for strategy tips
                    priority=SuggestionPriority.LOW,
                    confidence=pattern.confidence,
                    context={"pattern_id": pattern.pattern_id},
                )

                suggestions.append(suggestion)

        # 4. Integrate with cross-source patterns if available
        if self.cross_source_detector:
            try:
                # Get suggestions from cross-source detector
                cross_source_suggestions = self.cross_source_detector.generate_suggestions(max_suggestions=3)

                # Filter to just include query-related suggestions
                query_suggestions = [s for s in cross_source_suggestions if s.suggestion_type == SuggestionType.QUERY]

                suggestions.extend(query_suggestions)
            except Exception as e:
                self.logger.error(f"Error getting cross-source suggestions: {e}")

        # Prioritize and limit suggestions
        suggestions.sort(key=lambda x: (x.priority.value, x.confidence), reverse=True)
        return suggestions[:5]  # Limit to top 5

    def analyze_and_generate(self) -> tuple[dict[str, Any], list[ProactiveSuggestion]]:
        """
        Run a complete analysis cycle and generate suggestions.

        This method:
        1. Loads query history
        2. Analyzes query chains
        3. Detects query patterns
        4. Calculates metrics
        5. Generates suggestions

        Returns:
            Tuple containing:
            - Summary of analysis results
            - List of suggestions generated
        """
        # Load and analyze data
        query_count = self.load_query_history()

        if query_count == 0:
            return {"status": "no_data", "message": "No query history available"}, []

        # Analyze chains
        chains = self.analyze_query_chains()

        # Detect patterns
        patterns = self.detect_query_patterns()

        # Calculate metrics
        metrics = self.calculate_metrics()

        # Generate suggestions
        suggestions = self.generate_query_suggestions()

        # Create summary
        summary = {
            "status": "success",
            "query_count": query_count,
            "chain_count": len(chains),
            "pattern_count": len(patterns),
            "refinement_rate": metrics.refinement_rate if metrics else 0.0,
            "success_rate": metrics.success_rate if metrics else 0.0,
            "top_entities": (list(metrics.top_entities.keys())[:5] if metrics and metrics.top_entities else []),
            "top_intents": (list(metrics.top_intents.keys()) if metrics and metrics.top_intents else []),
        }

        # Log analysis results
        self.logger.info(f"Query pattern analysis: Processed {query_count} queries")
        self.logger.info(f"Query pattern analysis: Detected {len(chains)} chains")
        self.logger.info(f"Query pattern analysis: Identified {len(patterns)} patterns")
        self.logger.info(
            f"Query pattern analysis: Generated {len(suggestions)} suggestions",
        )

        # Update last update timestamp
        self.data.last_update = datetime.now(UTC)

        return summary, suggestions


def main():
    """
    Run a demonstration of the Query Pattern Analyzer.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Query Pattern Analysis demo")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to analyze",
    )
    parser.add_argument(
        "--max-queries",
        type=int,
        default=1000,
        help="Maximum number of queries to analyze",
    )
    parser.add_argument("--mock", action="store_true", help="Run with mock data")
    parser.add_argument("--save", action="store_true", help="Save results to a file")
    parser.add_argument(
        "--output",
        type=str,
        default="query_patterns.json",
        help="Output file name",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create analyzer
    analyzer = QueryPatternAnalyzer()

    if args.mock:
        # Create some mock data
        print("Running with mock data...")
        # Mock implementation would go here

    else:
        # Connect to the database
        from db.db_config import IndalekoDBConfig

        try:
            db_config = IndalekoDBConfig()
            connected = db_config.connect()

            if not connected:
                print("Failed to connect to database")
                return

            analyzer = QueryPatternAnalyzer(db_config)

            # Run analysis
            summary, suggestions = analyzer.analyze_and_generate()

            print("\nQuery Pattern Analysis Summary:")
            print(f"Processed {summary['query_count']} queries")
            print(f"Detected {summary['chain_count']} query chains")
            print(f"Identified {summary['pattern_count']} patterns")

            if summary["top_entities"]:
                print(f"\nTop entities: {', '.join(summary['top_entities'])}")

            if summary["top_intents"]:
                print(f"Top intents: {', '.join(summary['top_intents'])}")

            print(f"\nSuccess rate: {summary['success_rate']:.1%}")
            print(f"Refinement rate: {summary['refinement_rate']:.1%}")

            if suggestions:
                print("\nGenerated Suggestions:")
                for i, suggestion in enumerate(suggestions, 1):
                    print(
                        f"{i}. {suggestion.title} ({suggestion.suggestion_type.value}, confidence: {suggestion.confidence:.2f})",
                    )
                    print(f"   {suggestion.content}")
                    print()

            # Save results if requested
            if args.save:
                results = {
                    "summary": summary,
                    "suggestions": [s.model_dump() for s in suggestions],
                    "patterns": [p.model_dump() for p in analyzer.data.query_patterns],
                    "chains": [c.model_dump() for c in analyzer.data.query_chains],
                    "metrics": (
                        analyzer.data.user_metrics["current_user"].model_dump()
                        if "current_user" in analyzer.data.user_metrics
                        else None
                    ),
                }

                with open(args.output, "w") as f:
                    json.dump(results, f, indent=2, default=str)

                print(f"Results saved to {args.output}")

        except Exception as e:
            print(f"Error: {e}")
            logging.exception("Exception in query pattern analysis")


if __name__ == "__main__":
    main()
