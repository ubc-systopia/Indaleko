"""
Gemma LLM connector for the Indaleko system.

This module provides a connector for local Gemma instances running via LM Studio.

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
from pathlib import Path
from textwrap import dedent
from typing import Any

import openai
from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from query.query_processing.data_models.query_output import LLMTranslateQueryResponse
from query.utils.llm_connector.llm_base import IndalekoLLMBase
from query.utils.prompt_manager import (
    PromptManager,
    PromptOptimizationStrategy,
    PromptRegistry,
    create_aql_translation_template,
    create_nl_parser_template,
)

# pylint: enable=wrong-import-position


class GemmaConnector(IndalekoLLMBase):
    """Connector for Gemma models running locally via LM Studio."""

    llm_name = "Gemma"

    def __init__(self, **kwargs: dict) -> None:
        """
        Initialize the Gemma connector.

        Args:
            kwargs: Additional optional parameters
                - api_base (str): The base URL for the LM Studio API
                    (default: "http://localhost:1234/v1")
                - model (str): The name of the Gemma model to use (default: "Gemma")
                - max_tokens (int): Maximum tokens for prompts (default: 4096)
                - use_prompt_manager (bool): Whether to use the prompt manager (default: True)
                - optimization_strategies (Optional[List[PromptOptimizationStrategy]]):
                    Optimization strategies to use for prompts
        """
        # Check for api_base in kwargs, then environment, then use default
        self.base_url = kwargs.get(
            "api_base",
            kwargs.get("base_url", os.environ.get("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")),
        )

        # If the URL doesn't end with /v1, append it
        if not self.base_url.endswith("/v1"):
            self.base_url = f"{self.base_url}/v1"

        self.model = kwargs.get("model", "Gemma")
        max_tokens = kwargs.get("max_tokens", 4096)
        self.use_prompt_manager = kwargs.get("use_prompt_manager", True)
        self.optimization_strategies = kwargs.get(
            "optimization_strategies",
            [
                PromptOptimizationStrategy.WHITESPACE,
                PromptOptimizationStrategy.SCHEMA_SIMPLIFY,
                PromptOptimizationStrategy.EXAMPLE_REDUCE,
            ],
        )

        self.client = openai.OpenAI(base_url=self.base_url, api_key="not-needed")

        # Initialize prompt manager if enabled
        if self.use_prompt_manager:
            # Create registry and register default templates
            registry = PromptRegistry()
            registry.register(create_aql_translation_template())
            registry.register(create_nl_parser_template())

            # Create prompt manager
            self.prompt_manager = PromptManager(
                max_tokens=max_tokens,
                registry=registry,
            )

    def get_llm_name(self) -> str:
        """
        Get the name of the LLM.
        """
        return self.llm_name

    def generate_query(self, prompt: dict[str, str], temperature=0) -> LLMTranslateQueryResponse:
        """
        Generate a query using the Gemma model.

        Args:
            prompt (Dict[str, str]): The prompt to generate the query from
                Should contain 'system' and 'user' keys
            temperature (float): Temperature parameter for generation

        Returns:
            LLMTranslateQueryResponse: The generated query response
        """
        # If we have a prompt manager and this looks like a raw prompt dict with query
        if self.use_prompt_manager and isinstance(prompt, dict) and "query" in prompt and "template" in prompt:

            # Use prompt manager to create optimized prompt
            query = prompt["query"]
            template_name = prompt["template"]

            # Get other parameters if provided
            params = {k: v for k, v in prompt.items() if k not in ["query", "template", "system", "user"]}

            # Add query parameter
            params["query"] = query

            try:
                # Create prompt using manager
                managed_prompt = self.prompt_manager.create_prompt(
                    template_name=template_name,
                    optimize=True,
                    strategies=self.optimization_strategies,
                    **params,
                )

                # Update prompt with managed version
                prompt = managed_prompt

                # Log token usage
                combined = f"{prompt['system']}\n\n{prompt['user']}"
                # Note: Local models may not use the same tokenizer, but this gives us a rough estimate
                tokens = len(self.prompt_manager.tokenizer.encode(combined))
                ic(f"Optimized prompt token count (estimate): {tokens}")
            except ValueError as e:
                # If template not found, log warning and continue with original prompt
                ic(f"Warning: {e!s}. Using original prompt.")

        # Log submission details
        ic("Submitting prompt to Gemma")
        ic(f"Using model: {self.model}")
        ic(f"System prompt length: {len(prompt['system'])}")
        ic(f"User prompt length: {len(prompt['user'])}")

        try:
            # Get response schema
            response_schema = LLMTranslateQueryResponse.model_json_schema()

            # Make API call with timeout
            start_time = time.time()

            # More verbose logging for debugging
            ic("Starting Gemma API call")

            # For Gemma and similar models via LM Studio, we'll use the combined system+user format
            # as a single message because some models don't support system messages
            combined_prompt = dedent(
                f"""
                System: {prompt['system']}\n\nUser: {prompt['user']}\n\n
                Please respond with a valid JSON according to the following schema:
                \n{json.dumps(response_schema, indent=2)}
                """,
            )

            try:
                # First try to use the chat interface with JSON response format
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": combined_prompt},
                    ],
                    temperature=temperature,
                    response_format={"type": "json_object"},
                    max_tokens=2000,
                )

                content = completion.choices[0].message.content

            except (GeneratorExit, RecursionError, MemoryError, NotImplementedError) as e:
                ic(f"Chat format failed with {e!s}, trying completions API")
                # Fall back to completions API if chat format doesn't work
                completion = self.client.completions.create(
                    model=self.model,
                    prompt=combined_prompt,
                    temperature=temperature,
                    max_tokens=2000,
                )

                content = completion.choices[0].text

            elapsed_time = time.time() - start_time
            ic(f"Gemma API call completed in {elapsed_time:.2f} seconds")
            ic("Received response from Gemma")

            # Process response - clean it up in case it's not proper JSON
            content = content.strip()

            # Try to find JSON in the response
            json_start = content.find("{")
            json_end = content.rfind("}")

            if json_start >= 0 and json_end >= 0:
                json_content = content[json_start : json_end + 1]

                # Parse JSON response
                try:
                    doc = json.loads(json_content)
                    return LLMTranslateQueryResponse(**doc)
                except json.JSONDecodeError as e:
                    ic(f"Error parsing JSON response: {e}")
                    # Create a basic response with the error
                    return LLMTranslateQueryResponse(
                        query="",
                        translated_query="",
                        explanation=f"Error processing response: {e!s}",
                        error=True,
                        error_message=f"Failed to parse JSON: {e!s}",
                    )
            else:
                # No JSON found, create a basic error response
                return LLMTranslateQueryResponse(
                    query=prompt.get("query", ""),
                    translated_query="",
                    explanation=f"No valid JSON found in response: {content[:100]}...",
                    error=True,
                    error_message="No valid JSON response",
                )

        except (GeneratorExit, RecursionError, MemoryError, NotImplementedError) as e:
            ic(f"Gemma API error: {e!s}")
            # Return an error response
            return LLMTranslateQueryResponse(
                query=prompt.get("query", ""),
                translated_query="",
                explanation=f"Error: {e!s}",
                error=True,
                error_message=str(e),
            )

    def summarize_text(self, text: str, max_length: int = 100) -> str:
        """
        Summarize the given text using the Gemma model.

        Args:
            text (str): The text to summarize
            max_length (int): The maximum length of the summary

        Returns:
            str: The summarized text
        """
        prompt = f"Summarize the following text in no more than {max_length} words:\n\n{text}"
        try:
            response = self.client.chat.completions.create(
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
            return response.choices[0].message.content.strip()
        except (GeneratorExit, RecursionError, MemoryError, NotImplementedError) as e:
            ic(f"Error in summarize_text: {e}")
            # Try the completions API as fallback
            response = self.client.completions.create(
                model=self.model,
                prompt=f"You are a helpful assistant that facilitates finding relevant files in a unified personal index of storage.\n\n{prompt}",
                max_tokens=max_length * 2,  # Rough estimate of token count
            )
            return response.choices[0].text.strip()

    def extract_keywords(self, text: str, num_keywords: int = 5) -> list[str]:
        """
        Extract keywords from the given text using the Gemma model.

        Args:
            text (str): The text to extract keywords from
            num_keywords (int): The number of keywords to extract

        Returns:
            list[str]: The extracted keywords
        """
        prompt = f"Extract {num_keywords} keywords from the following text:\n\n{text}"
        try:
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
            content = response.choices[0].message.content.strip()
        except (GeneratorExit, RecursionError, MemoryError, NotImplementedError) as e:
            ic(f"Error in extract_keywords (chat): {e}")
            # Try the completions API as fallback
            response = self.client.completions.create(
                model=self.model,
                prompt=f"You are a helpful assistant that extracts keywords from text.\n\n{prompt}",
                max_tokens=100,
            )
            content = response.choices[0].text.strip()

        # Parse the response - looking for comma-separated words or a list
        if "," in content:
            keywords = content.split(",")
        else:
            # Try to find words wrapped in quotes or separated by newlines
            import re

            keywords = re.findall(r'[\'"](.*?)[\'"]|^([^\n]+)$', content, re.MULTILINE)
            # Flatten and clean the results
            keywords = [match[0] or match[1] for match in keywords if match[0] or match[1]]

        return [keyword.strip() for keyword in keywords[:num_keywords]]

    def classify_text(self, text: str, categories: list[str]) -> str:
        """
        Classify the given text into one of the provided categories using the Gemma model.

        Args:
            text (str): The text to classify
            categories (list[str]): The list of possible categories

        Returns:
            str: The predicted category
        """
        categories_str = ", ".join(categories)
        prompt = f"Classify the following text into one of these categories: {categories_str}\n\nText: {text}"
        try:
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
        except (GeneratorExit, RecursionError, MemoryError, NotImplementedError) as e:
            ic(f"Error in classify_text (chat): {e}")
            # Try the completions API as fallback
            response = self.client.completions.create(
                model=self.model,
                prompt=f"You are a helpful assistant that classifies text.\n\n{prompt}",
                max_tokens=50,
            )
            return response.choices[0].text.strip()

    def answer_question(
        self,
        context: str,
        question: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Answer a question based on the given context using the Gemma model.

        Args:
            context (str): The context to base the answer on
            question (str): The question to answer
            schema (dict[str, Any]): The schema for the response

        Returns:
            dict[str, Any]: The answer to the question
        """
        prompt = f"Context: {context}\n\n"
        question = f"User query: {question}"

        combined_prompt = (
            f"{prompt}\n{question}\n\nRespond with a valid JSON following this schema:\n{json.dumps(schema, indent=2)}"
        )

        try:
            ic("Starting answer_question call to Gemma")
            start_time = time.time()

            try:
                # First try with chat completions
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": combined_prompt}],
                    temperature=0,
                    response_format={"type": "json_object"},
                    max_tokens=1000,
                )
                content = response.choices[0].message.content
            except (GeneratorExit, RecursionError, MemoryError, NotImplementedError) as e:
                ic(f"Chat completion failed: {e}, trying regular completion")
                # Fall back to regular completions
                response = self.client.completions.create(
                    model=self.model,
                    prompt=combined_prompt,
                    temperature=0,
                    max_tokens=1000,
                )
                content = response.choices[0].text

            elapsed_time = time.time() - start_time
            ic(f"answer_question API call completed in {elapsed_time:.2f} seconds")

            # Try to extract JSON from the response
            content = content.strip()
            json_start = content.find("{")
            json_end = content.rfind("}")

            if json_start >= 0 and json_end >= 0:
                json_content = content[json_start : json_end + 1]
                try:
                    return json.loads(json_content)
                except json.JSONDecodeError:
                    # If parsing fails, return a basic response
                    return {"answer": content, "error": "Failed to parse JSON response"}
            else:
                # No JSON found, return the raw text
                return {"answer": content, "error": "No JSON found in response"}

        except (GeneratorExit, RecursionError, MemoryError, NotImplementedError) as e:
            ic(f"Error in answer_question: {type(e).__name__}: {e}")
            return {"error": f"Error in answer_question: {type(e).__name__}: {e!s}"}

    def get_completion(
        self,
        context: str,
        question: str,
        schema: dict[str, Any],
    ) -> Any:
        """
        Answer a question based on the given context using the Gemma model.

        Args:
            context (str): The context to base the answer on
            question (str): The question to answer
            schema (dict[str, Any]): The schema for the response

        Returns:
            Any: The raw completion result
        """
        prompt = f"Context: {context}\n\n"
        question = f"User query: {question}"

        combined_prompt = (
            f"{prompt}\n{question}\n\nRespond with a valid JSON following this schema:\n{json.dumps(schema, indent=2)}"
        )

        try:
            # Try chat completions first
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": combined_prompt}],
                temperature=0,
                response_format={"type": "json_object"},
                max_tokens=1000,
            )
            return response
        except (GeneratorExit, RecursionError, MemoryError, NotImplementedError) as e:
            ic(f"Chat completion failed: {e}, trying regular completion")
            # Fall back to regular completions
            response = self.client.completions.create(
                model=self.model,
                prompt=combined_prompt,
                temperature=0,
                max_tokens=1000,
            )

            # Create a compatible response object
            class MockChatChoice:
                def __init__(self, text):
                    self.message = {"content": text}
                    self.text = text

            class MockChatCompletion:
                def __init__(self, response):
                    self.choices = [MockChatChoice(response.choices[0].text)]

            return MockChatCompletion(response)

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
        try:
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
        except (GeneratorExit, RecursionError, MemoryError, NotImplementedError) as e:
            ic(f"Chat completion failed: {e}, trying regular completion")
            # Fall back to regular completions
            response = self.client.completions.create(
                model=self.model,
                prompt=f"You are a helpful assistant.\n\n{prompt}",
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].text.strip()

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
            try:
                # Try chat completions first
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
                content = response.choices[0].message.content
            except (GeneratorExit, RecursionError, MemoryError, NotImplementedError) as e:
                ic(f"Chat completion failed: {e}, trying regular completion")
                # Fall back to regular completions
                response = self.client.completions.create(
                    model=self.model,
                    prompt=f"You are a semantic analysis assistant.\n\n{prompt}\n\nRespond with a valid JSON object.",
                    temperature=0,
                    max_tokens=1000,
                )
                content = response.choices[0].text

            # Try to extract JSON from the response
            content = content.strip()
            json_start = content.find("{")
            json_end = content.rfind("}")

            if json_start >= 0 and json_end >= 0:
                json_content = content[json_start : json_end + 1]
                # Parse the JSON response
                attributes = json.loads(json_content)

                # Filter to only include requested attribute types
                return {k: v for k, v in attributes.items() if k in attr_types}
            else:
                # No JSON found, return minimal response
                return {attr: [] for attr in attr_types}

        except (GeneratorExit, RecursionError, MemoryError, NotImplementedError) as e:
            ic(f"Error extracting semantic attributes: {e}")
            # Return a minimal valid response
            return {attr: [] for attr in attr_types}
