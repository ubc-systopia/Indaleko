#!/usr/bin/env python3

from typing import Dict, Any
from .translator_base import TranslatorBase

from icecream import ic

class AQLTranslator(TranslatorBase):
    """
    Translator for converting parsed queries to AQL (ArangoDB Query Language).
    """

    def translate(self, parsed_query: Dict[str, Any], selected_md_attributes: Dict[str, Any], additional_notes: str, llm_connector: Any) -> str:
        """
        Translate a parsed query into an AQL query.

        Args:
            parsed_query (Dict[str, Any]): The parsed query from NLParser
            llm_connector (Any): Connector to the LLM service

        Returns:
            str: The translated AQL query
        """
        # Use the LLM to help generate the AQL query
        prompt = self._create_translation_prompt(parsed_query, selected_md_attributes, additional_notes)
        aql_query = llm_connector.generate_query(prompt)

        ic('translate')
        aql_statement = aql_query.message.content
        assert self.validate_query(aql_statement), "Generated AQL query is invalid"
        aql_statement = aql_statement[aql_statement.index('FOR'):] # trim preamble
        assert aql_statement.endswith('```'), "Code block not found at the end of the generated AQL query"
        aql_statement = aql_statement[:aql_statement.rindex('```')-1] # trim postamble
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
        # Implement AQL validation logic
        # This is a placeholder implementation
        return "FOR" in query and "RETURN" in query


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

    def _create_translation_prompt(self, parsed_query: Dict[str, Any], selected_md_attributes:Dict[str, Any], additional_notes: str) -> str:
        """
        Create a prompt for the LLM to generate an AQL query.

        Args:
            parsed_query (Dict[str, Any]): The parsed query

        Returns:
            str: The prompt for the LLM
        """
        # Implement prompt creation logic
        system_prompt = """
            You are an assistant that generates ArangoDB queries for a Unified Personal Index (UPI) system. The UPI stores metadata about digital objects (e.g., files, directories) in an ArangoDB database. Given a user query and a dictionary called selected_md_attributes, generate the corresponding AQL query that retrieves matching information.
            The schema includes two main collections:

            ActivityContext: Stores metadata related to the context of activities. It includes the location field.
            Objects: Stores information about digital objects, such as files and directories.
            You should iterate through each context in ActivityContext and access the Record or SemanticAttributes as required. Do not use both collections in a single query. The query should return the entire object from the Record or ActivityContext collection.

            Important Instructions:

            If "file.name" is specified in selected_md_attributes, include it in the query as Attributes.Name.
            If file.size is specified, use Record.Attributes.st_size.
            If file.directory is specified, use the Path in Record.Attributes.Path.
            If "location" is specified in selected_md_attributes, include logic to filter paths based on:
                "google_drive": /file/d/
                "dropbox": /s/...?dl=0
                "icloud": /iclouddrive/
                "local": paths that contain the local_dir_name specified in selected_md_attributes.
            Do not include path filters in the query unless they are explicitly specified in the selected_md_attributes dictionary.
            To match coordinates, find SemanticAttributes with an Identifier.Label of "Longitude" and ensure the Data matches the given longitude, and similarly for latitude. 
            When command is "within", check that the coordinates are within the value specified in "km" relative to the given longitude and latitude. e.g. FOR record IN ActivityContext FILTER TO_NUMBER(record.Record.Attributes.st_mtime) >= 1572566400 AND TO_NUMBER(record.Record.Attributes.st_mtime) <= 1573689599 LET longitude = FIRST(FOR attr IN record.SemanticAttributes FILTER attr.Identifier.Label == 'Longitude' RETURN attr.Data) LET latitude = FIRST(FOR attr IN record.SemanticAttributes FILTER attr.Identifier.Label == 'Latitude' RETURN attr.Data) FILTER longitude >= -123.113952 - 0.072 && longitude <= -123.113952 + 0.072 FILTER latitude >= 49.2608724 - 0.072 && latitude <= 49.2608724 + 0.072 RETURN record
            When comparing timestamps in the Record table, ensure that timestamps with a prefix of st_ are converted to number (use TO_NUMBER).
            Do not use DATE_TIMESTAMP() for converting timestamps in the dictionary; instead, compute the Unix timestamp value and include it directly in the AQL query.
            The query should only include the AQL code, without any additional explanations or comments. Return a code block.\n""" + \
            "Dictionary of attributes:" + str(selected_md_attributes) + "\n Additional Notes: " + additional_notes + "\n Schema:" + str(parsed_query['schema'])

        user_prompt = parsed_query['original_query']

        return {
            'system' : system_prompt,
            'user' : user_prompt
        }


