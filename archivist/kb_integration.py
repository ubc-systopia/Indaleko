"""
Knowledge Base integration with Archivist.

This module connects the Knowledge Base Updating functionality with the
Archivist component of Indaleko.

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
import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import UUID, uuid4
from datetime import datetime, timezone

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db import IndalekoDBConfig
from query.memory.archivist_memory import ArchivistMemory
from entity_equivalence import EntityEquivalenceManager
from knowledge_base import (
    KnowledgeBaseManager,
    LearningEventType,
    KnowledgePatternType,
    FeedbackType
)
# pylint: enable=wrong-import-position


class ArchivistKnowledgeIntegration:
    """
    Integrates the Knowledge Base Updating feature with the Archivist memory system
    and Entity Equivalence components.
    
    This class serves as the main integration point for all knowledge-related
    features in the Archivist, allowing them to work together seamlessly.
    """
    
    def __init__(self, db_config: IndalekoDBConfig = IndalekoDBConfig()):
        """
        Initialize the integration component.
        
        Args:
            db_config: Database configuration
        """
        self.db_config = db_config
        self.logger = logging.getLogger(__name__)
        
        # Initialize the knowledge components
        self.kb_manager = KnowledgeBaseManager(db_config)
        self.archivist_memory = ArchivistMemory(db_config)
        self.entity_equivalence = EntityEquivalenceManager(db_config)
    
    def process_query(self, query_text: str, query_intent: str = "",
                    entities: List[Dict[str, Any]] = None,
                    result_info: Dict[str, Any] = None,
                    context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a query through the knowledge integration system.
        
        This method:
        1. Enhances the query using learned knowledge patterns
        2. Records the query in Archivist memory
        3. Extracts and manages entity references
        4. Returns the enhanced query with additional context
        
        Args:
            query_text: The original query text
            query_intent: The intent of the query (if known)
            entities: List of entities extracted from the query
            result_info: Information about query results (if available)
            context: Additional context for query processing (optional)
            
        Returns:
            Enhanced query with additional context
        """
        entities = entities or []
        result_info = result_info or {}
        context = context or {}
        
        # 1. Process entity references from the query
        entity_data = self._process_entities(entities)
        
        # Enhanced: Build rich context for knowledge application
        query_context = {
            "entities": entity_data,
            "time_context": {
                "time_of_day": datetime.now(timezone.utc).hour,
                "day_of_week": datetime.now(timezone.utc).weekday()
            }
        }
        
        # Enhanced: Add location context if available
        if "location" in context:
            query_context["location_context"] = context["location"]
            
        # Enhanced: Add device context if available
        if "device" in context:
            query_context["device_context"] = context["device"]
            
        # 2. Apply knowledge patterns to enhance the query with context
        enhanced_query = self.kb_manager.apply_knowledge_to_query(
            query_text, 
            query_intent,
            query_context
        )
        
        # 3. Record in Archivist memory with enhanced metadata
        memory_metadata = {
            "query": query_text,
            "intent": query_intent,
            "entities": entities,
            "enhanced_query": enhanced_query.get("enhanced_query", query_text),
            "applied_patterns": enhanced_query.get("applied_patterns", [])
        }
        
        # Enhanced: Add context to memory
        if context:
            memory_metadata["context"] = context
            
        memory_entry = self.archivist_memory.add_memory(
            memory_type="query",
            content=memory_metadata
        )
        
        # 4. If results are available, record as a learning event with enhanced data
        if result_info:
            # Enhanced: Add first result for schema learning if available
            if "results" in result_info and result_info["results"] and len(result_info["results"]) > 0:
                result_info["first_result"] = result_info["results"][0]
                
            # Enhanced: Add context information to result info
            if context:
                result_info["context"] = context
                
            self._record_query_results(query_text, query_intent, entities, result_info, 
                                      enhanced_query.get("applied_patterns", []))
        
        # 5. Combine everything into a response
        response = {
            "original_query": query_text,
            "enhanced_query": enhanced_query.get("enhanced_query", query_text),
            "intent": enhanced_query.get("intent", query_intent),
            "collections": enhanced_query.get("collections", []),
            "query_template": enhanced_query.get("query_template", ""),
            "entities": entity_data,
            "context": {
                "memory_id": str(memory_entry.memory_id),
                "patterns_applied": enhanced_query.get("applied_patterns", []),
                "confidence": enhanced_query.get("confidence", 0.0)
            }
        }
        
        return response
    
    def _process_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process entities from a query through the entity equivalence system.
        
        Args:
            entities: List of entities extracted from the query
            
        Returns:
            Processed entity data with canonical references
        """
        processed_entities = []
        
        for entity in entities:
            entity_name = entity.get("name", "")
            entity_type_str = entity.get("type", "")
            
            # Convert entity type string to IndalekoNamedEntityType if possible
            from data_models.named_entity import IndalekoNamedEntityType
            try:
                entity_type = IndalekoNamedEntityType(entity_type_str)
            except ValueError:
                # Default to topic if type is unknown
                entity_type = IndalekoNamedEntityType.topic
            
            # Add to entity equivalence system
            entity_node = self.entity_equivalence.add_entity_reference(
                name=entity_name,
                entity_type=entity_type,
                source="query",
                context=f"Extracted from query: '{entity.get('original_text', entity_name)}'"
            )
            
            # Get canonical reference
            canonical = self.entity_equivalence.get_canonical_reference(entity_node.entity_id)
            
            # Get all equivalent references
            all_references = self.entity_equivalence.get_all_references(entity_node.entity_id)
            reference_names = [ref.name for ref in all_references]
            
            # Record as entity discovery event
            self.kb_manager.record_learning_event(
                event_type=LearningEventType.entity_discovery,
                source="query_entity",
                content={
                    "entity_name": entity_name,
                    "entity_type": entity_type.value,
                    "canonical_name": canonical.name if canonical else entity_name,
                    "attributes": entity.get("attributes", {}),
                    "context": entity.get("context", "")
                },
                confidence=0.8
            )
            
            # Add to processed entities
            processed_entities.append({
                "name": entity_name,
                "type": entity_type.value,
                "id": str(entity_node.entity_id),
                "canonical_name": canonical.name if canonical else entity_name,
                "canonical_id": str(canonical.entity_id) if canonical else str(entity_node.entity_id),
                "all_references": reference_names
            })
        
        return processed_entities
    
    def _record_query_results(self, query_text: str, query_intent: str,
                            entities: List[Dict[str, Any]], 
                            result_info: Dict[str, Any],
                            applied_patterns: List[str]) -> None:
        """
        Record query results as a learning event.
        
        Args:
            query_text: The original query text
            query_intent: The intent of the query
            entities: List of entities extracted from the query
            result_info: Information about query results
            applied_patterns: List of pattern IDs that were applied
        """
        # Extract result information
        result_count = result_info.get("count", 0)
        result_quality = result_info.get("quality", 0.0)
        execution_time = result_info.get("execution_time", 0.0)
        
        # Determine confidence based on result quality and count
        confidence = 0.5
        if result_count > 0:
            # More results and better quality increase confidence
            confidence = min(0.9, 0.6 + (0.1 * min(result_count / 10, 1.0)) + (0.2 * result_quality))
        
        # Enhanced: Include additional context and metadata
        content = {
            "query": query_text,
            "intent": query_intent,
            "entities": [e.get("name") for e in entities],
            "result_count": result_count,
            "execution_time": execution_time,
            "collections": result_info.get("collections", []),
            "applied_patterns": applied_patterns,
            "query_template": result_info.get("query_template", ""),
            "result_quality": result_quality
        }
        
        # Enhanced: Include schema learning data if available
        if "first_result" in result_info:
            content["first_result"] = result_info["first_result"]
            
        # Enhanced: Include context information
        if "context" in result_info:
            content["context"] = result_info["context"]
            
        # Enhanced: Include refinement information if available
        if "refinements" in result_info:
            content["refinements"] = result_info["refinements"]
            content["original_count"] = result_info.get("original_count", 0)
            content["original_quality"] = result_info.get("original_quality", 0.0)
            
        # Enhanced: Include more detailed result metrics if available
        if "metrics" in result_info:
            content["metrics"] = result_info["metrics"]
            
        # Record as learning event
        event = self.kb_manager.record_learning_event(
            event_type=LearningEventType.query_success if result_count > 0 else LearningEventType.pattern_discovery,
            source="query_execution",
            content=content,
            confidence=confidence
        )
        
        # Enhanced: Process query refinements if available
        if "refinements" in result_info and result_info["refinements"]:
            refinement_result = self.kb_manager.track_query_refinement(
                query_text=query_text,
                refinements=result_info["refinements"],
                result_info=result_info
            )
            
            # Add refinement tracking to Archivist memory for future reference
            if refinement_result.get("tracked", False):
                self.archivist_memory.add_memory(
                    memory_type="refinement",
                    content={
                        "query": query_text,
                        "refinements": result_info["refinements"],
                        "refinement_result": refinement_result,
                        "query_event_id": str(event.event_id)
                    }
                )
                
        # Enhanced: Check for database schema changes if applicable
        collections = result_info.get("collections", [])
        if collections and "first_result" in result_info and result_info["first_result"]:
            try:
                # Only check the first collection for schema changes
                schema_result = self.kb_manager.detect_schema_changes(
                    collection_name=collections[0],
                    data_sample=result_info["first_result"]
                )
                
                # If schema changes detected, record in memory
                if schema_result.get("change_detected", False):
                    self.archivist_memory.add_memory(
                        memory_type="schema_change",
                        content={
                            "collection": collections[0],
                            "schema_changes": schema_result.get("changes", {}),
                            "schema_version": schema_result.get("schema_version", 1),
                            "backwards_compatible": schema_result.get("backwards_compatible", True),
                            "query_event_id": str(event.event_id)
                        }
                    )
            except Exception as e:
                self.logger.warning(f"Error checking for schema changes: {str(e)}")
    
    def add_user_feedback(self, feedback_type: str, query_text: str,
                        feedback_data: Dict[str, Any],
                        strength: float = 0.8,
                        pattern_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Add user feedback about query results.
        
        Args:
            feedback_type: Type of feedback ("positive", "negative", etc.)
            query_text: The query that the feedback relates to
            feedback_data: Detailed feedback information
            strength: How strong the feedback is (0-1)
            pattern_id: ID of the pattern that was applied (if known)
            
        Returns:
            Information about the recorded feedback
        """
        # Convert feedback type string to FeedbackType
        feedback_enum = None
        if feedback_type.lower() in ("positive", "explicit_positive"):
            feedback_enum = FeedbackType.explicit_positive
        elif feedback_type.lower() in ("negative", "explicit_negative"):
            feedback_enum = FeedbackType.explicit_negative
        elif feedback_type.lower() in ("implicit_positive"):
            feedback_enum = FeedbackType.implicit_positive
        elif feedback_type.lower() in ("implicit_negative"):
            feedback_enum = FeedbackType.implicit_negative
        else:
            # Default to explicit_positive if unrecognized
            feedback_enum = FeedbackType.explicit_positive
        
        # Record feedback
        feedback = self.kb_manager.record_feedback(
            feedback_type=feedback_enum,
            feedback_strength=strength,
            feedback_data=feedback_data,
            pattern_id=pattern_id
        )
        
        # Record in Archivist memory
        memory_entry = self.archivist_memory.add_memory(
            memory_type="feedback",
            content={
                "query": query_text,
                "feedback_type": feedback_enum.value,
                "feedback_strength": strength,
                "feedback_data": feedback_data,
                "pattern_id": pattern_id
            }
        )
        
        return {
            "feedback_id": str(feedback.feedback_id),
            "memory_id": str(memory_entry.memory_id),
            "timestamp": feedback.timestamp.isoformat(),
            "type": feedback_enum.value,
            "strength": strength
        }
    
    def get_knowledge_insights(self) -> Dict[str, Any]:
        """
        Get insights from the knowledge base.
        
        Returns:
            Insights about patterns, entities, and feedback
        """
        # Get stats from each component
        kb_stats = self.kb_manager.get_stats()
        memory_stats = self.archivist_memory.get_stats()
        entity_stats = self.entity_equivalence.get_stats()
        
        # Get top patterns by confidence
        query_patterns = self.kb_manager.get_patterns_by_type(
            KnowledgePatternType.query_pattern,
            min_confidence=0.8
        )
        
        top_patterns = []
        for pattern in sorted(query_patterns, key=lambda p: p.confidence, reverse=True)[:5]:
            top_patterns.append({
                "id": str(pattern.pattern_id),
                "confidence": pattern.confidence,
                "usage_count": pattern.usage_count,
                "type": pattern.pattern_type.value,
                "intent": pattern.pattern_data.get("intent", "unknown"),
                "query_text": pattern.pattern_data.get("query_text", "")
            })
        
        # Get common entities
        entity_groups = self.entity_equivalence.list_entity_groups()
        top_entities = []
        for group in entity_groups[:5]:
            top_entities.append({
                "id": group.get("group_id", ""),
                "canonical_name": group.get("canonical", {}).get("name", ""),
                "type": group.get("entity_type", ""),
                "member_count": group.get("member_count", 0)
            })
        
        return {
            "stats": {
                "knowledge_base": kb_stats,
                "memory": memory_stats,
                "entity": entity_stats
            },
            "top_patterns": top_patterns,
            "top_entities": top_entities,
            "system_health": {
                "knowledge_confidence": sum(p.confidence for p in query_patterns) / max(len(query_patterns), 1),
                "pattern_count": kb_stats.get("pattern_count", 0),
                "entity_group_count": entity_stats.get("group_count", 0),
                "memory_count": memory_stats.get("memory_count", 0)
            }
        }


