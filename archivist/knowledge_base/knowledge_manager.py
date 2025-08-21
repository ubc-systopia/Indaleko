"""
Knowledge Base Manager implementation for Indaleko Archivist.

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

from datetime import UTC, datetime
from typing import Any
from uuid import UUID


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from archivist.knowledge_base.data_models import (
    FeedbackRecordDataModel,
    FeedbackType,
    KnowledgePatternDataModel,
    KnowledgePatternType,
    LearningEventDataModel,
    LearningEventType,
)
from db import IndalekoDBConfig
from db.i_collections import IndalekoCollections


# pylint: enable=wrong-import-position


# Define collection names
Indaleko_Learning_Event_Collection = "LearningEvents"
Indaleko_Knowledge_Pattern_Collection = "KnowledgePatterns"
Indaleko_Feedback_Record_Collection = "FeedbackRecords"


class KnowledgeBaseManager:
    """
    Manages the knowledge base updating functionality for Indaleko.

    This class is responsible for:
    1. Recording learning events from various sources
    2. Generating knowledge patterns from learning events
    3. Managing feedback on system performance
    4. Applying learned patterns to improve system behavior
    """

    def __init__(self, db_config: IndalekoDBConfig = IndalekoDBConfig()) -> None:
        """
        Initialize the knowledge base manager.

        Args:
            db_config: Database configuration
        """
        self.db_config = db_config
        self.logger = logging.getLogger(__name__)

        # Set up the necessary collections
        self._setup_collections()

        # Cache for events and patterns
        self._events_cache: dict[UUID, LearningEventDataModel] = {}
        self._patterns_cache: dict[UUID, KnowledgePatternDataModel] = {}
        self._feedback_cache: dict[UUID, FeedbackRecordDataModel] = {}

        # Load existing data
        self._load_data()

    def _setup_collections(self) -> None:
        """Set up the necessary collections in the database."""
        # Get collections from central registry using get_collection
        try:
            # Try to get the collections using the existing method
            self.events_collection = IndalekoCollections.get_collection(
                Indaleko_Learning_Event_Collection,
            )._arangodb_collection

            self.patterns_collection = IndalekoCollections.get_collection(
                Indaleko_Knowledge_Pattern_Collection,
            )._arangodb_collection

            self.feedback_collection = IndalekoCollections.get_collection(
                Indaleko_Feedback_Record_Collection,
            )._arangodb_collection

            self.logger.info("Successfully retrieved all Knowledge Base collections")
        except Exception as e:
            # If collections don't exist, log error and raise
            self.logger.exception(f"Error setting up Knowledge Base collections: {e!s}")
            self.logger.exception(
                "Please add Knowledge Base collections to db_collections.py first",
            )
            raise ValueError(
                "Knowledge Base collections are not defined in the database. "
                 "Please add them to db_collections.py first.",
            ) from e

    def _load_data(self) -> None:
        """Load existing knowledge base data from the database."""
        try:
            # Load events
            cursor = self.events_collection.all()
            while cursor.has_more():
                doc = cursor.next()
                event = LearningEventDataModel(**doc)
                self._events_cache[event.event_id] = event

            # Load patterns
            cursor = self.patterns_collection.all()
            while cursor.has_more():
                doc = cursor.next()
                pattern = KnowledgePatternDataModel(**doc)
                self._patterns_cache[pattern.pattern_id] = pattern

            # Load feedback
            cursor = self.feedback_collection.all()
            while cursor.has_more():
                doc = cursor.next()
                feedback = FeedbackRecordDataModel(**doc)
                self._feedback_cache[feedback.feedback_id] = feedback

            self.logger.info(
                f"Loaded {len(self._events_cache)} events, "
                f"{len(self._patterns_cache)} patterns, and "
                f"{len(self._feedback_cache)} feedback records",
            )
        except Exception as e:
            self.logger.exception(f"Error loading data: {e!s}")
            # Initialize empty caches if loading fails
            self._events_cache = {}
            self._patterns_cache = {}
            self._feedback_cache = {}

    def record_learning_event(
        self,
        event_type: LearningEventType,
        source: str,
        content: dict[str, Any],
        confidence: float = 0.8,
        metadata: dict[str, Any] | None = None,
    ) -> LearningEventDataModel:
        """
        Record a new learning event.

        Args:
            event_type: The type of learning event
            source: Origin of the learning (query, user, system)
            content: The actual learned information
            confidence: Confidence in the learned information (0-1)
            metadata: Additional context about this event

        Returns:
            The created learning event
        """
        # Create new event
        event = LearningEventDataModel(
            event_type=event_type,
            source=source,
            content=content,
            confidence=confidence,
            metadata=metadata or {},
        )

        # Insert into database
        event_doc = event.serialize()
        self.events_collection.insert(event_doc)

        # Add to cache
        self._events_cache[event.event_id] = event

        # Process event to potentially generate or update patterns
        self._process_learning_event(event)

        return event

    def _process_learning_event(self, event: LearningEventDataModel) -> None:
        """
        Process a learning event to extract and update knowledge patterns.

        Args:
            event: The learning event to process
        """
        # Different processing depending on event type
        if event.event_type == LearningEventType.query_success:
            self._process_query_success(event)
        elif event.event_type == LearningEventType.user_feedback:
            self._process_user_feedback(event)
        elif event.event_type == LearningEventType.entity_discovery:
            self._process_entity_discovery(event)
        elif event.event_type == LearningEventType.schema_update:
            self._process_schema_update(event)
        elif event.event_type == LearningEventType.pattern_discovery:
            self._process_pattern_discovery(event)

    def _process_query_success(self, event: LearningEventDataModel) -> None:
        """
        Process a successful query event to extract patterns.

        Args:
            event: The query success event
        """
        # Extract query information
        query_text = event.content.get("query", "")
        query_intent = event.content.get("intent", "unknown")
        result_count = event.content.get("result_count", 0)
        entities = event.content.get("entities", [])
        execution_time = event.content.get("execution_time", 0.0)
        applied_patterns = event.content.get("applied_patterns", [])

        # Extract contextual information about when this query was successful
        query_context = {
            "timestamp": datetime.now(UTC).isoformat(),
            "time_of_day": datetime.now(UTC).hour,
            "day_of_week": datetime.now(UTC).weekday(),
            "result_count": result_count,
            "execution_time": execution_time,
            "applied_patterns": applied_patterns,
        }

        # Enhanced: Add contextual data from event
        if "context" in event.content:
            query_context.update(event.content["context"])

        # Check if this matches an existing pattern
        matching_pattern = self._find_matching_query_pattern(query_text, query_intent)

        if matching_pattern:
            # Update existing pattern
            matching_pattern.usage_count += 1
            matching_pattern.updated_at = datetime.now(UTC)

            # Update confidence based on result success
            # Increase confidence if results were found, decrease if none
            if result_count > 0:
                matching_pattern.confidence = min(
                    1.0,
                    matching_pattern.confidence + 0.05,
                )
            else:
                matching_pattern.confidence = max(
                    0.0,
                    matching_pattern.confidence - 0.1,
                )

            # Enhanced: Track query success history
            success_history = matching_pattern.pattern_data.get("success_history", [])
            success_history.append(query_context)
            matching_pattern.pattern_data["success_history"] = success_history

            # Enhanced: Update entity-specific success tracking
            if entities:
                entity_success = matching_pattern.pattern_data.get("entity_success", {})
                for entity in entities:
                    entity_name = entity if isinstance(entity, str) else entity.get("name", "unknown")
                    if entity_name not in entity_success:
                        entity_success[entity_name] = {
                            "success_count": 0,
                            "fail_count": 0,
                        }

                    if result_count > 0:
                        entity_success[entity_name]["success_count"] += 1
                    else:
                        entity_success[entity_name]["fail_count"] += 1

                matching_pattern.pattern_data["entity_success"] = entity_success

            # Enhanced: Update collection success tracking
            collections = event.content.get("collections", [])
            if collections:
                collection_success = matching_pattern.pattern_data.get(
                    "collection_success",
                    {},
                )
                for collection in collections:
                    if collection not in collection_success:
                        collection_success[collection] = {
                            "success_count": 0,
                            "fail_count": 0,
                        }

                    if result_count > 0:
                        collection_success[collection]["success_count"] += 1
                    else:
                        collection_success[collection]["fail_count"] += 1

                matching_pattern.pattern_data["collection_success"] = collection_success

            # Add this event to source events
            if event.event_id not in matching_pattern.source_events:
                matching_pattern.source_events.append(event.event_id)

            # Get the document key first
            cursor = self.patterns_collection.find(
                {"pattern_id": str(matching_pattern.pattern_id)},
            )
            if cursor.empty():
                self.logger.warning(
                    f"Pattern {matching_pattern.pattern_id} not found for update",
                )
                return

            # Get the first document
            doc = cursor.next()
            doc_key = doc["_key"]

            # Update in database with serialized data
            matching_pattern_doc = matching_pattern.serialize()

            # Use document key for update
            self.patterns_collection.update(doc_key, matching_pattern_doc)

            # Update cache
            self._patterns_cache[matching_pattern.pattern_id] = matching_pattern
        elif event.confidence >= 0.7 and result_count > 0:
            pattern = KnowledgePatternDataModel(
                pattern_type=KnowledgePatternType.query_pattern,
                confidence=event.confidence,
                pattern_data={
                    "query_text": query_text,
                    "intent": query_intent,
                    "entities": entities,
                    "result_count": result_count,
                    "collections": event.content.get("collections", []),
                    "query_template": event.content.get("query_template", ""),
                    # Enhanced: Add success history tracking
                    "success_history": [query_context],
                    "entity_success": {},
                    "collection_success": {},
                    # Enhanced: Add pattern application metrics
                    "application_metrics": {
                        "success_count": 1 if result_count > 0 else 0,
                        "fail_count": 0 if result_count > 0 else 1,
                        "avg_execution_time": execution_time,
                        "avg_result_count": result_count,
                    },
                },
                source_events=[event.event_id],
            )

            # Insert into database
            pattern_doc = pattern.serialize()
            self.patterns_collection.insert(pattern_doc)

            # Add to cache
            self._patterns_cache[pattern.pattern_id] = pattern

            # Enhanced: Check for schema learning opportunity
            if result_count > 0 and event.content.get("first_result"):
                try:
                    # Analyze sample result for schema information
                    first_result = event.content.get("first_result")
                    collections = event.content.get("collections", [])

                    for collection in collections:
                        self.detect_schema_changes(collection, first_result)
                except Exception as e:
                    self.logger.warning(f"Error detecting schema changes: {e!s}")

    def _find_matching_query_pattern(
        self,
        query_text: str,
        intent: str,
    ) -> KnowledgePatternDataModel | None:
        """
        Find a matching query pattern for a given query text and intent.

        Args:
            query_text: The query text to match
            intent: The query intent to match

        Returns:
            Matching pattern or None
        """
        best_match = None
        best_score = 0.0

        for pattern in self._patterns_cache.values():
            if pattern.pattern_type != KnowledgePatternType.query_pattern:
                continue

            pattern_intent = pattern.pattern_data.get("intent", "")
            pattern_query = pattern.pattern_data.get("query_text", "")

            # Simple matching based on intent and text similarity
            # In a real implementation, we'd use more sophisticated matching
            intent_match = intent == pattern_intent

            # Calculate similarity between queries
            from utils.misc.string_similarity import jaro_winkler_similarity

            text_similarity = jaro_winkler_similarity(
                query_text.lower(),
                pattern_query.lower(),
            )

            # Score is a combination of intent match and text similarity
            score = (0.5 if intent_match else 0.0) + (0.5 * text_similarity)

            if score > best_score and score >= 0.7:
                best_score = score
                best_match = pattern

        return best_match

    def _process_user_feedback(self, event: LearningEventDataModel) -> None:
        """
        Process user feedback event.

        Args:
            event: The user feedback event
        """
        # Extract feedback information
        feedback_type = event.content.get("feedback_type", "")
        pattern_id = event.content.get("pattern_id")
        strength = event.content.get("strength", 0.5)

        # If feedback is about a specific pattern, update it
        if pattern_id:
            pattern = self._patterns_cache.get(UUID(pattern_id))
            if pattern:
                # Adjust confidence based on feedback
                if feedback_type in ("explicit_positive", "implicit_positive"):
                    pattern.confidence = min(1.0, pattern.confidence + (0.1 * strength))
                else:
                    pattern.confidence = max(0.0, pattern.confidence - (0.2 * strength))

                # Get the document key first
                cursor = self.patterns_collection.find(
                    {"pattern_id": str(pattern.pattern_id)},
                )
                if cursor.empty():
                    self.logger.warning(
                        f"Pattern {pattern.pattern_id} not found for update",
                    )
                    return

                # Get the first document
                doc = cursor.next()
                doc_key = doc["_key"]

                # Update in database with serialized data
                pattern_doc = pattern.serialize()

                # Use document key for update
                self.patterns_collection.update(doc_key, pattern_doc)

                # Update cache
                self._patterns_cache[pattern.pattern_id] = pattern

    def _process_entity_discovery(self, event: LearningEventDataModel) -> None:
        """
        Process entity discovery event.

        Args:
            event: The entity discovery event
        """
        # Extract entity information
        entity_name = event.content.get("entity_name", "")
        entity_type = event.content.get("entity_type", "")
        entity_attributes = event.content.get("attributes", {})

        # Check if we already have a pattern for this entity
        existing_pattern = None
        for pattern in self._patterns_cache.values():
            if (
                pattern.pattern_type == KnowledgePatternType.entity_relationship
                and pattern.pattern_data.get("entity_name") == entity_name
                and pattern.pattern_data.get("entity_type") == entity_type
            ):
                existing_pattern = pattern
                break

        if existing_pattern:
            # Update existing pattern with new attributes
            existing_attributes = existing_pattern.pattern_data.get("attributes", {})

            # Merge attributes, keeping both old and new
            merged_attributes = {**existing_attributes, **entity_attributes}
            existing_pattern.pattern_data["attributes"] = merged_attributes

            # Update confidence and usage
            existing_pattern.confidence = min(1.0, existing_pattern.confidence + 0.05)
            existing_pattern.usage_count += 1
            existing_pattern.updated_at = datetime.now(UTC)

            # Add this event to source events
            if event.event_id not in existing_pattern.source_events:
                existing_pattern.source_events.append(event.event_id)

            # Get the document key first
            cursor = self.patterns_collection.find(
                {"pattern_id": str(existing_pattern.pattern_id)},
            )
            if cursor.empty():
                self.logger.warning(
                    f"Pattern {existing_pattern.pattern_id} not found for update",
                )
                return

            # Get the first document
            doc = cursor.next()
            doc_key = doc["_key"]

            # Update in database with serialized data
            existing_pattern_doc = existing_pattern.serialize()

            # Use document key for update
            self.patterns_collection.update(doc_key, existing_pattern_doc)

            # Update cache
            self._patterns_cache[existing_pattern.pattern_id] = existing_pattern
        else:
            # Create new entity relationship pattern
            pattern = KnowledgePatternDataModel(
                pattern_type=KnowledgePatternType.entity_relationship,
                confidence=event.confidence,
                pattern_data={
                    "entity_name": entity_name,
                    "entity_type": entity_type,
                    "attributes": entity_attributes,
                    "relationships": event.content.get("relationships", []),
                },
                source_events=[event.event_id],
            )

            # Insert into database
            pattern_doc = pattern.serialize()
            self.patterns_collection.insert(pattern_doc)

            # Add to cache
            self._patterns_cache[pattern.pattern_id] = pattern

    def _process_schema_update(self, event: LearningEventDataModel) -> None:
        """
        Process schema update event.

        Args:
            event: The schema update event
        """
        # Extract schema information
        collection = event.content.get("collection", "")
        changes = event.content.get("changes", {})

        # Create or update schema pattern
        existing_pattern = None
        for pattern in self._patterns_cache.values():
            if (
                pattern.pattern_type == KnowledgePatternType.schema_update
                and pattern.pattern_data.get("collection") == collection
            ):
                existing_pattern = pattern
                break

        if existing_pattern:
            # Update existing schema pattern
            existing_changes = existing_pattern.pattern_data.get("changes", {})

            # Merge changes, with new ones taking precedence
            merged_changes = {**existing_changes, **changes}
            existing_pattern.pattern_data["changes"] = merged_changes

            # Enhanced: Track schema evolution over time
            evolution_history = existing_pattern.pattern_data.get(
                "evolution_history",
                [],
            )
            evolution_history.append(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "changes": changes,
                    "event_id": str(event.event_id),
                    "backwards_compatible": event.content.get(
                        "backwards_compatible",
                        True,
                    ),
                },
            )
            existing_pattern.pattern_data["evolution_history"] = evolution_history

            # Enhanced: Generate migration path if needed
            if not event.content.get(
                "backwards_compatible",
                True,
            ) and not existing_pattern.pattern_data.get("migration_path"):
                migration_path = self._generate_migration_path(collection, changes)
                existing_pattern.pattern_data["migration_path"] = migration_path

            # Update metadata
            existing_pattern.confidence = min(1.0, existing_pattern.confidence + 0.05)
            existing_pattern.usage_count += 1
            existing_pattern.updated_at = datetime.now(UTC)

            # Add this event to source events
            if event.event_id not in existing_pattern.source_events:
                existing_pattern.source_events.append(event.event_id)

            # Get the document key first
            cursor = self.patterns_collection.find(
                {"pattern_id": str(existing_pattern.pattern_id)},
            )
            if cursor.empty():
                self.logger.warning(
                    f"Pattern {existing_pattern.pattern_id} not found for update",
                )
                return

            # Get the first document
            doc = cursor.next()
            doc_key = doc["_key"]

            # Update in database with serialized data
            existing_pattern_doc = existing_pattern.serialize()

            # Use document key for update
            self.patterns_collection.update(doc_key, existing_pattern_doc)

            # Update cache
            self._patterns_cache[existing_pattern.pattern_id] = existing_pattern
        else:
            # Create new schema update pattern
            pattern = KnowledgePatternDataModel(
                pattern_type=KnowledgePatternType.schema_update,
                confidence=event.confidence,
                pattern_data={
                    "collection": collection,
                    "changes": changes,
                    "backwards_compatible": event.content.get(
                        "backwards_compatible",
                        True,
                    ),
                    "migration_path": event.content.get("migration_path", ""),
                    "evolution_history": [
                        {
                            "timestamp": datetime.now(UTC).isoformat(),
                            "changes": changes,
                            "event_id": str(event.event_id),
                            "backwards_compatible": event.content.get(
                                "backwards_compatible",
                                True,
                            ),
                        },
                    ],
                    "field_types": event.content.get("field_types", {}),
                    "field_usage_stats": event.content.get("field_usage_stats", {}),
                },
                source_events=[event.event_id],
            )

            # Insert into database
            pattern_doc = pattern.serialize()
            self.patterns_collection.insert(pattern_doc)

            # Add to cache
            self._patterns_cache[pattern.pattern_id] = pattern

    def _generate_migration_path(self, collection: str, changes: dict[str, Any]) -> str:
        """
        Generate a migration path for schema changes.

        Args:
            collection: The collection being changed
            changes: The schema changes

        Returns:
            A migration path for the changes
        """
        migration_path = f"// Migration path for {collection} schema changes\n"

        # Build AQL query for migration
        migration_path += "db._query(`\n"
        migration_path += f"FOR doc IN {collection}\n"
        migration_path += "  LET updated = doc\n"

        # Handle each type of change
        added_fields = changes.get("added_fields", {})
        removed_fields = changes.get("removed_fields", [])
        renamed_fields = changes.get("renamed_fields", {})

        # Handle added fields
        for field, default_value in added_fields.items():
            migration_path += f"  LET updated = MERGE(updated, {{ {field}: {json.dumps(default_value)} }})\n"

        # Handle renamed fields
        for old_field, new_field in renamed_fields.items():
            migration_path += (
                f"  LET updated = MERGE(UNSET(updated, '{old_field}'), {{ {new_field}: doc.{old_field} }})\n"
            )

        # Handle removed fields
        if removed_fields:
            fields_str = "', '".join(removed_fields)
            migration_path += f"  LET updated = UNSET(updated, '{fields_str}')\n"

        # Update document
        migration_path += "  UPDATE doc WITH updated IN " + collection + "\n"
        migration_path += "`);\n"

        return migration_path

    def _process_pattern_discovery(self, event: LearningEventDataModel) -> None:
        """
        Process pattern discovery event.

        Args:
            event: The pattern discovery event
        """
        # Extract pattern information
        pattern_type_str = event.content.get("pattern_type", "")
        pattern_data = event.content.get("pattern_data", {})

        # Convert to enum if possible
        try:
            pattern_type = KnowledgePatternType(pattern_type_str)
        except ValueError:
            # Unknown pattern type, log and return
            self.logger.warning(f"Unknown pattern type: {pattern_type_str}")
            return

        # Create new pattern directly
        pattern = KnowledgePatternDataModel(
            pattern_type=pattern_type,
            confidence=event.confidence,
            pattern_data=pattern_data,
            source_events=[event.event_id],
        )

        # Insert into database
        pattern_doc = pattern.serialize()
        self.patterns_collection.insert(pattern_doc)

        # Add to cache
        self._patterns_cache[pattern.pattern_id] = pattern

    def record_feedback(
        self,
        feedback_type: FeedbackType,
        feedback_strength: float,
        feedback_data: dict[str, Any],
        user_id: UUID | str | None = None,
        query_id: UUID | str | None = None,
        pattern_id: UUID | str | None = None,
    ) -> FeedbackRecordDataModel:
        """
        Record user feedback.

        Args:
            feedback_type: The type of feedback
            feedback_strength: How strong the feedback is (0-1)
            feedback_data: Detailed feedback information
            user_id: Associated user ID (optional)
            query_id: Associated query ID (optional)
            pattern_id: Pattern being evaluated (optional)

        Returns:
            The created feedback record
        """
        # Convert string IDs to UUID if needed
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        query_uuid = UUID(query_id) if isinstance(query_id, str) else query_id
        pattern_uuid = UUID(pattern_id) if isinstance(pattern_id, str) else pattern_id

        # Create feedback record
        feedback = FeedbackRecordDataModel(
            feedback_type=feedback_type,
            feedback_strength=feedback_strength,
            feedback_data=feedback_data,
            user_id=user_uuid,
            query_id=query_uuid,
            pattern_id=pattern_uuid,
        )

        # Insert into database
        feedback_doc = feedback.serialize()
        self.feedback_collection.insert(feedback_doc)

        # Add to cache
        self._feedback_cache[feedback.feedback_id] = feedback

        # Create a learning event from this feedback
        content = {
            "feedback_type": feedback_type,
            "strength": feedback_strength,
            "pattern_id": str(pattern_uuid) if pattern_uuid else None,
            "query_id": str(query_uuid) if query_uuid else None,
            "feedback_summary": feedback_data.get("comment", ""),
        }

        self.record_learning_event(
            event_type=LearningEventType.user_feedback,
            source="user_feedback",
            content=content,
            confidence=feedback_strength,
            metadata={
                "feedback_id": str(feedback.feedback_id),
                "user_id": str(user_uuid) if user_uuid else None,
            },
        )

        return feedback

    def get_knowledge_pattern(
        self,
        pattern_id: UUID,
    ) -> KnowledgePatternDataModel | None:
        """
        Get a knowledge pattern by ID.

        Args:
            pattern_id: The pattern ID

        Returns:
            The pattern or None if not found
        """
        return self._patterns_cache.get(pattern_id)

    def get_patterns_by_type(
        self,
        pattern_type: KnowledgePatternType,
        min_confidence: float = 0.0,
    ) -> list[KnowledgePatternDataModel]:
        """
        Get all patterns of a specific type.

        Args:
            pattern_type: The pattern type to filter by
            min_confidence: Minimum confidence threshold

        Returns:
            List of matching patterns
        """
        return [
            pattern
            for pattern in self._patterns_cache.values()
            if pattern.pattern_type == pattern_type and pattern.confidence >= min_confidence
        ]

    def find_matching_patterns(
        self,
        query_text: str,
        intent: str = "",
        min_confidence: float = 0.7,
    ) -> list[KnowledgePatternDataModel]:
        """
        Find patterns that match a query.

        Args:
            query_text: The query text to match
            intent: The query intent (optional)
            min_confidence: Minimum confidence threshold

        Returns:
            List of matching patterns
        """
        matching_patterns = []

        for pattern in self._patterns_cache.values():
            if pattern.pattern_type != KnowledgePatternType.query_pattern:
                continue

            if pattern.confidence < min_confidence:
                continue

            pattern_intent = pattern.pattern_data.get("intent", "")
            pattern_query = pattern.pattern_data.get("query_text", "")

            # Skip if intent doesn't match (when specified)
            if intent and pattern_intent != intent:
                continue

            # Calculate similarity between queries
            from utils.misc.string_similarity import jaro_winkler_similarity

            text_similarity = jaro_winkler_similarity(
                query_text.lower(),
                pattern_query.lower(),
            )

            # Add if similarity is high enough
            if text_similarity >= 0.7:
                matching_patterns.append(pattern)

        # Sort by confidence (highest first)
        matching_patterns.sort(key=lambda p: p.confidence, reverse=True)
        return matching_patterns

    def apply_knowledge_to_query(
        self,
        query_text: str,
        intent: str = "",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Apply knowledge patterns to enhance a query.

        Args:
            query_text: The original query text
            intent: The query intent (optional)
            context: Additional context for query enhancement (optional)

        Returns:
            Enhanced query information
        """
        context = context or {}

        # Find matching patterns
        matching_patterns = self.find_matching_patterns(query_text, intent)

        if not matching_patterns:
            # No matching patterns found
            return {
                "original_query": query_text,
                "enhanced_query": query_text,
                "applied_patterns": [],
                "enhancements_applied": False,
            }

        # Enhanced: Use contextual information to select the best pattern
        best_pattern = self._select_best_pattern_with_context(
            matching_patterns,
            context,
        )

        # Apply pattern enhancements
        enhancements = {
            "original_query": query_text,
            "enhanced_query": query_text,  # Will be replaced if enhanced
            "intent": best_pattern.pattern_data.get("intent", intent),
            "collections": best_pattern.pattern_data.get("collections", []),
            "query_template": best_pattern.pattern_data.get("query_template", ""),
            "applied_patterns": [str(best_pattern.pattern_id)],
            "enhancements_applied": True,
            "confidence": best_pattern.confidence,
        }

        # Enhanced: Apply the pattern's query template if available
        query_template = best_pattern.pattern_data.get("query_template", "")
        if query_template:
            # Extract entities from context or original query
            entities = context.get("entities", [])
            entity_names = [e.get("name", "") for e in entities if isinstance(e, dict)]

            # Apply template if possible
            if entities and query_template:
                try:
                    # For now, simple substitution
                    enhanced_query = query_template.replace("{entity}", entity_names[0])
                    enhancements["enhanced_query"] = enhanced_query
                except Exception as e:
                    self.logger.warning(f"Error applying query template: {e!s}")

        # Increment usage count for the pattern
        best_pattern.usage_count += 1
        best_pattern.updated_at = datetime.now(UTC)

        # Enhanced: Track pattern effectiveness
        success_history = best_pattern.pattern_data.get("success_history", [])
        success_history.append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "applied": True,
                "context": {
                    "time_of_day": datetime.now(UTC).hour,
                    "day_of_week": datetime.now(UTC).weekday(),
                },
            },
        )
        best_pattern.pattern_data["success_history"] = success_history

        # Get the document key first
        cursor = self.patterns_collection.find(
            {"pattern_id": str(best_pattern.pattern_id)},
        )
        if cursor.empty():
            self.logger.warning(
                f"Pattern {best_pattern.pattern_id} not found for update",
            )
            return enhancements

        # Get the first document
        doc = cursor.next()
        doc_key = doc["_key"]

        # Update in database with serialized data
        best_pattern_doc = best_pattern.serialize()

        # Use document key for update
        self.patterns_collection.update(doc_key, best_pattern_doc)

        # Update cache
        self._patterns_cache[best_pattern.pattern_id] = best_pattern

        return enhancements

    def _select_best_pattern_with_context(
        self,
        patterns: list[KnowledgePatternDataModel],
        context: dict[str, Any],
    ) -> KnowledgePatternDataModel:
        """
        Select the best pattern using contextual information.

        Args:
            patterns: List of patterns to choose from
            context: Query context information

        Returns:
            The best pattern for the given context
        """
        if not patterns:
            raise ValueError("No patterns provided")

        if len(patterns) == 1:
            return patterns[0]

        # Get contextual information
        current_hour = datetime.now(UTC).hour
        current_day = datetime.now(UTC).weekday()  # 0-6 (Mon-Sun)
        context.get("time_context", {})
        context.get("location_context", {})
        context.get("entities", [])

        # Score each pattern based on context
        pattern_scores = []

        for pattern in patterns:
            # Base score is the pattern confidence
            score = pattern.confidence

            # Enhanced scoring based on pattern history
            success_history = pattern.pattern_data.get("success_history", [])
            if success_history:
                # Calculate success rate
                recent_history = success_history[-min(len(success_history), 10) :]  # Last 10 uses
                success_results = [
                    h.get("result_count", 0) > 0 if isinstance(h, dict) else False for h in recent_history
                ]
                success_rate = sum(success_results) / len(success_results) if success_results else 0

                # Boost score based on success rate
                score += success_rate * 0.2

                # Check for time-of-day patterns
                time_matches = 0
                for history in recent_history:
                    if isinstance(history, dict) and "context" in history:
                        hist_hour = history["context"].get("time_of_day", -1)
                        hist_day = history["context"].get("day_of_week", -1)

                        # Check if current time is similar to successful times
                        if abs(hist_hour - current_hour) <= 3:  # Within 3 hours
                            time_matches += 1

                        if hist_day == current_day:  # Same day of week
                            time_matches += 1

                # Boost score based on time patterns
                if recent_history:
                    time_match_score = time_matches / (len(recent_history) * 2)  # Normalize
                    score += time_match_score * 0.1

            # Store the final score
            pattern_scores.append((pattern, score))

        # Sort by score (highest first)
        pattern_scores.sort(key=lambda x: x[1], reverse=True)

        # Return the highest scoring pattern
        return pattern_scores[0][0]

    def get_related_entities(
        self,
        entity_name: str,
        entity_type: str = "",
        min_confidence: float = 0.7,
    ) -> list[dict[str, Any]]:
        """
        Get entities related to a given entity.

        Args:
            entity_name: The entity name to find relationships for
            entity_type: The entity type (optional)
            min_confidence: Minimum confidence threshold

        Returns:
            List of related entities with relationship info
        """
        related_entities = []

        # Find entity relationship patterns for this entity
        for pattern in self._patterns_cache.values():
            if pattern.pattern_type != KnowledgePatternType.entity_relationship:
                continue

            if pattern.confidence < min_confidence:
                continue

            pattern_entity = pattern.pattern_data.get("entity_name", "")
            pattern_type = pattern.pattern_data.get("entity_type", "")

            # Skip if entity doesn't match
            if pattern_entity != entity_name:
                continue

            # Skip if type doesn't match (when specified)
            if entity_type and pattern_type != entity_type:
                continue

            # Add relationships
            relationships = pattern.pattern_data.get("relationships", [])
            for relationship in relationships:
                related_entities.append(
                    {
                        "entity_name": relationship.get("target_entity", ""),
                        "entity_type": relationship.get("target_type", ""),
                        "relationship_type": relationship.get("type", "related_to"),
                        "confidence": relationship.get(
                            "confidence",
                            pattern.confidence,
                        ),
                    },
                )

        # Sort by confidence (highest first)
        related_entities.sort(key=lambda e: e["confidence"], reverse=True)
        return related_entities

    def get_stats(self) -> dict:
        """Get statistics about the knowledge base."""
        # Count by pattern type
        pattern_type_counts = {t.value: 0 for t in KnowledgePatternType}
        for pattern in self._patterns_cache.values():
            pattern_type = pattern.pattern_type.value
            if pattern_type in pattern_type_counts:
                pattern_type_counts[pattern_type] += 1

        # Count by event type
        event_type_counts = {t.value: 0 for t in LearningEventType}
        for event in self._events_cache.values():
            event_type = event.event_type.value
            if event_type in event_type_counts:
                event_type_counts[event_type] += 1

        # Count by feedback type
        feedback_type_counts = {t.value: 0 for t in FeedbackType}
        for feedback in self._feedback_cache.values():
            feedback_type = feedback.feedback_type.value
            if feedback_type in feedback_type_counts:
                feedback_type_counts[feedback_type] += 1

        # Calculate pattern effectiveness
        pattern_effectiveness = {}
        for pattern in self._patterns_cache.values():
            success_history = pattern.pattern_data.get("success_history", [])
            if success_history:
                success_items = [h for h in success_history if isinstance(h, dict) and h.get("result_count", 0) > 0]
                success_rate = len(success_items) / len(success_history) if success_history else 0
                pattern_effectiveness[str(pattern.pattern_id)] = {
                    "pattern_type": pattern.pattern_type.value,
                    "success_rate": success_rate,
                    "usage_count": pattern.usage_count,
                    "confidence": pattern.confidence,
                }

        return {
            "event_count": len(self._events_cache),
            "pattern_count": len(self._patterns_cache),
            "feedback_count": len(self._feedback_cache),
            "pattern_types": pattern_type_counts,
            "event_types": event_type_counts,
            "feedback_types": feedback_type_counts,
            "effectiveness": pattern_effectiveness,
        }

    def detect_schema_changes(
        self,
        collection_name: str,
        data_sample: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Detect schema changes in a collection by comparing with known schema.

        Args:
            collection_name: The name of the collection
            data_sample: A sample document from the collection

        Returns:
            Schema change information
        """
        # Find existing schema pattern for this collection
        existing_schema = None
        for pattern in self._patterns_cache.values():
            if (
                pattern.pattern_type == KnowledgePatternType.schema_update
                and pattern.pattern_data.get("collection") == collection_name
            ):
                existing_schema = pattern
                break

        if not existing_schema:
            # No existing schema, record this as the initial schema
            self.record_learning_event(
                event_type=LearningEventType.schema_update,
                source="schema_detection",
                content={
                    "collection": collection_name,
                    "changes": {},
                    "backwards_compatible": True,
                    "field_types": self._extract_field_types(data_sample),
                    "schema_version": 1,
                },
                confidence=1.0,
            )

            return {
                "collection": collection_name,
                "change_detected": False,
                "message": "Initial schema recorded",
                "schema_version": 1,
            }

        # We have an existing schema, compare with the sample
        current_field_types = existing_schema.pattern_data.get("field_types", {})
        new_field_types = self._extract_field_types(data_sample)

        changes = {}

        # Check for new fields
        added_fields = {}
        for field, field_type in new_field_types.items():
            if field not in current_field_types:
                added_fields[field] = self._get_default_value_for_type(field_type)

        if added_fields:
            changes["added_fields"] = added_fields

        # Check for removed fields
        removed_fields = []
        for field in current_field_types:
            if field not in new_field_types:
                removed_fields.append(field)

        if removed_fields:
            changes["removed_fields"] = removed_fields

        # Check for type changes
        type_changes = {}
        for field, field_type in current_field_types.items():
            if field in new_field_types and new_field_types[field] != field_type:
                type_changes[field] = {
                    "old_type": field_type,
                    "new_type": new_field_types[field],
                }

        if type_changes:
            changes["type_changes"] = type_changes

        # Determine if changes are backwards compatible
        backwards_compatible = not removed_fields and not type_changes

        # If changes detected, record a schema update event
        if changes:
            # Get the current schema version
            current_version = existing_schema.pattern_data.get("schema_version", 1)
            new_version = current_version + 1

            self.record_learning_event(
                event_type=LearningEventType.schema_update,
                source="schema_detection",
                content={
                    "collection": collection_name,
                    "changes": changes,
                    "backwards_compatible": backwards_compatible,
                    "field_types": new_field_types,
                    "schema_version": new_version,
                },
                confidence=0.9 if backwards_compatible else 0.7,
            )

            return {
                "collection": collection_name,
                "change_detected": True,
                "changes": changes,
                "backwards_compatible": backwards_compatible,
                "schema_version": new_version,
            }

        return {
            "collection": collection_name,
            "change_detected": False,
            "message": "No schema changes detected",
            "schema_version": existing_schema.pattern_data.get("schema_version", 1),
        }

    def _extract_field_types(
        self,
        data: dict[str, Any],
        prefix: str = "",
        max_depth: int = 3,
    ) -> dict[str, str]:
        """
        Extract field types from a data sample.

        Args:
            data: The data sample
            prefix: Prefix for nested fields
            max_depth: Maximum depth for nested fields

        Returns:
            Dictionary of field names and types
        """
        field_types = {}

        if max_depth <= 0 or not isinstance(data, dict):
            return field_types

        for key, value in data.items():
            field_name = f"{prefix}.{key}" if prefix else key

            if value is None:
                field_types[field_name] = "null"
            elif isinstance(value, bool):
                field_types[field_name] = "boolean"
            elif isinstance(value, int):
                field_types[field_name] = "integer"
            elif isinstance(value, float):
                field_types[field_name] = "number"
            elif isinstance(value, str):
                field_types[field_name] = "string"
            elif isinstance(value, list):
                field_types[field_name] = "array"

                # Check first item if it's a non-empty array
                if value and max_depth > 1:
                    first_item = value[0]
                    if isinstance(first_item, dict):
                        # Extract types from the first item
                        nested_types = self._extract_field_types(
                            first_item,
                            f"{field_name}[0]",
                            max_depth - 1,
                        )
                        field_types.update(nested_types)
            elif isinstance(value, dict):
                field_types[field_name] = "object"

                # Extract nested fields
                nested_types = self._extract_field_types(
                    value,
                    field_name,
                    max_depth - 1,
                )
                field_types.update(nested_types)
            else:
                field_types[field_name] = type(value).__name__

        return field_types

    def _get_default_value_for_type(self, type_name: str) -> Any:
        """
        Get a default value for a data type.

        Args:
            type_name: The type name

        Returns:
            A default value for the type
        """
        defaults = {
            "null": None,
            "boolean": False,
            "integer": 0,
            "number": 0.0,
            "string": "",
            "array": [],
            "object": {},
        }

        return defaults.get(type_name)

    def track_query_refinement(
        self,
        query_text: str,
        refinements: list[dict[str, Any]],
        result_info: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Track query refinements to improve pattern learning.

        Args:
            query_text: The original query text
            refinements: List of refinements applied to the query
            result_info: Information about query results

        Returns:
            Information about the tracked refinements
        """
        if not refinements:
            return {"tracked": False, "message": "No refinements provided"}

        # Extract the final (most effective) refinement
        final_refinement = refinements[-1]

        # Check if this improved results
        original_result_count = result_info.get("original_count", 0)
        refined_result_count = result_info.get("count", 0)

        # Calculate improvement
        improved = refined_result_count > 0 and (
            original_result_count == 0 or result_info.get("quality", 0) > result_info.get("original_quality", 0)
        )

        # Adjust confidence based on improvement
        confidence = 0.8 if improved else 0.5

        # Record as a learning event
        learning_event = self.record_learning_event(
            event_type=LearningEventType.pattern_discovery,
            source="query_refinement",
            content={
                "query_text": query_text,
                "refinements": refinements,
                "final_refinement": final_refinement,
                "pattern_type": KnowledgePatternType.query_pattern,
                "pattern_data": {
                    "query_text": query_text,
                    "intent": result_info.get("intent", ""),
                    "refinement_type": final_refinement.get("type", ""),
                    "refinement_value": final_refinement.get("value", ""),
                    "success_rate": 1.0 if improved else 0.0,
                    "result_improvement": refined_result_count - original_result_count,
                },
            },
            confidence=confidence,
        )

        return {
            "tracked": True,
            "event_id": str(learning_event.event_id),
            "improved": improved,
            "confidence": confidence,
        }


def main() -> None:
    """Test the knowledge base functionality."""
    # Initialize the knowledge base manager
    kb_manager = KnowledgeBaseManager()

    # Record some test learning events
    query_event = kb_manager.record_learning_event(
        event_type=LearningEventType.query_success,
        source="test",
        content={
            "query": "Find documents about Indaleko",
            "intent": "document_search",
            "result_count": 5,
            "entities": ["Indaleko"],
            "collections": ["Objects"],
            "query_template": "FOR doc IN @@collection FILTER LIKE(doc.Label, @entity) RETURN doc",
        },
        confidence=0.9,
    )

    kb_manager.record_learning_event(
        event_type=LearningEventType.entity_discovery,
        source="test",
        content={
            "entity_name": "Indaleko",
            "entity_type": "project",
            "attributes": {
                "description": "Personal digital archivist project",
                "repository": "github.com/indaleko",
            },
            "relationships": [
                {
                    "target_entity": "Tony Mason",
                    "target_type": "person",
                    "type": "created_by",
                    "confidence": 0.95,
                },
            ],
        },
        confidence=0.95,
    )

    # Record some feedback
    kb_manager.record_feedback(
        feedback_type=FeedbackType.explicit_positive,
        feedback_strength=0.9,
        feedback_data={
            "comment": "Great results for this query!",
            "result_relevance": 0.95,
            "result_completeness": 0.85,
            "interaction": "clicked_result",
        },
        query_id=str(query_event.event_id),
    )

    # Test applying knowledge
    kb_manager.apply_knowledge_to_query(
        "Show me files related to Indaleko",
        intent="document_search",
    )


    # Get related entities
    kb_manager.get_related_entities("Indaleko", "project")

    # Get stats
    kb_manager.get_stats()


if __name__ == "__main__":
    main()
