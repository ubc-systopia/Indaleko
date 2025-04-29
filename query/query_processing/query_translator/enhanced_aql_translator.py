"""
This module defines an enhanced AQL translator for improved natural language query handling.

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
from typing import Any

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from query.query_processing.data_models.query_language_enhancer import (
    EnhancedQueryUnderstanding,
    QueryConstraint,
    QueryConstraintType,
)
from query.query_processing.data_models.translator_input import TranslatorInput
from query.query_processing.data_models.translator_response import TranslatorOutput
from query.query_processing.query_translator.aql_translator import AQLTranslator
from query.search_execution.data_models.query_execution_plan import QueryPerformanceHint

# pylint: enable=wrong-import-position


class EnhancedAQLTranslator(AQLTranslator):
    """
    Enhanced translator for converting NL parser results to AQL with improved capabilities.

    This translator extends the base AQLTranslator with additional capabilities:
    1. Direct handling of EnhancedQueryUnderstanding data model
    2. More sophisticated constraint handling
    3. Support for complex temporal and spatial queries
    4. Relationship-aware query generation
    5. Integration with dynamic facets
    6. Performance optimization hints
    7. Improved bind variable handling
    """

    def __init__(self, collections_metadata: IndalekoDBCollectionsMetadata):
        """
        Initialize the enhanced AQL translator.

        Args:
            collections_metadata: Metadata for collections in the database.
        """
        super().__init__(collections_metadata)
        self.performance_hints = []

    def translate_enhanced(
        self,
        enhanced_understanding: EnhancedQueryUnderstanding,
        input_data: TranslatorInput,
    ) -> TranslatorOutput:
        """
        Translate an enhanced query understanding directly to AQL.

        Args:
            enhanced_understanding: The enhanced query understanding from EnhancedNLParser
            input_data: The original translator input

        Returns:
            TranslatorOutput: The translated AQL query and metadata
        """
        # Create a comprehensive context for the LLM
        input_context = {
            "enhanced_query": enhanced_understanding.model_dump(),
            "db_collections": {name: meta.model_dump() for name, meta in self.collection_data.items()},
        }

        # Add collection indices for optimization
        collection_indices = {}
        for category in enhanced_understanding.context.collections:
            try:
                collection_indices[category] = []
                if category in self.db_config.db.collections():
                    indices = self.db_config.db.collection(category).indexes()
                    for index in indices:
                        if index["type"] != "primary":
                            collection_indices[category].append(index)
            except Exception as e:
                logging.warning(
                    f"Error retrieving indices for collection {category}: {e}",
                )

        input_context["collection_indices"] = collection_indices

        # Generate performance hints based on the query
        self.performance_hints = self._generate_performance_hints(
            enhanced_understanding,
        )
        input_context["performance_hints"] = [hint.model_dump() for hint in self.performance_hints]

        # Create the prompt for the LLM
        system_prompt = self._create_enhanced_translation_prompt(
            enhanced_understanding,
            input_context,
        )

        user_prompt = f"Generate an optimized AQL query for: '{enhanced_understanding.original_query}'"

        # Use the LLM to generate the AQL query
        completion = input_data.Connector.get_completion(
            context=system_prompt,
            question=user_prompt,
            schema=TranslatorOutput.model_json_schema(),
        )

        # Process and validate the response
        performance_data = json.loads(completion.usage.model_dump_json())
        response_data = json.loads(completion.choices[0].message.content)

        # Create the translator output
        translator_output = TranslatorOutput(
            aql_query=response_data["aql_query"],
            explanation=response_data["explanation"],
            confidence=response_data["confidence"],
            observations=response_data.get("observations", None),
            performance_info=performance_data,
            bind_vars=response_data.get("bind_vars", {}),
            additional_notes=response_data.get("additional_notes", None),
        )

        # Validate the query (basic validation from the parent class)
        if not self.validate_query(translator_output.aql_query, explain=True):
            logging.warning("Generated AQL query failed validation")
            translator_output.confidence *= 0.7  # Reduce confidence if validation fails
            translator_output.observations = (
                translator_output.observations or ""
            ) + "\nWarning: Query failed basic validation."

        return translator_output

    def _create_enhanced_translation_prompt(
        self,
        enhanced_understanding: EnhancedQueryUnderstanding,
        context_data: dict[str, Any],
    ) -> str:
        """
        Create an enhanced prompt for the LLM to generate a more sophisticated AQL query.

        Args:
            enhanced_understanding: The enhanced query understanding
            context_data: Additional context for the LLM

        Returns:
            str: The system prompt for the LLM
        """
        # Extract the collections from the enhanced understanding
        collections = enhanced_understanding.context.collections

        # Format collections for display
        collection_info = []
        for collection in collections:
            if collection in self.collection_data:
                meta = self.collection_data[collection]
                collection_info.append(f"- {collection}: {meta.Description}")
            else:
                collection_info.append(f"- {collection}: (No metadata available)")

        collection_info_text = "\n".join(collection_info)

        # Get view information
        view_info = []
        try:
            if hasattr(self.db_config, "db"):
                db_views = self.db_config.db.views()

                # Add information about views
                if "ObjectsTextView" in db_views:
                    view_info.append(
                        "- ObjectsTextView: Text search for Objects collection fields (Label, Record.Attributes.URI, Record.Attributes.Description, Tags)",
                    )

                if "NamedEntityTextView" in db_views:
                    view_info.append(
                        "- NamedEntityTextView: Text search for NamedEntities collection fields (name, description, address, tags)",
                    )

                if "ActivityTextView" in db_views:
                    view_info.append(
                        "- ActivityTextView: Text search for ActivityContext collection fields (Description, Location, Notes, Tags)",
                    )

                if "EntityEquivalenceTextView" in db_views:
                    view_info.append(
                        "- EntityEquivalenceTextView: Text search for EntityEquivalenceNodes collection fields (name, context)",
                    )

                if "KnowledgeTextView" in db_views:
                    view_info.append(
                        "- KnowledgeTextView: Text search for LearningEvents collection fields (content, source, metadata)",
                    )
        except Exception as e:
            logging.warning(f"Error getting views: {e}")

        view_info_text = "\n".join(view_info) if view_info else "No views available"

        # Create collection to view mapping for text search
        collection_view_mapping = {
            "Objects": "ObjectsTextView",
            "NamedEntities": "NamedEntityTextView",
            "ActivityContext": "ActivityTextView",
            "EntityEquivalenceNodes": "EntityEquivalenceTextView",
            "LearningEvents": "KnowledgeTextView",
        }

        # Determine if this query should use text search views
        is_text_search = False
        text_search_fields = []

        # Check if this is likely a text search query
        for constraint in enhanced_understanding.constraints:
            if constraint.operation in [
                "CONTAINS",
                "STARTS_WITH",
                "ENDS_WITH",
                "SIMILAR_TO",
            ]:
                is_text_search = True
                text_search_fields.append(constraint.field)

        # Also check intent and explicit keywords
        text_search_keywords = ["search", "find", "text", "contain", "like"]
        if enhanced_understanding.intent.primary_intent == "SEARCH":
            is_text_search = True

        query_text = enhanced_understanding.original_query.lower()
        if any(keyword in query_text for keyword in text_search_keywords):
            is_text_search = True

        # Determine which views should be used
        recommended_views = []
        for collection in collections:
            if collection in collection_view_mapping:
                view_name = collection_view_mapping[collection]
                if view_name not in recommended_views:
                    recommended_views.append(view_name)

        # Create the system prompt
        system_prompt = f"""
        You are **Archivist Query Generator**, an expert at translating natural language queries into
        ArangoDB Query Language (AQL) for the Indaleko unified personal index system.

        Your task is to generate an optimized AQL query based on the enhanced query understanding provided.
        The system has analyzed the user's query with an EnhancedNLParser and produced a structured representation
        of their intent, constraints, and context.

        The query should be constructed to search across the following collections:
        {collection_info_text}

        IMPORTANT: ArangoDB Views for Text Search
        The database has the following ArangoSearch views available for optimized text search:
        {view_info_text}

        For any text search operation (CONTAINS, STARTS_WITH, LIKE, etc.), you MUST use these views
        rather than filtering directly on collections. When using a view:
        1. Replace the collection name with the view name in the FOR statement
        2. Use SEARCH ANALYZER() instead of FILTER
        3. Use BM25() for sorting results by relevance

        Collection to View mapping for text search:
        - Objects → ObjectsTextView
        - NamedEntities → NamedEntityTextView
        - ActivityContext → ActivityTextView
        - EntityEquivalenceNodes → EntityEquivalenceTextView
        - LearningEvents → KnowledgeTextView

        The primary intent is: {enhanced_understanding.intent.primary_intent}
        Secondary intents: {enhanced_understanding.intent.secondary_intents}

        Please generate an optimized AQL query that:
        1. Searches the relevant collections based on the provided constraints
        2. Uses appropriate bind variables for all dynamic values
        3. Applies any temporal or spatial filters correctly
        4. Handles relationship queries if requested
        5. Returns complete objects with all required fields
        6. Uses indexes where available to optimize performance
        7. Uses ArangoSearch views for text search operations

        Collection Schema Information:
        - 'Objects' collection contains file metadata with fields like Label (filename),
          Path, Size, Timestamp, and SemanticAttributes
        - 'SemanticData' collection contains extracted content data with fields like
          ObjectId, Type, Data, and Confidence
        - 'ActivityContext' collection contains user activity data with fields like
          Timestamp, Action, ObjectId, and Location

        Use bind variables extensively to prevent query injection and improve performance.
        For example, use @value instead of directly embedding values in the query.

        For temporal queries, make sure to handle timestamp conversions properly.
        For spatial queries, consider using GeoJSON functions if appropriate.

        Include all fields necessary for the query to work, especially:
        - Query bind variables
        - Complete and valid AQL syntax
        - Appropriate collection access
        - Proper filtering conditions
        - Correct return structure

        Enhanced Query Understanding:
        {json.dumps(enhanced_understanding.model_dump(), indent=2)}

        IMPORTANT: The query must be syntactically correct AQL, ready to execute
        against an ArangoDB database without modification.

        Examples of proper view usage for text search:

        Example 1 - Search for files by name:
        ```aql
        FOR doc IN ObjectsTextView
        SEARCH ANALYZER(
            LIKE(doc.Label, @searchTerm),
            "text_en"
        )
        SORT BM25(doc) DESC
        LIMIT 50
        RETURN doc
        ```

        Example 2 - Search for files with multiple conditions:
        ```aql
        FOR doc IN ObjectsTextView
        SEARCH ANALYZER(
            LIKE(doc.Label, @namePattern) OR
            LIKE(doc.Record.Attributes.URI, @pathPattern) OR
            LIKE(doc.Record.Attributes.Description, @descPattern),
            "text_en"
        )
        FILTER doc.Size > @minSize
        SORT BM25(doc) DESC
        LIMIT 30
        RETURN doc
        ```

        Example 3 - Search for activities:
        ```aql
        FOR doc IN ActivityTextView
        SEARCH ANALYZER(
            LIKE(doc.Description, @searchTerm) OR
            LIKE(doc.Location, @searchTerm),
            "text_en"
        )
        FILTER TO_NUMBER(doc.Timestamp) > @startTime
        SORT BM25(doc) DESC
        LIMIT 20
        RETURN doc
        ```
        """

        # Add text search specific recommendations if this is a text search query
        if is_text_search:
            view_recommendations = "Based on the query intent and constraints, this appears to be a TEXT SEARCH query."
            if recommended_views:
                view_recommendations += f" You should use one of these views: {', '.join(recommended_views)}"
            if text_search_fields:
                view_recommendations += f" The query is searching these fields: {', '.join(text_search_fields)}"

            system_prompt += f"\n\nRECOMMENDATION: {view_recommendations}\n"

        return system_prompt

    def _generate_performance_hints(
        self,
        enhanced_understanding: EnhancedQueryUnderstanding,
    ) -> list[QueryPerformanceHint]:
        """
        Generate performance hints based on the query understanding.

        Args:
            enhanced_understanding: The enhanced query understanding

        Returns:
            List[QueryPerformanceHint]: Performance optimization hints for the query
        """
        hints = []

        # Analyze the collections and constraints to suggest performance optimizations
        collections = enhanced_understanding.context.collections
        constraints = enhanced_understanding.constraints

        # Check for field constraints that might benefit from indexing
        indexed_fields = {}
        for collection in collections:
            if collection in self.db_config.db.collections():
                indices = self.db_config.db.collection(collection).indexes()
                for index in indices:
                    if index["type"] != "primary":
                        for field in index["fields"]:
                            if collection not in indexed_fields:
                                indexed_fields[collection] = set()
                            indexed_fields[collection].add(field)

        # Check for text search operations that should use views
        has_text_search = False
        text_search_fields = []
        text_search_operations = ["CONTAINS", "STARTS_WITH", "ENDS_WITH", "SIMILAR_TO"]

        # Get available views
        available_views = {}
        try:
            if hasattr(self.db_config, "db"):
                db_views = self.db_config.db.views()
                for view in db_views:
                    available_views[view] = True
        except Exception:
            # Default views if we can't access the database
            available_views = {
                "ObjectsTextView": True,
                "NamedEntityTextView": True,
                "ActivityTextView": True,
                "EntityEquivalenceTextView": True,
                "KnowledgeTextView": True,
            }

        # Create collection to view mapping for text search
        collection_view_mapping = {
            "Objects": "ObjectsTextView",
            "NamedEntities": "NamedEntityTextView",
            "ActivityContext": "ActivityTextView",
            "EntityEquivalenceNodes": "EntityEquivalenceTextView",
            "LearningEvents": "KnowledgeTextView",
        }

        # Check if constraints use indexed fields
        for constraint in constraints:
            # Check for text search operations
            if constraint.operation in text_search_operations:
                has_text_search = True
                text_search_fields.append(constraint.field)

                # Determine which collection this field belongs to
                field_collection = None
                for collection in collections:
                    if collection in self.collection_data:
                        # Check if field is in this collection's schema
                        # This is a simplistic check - in a real implementation, you'd check the schema properly
                        if constraint.field in [
                            "Label",
                            "Name",
                            "Description",
                            "Content",
                            "Tags",
                        ]:
                            field_collection = collection
                            break

                # If we identified a collection and there's a view for it, suggest using it
                if field_collection and field_collection in collection_view_mapping:
                    view_name = collection_view_mapping[field_collection]
                    if view_name in available_views:
                        hints.append(
                            QueryPerformanceHint(
                                hint_type="view_usage",
                                description=f"Text search on field '{constraint.field}' should use the '{view_name}' view",
                                severity="info",
                                affected_component=f"{field_collection}.{constraint.field}",
                                performance_impact="positive",
                                recommendation=f"Use '{view_name}' with SEARCH ANALYZER instead of filtering {field_collection} directly",
                            ),
                        )

            # Check for indexed fields (for non-text search operations)
            found_index = False
            for collection in collections:
                if collection in indexed_fields and constraint.field in indexed_fields[collection]:
                    found_index = True
                    hints.append(
                        QueryPerformanceHint(
                            hint_type="index_usage",
                            description=f"Field '{constraint.field}' is indexed in collection '{collection}' and can be used to optimize the query",
                            severity="info",
                            affected_component=f"{collection}.{constraint.field}",
                            performance_impact="positive",
                            recommendation=None,
                        ),
                    )

            if not found_index and constraint.operation not in text_search_operations:
                # Suggest creating an index for frequently queried fields (except text search fields which should use views)
                hints.append(
                    QueryPerformanceHint(
                        hint_type="missing_index",
                        description=f"Field '{constraint.field}' is not indexed in any of the target collections",
                        severity="warning",
                        affected_component=f"{', '.join(collections)}.{constraint.field}",
                        performance_impact="negative",
                        recommendation=f"Consider creating an index on '{constraint.field}' if this query is run frequently",
                    ),
                )

        # Add a general view usage hint if this is a text search but we didn't find specific fields
        if has_text_search:
            for collection in collections:
                if collection in collection_view_mapping:
                    view_name = collection_view_mapping[collection]
                    if view_name in available_views:
                        # Only add if we haven't already added a specific hint for this view
                        if not any(h.hint_type == "view_usage" and view_name in h.description for h in hints):
                            hints.append(
                                QueryPerformanceHint(
                                    hint_type="view_usage",
                                    description=f"This query involves text search and should use the '{view_name}' view",
                                    severity="info",
                                    affected_component=collection,
                                    performance_impact="positive",
                                    recommendation=f"Use '{view_name}' with SEARCH ANALYZER for better text search performance",
                                ),
                            )

        # Check for full collection scans
        if len(constraints) == 0:
            hints.append(
                QueryPerformanceHint(
                    hint_type="full_scan",
                    description="Query has no constraints, which may result in a full collection scan",
                    severity="warning",
                    affected_component=", ".join(collections),
                    performance_impact="negative",
                    recommendation="Add constraints to limit the results or ensure appropriate indexing",
                ),
            )

        # Check for complex joins
        if len(collections) > 1:
            hints.append(
                QueryPerformanceHint(
                    hint_type="join_complexity",
                    description=f"Query involves {len(collections)} collections, which may require complex joins",
                    severity="info",
                    affected_component=", ".join(collections),
                    performance_impact="neutral",
                    recommendation="Ensure join conditions are indexed and consider pagination for large result sets",
                ),
            )

        # Suggest using BM25 for sorting results of text searches
        if has_text_search:
            for collection in collections:
                if collection in collection_view_mapping:
                    view_name = collection_view_mapping[collection]
                    if view_name in available_views:
                        hints.append(
                            QueryPerformanceHint(
                                hint_type="sorting",
                                description="Text search results should be sorted by relevance",
                                severity="info",
                                affected_component=view_name,
                                performance_impact="positive",
                                recommendation="Use 'SORT BM25(doc) DESC' when using ArangoSearch views",
                            ),
                        )
                        break  # Only add this hint once

        return hints

    def _map_constraint_to_aql(
        self,
        constraint: QueryConstraint,
        collection: str,
    ) -> tuple[str, dict[str, Any]]:
        """
        Map a query constraint to AQL filter syntax with bind variables.

        Args:
            constraint: The query constraint
            collection: The collection to apply the constraint to

        Returns:
            Tuple[str, Dict[str, Any]]: The AQL filter expression and bind variables
        """
        field = constraint.field
        operation = constraint.operation
        value = constraint.value
        bind_var_name = f"{field}_{operation}".replace(".", "_")
        bind_vars = {}

        # Map the constraint operation to AQL syntax
        if operation == QueryConstraintType.EQUALS:
            aql = f"doc.{field} == @{bind_var_name}"
            bind_vars[bind_var_name] = value

        elif operation == QueryConstraintType.CONTAINS:
            aql = f"CONTAINS(doc.{field}, @{bind_var_name})"
            bind_vars[bind_var_name] = value

        elif operation == QueryConstraintType.STARTS_WITH:
            aql = f"STARTS_WITH(doc.{field}, @{bind_var_name})"
            bind_vars[bind_var_name] = value

        elif operation == QueryConstraintType.ENDS_WITH:
            aql = f"ENDS_WITH(doc.{field}, @{bind_var_name})"
            bind_vars[bind_var_name] = value

        elif operation == QueryConstraintType.GREATER_THAN:
            aql = f"doc.{field} > @{bind_var_name}"
            bind_vars[bind_var_name] = value

        elif operation == QueryConstraintType.LESS_THAN:
            aql = f"doc.{field} < @{bind_var_name}"
            bind_vars[bind_var_name] = value

        elif operation == QueryConstraintType.BETWEEN:
            aql = f"doc.{field} >= @{bind_var_name}_start AND doc.{field} <= @{bind_var_name}_end"
            bind_vars[f"{bind_var_name}_start"] = value["start"]
            bind_vars[f"{bind_var_name}_end"] = value["end"]

        elif operation == QueryConstraintType.IN:
            aql = f"doc.{field} IN @{bind_var_name}"
            bind_vars[bind_var_name] = value

        elif operation == QueryConstraintType.SIMILAR_TO:
            # Use ArangoDB's similarity functions if available
            aql = f"LEVENSHTEIN_MATCH(doc.{field}, @{bind_var_name}, 0.6, true)"
            bind_vars[bind_var_name] = value

        else:
            # Default case for unsupported operations
            aql = f"doc.{field} == @{bind_var_name}"
            bind_vars[bind_var_name] = value
            logging.warning(f"Unsupported constraint operation: {operation}")

        return aql, bind_vars
