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

import os
import sys
import json
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import UUID, uuid4
from datetime import datetime, timezone
import logging

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections
from db.i_collections import IndalekoCollections
from data_models.base import IndalekoBaseModel

from archivist.knowledge_base.data_models import (
    LearningEventDataModel,
    LearningEventType,
    KnowledgePatternDataModel,
    KnowledgePatternType,
    FeedbackRecordDataModel,
    FeedbackType
)
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
    
    def __init__(self, db_config: IndalekoDBConfig = IndalekoDBConfig()):
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
        self._events_cache: Dict[UUID, LearningEventDataModel] = {}
        self._patterns_cache: Dict[UUID, KnowledgePatternDataModel] = {}
        self._feedback_cache: Dict[UUID, FeedbackRecordDataModel] = {}
        
        # Load existing data
        self._load_data()
    
    def _setup_collections(self):
        """Set up the necessary collections in the database."""
        # Get collections from central registry using get_collection
        try:
            # Try to get the collections using the existing method
            self.events_collection = IndalekoCollections.get_collection(
                Indaleko_Learning_Event_Collection
            ).collection
            
            self.patterns_collection = IndalekoCollections.get_collection(
                Indaleko_Knowledge_Pattern_Collection
            ).collection
            
            self.feedback_collection = IndalekoCollections.get_collection(
                Indaleko_Feedback_Record_Collection
            ).collection
            
            self.logger.info(f"Successfully retrieved all Knowledge Base collections")
        except Exception as e:
            # If collections don't exist, log error and raise
            self.logger.error(f"Error setting up Knowledge Base collections: {str(e)}")
            self.logger.error("Please add Knowledge Base collections to db_collections.py first")
            raise ValueError("Knowledge Base collections are not defined in the database. " +
                            "Please add them to db_collections.py first.") from e
    
    def _load_data(self):
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
                
            self.logger.info(f"Loaded {len(self._events_cache)} events, "
                            f"{len(self._patterns_cache)} patterns, and "
                            f"{len(self._feedback_cache)} feedback records")
        except Exception as e:
            self.logger.error(f"Error loading data: {str(e)}")
            # Initialize empty caches if loading fails
            self._events_cache = {}
            self._patterns_cache = {}
            self._feedback_cache = {}
    
    def record_learning_event(self,
                             event_type: LearningEventType,
                             source: str,
                             content: Dict[str, Any],
                             confidence: float = 0.8,
                             metadata: Optional[Dict[str, Any]] = None) -> LearningEventDataModel:
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
            metadata=metadata or {}
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
        
        # Check if this matches an existing pattern
        matching_pattern = self._find_matching_query_pattern(query_text, query_intent)
        
        if matching_pattern:
            # Update existing pattern
            matching_pattern.usage_count += 1
            matching_pattern.updated_at = datetime.now(timezone.utc)
            
            # Update confidence based on result success
            # Increase confidence if results were found, decrease if none
            if result_count > 0:
                matching_pattern.confidence = min(1.0, matching_pattern.confidence + 0.05)
            else:
                matching_pattern.confidence = max(0.0, matching_pattern.confidence - 0.1)
            
            # Add this event to source events
            if event.event_id not in matching_pattern.source_events:
                matching_pattern.source_events.append(event.event_id)
            
            # Get the document key first
            cursor = self.patterns_collection.find({"pattern_id": str(matching_pattern.pattern_id)})
            if cursor.empty():
                self.logger.warning(f"Pattern {matching_pattern.pattern_id} not found for update")
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
        else:
            # Create new pattern if confidence is high enough
            if event.confidence >= 0.7 and result_count > 0:
                pattern = KnowledgePatternDataModel(
                    pattern_type=KnowledgePatternType.query_pattern,
                    confidence=event.confidence,
                    pattern_data={
                        "query_text": query_text,
                        "intent": query_intent,
                        "entities": entities,
                        "result_count": result_count,
                        "collections": event.content.get("collections", []),
                        "query_template": event.content.get("query_template", "")
                    },
                    source_events=[event.event_id]
                )
                
                # Insert into database
                pattern_doc = pattern.serialize()
                self.patterns_collection.insert(pattern_doc)
                
                # Add to cache
                self._patterns_cache[pattern.pattern_id] = pattern
    
    def _find_matching_query_pattern(self, query_text: str, intent: str) -> Optional[KnowledgePatternDataModel]:
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
            text_similarity = jaro_winkler_similarity(query_text.lower(), pattern_query.lower())
            
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
                cursor = self.patterns_collection.find({"pattern_id": str(pattern.pattern_id)})
                if cursor.empty():
                    self.logger.warning(f"Pattern {pattern.pattern_id} not found for update")
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
            if (pattern.pattern_type == KnowledgePatternType.entity_relationship and
                pattern.pattern_data.get("entity_name") == entity_name and
                pattern.pattern_data.get("entity_type") == entity_type):
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
            existing_pattern.updated_at = datetime.now(timezone.utc)
            
            # Add this event to source events
            if event.event_id not in existing_pattern.source_events:
                existing_pattern.source_events.append(event.event_id)
            
            # Get the document key first
            cursor = self.patterns_collection.find({"pattern_id": str(existing_pattern.pattern_id)})
            if cursor.empty():
                self.logger.warning(f"Pattern {existing_pattern.pattern_id} not found for update")
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
                    "relationships": event.content.get("relationships", [])
                },
                source_events=[event.event_id]
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
            if (pattern.pattern_type == KnowledgePatternType.schema_update and
                pattern.pattern_data.get("collection") == collection):
                existing_pattern = pattern
                break
        
        if existing_pattern:
            # Update existing schema pattern
            existing_changes = existing_pattern.pattern_data.get("changes", {})
            
            # Merge changes, with new ones taking precedence
            merged_changes = {**existing_changes, **changes}
            existing_pattern.pattern_data["changes"] = merged_changes
            
            # Update metadata
            existing_pattern.confidence = min(1.0, existing_pattern.confidence + 0.05)
            existing_pattern.usage_count += 1
            existing_pattern.updated_at = datetime.now(timezone.utc)
            
            # Add this event to source events
            if event.event_id not in existing_pattern.source_events:
                existing_pattern.source_events.append(event.event_id)
            
            # Get the document key first
            cursor = self.patterns_collection.find({"pattern_id": str(existing_pattern.pattern_id)})
            if cursor.empty():
                self.logger.warning(f"Pattern {existing_pattern.pattern_id} not found for update")
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
                    "backwards_compatible": event.content.get("backwards_compatible", True),
                    "migration_path": event.content.get("migration_path", "")
                },
                source_events=[event.event_id]
            )
            
            # Insert into database
            pattern_doc = pattern.serialize()
            self.patterns_collection.insert(pattern_doc)
            
            # Add to cache
            self._patterns_cache[pattern.pattern_id] = pattern
    
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
            source_events=[event.event_id]
        )
        
        # Insert into database
        pattern_doc = pattern.serialize()
        self.patterns_collection.insert(pattern_doc)
        
        # Add to cache
        self._patterns_cache[pattern.pattern_id] = pattern
    
    def record_feedback(self,
                      feedback_type: FeedbackType,
                      feedback_strength: float,
                      feedback_data: Dict[str, Any],
                      user_id: Optional[Union[UUID, str]] = None,
                      query_id: Optional[Union[UUID, str]] = None,
                      pattern_id: Optional[Union[UUID, str]] = None) -> FeedbackRecordDataModel:
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
            pattern_id=pattern_uuid
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
            "feedback_summary": feedback_data.get("comment", "")
        }
        
        self.record_learning_event(
            event_type=LearningEventType.user_feedback,
            source="user_feedback",
            content=content,
            confidence=feedback_strength,
            metadata={
                "feedback_id": str(feedback.feedback_id),
                "user_id": str(user_uuid) if user_uuid else None
            }
        )
        
        return feedback
    
    def get_knowledge_pattern(self, pattern_id: UUID) -> Optional[KnowledgePatternDataModel]:
        """
        Get a knowledge pattern by ID.
        
        Args:
            pattern_id: The pattern ID
            
        Returns:
            The pattern or None if not found
        """
        return self._patterns_cache.get(pattern_id)
    
    def get_patterns_by_type(self, pattern_type: KnowledgePatternType, 
                            min_confidence: float = 0.0) -> List[KnowledgePatternDataModel]:
        """
        Get all patterns of a specific type.
        
        Args:
            pattern_type: The pattern type to filter by
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of matching patterns
        """
        return [
            pattern for pattern in self._patterns_cache.values()
            if pattern.pattern_type == pattern_type and pattern.confidence >= min_confidence
        ]
    
    def find_matching_patterns(self, query_text: str, intent: str = "",
                             min_confidence: float = 0.7) -> List[KnowledgePatternDataModel]:
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
            text_similarity = jaro_winkler_similarity(query_text.lower(), pattern_query.lower())
            
            # Add if similarity is high enough
            if text_similarity >= 0.7:
                matching_patterns.append(pattern)
        
        # Sort by confidence (highest first)
        matching_patterns.sort(key=lambda p: p.confidence, reverse=True)
        return matching_patterns
    
    def apply_knowledge_to_query(self, query_text: str, intent: str = "") -> Dict[str, Any]:
        """
        Apply knowledge patterns to enhance a query.
        
        Args:
            query_text: The original query text
            intent: The query intent (optional)
            
        Returns:
            Enhanced query information
        """
        # Find matching patterns
        matching_patterns = self.find_matching_patterns(query_text, intent)
        
        if not matching_patterns:
            # No matching patterns found
            return {
                "original_query": query_text,
                "enhanced_query": query_text,
                "applied_patterns": [],
                "enhancements_applied": False
            }
        
        # Use the best (highest confidence) pattern
        best_pattern = matching_patterns[0]
        
        # Apply pattern enhancements
        enhancements = {
            "original_query": query_text,
            "enhanced_query": query_text,  # Will be replaced if enhanced
            "intent": best_pattern.pattern_data.get("intent", intent),
            "collections": best_pattern.pattern_data.get("collections", []),
            "query_template": best_pattern.pattern_data.get("query_template", ""),
            "applied_patterns": [str(best_pattern.pattern_id)],
            "enhancements_applied": True,
            "confidence": best_pattern.confidence
        }
        
        # Increment usage count for the pattern
        best_pattern.usage_count += 1
        
        # Get the document key first
        cursor = self.patterns_collection.find({"pattern_id": str(best_pattern.pattern_id)})
        if cursor.empty():
            self.logger.warning(f"Pattern {best_pattern.pattern_id} not found for update")
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
    
    def get_related_entities(self, entity_name: str, entity_type: str = "",
                           min_confidence: float = 0.7) -> List[Dict[str, Any]]:
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
                related_entities.append({
                    "entity_name": relationship.get("target_entity", ""),
                    "entity_type": relationship.get("target_type", ""),
                    "relationship_type": relationship.get("type", "related_to"),
                    "confidence": relationship.get("confidence", pattern.confidence)
                })
        
        # Sort by confidence (highest first)
        related_entities.sort(key=lambda e: e["confidence"], reverse=True)
        return related_entities
    
    def get_stats(self) -> Dict:
        """Get statistics about the knowledge base."""
        return {
            "event_count": len(self._events_cache),
            "pattern_count": len(self._patterns_cache),
            "feedback_count": len(self._feedback_cache),
            "pattern_types": {t.value: 0 for t in KnowledgePatternType},
            "event_types": {t.value: 0 for t in LearningEventType},
            "feedback_types": {t.value: 0 for t in FeedbackType}
        }


