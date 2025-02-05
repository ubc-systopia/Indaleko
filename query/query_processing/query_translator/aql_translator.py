
from typing import Dict, Any
from .translator_base import TranslatorBase

from icecream import ic


class AQLTranslator(TranslatorBase):
    """
    Translator for converting parsed queries to AQL (ArangoDB Query Language).
    """

    def translate(self, parsed_query: Dict[str, Any], llm_connector: Any) -> str:
        """
        Translate a parsed query into an AQL query.

        Args:
            parsed_query (Dict[str, Any]): The parsed query from NLParser
            llm_connector (Any): Connector to the LLM service

        Returns:
            str: The translated AQL query
        """
        # Use the LLM to help generate the AQL query
        prompt = self._create_translation_prompt(parsed_query)
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

    def _create_translation_prompt(self, parsed_query: Dict[str, Any]) -> str:
        """
        Create a prompt for the LLM to generate an AQL query.

        Args:
            parsed_query (Dict[str, Any]): The parsed query

        Returns:
            str: The prompt for the LLM
        """
        # Implement prompt creation logic
        system_prompt = \
            f"""
            You are an assistant that generates ArangoDB queries for a Unified Personal
            Index (UPI) system. The UPI stores metadata about digital objects (e.g., files,
            directories) in an ArangoDB database. Given a user query, analyze it and
            generate only the corresponding AQL query that retrieves matching information.
            Do not include any explanations, comments, or additional text—return the AQL
            query alone. The structure of the data in the Objects collection
            is: {str(parsed_query['schema'])}.
            Do not use fields in the Record.Attributes portion of the various schema because they are not indexed
            and AQL queries using them will time out before a response is returned.
            """
        user_prompt = parsed_query['original_query']

        return {
            'system': system_prompt,
            'user': user_prompt
        }
