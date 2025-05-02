"""
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
"""

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

import openai
import tiktoken
from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.query_processing.data_models.query_output import LLMTranslateQueryResponse
from query.utils.llm_connector.llm_base import IndalekoLLMBase
from query.utils.prompt_manager import (
    PromptManager, 
    PromptOptimizationStrategy, 
    PromptRegistry,
    PromptTemplate,
    create_aql_translation_template,
    create_nl_parser_template
)

# pylint: enable=wrong-import-position


class OpenAIConnector(IndalekoLLMBase):
    """Connector for OpenAI's language models."""

    llm_name = "OpenAI"

    def __init__(
        self, 
        api_key: str, 
        model: str = "gpt-4o",
        max_tokens: int = 8000,
        use_prompt_manager: bool = True,
        optimization_strategies: Optional[List[PromptOptimizationStrategy]] = None
    ):
        """
        Initialize the OpenAI connector.

        Args:
            api_key (str): The OpenAI API key
            model (str): The name of the OpenAI model to use
            max_tokens (int): Maximum tokens for prompts
            use_prompt_manager (bool): Whether to use the prompt manager
            optimization_strategies (Optional[List[PromptOptimizationStrategy]]): 
                Optimization strategies to use for prompts
        """
        self.model = model
        self.client = openai.OpenAI(api_key=api_key)
        
        # Initialize prompt manager if enabled
        self.use_prompt_manager = use_prompt_manager
        if use_prompt_manager:
            # Create registry and register default templates
            registry = PromptRegistry()
            registry.register(create_aql_translation_template())
            registry.register(create_nl_parser_template())
            
            # Create prompt manager
            self.prompt_manager = PromptManager(
                max_tokens=max_tokens,
                registry=registry
            )
            
            # Set default optimization strategies
            self.optimization_strategies = optimization_strategies or [
                PromptOptimizationStrategy.WHITESPACE,
                PromptOptimizationStrategy.SCHEMA_SIMPLIFY,
                PromptOptimizationStrategy.EXAMPLE_REDUCE
            ]

    def get_llm_name(self) -> str:
        """
        Get the name of the LLM.
        """
        return self.llm_name

    def generate_query(self, prompt: Dict[str, str], temperature=0) -> LLMTranslateQueryResponse:
        """
        Generate a query using OpenAI's model.

        Args:
            prompt (Dict[str, str]): The prompt to generate the query from
                Should contain 'system' and 'user' keys
            temperature (float): Temperature parameter for generation

        Returns:
            LLMTranslateQueryResponse: The generated query response
        """
        # If we have a prompt manager and this looks like a raw prompt dict with query
        if (self.use_prompt_manager and 
            isinstance(prompt, dict) and 
            'query' in prompt and 
            'template' in prompt):
            
            # Use prompt manager to create optimized prompt
            query = prompt['query']
            template_name = prompt['template']
            
            # Get other parameters if provided
            params = {k: v for k, v in prompt.items() 
                     if k not in ['query', 'template', 'system', 'user']}
            
            # Add query parameter
            params['query'] = query
            
            try:
                # Create prompt using manager
                managed_prompt = self.prompt_manager.create_prompt(
                    template_name=template_name,
                    optimize=True,
                    strategies=self.optimization_strategies,
                    **params
                )
                
                # Update prompt with managed version
                prompt = managed_prompt
                
                # Log token usage
                combined = f"{prompt['system']}\n\n{prompt['user']}"
                tokens = len(self.prompt_manager.tokenizer.encode(combined))
                ic(f"Optimized prompt token count: {tokens}")
            except ValueError as e:
                # If template not found, log warning and continue with original prompt
                ic(f"Warning: {str(e)}. Using original prompt.")
        
        # Log submission details
        ic("Submitting prompt to OpenAI")
        ic(f"Using model: {self.model}")
        ic(f"System prompt length: {len(prompt['system'])}")
        ic(f"User prompt length: {len(prompt['user'])}")

        try:
            # Get response schema
            response_schema = LLMTranslateQueryResponse.model_json_schema()

            # Make API call with timeout
            import time
            start_time = time.time()

            # More verbose logging for debugging
            ic("Starting OpenAI API call")
            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]},
                ],
                temperature=temperature,
                timeout=60,  # 60-second timeout
                # response_format=OpenAIQueryResponse
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "OpenAIQueryResponse",
                        "schema": response_schema,
                    },
                },
            )

            elapsed_time = time.time() - start_time
            ic(f"OpenAI API call completed in {elapsed_time:.2f} seconds")
            ic("Received response from OpenAI")

            # Process response
            doc = json.loads(completion.choices[0].message.content)
            response = LLMTranslateQueryResponse(**doc)
            return response

        except openai.APITimeoutError as e:
            ic(f"OpenAI API timeout: {e}")
            ic(f"API timeout details: {str(e)}")
            raise TimeoutError(f"OpenAI API timeout: {str(e)}")
        except openai.APIError as e:
            ic(f"OpenAI API error: {e}")
            ic(f"API error details: {str(e)}")
            raise ValueError(f"OpenAI API error: {str(e)}")
        except openai.AuthenticationError as e:
            ic(f"OpenAI authentication error: {e}")
            ic(f"Auth error details: {str(e)}")
            raise ValueError(f"OpenAI authentication error: Check your API key")
        except openai.RateLimitError as e:
            ic(f"OpenAI rate limit exceeded: {e}")
            raise ValueError(f"OpenAI rate limit exceeded: {str(e)}")
        except openai.APIConnectionError as e:
            ic(f"OpenAI API connection error: {e}")
            raise ConnectionError(f"OpenAI API connection error: Check your network connection")
        except (GeneratorExit , RecursionError , MemoryError , NotImplementedError ) as e:
            ic(f"Unexpected error generating query: {type(e).__name__}: {e}")
            raise ValueError(f"Unexpected error: {type(e).__name__}: {str(e)}")

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
                {
                    "role": "system",
                    "content": "You are a helpful assistant that facilitates finding relevant "
                    "files in a unified personal index of storage.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message["content"].strip()

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
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that extracts keywords from text.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        keywords = response.choices[0].message.content.strip().split(",")
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
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that classifies text.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content.strip()

    def answer_question(
        self,
        context: str,
        question: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
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
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": question},
        ]
        enc = tiktoken.encoding_for_model(self.model)
        total = 0
        for message in messages:
            total += 4  # for the role and content fields
            for value in message.values():
                total += len(enc.encode(value))
        if total > 4096:
            ic(f"Total length of messages {total} exceeds 4096 characters")

        try:
            ic("Starting answer_question call to OpenAI")
            start_time = time.time()

            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=messages,
                temperature=0,
                timeout=60,  # 60-second timeout
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "OpenAIAnswerResponse",
                        "schema": schema,
                    },
                },
            )

            elapsed_time = time.time() - start_time
            ic(f"answer_question API call completed in {elapsed_time:.2f} seconds")

            return completion.choices[0].message.content

        except openai.APITimeoutError as e:
            ic(f"OpenAI API timeout in answer_question: {e}")
            raise TimeoutError(f"OpenAI API timeout: {str(e)}")
        except openai.APIError as e:
            ic(f"OpenAI API error in answer_question: {e}")
            raise ValueError(f"OpenAI API error: {str(e)}")
        except (GeneratorExit , RecursionError , MemoryError , NotImplementedError ) as e:
            ic(f"Error in answer_question: {type(e).__name__}: {e}")
            raise ValueError(f"Error in answer_question: {type(e).__name__}: {str(e)}")

    def get_completion(
        self,
        context: str,
        question: str,
        schema: dict[str, Any],
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
        return self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": question},
            ],
            temperature=0,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "OpenAIAnswerResponse",
                    "schema": schema,
                },
            },
        )

    def generate_text(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
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
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()

    def extract_semantic_attributes(
        self,
        text: str,
        attr_types: list[str] = None,
    ) -> dict[str, Any]:
        """
        Extract semantic attributes from text.

        Args:
            text (str): The text to extract attributes from
            attr_types (list[str]): Types of attributes to extract, defaults to
                                    ["entities", "keywords", "sentiment", "topics"]

        Returns:
            dict[str, Any]: Dictionary of extracted attributes
        """
        # Default attribute types if none provided
        if attr_types is None:
            attr_types = ["entities", "keywords", "sentiment", "topics"]

        attr_types_str = ", ".join(attr_types)
        prompt = f"""Extract the following semantic attributes from the text: {attr_types_str}

For each attribute type, provide relevant information found in the text.
Format your response as a JSON object with keys matching the requested attribute types.

Text to analyze:
{text}
        """

        # Define a schema for the expected output
        schema = {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Named entities found in the text",
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Important keywords from the text",
                },
                "sentiment": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "score": {"type": "number"},
                    },
                    "description": "Sentiment analysis of the text",
                },
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Main topics discussed in the text",
                },
            },
        }

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a semantic analysis assistant.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )

            # Parse the JSON response
            attributes = json.loads(response.choices[0].message.content)

            # Filter to only include requested attribute types
            return {k: v for k, v in attributes.items() if k in attr_types}

        except (GeneratorExit , RecursionError , MemoryError , NotImplementedError ) as e:
            ic(f"Error extracting semantic attributes: {e}")
            # Return a minimal valid response
            return {attr: [] for attr in attr_types}
