#!/usr/bin/env python3
'''
This is the OpenAI connector for the Indaleko project.

Project Indaleko
Copyright (C) 2024 Tony Mason

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

from typing import List
import openai
from openai import OpenAI
from llm_base import IndalekoLLMBase

class IndalekoOpenAIConnector(IndalekoLLMBase):
    '''This is the openAI connector for the Indaleko project.'''

    default_prompt = """
        You are an assistant that generates database queries for
        a Unified Personal Index (UPI) system. The UPI system uses
        data stored in a database, with tables representing
        various metadata about and related to digital objects (e.g.,
        files, directories). Analyze the user request
        and generate an appropriate structured query description
        that retrieves the most relevant information from the
        database. Consider all available metadata, such as file
        names, timestamps, sizes, and semantic attributes, to find
        matches. If the user's query includes specific details
        (e.g., file name, date, size), prioritize those in the
        generated query.
        """,

    def __init__(self, **kwargs):
        '''Initialize the OpenAI connector for the Indaleko project.'''
        self.model = kwargs.get('model', 'gpt-3.5-turbo')
        self.api_key = kwargs.get('api_key', None)
        self.prompt = kwargs.get('prompt', self.default_prompt)
        self.temperature = kwargs.get('temperature', 0.4)
        self.client = openai.OpenAI(api_key=self.api_key)

    def generate_query(self, prompt: str) -> str:
        '''Generate a query based on the prompt.'''
        completion = self.client.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": self.prompt,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=self.temperature,
        )
        return completion.choices[0].message

    def summarize_text(self, text: str, max_length : int = 100) -> str:
        '''Summarize the text provided.'''
        completion = self.client.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Summarize the text.",
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
            temperature=self.temperature,
        )
        return completion.choices[0].message

    def extract_keywords(self, text: str, num_keywords: int = 5) -> List[str]:
        '''Extract keywords from the text provided.'''
        completion = self.client.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Extract keywords from the text.",
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
            temperature=self.temperature,
        )
        return completion.choices[0].message

    def classify_text(self, text: str, categories: List[str]) -> str:
        '''Classify the text provided into the categories provided.'''
        completion = self.client.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Classify the text.",
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
            temperature=self.temperature,
        )
        return completion.choices[0].message

    def answer_question(self, context: str, question: str) -> str:
        '''Answer the question based on the context provided.'''
        completion = self.client.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Answer the question.",
                },
                {
                    "role": "user",
                    "content": f"{context} {question}",
                },
            ],
            temperature=self.temperature,
        )
        return completion.choices[0].message