def test_kb_integration():
    """Test the knowledge base integration."""
    # Initialize the integration
    kb_integration = ArchivistKnowledgeIntegration()
    
    # Test processing a query
    query_response = kb_integration.process_query(
        query_text="Find documents about knowledge base systems",
        query_intent="document_search",
        entities=[
            {
                "name": "knowledge base systems",
                "type": "topic",
                "original_text": "knowledge base systems"
            }
        ]
    )
    
    print("\n--- Query Processing Response ---")
    print(json.dumps(query_response, indent=2, default=str))
    
    # Test processing results
    result_response = kb_integration.process_query(
        query_text="Find documents about entity resolution",
        query_intent="document_search",
        entities=[
            {
                "name": "entity resolution",
                "type": "topic",
                "original_text": "entity resolution"
            }
        ],
        result_info={
            "count": 5,
            "quality": 0.85,
            "execution_time": 0.15,
            "collections": ["Objects"]
        }
    )
    
    print("\n--- Query with Results Response ---")
    print(json.dumps(result_response, indent=2, default=str))
    
    # Test feedback
    feedback_response = kb_integration.add_user_feedback(
        feedback_type="positive",
        query_text="Find documents about entity resolution",
        feedback_data={
            "comment": "Excellent results!",
            "result_relevance": 0.9,
            "result_completeness": 0.85
        },
        strength=0.9
    )
    
    print("\n--- Feedback Response ---")
    print(json.dumps(feedback_response, indent=2, default=str))
    
    # Test insights
    insights = kb_integration.get_knowledge_insights()
    
    print("\n--- Knowledge Insights ---")
    print(json.dumps(insights, indent=2, default=str))
    
    return {
        "query_response": query_response,
        "result_response": result_response,
        "feedback_response": feedback_response,
        "insights": insights
    }


def main():
    """Main function for testing knowledge base integration."""
    test_kb_integration()


if __name__ == "__main__":
    main()