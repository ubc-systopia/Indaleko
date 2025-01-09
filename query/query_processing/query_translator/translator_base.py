
from abc import ABC, abstractmethod
from typing import Dict, Any

class TranslatorBase(ABC):
    """
    Abstract base class for query translators.
    """

    @abstractmethod
    def translate(self, parsed_query: Dict[str, Any], llm_connector: Any) -> str:
        """
        Translate a parsed query into a specific query language.

        Args:
            parsed_query (Dict[str, Any]): The parsed query from NLParser
            llm_connector (Any): Connector to the LLM service

        Returns:
            str: The translated query string
        """
        pass

    @abstractmethod
    def validate_query(self, query: str) -> bool:
        """
        Validate the translated query.

        Args:
            query (str): The translated query

        Returns:
            bool: True if the query is valid, False otherwise
        """
        pass

    @abstractmethod
    def optimize_query(self, query: str) -> str:
        """
        Optimize the translated query for better performance.

        Args:
            query (str): The translated query

        Returns:
            str: The optimized query
        """
        pass
