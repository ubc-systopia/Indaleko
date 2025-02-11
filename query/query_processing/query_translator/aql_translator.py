"""
This module defines the AQL translator to use with an LLM.

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

from typing import Any

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db import IndalekoDBConfig
from query.query_processing.query_translator.translator_base import TranslatorBase
# pylint: enable=wrong-import-position


class AQLTranslator(TranslatorBase):
    """
    Translator for converting parsed queries to AQL (ArangoDB Query Language).
    """

    def translate(
            self,
            parsed_query: dict[str, Any],
            selected_md_attributes: dict[str, Any],
            additional_notes: str,
            n_truth: int,
            llm_connector: Any,
            db: IndalekoDBConfig = IndalekoDBConfig()
    ) -> str:
        """
        Translate a parsed query into an AQL query.

        Args:
            parsed_query (dict[str, Any]): The parsed query from NLParser
            llm_connector (Any): Connector to the LLM service

        Returns:
            str: The translated AQL query
        """
        # Use the LLM to help generate the AQL query
        prompt = self._create_translation_prompt2(parsed_query, selected_md_attributes, additional_notes, n_truth)
        aql_query = llm_connector.generate_query(prompt)

        ic('translate')
        aql_statement = aql_query.message.content
        assert self.validate_query(aql_statement), "Generated AQL query is invalid"
        aql_statement = aql_statement[aql_statement.index('FOR'):]  # trim preamble
        assert aql_statement.endswith('```'), "Code block not found at the end of the generated AQL query"
        aql_statement = aql_statement[:aql_statement.rindex('```')-1]  # trim postamble
        ic(aql_statement)
        return self.optimize_query(aql_statement)

    def validate_query(self, query: str) -> bool:
        """
        Validate the translated AQL query.

        Args:
            query (str): The translated AQL query

        Returns:
            bool: True if the query is valid, False otherwise
        """
        result = ("FOR" in query and "RETURN" in query) and (
                ".Size" in query or ".Label" in query or ".URI" in query or ".Timestamp" in query or
                ".Label" in query or ".SemanticAttributes" in
                query or ".Timestamp" in query or ".Size" in
                query or ".URI" in query)
        if not result:
            ic("Invalid AQL query:", query)
        return result

    def optimize_query(self, query: str) -> str:
        """
        Optimize the translated AQL query.

        Args:
            query (str): The translated AQL query

        Returns:
            str: The optimized AQL query
        """
        # Implement query optimization logic
        # This is a placeholder implementation
        return query

    def _create_translation_prompt(
            self,
            parsed_query: dict[str, Any],
            selected_md_attributes: dict[str, Any],
            additional_notes: str,
            n_truth_md: int) -> str:
        """
        Create a prompt for the LLM to generate an AQL query.

        Args:
            parsed_query (dict[str, Any]): The parsed query

        Returns:
            str: The prompt for the LLM
        """
        # Implement prompt creation logic
        system_prompt = """
            You are an assistant that generates ArangoDB queries for a Unified Personal Index (UPI) system.
            The UPI stores metadata about digital objects (e.g., files, directories) in an ArangoDB database.
            Given a user query and a dictionary called selected_md_attributes, generate the corresponding AQL
            query that retrieves matching information. The schema includes two main collections:

            ActivityContext: Stores metadata related to the context of activities. It includes the location field.
            Objects: Stores information about digital objects, such as files and directories.
            You should iterate through each context in ActivityContext and access the SemanticAttributes or relevant
            fields as required. Do not use both collections in a single query. The query should return the entire object
            from the Objects or ActivityContext collection.

            Important Instructions:
            If 'Activity' is specified in selected_md_attributes, search within the ActivityContext if not,
            search within Objects.

            In selected_md_attributes['Posix']:
                If "file.name" is specified, include it in the query as Label.
                If file.size is specified, use Size.
                If file.directory is specified, use the LocalPath.
                If "location" is specified in selected_md_attributes, include logic to filter paths based on:
                    "google_drive": /file/d/
                    "dropbox": /s/...?dl=0
                    "icloud": /iclouddrive/
                    "local": paths that contain the local_dir_name specified in selected_md_attributes.
            Do not include path filters in the query unless they are explicitly specified in the
            selected_md_attributes dictionary. The timestamp in geo_location is the time when the
            activity context was collected. The timestamp in the Posix is when the file was modified, changed,
            accessed or created; you don't have to convert the timestamps, just use the posix
            timestamp as is e.g.) when given {'Posix': {'timestamps': {'birthtime': {'starttime': 1736064000.0 ,
            'endtime': 1736064000.0 , 'command': 'equal'}}}, Activity': {geo_location: {'location': 'Victoria',
            'command': 'at', 'timestamp': 'birthtime'}} aql query is:
            FILTER TO_NUMBER(activity.Timestamp) == 1736064000.0
            To match coordinates, find SemanticAttributes with an Identifier.Label of "Longitude" and ensure
            the Data matches the given longitude, and similarly for latitude. Make sure to still check the
            activity.Record.Attributes for posix metadata as well (like name, path, timestamps, size, etc.)
            When command is "within", check that the coordinates are within the value specified in "km"
            relative to the given longitude and latitude coordinates.
            Only get semantic attributes if the 'Semantic' is populated.
            If the number of truth attributes is greater than one and in the dictionary, the file name command is
            'exactly' with a local directory specified, make sure to add % in command as there could be files with
            duplicate names in the same directory: {'Posix': {'file.name': {'pattern': 'photo', 'command': 'exactly',
            'extension': ['.jpg']}, 'file.directory': {'location': 'local', 'local_dir_name': 'photo'}}} should
            give aql: Label LIKE 'photo%.pdf' OR 'photo(%).pdf'; instead of
            Label LIKE 'photo.pdf'. If number of attributes is one, just use
            Label LIKE 'photo.pdf.
            When getting semantic attributes, retrieve the attribute via the dictionary attribute specified.
            All attributes are stored within list of attributes, the labels are the keys of the dictionary like
            'Text' or 'Type' and ther respective data are the values of the keys e.g., 'cats and dogs' is a datum
            for the key 'Text' and 'Title' a datum for the key 'Type'. Any text content is specified with 'Text'
            and 'Type' emphasizes what kind of text it is: ex.)
            {'Posix': {'file.name': {'pattern': 'essay', 'command': 'starts', 'extension': ['.txt']},
            'timestamps': {'modified': {'starttime': 1572505200.0, 'endtime': 1572505200.0, 'command': 'equal'}},
            'file.size': {'target_min': 7516192768, 'target_max': 7516192768, 'command': 'less_than'}},
            'Semantic': {'Content_1': {'Languages': 'str', 'Text': 'advancements in computer science'}}}
            then the Aql query would be: FOR record IN Objects FILTER record.Label LIKE
            'essay%.txt' AND TO_NUMBER(record.Record.Attributes.st_mtime) >= 1572505200.0 AND
            TO_NUMBER(record.Record.Attributes.st_mtime) <= 1572505200.0 AND
            record.Size < 7516192768
            LET semanticTitle = FIRST(FOR attr IN record.SemanticAttributes
            FILTER attr.Identifier.Label == 'Text' RETURN attr.Data)
            FILTER semanticTitle == 'advancements in computer science'
            RETURN record.
            When comparing timestamps in the Record table, ensure that timestamps with a prefix of
            st_ are converted to number (use TO_NUMBER) When matching file names, names should have
            an extension at the end, so use 'LIKE' command not ==.
            Make sure to incorporate all attributes from the given dictionary into the aql statement.
            The query should only include the AQL code, without any additional explanations or  comments.
            You must return one single code block enclosed in '```'s with only one FOR and RETURN statement.\n""" + \
            f"""
            Dictionary of attributes: {str(selected_md_attributes)}
            Number of truth attributes: {str(n_truth_md)}
            Additional Notes: {additional_notes}
            Schema: {str(parsed_query['schema'])}
            """

        user_prompt = parsed_query['original_query']

        return {
            'system': system_prompt,
            'user': user_prompt
        }

    def _generate_collection_mapping(
            self,
            db: IndalekoDBConfig = IndalekoDBConfig()
    ) -> dict[str, str]:
        """
        Dynamically generates a mapping of keywords to collections based on CollectionMetadata.

        Args:
            db: ArangoDB database connection.

        Returns:
            dict[str, str]: A mapping of keywords to their relevant collections.
        """
        collection_mapping = {}

        # Fetch all collection metadata from CollectionMetadata
        cursor = db.db_config.db.aql.execute("FOR doc IN CollectionMetadata RETURN doc")

        for doc in cursor:
            collection_name = doc["Name"]
            description = doc["Description"].lower()  # Normalize text for matching

            # Identify potential keywords for this collection
            keywords = set(description.split())  # Simple tokenization (can be improved)

            # Map each keyword to the collection
            for keyword in keywords:
                if keyword not in collection_mapping:
                    collection_mapping[keyword] = collection_name

        return collection_mapping

    def _determine_relevant_collections(
            self,
            parsed_query: dict[str, Any],
            selected_md_attributes: dict[str, Any],
            db: IndalekoDBConfig = IndalekoDBConfig()
    ) -> list[str]:
        """
        Dynamically determine the relevant collections based on the user query.

        Args:
            parsed_query (dict[str, Any]): The parsed user query.
            selected_md_attributes (dict[str, Any]): Extracted metadata attributes.
            db: ArangoDB database connection.

        Returns:
            List[str]: A list of relevant collections for AQL generation.
        """
        assert isinstance(db, IndalekoDBConfig), "Database connection must be an IndalekoDBConfig object"
        relevant_collections = set()

        # Step 1: Fetch dynamic keyword → collection mapping from CollectionMetadata
        collection_mapping = self._generate_collection_mapping(db)

        # Step 2: Extract keywords from user query
        user_query_text = parsed_query.get("original_query", "").lower().split()

        # Step 3: Identify collections based on static metadata
        for word in user_query_text:
            if word in collection_mapping:
                relevant_collections.add(collection_mapping[word])

        # Step 4: Identify if the query requires activity tracking
        needs_activity_data = any(
            keyword in user_query_text for keyword in [
                "edited",
                "viewed",
                "accessed",
                "created",
                "deleted",
                "location",
                "timestamp"]
            )

        if needs_activity_data:
            # Step 5: Query `ActivityDataProviders` to find available sources
            activity_providers = db.db_config.db.aql.execute(
                "FOR provider IN ActivityDataProviders RETURN provider.Name"
            )
            provider_collections = list(activity_providers)

            # Step 6: Add available provider collections to the relevant collections list
            relevant_collections.update(provider_collections)

            # Step 7: Ensure ActivityContext is included (acts as an index/cursor)
            relevant_collections.add("ActivityContext")

        return list(relevant_collections)

    def _create_translation_prompt2(
            self,
            parsed_query: dict[str, Any],
            selected_md_attributes: dict[str, Any],
            additional_notes: str,
            n_truth_md: int,) -> dict[str, str]:
        """
        Constructs a structured prompt for the LLM to generate an AQL query.
        """

        relevant_collections = self._determine_relevant_collections(parsed_query, selected_md_attributes)

        # Fetch schema details for relevant collections
        schema_descriptions = "\n".join([
            f"- **{col}**: {parsed_query['schema'][col]['description']}\n"
            f"  Indexed Fields: {', '.join(parsed_query['schema'][col].get('indexed_fields', []))}"
            for col in relevant_collections
        ])

        system_prompt = f"""
            You are an advanced ArangoDB query assistant, generating **optimized AQL queries**
            for a **Unified Personal Index (UPI)** system. Your goal is to **create the most efficient
            query possible**, prioritizing **indexed fields** and minimizing full scans.

            ### **Database Schema**
            The following collections are relevant for this query:
            {schema_descriptions}

            ### **Query Guidelines**
            - Prefer **indexed fields** in `FILTER` conditions.
            - Use **subqueries** when joining collections, but avoid joins if unnecessary.
            - Ensure **only one `FOR` statement** in the final AQL query.
            - If an attribute is missing an index, indicate this in the response.

            ### **User Query**
            "{parsed_query['original_query']}"

            ### **Expected Response Format**
            ```json
            {{
                "aql_query": "string",
                "rationale": "string",
                "alternatives_considered": [
                    {{
                        "query": "string",
                        "reason_for_rejection": "string"
                    }}
                ],
                "index_warnings": [
                    {{
                        "collection": "string",
                        "field": "string",
                        "recommendation": "string"
                    }}
                ]
            }}
            ```
            Please provide a **single JSON object** following this format.
        """

        return {
            'system': system_prompt,
            'user': parsed_query['original_query']
        }
