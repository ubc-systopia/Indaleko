"""
This module provides a CLI based interface for querying Indaleko.

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
from textwrap import dedent

from icecream import ic
from typing import Any

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.named_entity import IndalekoNamedEntityType, example_entities, NamedEntityCollection
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from query.query_processing.data_models.query_output import LLMIntentQueryResponse, \
    LLMFilterConstraintQueryResponse, LLMIntentTypeEnum, LLMCollectionCategoryQueryResponse, \
    LLMCollectionCategoryEnum, LLMCollectionCategory
from query.query_processing.data_models.parser_data import ParserResults
from query.utils.llm_connector.openai_connector import OpenAIConnector
# pylint: enable=wrong-import-position


class NLParser:
    """
    Natural Language Parser for processing user queries.
    """

    def __init__(
        self,
        llm_connector: OpenAIConnector,
        collections_metadata: IndalekoDBCollectionsMetadata
    ):
        '''
        Initialize the parser.

        Args:
            llm_connector (OpenAIConnector): The connector to the language model
            collections_metadata (IndalekoDBCollectionsMetadata): Metadata for the database collections

        The connector is used for communicating with the language model, and the collections_metadata
        is used for obtaining information about the shape of the database, which can be used to parse the query.
        '''
        # Initialize any necessary components or models
        self.llm_connector = llm_connector
        self.collections_metadata = collections_metadata
        self.collection_data = self.collections_metadata.get_all_collections_metadata()

    def parse(self, query: str) -> ParserResults:
        """
        Parse the natural language query into a structured format.

        Args:
            query (str): The user's natural language query

        Returns:
            dict[str, Any]: A structured representation of the query
        """
        logging.info(f"Parsing query: {query}")
        ic('Extracting categories from query')
        categories = self._extract_categories(query)
        ic('Determing intent of query')
        intent = self._detect_intent(query)
        ic('Extracting entities from query')
        entities = self._extract_entities(query)
        assert isinstance(query, str), f'query is unexpected type {type(query)}'
        assert isinstance(categories, LLMCollectionCategoryQueryResponse), \
            f'categories is unexpected type {type(categories)}'
        LLMCollectionCategoryQueryResponse.model_validate(categories)
        assert isinstance(intent, LLMIntentQueryResponse), f'intent is unexpected type {type(intent)}'
        LLMIntentQueryResponse.model_validate(intent)
        assert isinstance(entities, NamedEntityCollection), f'entities is unexpected type {type(entities)}'
        NamedEntityCollection.model_validate(entities)
        results = ParserResults(
            OriginalQuery=query,
            Categories=categories,
            Intent=intent,
            Entities=entities,
        )
        ParserResults.model_validate(results)
        return results

    def _detect_intent(self, query: str) -> LLMIntentQueryResponse:
        """
        Detect the primary intent of the query.

        Args:
            query (str): The user's query

        Returns:
            str: The detected intent
        """
        # Define typical intents for a storage search service
        typical_intents = [intent for intent in LLMIntentTypeEnum]

        # Extract the schema from the LLMIntentQueryResponse Pydantic class
        query_response = LLMIntentQueryResponse(
            intent="search",
            rationale="because this is a search tool, the default intent is search",
            alternatives_considered=[
                {"example": "this is an example, so it is static and nothing else was considered"}
            ],
            suggestion="No suggestions, this is an optimal process in my opinion"
            "Like Mary Poppins, practically perfect in every way. (laugh)",
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
            "ao that we can work together to improve the quality of the results."
        )
        logging.info(f"Detecting intent for query: {query}")

        # Use the LLM connector to get the intent
        response = self.llm_connector.answer_question(prompt, query, schema)
        doc = json.loads(response)
        data = LLMIntentQueryResponse(**doc)

        # Validate the intent
        if data.intent not in typical_intents:
            logging.warning(f"Unrecognized intent: {data.intent}")
            data.intent = "unknown"  # Default to "unknown" if the intent is not recognized
        logging.info(ic(f"Detected intent: {data.intent}"))
        return data

    def _extract_categories(self, query: str) -> LLMCollectionCategoryQueryResponse:
        """
        Using the collections in the database, identify which categories of information
        are likely to be useful for the query.

        Args:
            query (str): The user's query

        Returns:
            A list of dictionaries, each containing the category name,
            the database collection name, and a description of the collection.
        """
        # ic(self.collection_data)
        ic(type(self.collection_data['Objects']))

        category_response = LLMCollectionCategoryQueryResponse(
            category_map=[
                LLMCollectionCategory(
                    category=LLMCollectionCategoryEnum.OBJECTS,
                    collection=self.collection_data['Objects'].Name,
                    confidence=0.6,
                    rationale="This seems to be related to storage objects.",
                    alternatives_considered=[],  # No alternatives considered
                    suggestion=dedent(
                        "Where to begin?  This looks like nobody bothered to fill it in. I'll take a guess based upon "
                        "the intuition based upon the label: this is about storage objects, "
                        "like files and directories. "
                        "You know, given this is a collaboration, maybe you could do a better "
                        "job of not being lazy and "
                        "omitting these descriptions? Who am I to judge?  I'm just a computer program.  I don't have "
                        "feelings.  I'm just a bunch of code.  "
                    )
                ),
            ],
            feedback=dedent(
                "The query includes questions about the temperature in the room and the music playing, "
                "which are not represented by any of the activity collections.  You might want to consider adding "
                "activity data providers to gather that information and expose that information via activity "
                "collections. "),
        )

        # define existing category types
        typical_categories = [category.value for category in LLMCollectionCategoryEnum]
        ic(typical_categories)

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
            "ao that we can work together to improve the quality of the results. "
        )

        response = self.llm_connector.answer_question(prompt, query, category_response.model_json_schema())
        doc = json.loads(response)
        ic(doc)
        data = LLMCollectionCategoryQueryResponse(**doc)
        return data

    def _extract_entities(self, query: str) -> NamedEntityCollection:
        """
        Extract named entities from the query.

        Args:
            query (str): The user's query

        Returns:
            dict[str, Any]: Extracted entities
        """
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
            "ao that we can work together to improve the quality of the results."
        )
        logging.info(f"Extracting entities for query: {query}")

        # Use the LLM connector to get the entities
        response = self.llm_connector.answer_question(
            prompt,
            query,
            example_entities.model_json_schema()
        )
        entities = json.loads(response)
        logging.info(ic(f"Extracted entities: {entities}"))
        return NamedEntityCollection(**entities)

    def _extract_filters(self, query: str) -> dict[str, Any]:
        '''
        This is a dummy function that returns a hard-coded filter for now.
        '''
        return {}

    def _extract_filters2(self, query: str) -> dict[str, Any]:
        """
        Extract any filters or constraints from the query.

        Args:
            query (str): The user's query

        Returns:
            dict[str, Any]: Extracted filters
        """
        logging.info(f"Extracting filters from query: {query}")

        # Define typical filters and constraints
        typical_filters = ["name", "type", "size", "date", "location"]
        typical_constraints = ["before", "after", "between", "equals", "contains"]

        schema = LLMFilterConstraintQueryResponse(
            **LLMFilterConstraintQueryResponse.Config.json_schema_extra['example']).model_json_schema()
        # Create a prompt for the LLM
        prompt = (
            "You are a personal digital archivist helping this tool (Indaleko) assist a human user in finding "
            "specific information in their vast collection of personal files. We need to extract "
            "filters and constraints from the user's query to refine the search. "
            f"The current typical filters are: {typical_filters} and the typical constraints "
            f"are: {typical_constraints}. "
            "In returning your response, please provide the filters and constraints as a JSON "
            "structure with the following schema: "
            f"{schema}.\n"
        )
        logging.info(f"Extracting filters and constraints for query: {query}")

        # Use the LLM connector to get the filters and constraints
        response = self.llm_connector.answer_question(prompt, query, schema)
        filters_constraints = json.loads(response)

        # Validate the filters and constraints
        for filter_name, constraint in filters_constraints.items():
            if filter_name not in typical_filters:
                logging.warning(f"Unrecognized filter: {filter_name}")
            continue
            if constraint not in typical_constraints:
                logging.warning(f"Unrecognized constraint: {constraint}")
            continue

        logging.info(ic(f"Extracted filters and constraints: {filters_constraints}"))
        return filters_constraints
