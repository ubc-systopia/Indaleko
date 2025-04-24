"""
This module defines the base data model for LLM connectors.

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
from abc import ABC, abstractmethod

# from icecream import ic
from typing import Any

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.query_processing.data_models.query_output import LLMTranslateQueryResponse

# pylint: enable=wrong-import-position


class IndalekoLLMBase(ABC):
    """
    Abstract base class for LLM connectors.
    """

    @abstractmethod
    def get_llm_name(self) -> str:
        """
        Get the name of the LLM.

        Returns:
            str: The name of the LLM
        """

    @abstractmethod
    def generate_query(self, prompt: str) -> LLMTranslateQueryResponse:
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
            List[str]: The extracted keywords
        """

    @abstractmethod
    def classify_text(self, text: str, categories: list[str]) -> str:
        """
        Classify the given text into one of the provided categories.

        Args:
            text (str): The text to classify
            categories (List[str]): The list of possible categories

        Returns:
            str: The predicted category
        """

    @abstractmethod
    def answer_question(
        self,
        context: str,
        question: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Answer a question based on the given context.

        Args:
            context (str): The context to base the answer on
            question (str): The question to answer
            schema (dict[str, Any]): The schema for the response

        Returns:
            str: The answer to the question
        """

    @abstractmethod
    def get_completion(self, context: str, question: str, schema: Any) -> Any:
        """
        Get a completion based on the given context.

        Args:
            context (str): The context to base the completion on
            question (str): The question to answer
            schema (Any): The schema (or a model) for the response

        Returns:
            Any: The completion

        Note: This method allows returning extended information
        from the LLM, but requires the caller understand the explicit
        format of the response, which does obviate the point of this
        abstraction layer somewhat.
        """
