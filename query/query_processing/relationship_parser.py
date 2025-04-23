"""
This module provides a parser for relationship-based queries in Indaleko.

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
import re
import sys
import uuid
from textwrap import dedent
from typing import Any

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from query.query_processing.data_models.query_language_enhancer import EntityResolution
from query.query_processing.data_models.relationship_query_model import (
    EntityType,
    RelationshipDirection,
    RelationshipEntity,
    RelationshipQuery,
    RelationshipType,
)
from query.query_processing.enhanced_nl_parser import EnhancedNLParser
from query.utils.llm_connector.openai_connector import OpenAIConnector

# pylint: enable=wrong-import-position


class RelationshipParser:
    """
    Parser for relationship-based queries in Indaleko.

    This parser extends the NL parser to identify and extract relationship patterns from
    natural language queries, focusing on connections between entities.
    """

    def __init__(
        self,
        llm_connector: OpenAIConnector,
        collections_metadata: IndalekoDBCollectionsMetadata,
        enhanced_parser: EnhancedNLParser | None = None,
    ):
        """
        Initialize the relationship parser.

        Args:
            llm_connector: Connector to the language model
            collections_metadata: Metadata for database collections
            enhanced_parser: Optional enhanced NL parser instance to use
        """
        self.llm_connector = llm_connector
        self.collections_metadata = collections_metadata

        if enhanced_parser:
            self.enhanced_parser = enhanced_parser
        else:
            self.enhanced_parser = EnhancedNLParser(llm_connector, collections_metadata)

        # Initialize common relationship patterns for rules-based matching
        self._initialize_patterns()

    def _initialize_patterns(self):
        """Initialize regex patterns for common relationship queries."""
        self.user_file_patterns = {
            RelationshipType.CREATED: [
                r"(files|documents)(?:\s+that)?(?:\s+I|\s+\w+)?\s+created",
                r"created by\s+(me|\w+)",
            ],
            RelationshipType.MODIFIED: [
                r"(files|documents)(?:\s+that)?(?:\s+I|\s+\w+)?\s+(modified|edited|changed)",
                r"(modified|edited|changed) by\s+(me|\w+)",
            ],
            RelationshipType.VIEWED: [
                r"(files|documents)(?:\s+that)?(?:\s+I|\s+\w+)?\s+(viewed|opened|read)",
                r"(viewed|opened|read) by\s+(me|\w+)",
            ],
        }

        self.file_file_patterns = {
            RelationshipType.DERIVED_FROM: [
                r"(derived|generated|created)\s+from",
                r"source (?:files|documents) for",
            ],
            RelationshipType.SAME_FOLDER: [
                r"(files|documents) in (?:the )?same (folder|directory) as",
                r"other (files|documents) in (?:the )?(?:folder|directory)",
            ],
        }

        self.user_user_patterns = {
            RelationshipType.SHARED_WITH: [
                r"(files|documents)(?:\s+that)?(?:\s+I|\s+\w+)?\s+shared with\s+(\w+)",
                r"shared (?:by\s+\w+)?\s+with\s+(\w+)",
            ],
            RelationshipType.COLLABORATED_WITH: [
                r"(files|documents)(?:\s+that)?(?:\s+I|\s+\w+)?\s+worked on with\s+(\w+)",
                r"collaborated (?:with\s+\w+)?\s+on",
            ],
        }

    def parse_relationship_query(self, query: str) -> RelationshipQuery:
        """
        Parse a natural language query to extract relationship information.

        Args:
            query: The natural language query to parse

        Returns:
            RelationshipQuery: A structured representation of the relationship query
        """
        # Get enhanced understanding of the query first
        enhanced_understanding = self.enhanced_parser.parse_enhanced(query)

        # Quick rules-based check for common relationship patterns
        relationship_type, entities = self._check_relationship_patterns(query)

        # If we found a relationship pattern, use it to build the query
        if relationship_type != RelationshipType.UNKNOWN:
            logging.info(
                f"Detected relationship type {relationship_type} using pattern matching",
            )
            return self._build_relationship_query(
                relationship_type, entities, query, enhanced_understanding,
            )

        # Otherwise, use the LLM for more complex analysis
        return self._extract_relationship_query_llm(query, enhanced_understanding)

    def _check_relationship_patterns(
        self, query: str,
    ) -> tuple[RelationshipType, dict[str, Any] | None]:
        """
        Check if the query matches common relationship patterns.

        Args:
            query: The natural language query

        Returns:
            Tuple of RelationshipType and optional extracted entities
        """
        query_lower = query.lower()

        # Check user-file relationships
        for rel_type, patterns in self.user_file_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, query_lower)
                if match:
                    # Extract entities from the match
                    entities = self._extract_entities_from_match(match, rel_type)
                    return rel_type, entities

        # Check file-file relationships
        for rel_type, patterns in self.file_file_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, query_lower)
                if match:
                    entities = self._extract_entities_from_match(match, rel_type)
                    return rel_type, entities

        # Check user-user relationships
        for rel_type, patterns in self.user_user_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, query_lower)
                if match:
                    entities = self._extract_entities_from_match(match, rel_type)
                    return rel_type, entities

        # No matches found
        return RelationshipType.UNKNOWN, None

    def _extract_entities_from_match(
        self, match: re.Match, rel_type: RelationshipType,
    ) -> dict[str, Any]:
        """
        Extract entities from a regex match of a relationship pattern.

        Args:
            match: The regex match object
            rel_type: The relationship type

        Returns:
            Dict of extracted entities
        """
        entities = {}

        if rel_type in (
            RelationshipType.CREATED,
            RelationshipType.MODIFIED,
            RelationshipType.VIEWED,
        ):
            # User-File relationship
            if match.group(2) == "me" or "I" in match.group(0):
                entities["user"] = "current_user"
            elif len(match.groups()) > 1:
                entities["user"] = match.group(2)

        elif rel_type in (
            RelationshipType.SHARED_WITH,
            RelationshipType.COLLABORATED_WITH,
        ):
            # User-User relationship
            if "I" in match.group(0):
                entities["source_user"] = "current_user"

            if len(match.groups()) > 1:
                entities["target_user"] = match.group(2)

        elif rel_type == RelationshipType.SAME_FOLDER:
            # Extract file/folder information if available
            if "as" in match.group(0) and len(match.groups()) > 0:
                # Try to extract file name after "as"
                file_part = match.group(0).split("as")[1].strip()
                if file_part:
                    entities["reference_file"] = file_part

        return entities

    def _build_relationship_query(
        self,
        relationship_type: RelationshipType,
        entities: dict[str, Any] | None,
        original_query: str,
        enhanced_understanding: Any,
    ) -> RelationshipQuery:
        """
        Build a structured relationship query from extracted information.

        Args:
            relationship_type: The type of relationship
            entities: Extracted entities from pattern matching
            original_query: The original natural language query
            enhanced_understanding: Enhanced understanding of the query

        Returns:
            RelationshipQuery: A structured relationship query
        """
        # Default source entity (typically the current user)
        source_entity = RelationshipEntity(
            entity_type=EntityType.USER,
            identifier="current_user",
            attributes={"is_self": True},
        )

        # Default to no target entity
        target_entity = None

        # Default direction
        direction = RelationshipDirection.ANY

        # Set relationship-specific entities and direction
        if relationship_type in (
            RelationshipType.CREATED,
            RelationshipType.MODIFIED,
            RelationshipType.VIEWED,
        ):
            # User-File relationship
            if entities and "user" in entities:
                if entities["user"] == "current_user":
                    # Current user is source
                    direction = RelationshipDirection.OUTBOUND
                else:
                    # Other user is source
                    source_entity = RelationshipEntity(
                        entity_type=EntityType.USER, identifier=entities["user"],
                    )
                    direction = RelationshipDirection.OUTBOUND

            # Target is a file (any file matching conditions)
            target_entity = RelationshipEntity(
                entity_type=EntityType.FILE, attributes={},
            )

        elif relationship_type in (
            RelationshipType.SHARED_WITH,
            RelationshipType.COLLABORATED_WITH,
        ):
            # User-User relationship
            if entities and "target_user" in entities:
                target_entity = RelationshipEntity(
                    entity_type=EntityType.USER, identifier=entities["target_user"],
                )

            direction = RelationshipDirection.OUTBOUND

        elif relationship_type == RelationshipType.SAME_FOLDER:
            # File-File relationship
            source_entity = RelationshipEntity(
                entity_type=EntityType.FILE, attributes={},
            )

            if entities and "reference_file" in entities:
                source_entity = RelationshipEntity(
                    entity_type=EntityType.FILE, identifier=entities["reference_file"],
                )

            target_entity = RelationshipEntity(
                entity_type=EntityType.FILE, attributes={},
            )

        # Extract time constraints from enhanced understanding
        time_constraint = None
        additional_filters = {}

        # Handle time constraints if available
        if hasattr(enhanced_understanding, "constraints"):
            for constraint in enhanced_understanding.constraints:
                if constraint.field in (
                    "timestamp",
                    "date",
                    "time",
                    "created",
                    "modified",
                ):
                    if not time_constraint:
                        time_constraint = {}

                    if constraint.operation in ("between", "range"):
                        time_constraint["start_time"] = constraint.value.get("start")
                        time_constraint["end_time"] = constraint.value.get("end")
                    elif constraint.operation in ("after", "greater_than"):
                        time_constraint["start_time"] = constraint.value
                    elif constraint.operation in ("before", "less_than"):
                        time_constraint["end_time"] = constraint.value
                else:
                    # Add other constraints as additional filters
                    additional_filters[constraint.field] = {
                        "operation": constraint.operation,
                        "value": constraint.value,
                    }

        # Build the complete relationship query
        relationship_query = RelationshipQuery(
            relationship_type=relationship_type,
            direction=direction,
            source_entity=source_entity,
            target_entity=target_entity,
            time_constraint=time_constraint,
            additional_filters=additional_filters,
            natural_language_query=original_query,
            confidence=0.8,  # Pattern-based matching has good confidence
        )

        return relationship_query

    def _extract_relationship_query_llm(
        self, query: str, enhanced_understanding: Any,
    ) -> RelationshipQuery:
        """
        Use the LLM to extract a relationship query for more complex or ambiguous queries.

        Args:
            query: The natural language query
            enhanced_understanding: Enhanced understanding from the parser

        Returns:
            RelationshipQuery: A structured relationship query
        """
        # Create an example response
        example_response = RelationshipQuery(
            relationship_type=RelationshipType.SHARED_WITH,
            direction=RelationshipDirection.OUTBOUND,
            source_entity=RelationshipEntity(
                entity_type=EntityType.USER,
                identifier="current_user",
                attributes={"is_self": True},
            ),
            target_entity=RelationshipEntity(
                entity_type=EntityType.USER,
                identifier="bob@example.com",
                resolution=EntityResolution(
                    original_text="Bob",
                    normalized_value="bob@example.com",
                    entity_type="user",
                    confidence=0.9,
                ),
            ),
            time_constraint={
                "start_time": "2023-01-01T00:00:00Z",
                "end_time": "2023-01-31T23:59:59Z",
            },
            additional_filters={"file_type": "document"},
            natural_language_query=query,
            confidence=0.85,
        )

        # Create context data for the LLM
        context_data = {
            "relationship_types": [rt.value for rt in RelationshipType],
            "entity_types": [et.value for et in EntityType],
            "directions": [d.value for d in RelationshipDirection],
            "enhanced_understanding": (
                enhanced_understanding.model_dump()
                if hasattr(enhanced_understanding, "model_dump")
                else str(enhanced_understanding)
            ),
        }

        # Create the prompt for the LLM
        try:
            # Custom JSON serializer for complex types
            def _json_serializable(obj):
                if isinstance(obj, uuid.UUID):
                    return str(obj)
                elif hasattr(obj, "model_dump"):
                    return obj.model_dump()
                return str(obj)

            context_json = json.dumps(
                context_data, indent=2, default=_json_serializable,
            )
        except Exception as e:
            logging.warning(f"Error serializing context data: {e}")
            context_json = json.dumps(
                {
                    "query": query,
                    "relationship_types": [rt.value for rt in RelationshipType],
                    "entity_types": [et.value for et in EntityType],
                },
            )

        system_prompt = dedent(
            f"""
        You are a relationship analysis expert for Indaleko, a unified personal index system.
        Your task is to analyze natural language queries and identify relationships between entities.

        Parse the user's query and return a structured JSON representation of the relationship query
        that matches the RelationshipQuery schema provided. Focus on identifying:

        1. The primary relationship type (e.g., created, modified, shared_with)
        2. The direction of the relationship (outbound, inbound, any)
        3. The source entity (usually a user or file)
        4. The target entity (what the relationship points to)
        5. Any time constraints on the relationship
        6. Additional filters to apply to the results

        Context Data:
        {context_json}

        Base your analysis on the provided enhanced understanding of the query and the available
        relationship types, entity types, and directions. Be as specific as possible in identifying
        the relationship pattern.
        """,
        )

        user_prompt = f"Analyze this relationship query: '{query}'"
        schema = example_response.model_json_schema()

        # Use the LLM connector to get enhanced understanding
        response = self.llm_connector.get_completion(
            context=system_prompt, question=user_prompt, schema=schema,
        )

        # Parse the response
        try:
            response_data = json.loads(response.choices[0].message.content)
            relationship_query = RelationshipQuery(**response_data)
            return relationship_query
        except Exception as e:
            logging.exception(f"Error parsing LLM response: {e}")
            # Fall back to a default relationship query
            return RelationshipQuery(
                relationship_type=RelationshipType.UNKNOWN,
                source_entity=RelationshipEntity(
                    entity_type=EntityType.USER, identifier="current_user",
                ),
                natural_language_query=query,
                confidence=0.3,  # Low confidence due to error
            )
