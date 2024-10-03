#!/usr/bin/env python3

from abc import ABC, abstractmethod
from typing import Dict, Any, List

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
        pass

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
    def extract_keywords(self, text: str, num_keywords: int = 5) -> List[str]:
        """
        Extract keywords from the given text.

        Args:
            text (str): The text to extract keywords from
            num_keywords (int): The number of keywords to extract

        Returns:
            List[str]: The extracted keywords
        """
        pass

    @abstractmethod
    def classify_text(self, text: str, categories: List[str]) -> str:
        """
        Classify the given text into one of the provided categories.

        Args:
            text (str): The text to classify
            categories (List[str]): The list of possible categories

        Returns:
            str: The predicted category
        """
        pass

    @abstractmethod
    def answer_question(self, context: str, question: str) -> str:
        """
        Answer a question based on the given context.

        Args:
            context (str): The context to base the answer on
            question (str): The question to answer

        Returns:
            str: The answer to the question
        """
        pass
