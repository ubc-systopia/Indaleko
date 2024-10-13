#!/usr/bin/env python3

from typing import Dict, Any, List, Union
from .llm_base import LLMBase

from enum import Enum
from pydantic import BaseModel

from icecream import ic

import openai
from openai import OpenAI


class OpenAIConnector(LLMBase):
    """
    Connector for OpenAI's language models.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Initialize the OpenAI connector.

        Args:
            api_key (str): The OpenAI API key
            model (str): The name of the OpenAI model to use
        """
        self.model = model
        self.client = openai.OpenAI(api_key=api_key)

    def generate_query(self, prompt: str) -> str:
        """
        Generate a query using OpenAI's model.

        Args:
            prompt (str): The prompt to generate the query from

        Returns:
            str: The generated query
        """
        ic('Submitting prompt to OpenAI')
        completion = self.client.beta.chat.completions.parse(
            model='gpt-4o',
            messages=[
                {
                    "role" : "system",
                    "content": prompt['system']
                },
                {
                    'role' : 'user',
                    'content' : prompt['user']
                }
            ],
        )
        ic('Received response from OpenAI')
        ic(completion.choices)
        return completion.choices[0]

    def summarize_text(self, text: str, max_length: int = 100) -> str:
        """
        Summarize the given text using OpenAI's model.

        Args:
            text (str): The text to summarize
            max_length (int): The maximum length of the summary

        Returns:
            str: The summarized text
        """
        prompt = f"Summarize the following text in no more than {max_length} words:\n\n{text}"
        response = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system",
                 "content": "You are a helpful assistant that facilitates finding relevant "
                            "files in a unified personal index of storage."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message['content'].strip()

    def extract_keywords(self, text: str, num_keywords: int = 5) -> List[str]:
        """
        Extract keywords from the given text using OpenAI's model.

        Args:
            text (str): The text to extract keywords from
            num_keywords (int): The number of keywords to extract

        Returns:
            List[str]: The extracted keywords
        """
        prompt = f"Extract {num_keywords} keywords from the following text:\n\n{text}"
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts keywords from text."},
                {"role": "user", "content": prompt}
            ]
        )
        keywords = response.choices[0].message['content'].strip().split(',')
        return [keyword.strip() for keyword in keywords[:num_keywords]]

    def classify_text(self, text: str, categories: List[str]) -> str:
        """
        Classify the given text into one of the provided categories using OpenAI's model.

        Args:
            text (str): The text to classify
            categories (List[str]): The list of possible categories

        Returns:
            str: The predicted category
        """
        categories_str = ", ".join(categories)
        prompt = f"Classify the following text into one of these categories: {categories_str}\n\nText: {text}"
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that classifies text."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message['content'].strip()

    def answer_question(self, context: str, question: str) -> str:
        """
        Answer a question based on the given context using OpenAI's model.

        Args:
            context (str): The context to base the answer on
            question (str): The question to answer

        Returns:
            str: The answer to the question
        """
        prompt = f"Context: {context}\n\nQuestion: {question}\n\nAnswer:"
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that answers questions based on provided context."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message['content'].strip()