def main():
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
            "query_template": "FOR doc IN @@collection FILTER LIKE(doc.Label, @entity) RETURN doc"
        },
        confidence=0.9
    )
    
    entity_event = kb_manager.record_learning_event(
        event_type=LearningEventType.entity_discovery,
        source="test",
        content={
            "entity_name": "Indaleko",
            "entity_type": "project",
            "attributes": {
                "description": "Personal digital archivist project",
                "repository": "github.com/indaleko"
            },
            "relationships": [
                {
                    "target_entity": "Tony Mason",
                    "target_type": "person",
                    "type": "created_by",
                    "confidence": 0.95
                }
            ]
        },
        confidence=0.95
    )
    
    # Record some feedback
    feedback = kb_manager.record_feedback(
        feedback_type=FeedbackType.explicit_positive,
        feedback_strength=0.9,
        feedback_data={
            "comment": "Great results for this query!",
            "result_relevance": 0.95,
            "result_completeness": 0.85,
            "interaction": "clicked_result"
        },
        query_id=str(query_event.event_id)
    )
    
    # Test applying knowledge
    enhanced_query = kb_manager.apply_knowledge_to_query(
        "Show me files related to Indaleko",
        intent="document_search"
    )
    
    print(f"Enhanced Query: {enhanced_query}")
    
    # Get related entities
    related = kb_manager.get_related_entities("Indaleko", "project")
    print(f"Related entities: {related}")
    
    # Get stats
    stats = kb_manager.get_stats()
    print(f"Knowledge Base Stats: {stats}")


if __name__ == "__main__":
    main()