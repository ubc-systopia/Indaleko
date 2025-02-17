'''
This module defines the base data model for semantic metadata recorders.

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
'''

import json
import os
import sys

import openai
from icecream import ic
from typing import Any

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.query_processing.data_models.query_output import LLMTranslateQueryResponse
from query.llm_base import IndalekoLLMBase
# pylint: enable=wrong-import-position


class OpenAIConnector(IndalekoLLMBase):
    """
    Connector for OpenAI's language models.
    """
    llm_name = 'OpenAI'

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Initialize the OpenAI connector.

        Args:
            api_key (str): The OpenAI API key
            model (str): The name of the OpenAI model to use
        """
        self.model = model
        self.client = openai.OpenAI(api_key=api_key)

    def get_llm_name(self) -> str:
        '''
        Get the name of the LLM.
        '''
        return self.llm_name

    def generate_query(self, prompt: str, temperature=0) -> LLMTranslateQueryResponse:
        """
        Generate a query using OpenAI's model.

        Args:
            prompt (str): The prompt to generate the query from

        Returns:
            str: The generated query
        """
        ic('Submitting prompt to OpenAI')
        response_schema = LLMTranslateQueryResponse.model_json_schema()
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": prompt['system']
                },
                {
                    'role': 'user',
                    'content': prompt['user']
                }
            ],
            temperature=temperature,
            # response_format=OpenAIQueryResponse
            response_format={
                'type':  'json_schema',
                'json_schema': {
                    'name': 'OpenAIQueryResponse',
                    'schema': response_schema
                }
            }
        )
        ic('Received response from OpenAI')
        doc = json.loads(completion.choices[0].message.content)
        response = LLMTranslateQueryResponse(**doc)
        return response

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

    def extract_keywords(self, text: str, num_keywords: int = 5) -> list[str]:
        """
        Extract keywords from the given text using OpenAI's model.

        Args:
            text (str): The text to extract keywords from
            num_keywords (int): The number of keywords to extract

        Returns:
            list[str]: The extracted keywords
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

    def classify_text(self, text: str, categories: list[str]) -> str:
        """
        Classify the given text into one of the provided categories using OpenAI's model.

        Args:
            text (str): The text to classify
            categories (list[str]): The list of possible categories

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

    def answer_question(self, context: str, question: str, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Answer a question based on the given context using OpenAI's model.

        Args:
            context (str): The context to base the answer on
            question (str): The question to answer
            schema (dict[str, Any]): The schema for the response

        Returns:
            str: The answer to the question
        """
        prompt = f"Context: {context}\n\n"
        question = f"User query: {question}"
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": prompt
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
            temperature=0,
            response_format={
                'type': 'json_schema',
                'json_schema': {
                    'name': 'OpenAIAnswerResponse',
                    'schema': schema,
                }
            }
        )
        ic(completion)
        return completion.choices[0].message.content

    def get_completion(
            self,
            context: str,
            question: str,
            schema: dict[str, Any]
    ) -> openai.types.chat.parsed_chat_completion.ParsedChatCompletion:
        """
        Answer a question based on the given context using OpenAI's model.

        Args:
            context (str): The context to base the answer on
            question (str): The question to answer
            schema (dict[str, Any]): The schema for the response

        Returns:
            str: The answer to the question
        """
        prompt = f"Context: {context}\n\n"
        question = f"User query: {question}"
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": prompt
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
            temperature=0,
            response_format={
                'type': 'json_schema',
                'json_schema': {
                    'name': 'OpenAIAnswerResponse',
                    'schema': schema,
                }
            }
        )
        return completion
