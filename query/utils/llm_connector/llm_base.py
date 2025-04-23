"""
Base classes for LLM connectors in the Indaleko system.

This module provides abstract base classes for various LLM connector implementations.

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

from abc import ABC, abstractmethod
from typing import Any


class LLMBase(ABC):
    """
    Abstract base class for LLM connectors.
    """

    @abstractmethod
    def generate_query(self, prompt: str) -> str:
        """
        Generate a query based on the given prompt.

        Args:
            prompt (str): The prompt to generate the query from

        Returns:
            str: The generated query
        """

    @abstractmethod
    def summarize_text(self, text: str, max_length: int = 100) -> str:
        """
        Summarize the given text.

        Args:
            text (str): The text to summarize
            max_length (int): The maximum length of the summary

        Returns:
            str: The summarized text
        """

    @abstractmethod
    def extract_keywords(self, text: str, num_keywords: int = 5) -> list[str]:
        """
        Extract keywords from the given text.

        Args:
            text (str): The text to extract keywords from
            num_keywords (int): The number of keywords to extract

        Returns:
            list[str]: The extracted keywords
        """

    @abstractmethod
    def classify_text(self, text: str, categories: list[str]) -> str:
        """
        Classify the given text into one of the provided categories.

        Args:
            text (str): The text to classify
            categories (list[str]): The list of possible categories

        Returns:
            str: The predicted category
        """

    @abstractmethod
    def answer_question(
        self, context: str, question: str, schema: dict[str, Any] | None = None,
    ) -> str:
        """
        Answer a question based on the given context.

        Args:
            context (str): The context to base the answer on
            question (str): The question to answer
            schema (Optional[Dict[str, Any]]): Optional schema for validating the response

        Returns:
            str: The answer to the question
        """


class IndalekoLLMBase(ABC):
    """
    Extended abstract base class for Indaleko LLM connectors with additional functionality.
    """

    @abstractmethod
    def get_completion(
        self, context: str, question: str, schema: dict[str, Any] | None = None,
    ) -> Any:
        """
        Get a completion from the LLM based on the given context and question.

        Args:
            context (str): The context for the completion
            question (str): The question or prompt to complete
            schema (Optional[Dict[str, Any]]): Optional schema for validating the response

        Returns:
            Any: The completion response object
        """

    @abstractmethod
    def answer_question(
        self, context: str, question: str, schema: dict[str, Any] | None = None,
    ) -> str:
        """
        Answer a question based on the given context.

        Args:
            context (str): The context to base the answer on
            question (str): The question to answer
            schema (Optional[Dict[str, Any]]): Optional schema for validating the response

        Returns:
            str: The answer to the question
        """

    @abstractmethod
    def generate_text(
        self, prompt: str, max_tokens: int = 500, temperature: float = 0.7,
    ) -> str:
        """
        Generate text based on the provided prompt.

        Args:
            prompt (str): The prompt for text generation
            max_tokens (int): Maximum number of tokens to generate
            temperature (float): Controls randomness of generation (0.0-1.0)

        Returns:
            str: The generated text
        """

    @abstractmethod
    def extract_semantic_attributes(
        self, text: str, attr_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Extract semantic attributes from text.

        Args:
            text (str): The text to extract attributes from
            attr_types (Optional[list[str]]): Types of attributes to extract

        Returns:
            Dict[str, Any]: Dictionary of extracted attributes
        """
