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

from typing import Dict, Any

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.query_processing.query_translator.translator_base import TranslatorBase
# pylint: enable=wrong-import-position


class AQLTranslator(TranslatorBase):
    """
    Translator for converting parsed queries to AQL (ArangoDB Query Language).
    """

    def translate(
            self,
            parsed_query: Dict[str, Any],
            selected_md_attributes: Dict[str, Any],
            additional_notes: str,
            n_truth: int,
            llm_connector: Any) -> str:
        """
        Translate a parsed query into an AQL query.

        Args:
            parsed_query (Dict[str, Any]): The parsed query from NLParser
            llm_connector (Any): Connector to the LLM service

        Returns:
            str: The translated AQL query
        """
        # Use the LLM to help generate the AQL query
        prompt = self._create_translation_prompt(parsed_query, selected_md_attributes, additional_notes, n_truth)
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
                ".Record" in query or ".SemanticAttributes" in
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
            self, parsed_query: Dict[str, Any],
            selected_md_attributes: Dict[str, Any],
            additional_notes: str,
            n_truth_md: int) -> str:
        """
        Create a prompt for the LLM to generate an AQL query.

        Args:
            parsed_query (Dict[str, Any]): The parsed query

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
            You should iterate through each context in ActivityContext and access the Record or SemanticAttributes
            as required. Do not use both collections in a single query. The query should return the entire object
            from the Record or ActivityContext collection.

            Important Instructions:
            If 'Activity' is specified in selected_md_attributes, search within the ActivityContext if not,
            search within Objects.

            In selected_md_attributes['Posix']:
                If "file.name" is specified, include it in the query as Attributes.Name.
                If file.size is specified, use Record.Attributes.st_size.
                If file.directory is specified, use the Path in Record.Attributes.Path.
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
            give aql: record.Record.Attributes.Name LIKE 'photo%.pdf' OR 'photo(%).pdf'; instead of
            record.Record.Attributes.Name LIKE 'photo.pdf'. If number of attributes is one, just use
            record.Record.Attributes.Name LIKE 'photo.pdf.
            When getting semantic attributes, retrieve the attribute via the dictionary attribute specified.
            All attributes are stored within list of attributes, the labels are the keys of the dictionary like
            'Text' or 'Type' and ther respective data are the values of the keys e.g., 'cats and dogs' is a datum
            for the key 'Text' and 'Title' a datum for the key 'Type'. Any text content is specified with 'Text'
            and 'Type' emphasizes what kind of text it is: ex.)
            {'Posix': {'file.name': {'pattern': 'essay', 'command': 'starts', 'extension': ['.txt']},
            'timestamps': {'modified': {'starttime': 1572505200.0, 'endtime': 1572505200.0, 'command': 'equal'}},
            'file.size': {'target_min': 7516192768, 'target_max': 7516192768, 'command': 'less_than'}},
            'Semantic': {'Content_1': {'Languages': 'str', 'Text': 'advancements in computer science'}}}
            then the Aql query would be: FOR record IN Objects FILTER record.Record.Attributes.Name LIKE
            'essay%.txt' AND TO_NUMBER(record.Record.Attributes.st_mtime) >= 1572505200.0 AND
            TO_NUMBER(record.Record.Attributes.st_mtime) <= 1572505200.0 AND
            record.Record.Attributes.st_size < 7516192768
            LET semanticTitle = FIRST(FOR attr IN record.SemanticAttributes
            FILTER attr.Identifier.Label == 'Text' RETURN attr.Data)
            FILTER semanticTitle == 'advancements in computer science'
            RETURN record.
            When comparing timestamps in the Record table, ensure that timestamps with a prefix of
            st_ are converted to number (use TO_NUMBER) When matching file names, names should have
            an extension at the end, so use 'LIKE' command not ==.
            Make sure to incorporate all attributes from the given dictionary into the aql statement.
            The query should only include the AQL code, without any additional explanations or comments.
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
