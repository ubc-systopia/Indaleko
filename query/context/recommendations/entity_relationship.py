"""
Entity Relationship Recommender for the Contextual Query Recommendation Engine.

This module provides the EntityRelationshipRecommender class, which generates
query suggestions based on entity relationships identified in queries and activities.

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

import logging
import os
import sys
import uuid

from datetime import UTC, datetime, timedelta
from typing import Any


# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from archivist.entity_equivalence import EntityEquivalenceManager
from query.context.data_models.recommendation import (
    FeedbackType,
    QuerySuggestion,
    RecommendationSource,
)
from query.context.recommendations.base import RecommendationProvider


# pylint: enable=wrong-import-position


class EntityRelationshipRecommender(RecommendationProvider):
    """
    Generates query suggestions based on entity relationships.

    This recommender analyzes entities in the current context and their
    relationships to generate query suggestions that explore related entities
    and their connections. It leverages both the entity equivalence system
    and detected entities in past queries and activities.
    """

    def __init__(self, db_config=None, debug: bool = False) -> None:
        """
        Initialize the entity relationship recommender.

        Args:
            db_config: Optional database configuration
            debug: Whether to enable debug output
        """
        super().__init__(RecommendationSource.ENTITY_RELATIONSHIP, debug)

        # Set up logging
        self._logger = logging.getLogger("EntityRelationshipRecommender")
        if debug:
            self._logger.setLevel(logging.DEBUG)

        # Initialize entity equivalence manager
        try:
            self._entity_manager = EntityEquivalenceManager(db_config=db_config)
            self._logger.info("Connected to Entity Equivalence Manager")
        except Exception as e:
            self._logger.exception(f"Error connecting to Entity Equivalence Manager: {e}")
            self._entity_manager = None

        # Initialize entity type configurations
        self._entity_types = {
            "person": {
                "templates": [
                    "Find files shared with {name}",
                    "Show communications with {name}",
                    "Find documents mentioning {name}",
                    "Show projects involving {name}",
                    "Find recent interactions with {name}",
                ],
                "confidence": 0.9,
                "relationships": [
                    "shared_with",
                    "created_by",
                    "modified_by",
                    "mentioned_in",
                ],
            },
            "organization": {
                "templates": [
                    "Find documents related to {name}",
                    "Show files about {name}",
                    "Find communications with {name}",
                    "Show projects involving {name}",
                ],
                "confidence": 0.85,
                "relationships": ["about", "created_by", "shared_with"],
            },
            "project": {
                "templates": [
                    "Find files related to project {name}",
                    "Show recent activity on {name}",
                    "Find team members involved in {name}",
                    "Show documents mentioning {name}",
                ],
                "confidence": 0.8,
                "relationships": ["part_of", "worked_on_by", "mentioned_in"],
            },
            "topic": {
                "templates": [
                    "Find documents about {name}",
                    "Show files related to {name}",
                    "Find information about {name}",
                    "Show projects related to {name}",
                ],
                "confidence": 0.75,
                "relationships": ["about", "related_to", "mentioned_in"],
            },
            "file": {
                "templates": [
                    "Find documents similar to {name}",
                    "Show files in the same folder as {name}",
                    "Find files created around the same time as {name}",
                    "Show files that reference {name}",
                    "Find previous versions of {name}",
                ],
                "confidence": 0.9,
                "relationships": [
                    "similar_to",
                    "same_folder",
                    "references",
                    "version_of",
                ],
            },
            "location": {
                "templates": [
                    "Find files created in {name}",
                    "Show documents related to {name}",
                    "Find activities that occurred in {name}",
                ],
                "confidence": 0.7,
                "relationships": ["created_in", "about", "occurred_in"],
            },
            "date": {
                "templates": [
                    "Find files created on {name}",
                    "Show activities from {name}",
                    "Find documents modified on {name}",
                ],
                "confidence": 0.7,
                "relationships": ["created_on", "modified_on", "occurred_on"],
            },
            "default": {
                "templates": [
                    "Find documents related to {name}",
                    "Show files mentioning {name}",
                    "Find information about {name}",
                ],
                "confidence": 0.6,
                "relationships": ["related_to", "about", "mentioned_in"],
            },
        }

        # Track successful entity-template combinations
        self._entity_type_success = dict.fromkeys(self._entity_types, 0)
        self._entity_type_failure = dict.fromkeys(self._entity_types, 0)
        self._template_success = {}  # {template: success_count}
        self._template_failure = {}  # {template: failure_count}

        # Cache recent entities to avoid redundant lookups
        self._entity_cache = {}  # {entity_id: entity_data}
        self._entity_cache_ttl = 300  # seconds
        self._entity_cache_time = {}  # {entity_id: last_access_time}

    def generate_suggestions(
        self,
        current_query: str | None = None,
        context_data: dict[str, Any] | None = None,
        max_suggestions: int = 10,
    ) -> list[QuerySuggestion]:
        """
        Generate query suggestions based on entity relationships.

        Args:
            current_query: The current query, if any
            context_data: Additional context data
            max_suggestions: Maximum number of suggestions to generate

        Returns:
            List of query suggestions based on entity relationships
        """
        suggestions = []
        context_data = context_data or {}

        # Extract entities from current query and context
        entities = self._extract_entities(current_query, context_data)

        if not entities:
            self._logger.info("No entities found in current context")
            return []

        # Get related entities for each entity
        for entity in entities:
            entity_suggestions = self._generate_suggestions_for_entity(
                entity,
                entities,
                max_per_entity=max_suggestions // len(entities) + 1,
            )
            suggestions.extend(entity_suggestions)

        # Ensure diversity across entity types
        diverse_suggestions = self._ensure_entity_type_diversity(suggestions)

        # Sort by confidence and limit to max_suggestions
        diverse_suggestions.sort(key=lambda x: x.confidence, reverse=True)
        return diverse_suggestions[:max_suggestions]

    def _extract_entities(
        self,
        current_query: str | None,
        context_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Extract entities from the current query and context.

        Args:
            current_query: The current query, if any
            context_data: Additional context data

        Returns:
            List of entity dictionaries
        """
        entities = []

        # Extract entities from context data if available
        context_entities = context_data.get("entities", [])
        entities.extend(context_entities)

        # Extract entities from current query if available
        if current_query and self._entity_manager:
            try:
                # Simulated entity extraction for demonstration
                # In a real implementation, this would use the entity extraction system
                query_entities = self._extract_entities_from_query(current_query)
                entities.extend(query_entities)
            except Exception as e:
                self._logger.exception(f"Error extracting entities from query: {e}")

        # If no entities found, generate some based on recent activities
        if not entities:
            entities = self._get_recent_activity_entities()

        # Deduplicate entities by ID
        deduplicated = {}
        for entity in entities:
            entity_id = entity.get("id")
            if entity_id and entity_id not in deduplicated:
                deduplicated[entity_id] = entity

        return list(deduplicated.values())

    def _extract_entities_from_query(self, query: str) -> list[dict[str, Any]]:
        """
        Extract entities from a query string.

        Args:
            query: The query string

        Returns:
            List of entity dictionaries
        """
        # In a real implementation, this would use a proper entity extraction system
        # For demonstration, we'll use a simple rule-based approach

        entities = []

        # Look for person names (simplified)
        if "shared with" in query.lower():
            parts = query.lower().split("shared with")
            if len(parts) > 1:
                person = parts[1].strip().split()[0].title()
                entities.append(
                    {
                        "id": str(uuid.uuid4()),
                        "name": person,
                        "type": "person",
                        "confidence": 0.8,
                        "source": "query",
                    },
                )

        # Look for file types
        file_types = ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt"]
        for file_type in file_types:
            if file_type in query.lower():
                entities.append(
                    {
                        "id": str(uuid.uuid4()),
                        "name": file_type,
                        "type": "file_type",
                        "confidence": 0.9,
                        "source": "query",
                    },
                )

        # Look for dates (simplified)
        date_indicators = [
            "yesterday",
            "today",
            "last week",
            "last month",
            "this month",
        ]
        for date in date_indicators:
            if date in query.lower():
                entities.append(
                    {
                        "id": str(uuid.uuid4()),
                        "name": date,
                        "type": "date",
                        "confidence": 0.7,
                        "source": "query",
                    },
                )

        return entities

    def _get_recent_activity_entities(self) -> list[dict[str, Any]]:
        """
        Get entities from recent activities when no context is available.

        Returns:
            List of entity dictionaries
        """
        # In a real implementation, this would query the database
        # For demonstration, we'll return some sample entities

        return [
            {
                "id": str(uuid.uuid4()),
                "name": "Quarterly Report",
                "type": "file",
                "confidence": 0.9,
                "source": "recent_activity",
                "metadata": {
                    "file_type": "pdf",
                    "last_modified": datetime.now(UTC).isoformat(),
                },
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Marketing",
                "type": "project",
                "confidence": 0.8,
                "source": "recent_activity",
                "metadata": {
                    "members": ["Alice", "Bob", "Charlie"],
                    "start_date": (datetime.now(UTC) - timedelta(days=30)).isoformat(),
                },
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Alice Smith",
                "type": "person",
                "confidence": 0.9,
                "source": "recent_activity",
                "metadata": {"email": "alice@example.com", "department": "Marketing"},
            },
        ]

    def _get_related_entities(self, entity: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Get entities related to the given entity.

        Args:
            entity: The entity to find related entities for

        Returns:
            List of related entity dictionaries
        """
        # In a real implementation, this would query the entity relationship system
        # For demonstration, we'll return some sample related entities

        entity_type = entity.get("type", "default")
        entity_name = entity.get("name", "")

        related_entities = []

        if entity_type == "person":
            # Sample related entities for a person
            related_entities = [
                {
                    "id": str(uuid.uuid4()),
                    "name": f"Project {entity_name[:1]}",
                    "type": "project",
                    "confidence": 0.8,
                    "relationship": "worked_on_by",
                    "source": "entity_relationship",
                },
                {
                    "id": str(uuid.uuid4()),
                    "name": f"Team {entity_name[:1]}",
                    "type": "organization",
                    "confidence": 0.7,
                    "relationship": "member_of",
                    "source": "entity_relationship",
                },
            ]
        elif entity_type == "file":
            # Sample related entities for a file
            related_entities = [
                {
                    "id": str(uuid.uuid4()),
                    "name": "Alice Smith",
                    "type": "person",
                    "confidence": 0.9,
                    "relationship": "created_by",
                    "source": "entity_relationship",
                },
                {
                    "id": str(uuid.uuid4()),
                    "name": f"{entity_name} v2",
                    "type": "file",
                    "confidence": 0.8,
                    "relationship": "version_of",
                    "source": "entity_relationship",
                },
            ]
        elif entity_type == "project":
            # Sample related entities for a project
            related_entities = [
                {
                    "id": str(uuid.uuid4()),
                    "name": "Alice Smith",
                    "type": "person",
                    "confidence": 0.9,
                    "relationship": "worked_on_by",
                    "source": "entity_relationship",
                },
                {
                    "id": str(uuid.uuid4()),
                    "name": f"{entity_name} Requirements",
                    "type": "file",
                    "confidence": 0.8,
                    "relationship": "part_of",
                    "source": "entity_relationship",
                },
            ]

        return related_entities

    def _generate_suggestions_for_entity(
        self,
        entity: dict[str, Any],
        all_entities: list[dict[str, Any]],
        max_per_entity: int = 3,
    ) -> list[QuerySuggestion]:
        """
        Generate suggestions for a specific entity.

        Args:
            entity: The entity to generate suggestions for
            all_entities: All entities in the current context
            max_per_entity: Maximum suggestions per entity

        Returns:
            List of query suggestions
        """
        suggestions = []

        # Get entity type configuration
        entity_type = entity.get("type", "default")
        entity_config = self._entity_types.get(
            entity_type,
            self._entity_types["default"],
        )

        # Get templates for this entity type
        templates = entity_config["templates"]
        base_confidence = entity_config["confidence"]

        # Get relationships for this entity type
        relationships = entity_config["relationships"]

        # Generate direct suggestions for this entity
        for template in templates:
            try:
                # Format template with entity name
                query_text = template.format(name=entity.get("name", "unknown"))

                # Calculate confidence based on entity confidence, template success, etc.
                confidence = self._calculate_confidence(
                    base_confidence,
                    entity,
                    template,
                )

                # Create suggestion
                suggestion = self.create_suggestion(
                    query_text=query_text,
                    rationale=f"Based on {entity_type} entity '{entity.get('name', 'unknown')}'",
                    confidence=confidence,
                    source_context={
                        "entity_type": entity_type,
                        "entity_id": entity.get("id"),
                        "entity_name": entity.get("name"),
                        "template": template,
                    },
                    relevance_factors={
                        "entity_confidence": entity.get("confidence", 0.5),
                        "template_success": self._get_template_success_ratio(template),
                        "entity_type_success": self._get_entity_type_success_ratio(
                            entity_type,
                        ),
                    },
                    tags=[
                        f"entity_type:{entity_type}",
                        f"entity:{entity.get('name', 'unknown')}",
                    ],
                )

                suggestions.append(suggestion)

            except (KeyError, ValueError) as e:
                self._logger.debug(f"Error formatting template {template}: {e}")

        # Get related entities and generate suggestions for them
        related_entities = self._get_related_entities(entity)

        for related_entity in related_entities:
            # Skip if already among all context entities
            if any(e.get("id") == related_entity.get("id") for e in all_entities):
                continue

            relationship = related_entity.get("relationship")
            related_type = related_entity.get("type", "default")
            related_config = self._entity_types.get(
                related_type,
                self._entity_types["default"],
            )

            # Generate suggestions based on relationship
            if relationship in relationships:
                for template in related_config["templates"][:2]:  # Limit to 2 templates for diversity
                    try:
                        # Format template with related entity name
                        query_text = template.format(
                            name=related_entity.get("name", "unknown"),
                        )

                        # Calculate confidence
                        rel_confidence = self._calculate_relationship_confidence(
                            entity,
                            related_entity,
                            relationship,
                        )

                        # Create suggestion
                        suggestion = self.create_suggestion(
                            query_text=query_text,
                            rationale=f"Based on {relationship} relationship with '{entity.get('name', 'unknown')}'",
                            confidence=rel_confidence,
                            source_context={
                                "entity_type": related_type,
                                "entity_id": related_entity.get("id"),
                                "entity_name": related_entity.get("name"),
                                "relationship": relationship,
                                "source_entity": entity.get("name"),
                                "template": template,
                            },
                            relevance_factors={
                                "entity_confidence": related_entity.get(
                                    "confidence",
                                    0.5,
                                ),
                                "relationship_strength": 0.8,  # Would be based on actual relationship data
                                "template_success": self._get_template_success_ratio(
                                    template,
                                ),
                            },
                            tags=[
                                f"entity_type:{related_type}",
                                f"relationship:{relationship}",
                            ],
                        )

                        suggestions.append(suggestion)

                    except (KeyError, ValueError) as e:
                        self._logger.debug(f"Error formatting template {template}: {e}")

        # Sort by confidence and limit to max_per_entity
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        return suggestions[:max_per_entity]

    def _ensure_entity_type_diversity(
        self,
        suggestions: list[QuerySuggestion],
    ) -> list[QuerySuggestion]:
        """
        Ensure diversity across entity types in suggestions.

        Args:
            suggestions: List of suggestions

        Returns:
            Diverse list of suggestions
        """
        if len(suggestions) <= 3:
            return suggestions

        # Group by entity type
        by_type = {}
        for suggestion in suggestions:
            entity_type = suggestion.source_context.get("entity_type", "unknown")
            if entity_type not in by_type:
                by_type[entity_type] = []
            by_type[entity_type].append(suggestion)

        # Create diverse list
        diverse = []
        max_per_type = 3  # Maximum suggestions per entity type

        # First, add the top suggestion for each entity type
        for entity_type, type_suggestions in by_type.items():
            type_suggestions.sort(key=lambda x: x.confidence, reverse=True)
            diverse.append(type_suggestions[0])

        # Then, fill in with remaining suggestions by confidence
        all_remaining = []
        for entity_type, type_suggestions in by_type.items():
            for suggestion in type_suggestions[1:max_per_type]:  # Skip first one which was added above
                all_remaining.append(suggestion)

        all_remaining.sort(key=lambda x: x.confidence, reverse=True)
        diverse.extend(all_remaining)

        return diverse

    def _calculate_confidence(
        self,
        base_confidence: float,
        entity: dict[str, Any],
        template: str,
    ) -> float:
        """
        Calculate confidence score for an entity-based suggestion.

        Args:
            base_confidence: Base confidence for entity type
            entity: Entity dictionary
            template: Query template

        Returns:
            Confidence score (0.0-1.0)
        """
        # Get entity confidence
        entity_confidence = entity.get("confidence", 0.5)

        # Get template success ratio
        template_success = self._get_template_success_ratio(template)

        # Get entity type success ratio
        entity_type = entity.get("type", "default")
        entity_type_success = self._get_entity_type_success_ratio(entity_type)

        # Calculate weighted confidence
        factors = {
            "base": base_confidence,
            "entity_confidence": entity_confidence,
            "template_success": template_success,
            "entity_type_success": entity_type_success,
        }

        weights = {
            "base": 0.3,
            "entity_confidence": 0.3,
            "template_success": 0.2,
            "entity_type_success": 0.2,
        }

        return self.calculate_confidence(factors, weights)

    def _calculate_relationship_confidence(
        self,
        source_entity: dict[str, Any],
        target_entity: dict[str, Any],
        relationship: str,
    ) -> float:
        """
        Calculate confidence for a relationship-based suggestion.

        Args:
            source_entity: Source entity
            target_entity: Target entity
            relationship: Relationship type

        Returns:
            Confidence score (0.0-1.0)
        """
        # Start with target entity confidence
        base_confidence = target_entity.get("confidence", 0.5)

        # Adjust based on relationship strength (this would be based on actual data)
        relationship_strength = 0.8

        # Adjust based on source entity confidence
        source_confidence = source_entity.get("confidence", 0.5)

        # Calculate weighted confidence
        factors = {
            "base": base_confidence,
            "relationship_strength": relationship_strength,
            "source_confidence": source_confidence,
        }

        weights = {"base": 0.4, "relationship_strength": 0.4, "source_confidence": 0.2}

        return self.calculate_confidence(factors, weights)

    def _get_template_success_ratio(self, template: str) -> float:
        """
        Get success ratio for a template based on feedback history.

        Args:
            template: The query template

        Returns:
            Success ratio (0.0-1.0)
        """
        successes = self._template_success.get(template, 0)
        failures = self._template_failure.get(template, 0)

        if successes + failures == 0:
            return 0.5  # No history

        return successes / (successes + failures)

    def _get_entity_type_success_ratio(self, entity_type: str) -> float:
        """
        Get success ratio for an entity type based on feedback history.

        Args:
            entity_type: The entity type

        Returns:
            Success ratio (0.0-1.0)
        """
        successes = self._entity_type_success.get(entity_type, 0)
        failures = self._entity_type_failure.get(entity_type, 0)

        if successes + failures == 0:
            return 0.5  # No history

        return successes / (successes + failures)

    def update_from_feedback(
        self,
        suggestion: QuerySuggestion,
        feedback: FeedbackType,
        result_count: int | None = None,
    ) -> None:
        """
        Update internal models based on feedback.

        Args:
            suggestion: The suggestion that received feedback
            feedback: The type of feedback provided
            result_count: Number of results from the suggested query, if applicable
        """
        # Extract entity information from source context
        source_context = suggestion.source_context
        entity_type = source_context.get("entity_type", "default")
        template = source_context.get("template", "")

        # Update template success/failure
        if template:
            if self.is_positive_feedback(feedback):
                self._template_success[template] = self._template_success.get(template, 0) + 1

                # Bonus for highly successful queries (many results)
                if result_count and result_count > 5:
                    self._template_success[template] = self._template_success.get(template, 0) + 1
            elif self.is_negative_feedback(feedback):
                self._template_failure[template] = self._template_failure.get(template, 0) + 1

        # Update entity type success/failure
        if entity_type:
            if self.is_positive_feedback(feedback):
                self._entity_type_success[entity_type] = self._entity_type_success.get(entity_type, 0) + 1

                # Bonus for highly successful queries (many results)
                if result_count and result_count > 5:
                    self._entity_type_success[entity_type] = self._entity_type_success.get(entity_type, 0) + 1
            elif self.is_negative_feedback(feedback):
                self._entity_type_failure[entity_type] = self._entity_type_failure.get(entity_type, 0) + 1

        self._logger.debug(
            f"Updated feedback for entity type {entity_type}, template: {template}",
        )
        self._logger.debug(
            f"Entity type success: {self._entity_type_success.get(entity_type, 0)}, failure: {self._entity_type_failure.get(entity_type, 0)}",
        )
        self._logger.debug(
            f"Template success: {self._template_success.get(template, 0)}, failure: {self._template_failure.get(template, 0)}",
        )


def main() -> None:
    """Test the EntityRelationshipRecommender."""
    logging.basicConfig(level=logging.DEBUG)


    # Create recommender
    recommender = EntityRelationshipRecommender(debug=True)

    # Test with a current query
    current_query = "Find files shared with Alice"
    context_data = {
        "entities": [
            {
                "id": str(uuid.uuid4()),
                "name": "Quarterly Report",
                "type": "file",
                "confidence": 0.9,
                "source": "recent_activity",
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Marketing",
                "type": "project",
                "confidence": 0.8,
                "source": "recent_activity",
            },
        ],
    }


    # Generate suggestions
    suggestions = recommender.generate_suggestions(
        current_query=current_query,
        context_data=context_data,
        max_suggestions=5,
    )

    # Print suggestions
    for _i, suggestion in enumerate(suggestions):
        if "relationship" in suggestion.source_context:
            pass

    # Test feedback
    if suggestions:
        recommender.update_from_feedback(
            suggestion=suggestions[0],
            feedback=FeedbackType.ACCEPTED,
            result_count=7,
        )

        # Generate new suggestions to see effect of feedback
        new_suggestions = recommender.generate_suggestions(
            current_query=current_query,
            context_data=context_data,
            max_suggestions=5,
        )

        for _i, suggestion in enumerate(new_suggestions):

            # Check if this matches an original suggestion to see confidence change
            for orig in suggestions:
                if suggestion.query_text == orig.query_text:
                    confidence_change = suggestion.confidence - orig.confidence
                    if abs(confidence_change) > 0.01:
                        pass


if __name__ == "__main__":
    main()
