"""
This module provides a natural language parser for Indaleko queries.

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
import time
import traceback

from textwrap import dedent
from typing import Any

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.named_entity import (
    IndalekoNamedEntityDataModel,
    IndalekoNamedEntityType,
    NamedEntityCollection,
    example_entities,
)
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from query.query_processing.data_models.parser_data import ParserResults
from query.query_processing.data_models.query_output import (
    LLMCollectionCategory,
    LLMCollectionCategoryEnum,
    LLMCollectionCategoryQueryResponse,
    LLMIntentQueryResponse,
    LLMIntentTypeEnum,
)
from query.utils.llm_connector.llm_base import IndalekoLLMBase


# pylint: enable=wrong-import-position

# Configure logger for this module
logger = logging.getLogger(__name__)


class LLMResponseValidationError(Exception):
    """Exception raised when the LLM returns an invalid response."""


class LLMResponseValidator:
    """Validate and repair LLM responses."""

    @staticmethod
    def validate_and_repair_category_response(response: dict) -> dict:
        """
        Validate and attempt to repair a category response from an LLM.

        Args:
            response: The raw response from the LLM

        Returns:
            A validated and potentially repaired response

        Raises:
            LLMResponseValidationError: If the response cannot be repaired
        """
        if not response:
            raise LLMResponseValidationError("Empty response")

        # Check if category_map exists
        if "category_map" not in response:
            raise LLMResponseValidationError("Missing required field 'category_map'")

        # Ensure category_map is a list
        if not isinstance(response["category_map"], list):
            raise LLMResponseValidationError("'category_map' must be a list")

        # Process each category in the map
        for i, category in enumerate(response["category_map"]):
            # Check required fields
            required_fields = ["category", "collection", "confidence", "rationale"]
            missing_fields = [field for field in required_fields if field not in category]

            if missing_fields:
                logger.warning(
                    f"Category {i} missing required fields: {missing_fields}",
                )
                for field in missing_fields:
                    if field == "confidence":
                        category[field] = 0.8  # Default confidence
                    elif field == "rationale":
                        category[field] = "Auto-generated rationale due to missing field"
                    else:
                        raise LLMResponseValidationError(
                            f"Category {i} missing required field: {field}",
                        )

            # Add alternatives_considered if missing
            if "alternatives_considered" not in category:
                logger.warning(
                    f"Adding missing 'alternatives_considered' to category {i}",
                )
                category["alternatives_considered"] = []

        return response

    @staticmethod
    def validate_and_repair_intent_response(response: dict) -> dict:
        """
        Validate and attempt to repair an intent response from an LLM.

        Args:
            response: The raw response from the LLM

        Returns:
            A validated and potentially repaired response

        Raises:
            LLMResponseValidationError: If the response cannot be repaired
        """
        if not response:
            raise LLMResponseValidationError("Empty response")

        # Check required fields
        required_fields = ["intent", "confidence", "rationale"]
        missing_fields = [field for field in required_fields if field not in response]

        if missing_fields:
            for field in missing_fields:
                if field == "confidence":
                    response[field] = 0.8  # Default confidence
                elif field == "rationale":
                    response[field] = "Auto-generated rationale due to missing field"
                elif field == "intent":
                    response[field] = "search"  # Default intent
                else:
                    raise LLMResponseValidationError(f"Missing required field: {field}")

        # Add alternatives_considered if missing
        if "alternatives_considered" not in response:
            logger.warning(
                "Adding missing 'alternatives_considered' to intent response",
            )
            response["alternatives_considered"] = []

        return response

    @staticmethod
    def validate_and_repair_entities_response(response: dict) -> dict:
        """
        Validate and attempt to repair an entities response from an LLM.

        Args:
            response: The raw response from the LLM

        Returns:
            A validated and potentially repaired response

        Raises:
            LLMResponseValidationError: If the response cannot be repaired
        """
        if not response:
            raise LLMResponseValidationError("Empty response")

        # Check if entities exist
        if "entities" not in response:
            raise LLMResponseValidationError("Missing required field 'entities'")

        # Ensure entities is a list
        if not isinstance(response["entities"], list):
            raise LLMResponseValidationError("'entities' must be a list")

        # Process each entity
        for i, entity in enumerate(response["entities"]):
            # Check required fields
            if "name" not in entity:
                raise LLMResponseValidationError(
                    f"Entity {i} missing required field 'name'",
                )

            # Add category/type if missing
            if "category" not in entity and "type" not in entity:
                logger.warning(f"Adding default category 'item' to entity {i}")
                entity["category"] = "item"

            # Normalize between category and type
            if "type" in entity and "category" not in entity:
                entity["category"] = entity["type"]

        return response


class NLParser:
    """
    Natural Language Parser for processing queries.
    """

    def __init__(
        self,
        collections_metadata: IndalekoDBCollectionsMetadata,
        llm_connector: IndalekoLLMBase | None = None,
    ):
        """
        Initialize the parser.

        Args:
            collections_metadata: Metadata for the database collections.
            llm_connector: An optional connector to the LLM service.
        """
        # Initialize components
        self.llm_connector = llm_connector
        self.collections_metadata = collections_metadata
        self.validator = LLMResponseValidator()

        # Error tracking
        self.error_log = []
        self.error_count = {
            "category": 0,
            "intent": 0,
            "entities": 0,
            "total": 0,
            "validation": 0,
        }

        # Handle collection metadata correctly
        if hasattr(self.collections_metadata, "get_all_collections_metadata"):
            self.collection_data = self.collections_metadata.get_all_collections_metadata()
        else:
            # Fallback to using collections_metadata directly if it's a dictionary
            self.collection_data = getattr(
                self.collections_metadata,
                "collections_metadata",
                {},
            )
            if not self.collection_data:
                # If that's also empty, create a minimal default structure with Objects
                self.collection_data = {
                    "Objects": {
                        "Name": "Objects",
                        "Description": "Storage objects collection",
                        "Indices": [],
                        "Schema": {},
                        "QueryGuidelines": ["Search for files and folders"],
                    },
                }

    def parse(self, query: str) -> ParserResults:
        """
        Parse the natural language query into a structured format.

        Args:
            query: The user's natural language query

        Returns:
            ParserResults: A structured representation of the query
        """
        return ParserResults(
            OriginalQuery=query,
            Intent=self._detect_intent(query),
            Entities=self._extract_entities(query),
            Categories=self._extract_categories(query),
        )


    def _detect_intent(self, query: str) -> LLMIntentQueryResponse:
        """
        Detect the primary intent of the query.

        Args:
            query: The query

        Returns:
            LLMIntentQueryResponse: The detected intent
        """
        try:
            # Define typical intents
            typical_intents = list(LLMIntentTypeEnum)

            # Create query response template
            query_response = LLMIntentQueryResponse(
                intent="search",
                rationale="because this is a search tool, the default intent is search",
                alternatives_considered=[
                    {
                        "example": "this is an example, so it is static and nothing else was considered",
                    },
                ],
                suggestion="No suggestions, this is an optimal process in my opinion",
                confidence=0.5,
            )
            schema = query_response.model_json_schema()

            # Create a prompt for the LLM
            prompt = dedent(
                "You are a personal digital archivist collaborating with a human user and a tool called "
                "Indaleko.  Together your goal is to help the human user find a specific storage object "
                "(typically a file) that is stored in a storage services.  Indaleko is an index of all this "
                "human user's storage services, with normalized data.  The human user has submitted a query "
                "and our first step in our collaboration is to infer the user's intent from the query. "
                f"The current typical intents are: {typical_intents}, where unknown is used when "
                "the intent is unclear. Given the nature of our collaboration, search is the most likely intent. "
                "In returning your response, please provide the intent as a JSON structure with the following "
                f"schema: {schema}\n"
                "Since this is a collaboration between us, we value your feedback on this process, "
                "so that we can work together to improve the quality of the results.",
            )

            # Use the LLM connector to get the intent
            response = self.llm_connector.answer_question(prompt, query, schema)
            doc = json.loads(response)

            # Validate and repair intent response
            try:
                doc = self.validator.validate_and_repair_intent_response(doc)
            except LLMResponseValidationError as e:
                logger.error(f"Intent validation error: {e}")
                self.error_count["validation"] += 1
                self.error_count["intent"] += 1
                self.error_count["total"] += 1
                self.error_log.append(
                    {
                        "timestamp": time.time(),
                        "query": query,
                        "stage": "intent_validation",
                        "error": str(e),
                        "response": doc,
                    },
                )
                # Create default intent
                return LLMIntentQueryResponse(
                    intent="search",
                    confidence=0.8,
                    rationale="Default fallback due to validation error",
                    alternatives_considered=[],
                )

            # Create intent response object
            data = LLMIntentQueryResponse(**doc)

            # Validate the intent
            if data.intent not in typical_intents:
                logger.warning(f"Unrecognized intent: {data.intent}")
                data.intent = "unknown"  # Default to "unknown" if not recognized

            logging.info(ic(f"Detected intent: {data.intent}"))
            return data

        except Exception as e:
            logger.error(f"Error detecting intent: {e}")
            logger.debug(traceback.format_exc())
            self.error_count["intent"] += 1
            self.error_count["total"] += 1
            self.error_log.append(
                {
                    "timestamp": time.time(),
                    "query": query,
                    "stage": "intent",
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                },
            )

            # Create default intent
            return LLMIntentQueryResponse(
                intent="search",
                confidence=0.8,
                rationale="Default fallback due to error",
                alternatives_considered=[],
            )

    def _extract_categories(self, query: str) -> LLMCollectionCategoryQueryResponse:
        """
        Using the collections in the database, identify which categories of information
        are likely to be useful for the query.

        Args:
            query: The user's query

        Returns:
            LLMCollectionCategoryQueryResponse: A response with category mappings
        """
        try:

            # Define existing category types
            typical_categories = [category.value for category in LLMCollectionCategoryEnum]
            ic(typical_categories)

            # Create default category response
            category_response = LLMCollectionCategoryQueryResponse(
                category_map=[
                    LLMCollectionCategory(
                        category=LLMCollectionCategoryEnum.OBJECTS,
                        collection=(
                            self.collection_data["Objects"]["Name"]
                            if isinstance(self.collection_data["Objects"], dict)
                            else self.collection_data["Objects"].Name
                        ),
                        confidence=0.6,
                        rationale="This seems to be related to storage objects.",
                        alternatives_considered=[],  # No alternatives considered
                        suggestion="Default suggestion",
                    ),
                ],
                feedback="Default feedback",
            )

            # Create a prompt for the LLM
            prompt = dedent(
                "You are a personal digital archivist collaborating with a human user and a tool called "
                "Indaleko.  Together your goal is to help the human user find a specific storage object "
                "(typically a file) that is stored in a storage services.  Indaleko is an index of all this "
                "human user's storage services, with normalized data.  The human user has submitted a query "
                "and our third step in our collaborative process is to identify the ArangoDB collections "
                "that may be useful for evaluating this query against the schema of the collection. "
                "Indaleko is a unified personal index of storage services, and the collections include "
                "normalized metadata about storage objects, which are maintained across multiple "
                "disparate storage services, "
                "semantic information, which is derived from those storage objects, and activity information, which is "
                "derived from the user's experiential data, which we call activity data.  The goal is to weave "
                "our human user's episodic memories with this rich metadata to augment their ability "
                "to find specific "
                "storage objects.  The better we do this, the more efficient our user is, which satisfies "
                "our mutual utility "
                "functions. "
                f"Thus, broadly speaking the categories of collections correspond to {typical_categories}, though "
                "we suspect that more refined categories might be useful.  "
                f"The current data for the Indaleko ArangoDB collections is: {self.collection_data}\n"
                f"The current data schema for the response data is: {category_response.model_json_schema()}\n"
                "Since this is a collaboration between us, we value your feedback on this process, "
                "so that we can work together to improve the quality of the results. ",
            )

            # Use the LLM connector to get the categories
            response = self.llm_connector.answer_question(
                prompt,
                query,
                category_response.model_json_schema(),
            )
            doc = json.loads(response)

            # Validate and repair category response
            try:
                doc = self.validator.validate_and_repair_category_response(doc)
            except LLMResponseValidationError as e:
                logger.error(f"Category validation error: {e}")
                self.error_count["validation"] += 1
                self.error_count["category"] += 1
                self.error_count["total"] += 1
                self.error_log.append(
                    {
                        "timestamp": time.time(),
                        "query": query,
                        "stage": "category_validation",
                        "error": str(e),
                        "response": doc,
                    },
                )
                # Return default category response
                return category_response

            # Create category response object
            data = LLMCollectionCategoryQueryResponse(**doc)
            return data

        except Exception as e:
            logger.error(f"Error extracting categories: {e}")
            logger.debug(traceback.format_exc())
            self.error_count["category"] += 1
            self.error_count["total"] += 1
            self.error_log.append(
                {
                    "timestamp": time.time(),
                    "query": query,
                    "stage": "categories",
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                },
            )

            # Return default category response
            return LLMCollectionCategoryQueryResponse(
                category_map=[
                    LLMCollectionCategory(
                        category=LLMCollectionCategoryEnum.OBJECTS,
                        collection="Objects",
                        confidence=0.8,
                        rationale="Default fallback due to error",
                        alternatives_considered=[],
                    ),
                ],
                feedback="Error occurred during category processing. Using default.",
            )

    def _extract_entities(self, query: str) -> NamedEntityCollection:
        """
        Extract named entities from the query.

        Args:
            query: The user's query

        Returns:
            NamedEntityCollection: Extracted entities
        """
        try:
            logging.info(f"Extracting entities from query: {query}")

            # Define typical entity types
            typical_entities = [entity.value for entity in IndalekoNamedEntityType]

            # Create a prompt for the LLM
            prompt = dedent(
                "You are a personal digital archivist collaborating with a human user and a tool called "
                "Indaleko.  Together your goal is to help the human user find a specific storage object "
                "(typically a file) that is stored in a storage services.  Indaleko is an index of all this "
                "human user's storage services, with normalized data.  The human user has submitted a query "
                "and our second step in our collaboration is to extract possibly named entities from the user's "
                "query."
                f"The current typical kinds of entities are: {typical_entities}. "
                "In returning your response, please provide the entity names in the "
                "name field of the IndalekoNamedEntityCollection, along with the relevant category. "
                "The other fields should be left blank, as they will  be retrieved from the database "
                "if there is a matching named entity.  This can then be used for further processing of"
                "the user's query.  The schema of the IndalekoNamedEntityCollection is: "
                f"{example_entities.model_json_schema()}\n "
                "Since this is a collaboration between us, we value your feedback on this process, "
                "so that we can work together to improve the quality of the results.",
            )

            # Use the LLM connector to get the entities
            response = self.llm_connector.answer_question(
                prompt,
                query,
                example_entities.model_json_schema(),
            )
            doc = json.loads(response)

            # Validate and repair entities response
            try:
                doc = self.validator.validate_and_repair_entities_response(doc)
            except LLMResponseValidationError as e:
                logger.error(f"Entities validation error: {e}")
                self.error_count["validation"] += 1
                self.error_count["entities"] += 1
                self.error_count["total"] += 1
                self.error_log.append(
                    {
                        "timestamp": time.time(),
                        "query": query,
                        "stage": "entities_validation",
                        "error": str(e),
                        "response": doc,
                    },
                )
                # Create default entity
                entity = IndalekoNamedEntityDataModel(
                    name=query,
                    category=IndalekoNamedEntityType.item,
                    description=query,
                )
                return NamedEntityCollection(entities=[entity])

            # Create entity collection
            logging.info(ic(f"Extracted entities: {doc}"))
            return NamedEntityCollection(**doc)

        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            logger.debug(traceback.format_exc())
            self.error_count["entities"] += 1
            self.error_count["total"] += 1
            self.error_log.append(
                {
                    "timestamp": time.time(),
                    "query": query,
                    "stage": "entities",
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                },
            )

            # Create default entity
            entity = IndalekoNamedEntityDataModel(
                name=query,
                category=IndalekoNamedEntityType.item,
                description=query,
            )
            return NamedEntityCollection(entities=[entity])

    def get_error_stats(self) -> dict[str, Any]:
        """Get statistics about encountered errors."""
        return {
            "error_counts": self.error_count,
            "error_rate": (self.error_count["total"] / max(1, len(self.error_log)) if self.error_log else 0),
            "common_errors": self._analyze_common_errors(),
        }

    def _analyze_common_errors(self) -> list[dict[str, Any]]:
        """Analyze common error patterns in the error log."""
        if not self.error_log:
            return []

        # Group errors by type
        error_types = {}
        for error in self.error_log:
            error_type = error["error"]
            if error_type not in error_types:
                error_types[error_type] = {"count": 0, "samples": [], "stages": {}}

            error_types[error_type]["count"] += 1

            # Track which stage this error occurred in
            stage = error["stage"]
            if stage not in error_types[error_type]["stages"]:
                error_types[error_type]["stages"][stage] = 0
            error_types[error_type]["stages"][stage] += 1

            # Store sample queries (up to 3 per error type)
            if len(error_types[error_type]["samples"]) < 3:
                error_types[error_type]["samples"].append(error["query"])

        # Convert to a sorted list
        result = []
        for error_type, data in error_types.items():
            result.append(
                {
                    "error": error_type,
                    "count": data["count"],
                    "samples": data["samples"],
                    "stages": data["stages"],
                },
            )

        # Sort by count (most frequent first)
        result.sort(key=lambda x: x["count"], reverse=True)

        return result
