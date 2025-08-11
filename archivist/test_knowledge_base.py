"""
Test file for the knowledge base updating feature.

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
import os
import sys
import uuid

from datetime import UTC, datetime


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position, import-error
from knowledge_base import (
    FeedbackType,
    KnowledgeBaseManager,
    KnowledgePatternType,
    LearningEventType,
)


# pylint: enable=wrong-import-position, import-error


def test_create_and_retrieve_events(kb_manager):
    """Test creating and retrieving learning events."""

    # Skip tests if kb_manager is None (collections not available)
    if kb_manager is None:
        return None, None

    # Create a test event
    event = kb_manager.record_learning_event(
        event_type=LearningEventType.query_success,
        source="test_script",
        content={
            "query": "Find documents related to knowledge base",
            "intent": "document_search",
            "result_count": 3,
            "entities": ["knowledge base"],
            "collections": ["Objects"],
            "query_template": "FOR doc IN @@collection FILTER LIKE(doc.Label, @entity) RETURN doc",
        },
        confidence=0.85,
        metadata={
            "test_run": True,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


    # Create a pattern discovery event
    pattern_event = kb_manager.record_learning_event(
        event_type=LearningEventType.pattern_discovery,
        source="test_script",
        content={
            "pattern_type": KnowledgePatternType.query_pattern,
            "pattern_data": {
                "intent": "document_search",
                "entity_types": ["topic"],
                "collection": "Objects",
                "query_template": "FOR doc IN @@collection FILTER LIKE(doc.Label, @entity) RETURN doc",
                "success_rate": 0.9,
            },
        },
        confidence=0.8,
    )


    return event, pattern_event


def test_create_and_retrieve_patterns(kb_manager, event_id):
    """Test creating and retrieving knowledge patterns."""

    # Skip tests if kb_manager is None (collections not available)
    if kb_manager is None:
        return None, None

    # Get patterns of type query_pattern
    query_patterns = kb_manager.get_patterns_by_type(
        KnowledgePatternType.query_pattern,
        min_confidence=0.7,
    )


    # Test that a pattern was created from our learning event
    if query_patterns:
        pass

    # Create an entity relationship pattern directly through an event
    kb_manager.record_learning_event(
        event_type=LearningEventType.entity_discovery,
        source="test_script",
        content={
            "entity_name": "Knowledge Base",
            "entity_type": "concept",
            "attributes": {
                "description": "A structured collection of information",
                "domain": "information science",
            },
            "relationships": [
                {
                    "target_entity": "Database",
                    "target_type": "concept",
                    "type": "related_to",
                    "confidence": 0.9,
                },
                {
                    "target_entity": "Information Retrieval",
                    "target_type": "field",
                    "type": "belongs_to",
                    "confidence": 0.85,
                },
            ],
        },
        confidence=0.9,
    )


    # Get patterns of type entity_relationship
    entity_patterns = kb_manager.get_patterns_by_type(
        KnowledgePatternType.entity_relationship,
        min_confidence=0.7,
    )


    return query_patterns, entity_patterns


def test_feedback_integration(kb_manager, pattern_id):
    """Test feedback integration with the knowledge base."""

    # Skip tests if kb_manager is None (collections not available)
    if kb_manager is None:
        return None, None

    # Record positive feedback
    positive_feedback = kb_manager.record_feedback(
        feedback_type=FeedbackType.explicit_positive,
        feedback_strength=0.9,
        feedback_data={
            "comment": "These results were very helpful",
            "result_relevance": 0.95,
            "result_completeness": 0.85,
            "interaction": "used_results",
        },
        pattern_id=pattern_id,
    )


    # Record negative feedback for another pattern
    negative_feedback = kb_manager.record_feedback(
        feedback_type=FeedbackType.explicit_negative,
        feedback_strength=0.7,
        feedback_data={
            "comment": "These results were not what I expected",
            "result_relevance": 0.3,
            "result_completeness": 0.5,
            "interaction": "abandoned_results",
        },
    )


    # Check if feedback affected pattern confidence
    if pattern_id:
        pattern = kb_manager.get_knowledge_pattern(uuid.UUID(pattern_id))
        if pattern:
            pass

    return positive_feedback, negative_feedback


def test_query_enhancement(kb_manager):
    """Test query enhancement using knowledge patterns."""

    # Skip tests if kb_manager is None (collections not available)
    if kb_manager is None:
        return None, None

    # Test query that should match existing patterns
    enhanced_query1 = kb_manager.apply_knowledge_to_query(
        "Find documents about knowledge bases",
        intent="document_search",
    )


    # Test query that shouldn't match existing patterns
    enhanced_query2 = kb_manager.apply_knowledge_to_query(
        "What is the capital of France?",
        intent="factoid_question",
    )


    return enhanced_query1, enhanced_query2


def test_entity_relationships(kb_manager):
    """Test entity relationship functionality."""

    # Skip tests if kb_manager is None (collections not available)
    if kb_manager is None:
        return None

    # Get related entities for "Knowledge Base"
    related_entities = kb_manager.get_related_entities(
        "Knowledge Base",
        entity_type="concept",
    )

    for _entity in related_entities:
        pass

    return related_entities


def test_stats(kb_manager):
    """Test stats functionality."""

    # Skip tests if kb_manager is None (collections not available)
    if kb_manager is None:
        return None

    return kb_manager.get_stats()




def run_all_tests():
    """Run all knowledge base tests."""

    # Try to initialize the KnowledgeBaseManager, but handle the case where collections don't exist
    try:
        kb_manager = KnowledgeBaseManager()
    except ValueError:
        kb_manager = None

    # Run tests
    event, pattern_event = test_create_and_retrieve_events(kb_manager)

    query_patterns, entity_patterns = test_create_and_retrieve_patterns(
        kb_manager,
        event.event_id,
    )

    # Use the first pattern ID for feedback tests if available
    pattern_id = None
    if query_patterns:
        pattern_id = str(query_patterns[0].pattern_id)

    positive_feedback, negative_feedback = test_feedback_integration(
        kb_manager,
        pattern_id,
    )

    enhanced_query1, enhanced_query2 = test_query_enhancement(kb_manager)

    test_entity_relationships(kb_manager)

    test_stats(kb_manager)

    return True


def main():
    """Main function for testing knowledge base functionality."""
    parser = argparse.ArgumentParser(description="Test Knowledge Base Updating Feature")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--events", action="store_true", help="Test learning events")
    parser.add_argument(
        "--patterns",
        action="store_true",
        help="Test knowledge patterns",
    )
    parser.add_argument(
        "--feedback",
        action="store_true",
        help="Test feedback integration",
    )
    parser.add_argument("--queries", action="store_true", help="Test query enhancement")
    parser.add_argument(
        "--entities",
        action="store_true",
        help="Test entity relationships",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Test knowledge base stats",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear test data (not implemented)",
    )
    parser.add_argument(
        "--setup-check",
        action="store_true",
        help="Check if Knowledge Base collections exist",
    )

    args = parser.parse_args()

    # Just check if Knowledge Base is properly set up
    if args.setup_check:
        try:
            from archivist.knowledge_base.knowledge_manager import (
                Indaleko_Feedback_Record_Collection,
                Indaleko_Knowledge_Pattern_Collection,
                Indaleko_Learning_Event_Collection,
            )
            from db.db_collections import IndalekoDBCollections
            from db.i_collections import IndalekoCollections


            # Check if collections exist in IndalekoDBCollections
            collections_defined = (
                hasattr(IndalekoDBCollections, "Indaleko_Learning_Event_Collection")
                and hasattr(
                    IndalekoDBCollections,
                    "Indaleko_Knowledge_Pattern_Collection",
                )
                and hasattr(
                    IndalekoDBCollections,
                    "Indaleko_Feedback_Record_Collection",
                )
            )

            if collections_defined:
                pass
            else:
                pass

            # Try to get collections
            try:
                IndalekoCollections.get_collection(
                    Indaleko_Learning_Event_Collection,
                )
                IndalekoCollections.get_collection(
                    Indaleko_Knowledge_Pattern_Collection,
                )
                IndalekoCollections.get_collection(
                    Indaleko_Feedback_Record_Collection,
                )
                return
            except Exception:
                return
        except Exception:
            return

    # Initialize KB manager
    try:
        kb_manager = KnowledgeBaseManager()
    except ValueError:
        kb_manager = None

    # If no specific tests are selected, run all
    if not any(
        [
            args.all,
            args.events,
            args.patterns,
            args.feedback,
            args.queries,
            args.entities,
            args.stats,
            args.clear,
        ],
    ):
        args.all = True

    if args.all:
        run_all_tests()
        return

    # Run individual tests as requested
    if args.events:
        test_create_and_retrieve_events(kb_manager)

    if args.patterns:
        test_create_and_retrieve_patterns(kb_manager, None)

    if args.feedback:
        test_feedback_integration(kb_manager, None)

    if args.queries:
        test_query_enhancement(kb_manager)

    if args.entities:
        test_entity_relationships(kb_manager)

    if args.stats:
        test_stats(kb_manager)

    if args.clear:
        pass


if __name__ == "__main__":
    main()
