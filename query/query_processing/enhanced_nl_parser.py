"""
This module provides an enhanced natural language parser for Indaleko queries.

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
from typing import Any, Dict, List, Optional, Union

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.named_entity import (
    IndalekoNamedEntityType,
    NamedEntityCollection,
)
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from query.query_processing.data_models.parser_data import ParserResults
from query.query_processing.data_models.query_language_enhancer import (
    EnhancedQueryUnderstanding,
    EntityResolution,
    FacetSuggestion,
    QueryConstraint,
    QueryConstraintType,
    QueryContext,
    QueryIntent,
    QueryIntentType,
    RelationshipInfo,
    TimeConstraint,
)
from query.query_processing.data_models.query_output import (
    LLMCollectionCategoryEnum,
    LLMCollectionCategoryQueryResponse,
    LLMIntentQueryResponse,
    LLMIntentTypeEnum,
)
from query.query_processing.nl_parser import NLParser
from query.result_analysis.data_models.facet_data_model import DynamicFacets, Facet
from query.utils.llm_connector.openai_connector import OpenAIConnector
# pylint: enable=wrong-import-position


class EnhancedNLParser(NLParser):
    """
    Enhanced Natural Language Parser for processing user queries with improved understanding.
    
    This parser extends the base NLParser with additional capabilities:
    1. More detailed intent classification
    2. Entity resolution and linking
    3. Constraint extraction and normalization
    4. Integration with dynamic facets
    5. Relationship identification
    6. Temporal and spatial context extraction
    7. Conversational query understanding
    """

    def __init__(
        self,
        llm_connector: OpenAIConnector,
        collections_metadata: IndalekoDBCollectionsMetadata,
    ):
        """
        Initialize the enhanced parser.

        Args:
            llm_connector (OpenAIConnector): The connector to the language model
            collections_metadata (IndalekoDBCollectionsMetadata): Metadata for database collections
        """
        super().__init__(llm_connector, collections_metadata)
        self.query_history = []  # Store recent queries for context
        self.max_history_length = 5
        self.facet_context = None  # Store recent facet data for context
        
    def parse_enhanced(self, query: str, 
                       facet_context: Optional[DynamicFacets] = None, 
                       include_history: bool = True) -> EnhancedQueryUnderstanding:
        """
        Parse the natural language query into an enhanced structured format.

        Args:
            query (str): The user's natural language query
            facet_context (Optional[DynamicFacets]): Recent facet data for context-aware parsing
            include_history (bool): Whether to include query history in the context

        Returns:
            EnhancedQueryUnderstanding: A comprehensive structured representation of the query
        """
        logging.info(f"Enhanced parsing for query: {query}")
        
        # Store facet context for use in parsing
        self.facet_context = facet_context
        
        # Get basic parsing results first
        basic_results = self.parse(query)
        
        # Extract enhanced understanding with a more comprehensive prompt
        enhanced_understanding = self._extract_enhanced_understanding(
            query, basic_results, facet_context, include_history
        )
        
        # Add the query to history
        if include_history:
            self._update_query_history(query, enhanced_understanding)
            
        return enhanced_understanding
    
    def _extract_enhanced_understanding(
        self, 
        query: str, 
        basic_results: ParserResults,
        facet_context: Optional[DynamicFacets] = None,
        include_history: bool = True
    ) -> EnhancedQueryUnderstanding:
        """
        Extract enhanced understanding of the query using a more comprehensive approach.
        
        Args:
            query (str): The user's query
            basic_results (ParserResults): Basic parsing results
            facet_context (Optional[DynamicFacets]): Recent facet data for context
            include_history (bool): Whether to include query history
            
        Returns:
            EnhancedQueryUnderstanding: Comprehensive query understanding
        """
        # Prepare context information for the LLM
        context_data = {
            "basic_parse_results": basic_results.model_dump(),
            "collection_data": {name: metadata.model_dump() for name, metadata in self.collection_data.items()},
        }
        
        # Add facet context if available
        if facet_context:
            context_data["facet_context"] = facet_context.model_dump()
            
        # Add query history if available and requested
        if include_history and self.query_history:
            context_data["query_history"] = self.query_history
        
        # Create an example response
        example_response = EnhancedQueryUnderstanding(
            original_query="Find documents about climate change from last year",
            intent=QueryIntent(
                primary_intent=QueryIntentType.SEARCH,
                secondary_intents=[QueryIntentType.FILTER, QueryIntentType.TIMELINE],
                confidence=0.95,
                description="Find documents containing information about climate change that were created or modified during last year"
            ),
            entities=[
                EntityResolution(
                    original_text="climate change",
                    normalized_value="climate change",
                    entity_type="topic",
                    confidence=0.98,
                    resolved_entity=None
                ),
                EntityResolution(
                    original_text="last year",
                    normalized_value="2023-01-01 to 2023-12-31",
                    entity_type="time_period",
                    confidence=0.9,
                    resolved_entity=None
                )
            ],
            constraints=[
                QueryConstraint(
                    field="content",
                    operation=QueryConstraintType.CONTAINS,
                    value="climate change",
                    confidence=0.95
                ),
                QueryConstraint(
                    field="timestamp",
                    operation=QueryConstraintType.BETWEEN,
                    value={"start": "2023-01-01", "end": "2023-12-31"},
                    confidence=0.9
                )
            ],
            context=QueryContext(
                collections=["Objects", "SemanticData"],
                temporal_context=TimeConstraint(
                    start_time="2023-01-01",
                    end_time="2023-12-31",
                    time_field="timestamp"
                ),
                spatial_context=None,
                user_context=None,
                activity_context=None
            ),
            relationships=None,
            suggested_facets=[
                FacetSuggestion(
                    facet_name="file_type",
                    facet_description="Type of document (PDF, Word, etc.)",
                    relevance=0.8,
                    example_values=["PDF", "DOCX", "TXT"]
                ),
                FacetSuggestion(
                    facet_name="author",
                    facet_description="Author of the document",
                    relevance=0.7,
                    example_values=[]
                )
            ],
            refinement_suggestions=[
                "Try specifying a particular file type, like 'Find PDF documents about climate change from last year'",
                "You could narrow down by author, such as 'Find documents about climate change by IPCC from last year'"
            ],
            conversational_response="I'm looking for documents about climate change that were created or modified last year (2023). I can help you narrow this down by file type or author if needed.",
            confidence=0.92
        )
        
        # Create the prompt for the LLM
        system_prompt = dedent(f"""
        You are Archivist, an expert at analyzing natural language queries about digital objects stored within Indaleko, 
        a unified personal index system. Your task is to provide a comprehensive, structured understanding of user queries 
        related to file search and analysis.
        
        Parse the user's query and return a detailed JSON structure matching the EnhancedQueryUnderstanding schema. Your 
        goal is to extract all relevant information, from intent to constraints, to produce an accurate and comprehensive 
        representation of what the user is looking for.
        
        Pay special attention to:
        1. Identifying the primary and secondary intents
        2. Extracting and normalizing entities (people, locations, dates, etc.)
        3. Identifying query constraints and their types
        4. Determining which collections are relevant
        5. Understanding temporal and spatial context
        6. Detecting relationships between entities
        7. Suggesting relevant facets for further exploration
        8. Proposing query refinements for better results
        9. Providing a natural language explanation of your understanding
        
        Make sure you use the appropriate fields and formats from the schema.
        
        Context Data:
        {json.dumps(context_data, indent=2)}
        
        Remember to identify highly relevant facets based on the query context.
        """)
        
        user_prompt = f"Analyze this query: '{query}'"
        schema = example_response.model_json_schema()
        
        # Use the LLM connector to get enhanced understanding
        response = self.llm_connector.get_completion(
            context=system_prompt,
            question=user_prompt,
            schema=schema
        )
        
        # Parse the response
        response_data = json.loads(response.choices[0].message.content)
        enhanced_understanding = EnhancedQueryUnderstanding(**response_data)
        
        return enhanced_understanding

    def _update_query_history(self, query: str, understanding: EnhancedQueryUnderstanding) -> None:
        """
        Update the query history with the latest query and its understanding.
        
        Args:
            query (str): The user's query
            understanding (EnhancedQueryUnderstanding): The parsed understanding
        """
        # Create a simplified history entry
        history_entry = {
            "query": query,
            "intent": understanding.intent.primary_intent,
            "constraints": [
                {"field": c.field, "operation": c.operation, "value": c.value}
                for c in understanding.constraints
            ],
            "timestamp": "now"  # In a real implementation, use actual timestamp
        }
        
        # Add to history and maintain max length
        self.query_history.append(history_entry)
        if len(self.query_history) > self.max_history_length:
            self.query_history.pop(0)