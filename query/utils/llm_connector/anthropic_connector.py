"""
Anthropic Claude connector for the Indaleko system.

This module provides a connector for Anthropic's Claude models.

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
from typing import Any

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

try:
    from anthropic import Anthropic, AsyncAnthropic
except ImportError:
    ic("Warning: Anthropic Python SDK not installed. Please run: pip install anthropic")

# pylint: enable=wrong-import-position


class AnthropicConnector(IndalekoLLMBase):
    """Connector for Anthropic's Claude models."""

    llm_name = "Claude"

    def __init__(self, **kwargs: dict) -> None:
        """
        Initialize the Anthropic connector.

        Args:
            kwargs: Additional optional parameters
                - api_key (str): The Anthropic API key
                - model (str): The name of the Claude model to use
                    (default: "claude-3-sonnet-20240229")
                - max_tokens (int): Maximum tokens for prompts (default: 100000)
                - use_prompt_manager (bool): Whether to use the prompt manager (default: True)
                - optimization_strategies (Optional[List[PromptOptimizationStrategy]]):
                    Optimization strategies to use for prompts
        """
        self.api_key = kwargs.get("api_key")
        self.model = kwargs.get("model", "claude-3-7-sonnet-latest")
        max_tokens = int(kwargs.get("max_tokens", 10000))
        self.max_tokens_to_sample = max_tokens
        self.use_prompt_manager = kwargs.get("use_prompt_manager", True)
        self.optimization_strategies = kwargs.get(
            "optimization_strategies",
            [
                PromptOptimizationStrategy.WHITESPACE,
                PromptOptimizationStrategy.SCHEMA_SIMPLIFY,
                PromptOptimizationStrategy.EXAMPLE_REDUCE,
            ],
        )

        # Initialize client
        try:
            self.client = Anthropic(api_key=self.api_key)
        except NameError:
            ic("Anthropic Python SDK not installed. Some functionality won't work.")
            self.client = None

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
        Get the name of the LLM provider.

        Returns:
            str: The name of the LLM provider.
        """
        return self.llm_name

    def generate_query(self, prompt: dict[str, str], temperature=0) -> LLMTranslateQueryResponse:
        """
        Generate a query using the Claude model.

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
                tokens = len(self.prompt_manager.tokenizer.encode(combined))
                ic(f"Optimized prompt token count (estimate): {tokens}")
            except ValueError as e:
                # If template not found, log warning and continue with original prompt
                ic(f"Warning: {e!s}. Using original prompt.")

        # Log submission details
        ic("Submitting prompt to Claude")
        ic(f"Using model: {self.model}")
        ic(f"System prompt length: {len(prompt['system'])}")
        ic(f"User prompt length: {len(prompt['user'])}")

        try:
            # Get response schema
            response_schema = LLMTranslateQueryResponse.model_json_schema()

            # Make API call with timeout
            start_time = time.time()

            # More verbose logging for debugging
            ic("Starting Claude API call")

            # Create the message for Claude
            message = self.client.messages.create(
                model=self.model,
                system=prompt["system"],
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt['user']}\n\nPlease respond with a valid JSON according to the following schema:\n{json.dumps(response_schema, indent=2)}",
                    },
                ],
                temperature=temperature,
                max_tokens=self.max_tokens_to_sample,
                stream=False,  # Explicitly disable streaming to avoid the warning
            )

            elapsed_time = time.time() - start_time
            ic(f"Claude API call completed in {elapsed_time:.2f} seconds")
            ic("Received response from Claude")

            # Extract content from response
            content = message.content[0].text

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

        except Exception as e:
            ic(f"Claude API error: {e!s}")
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
        Summarize the given text using the Claude model.

        Args:
            text (str): The text to summarize
            max_length (int): The maximum length of the summary

        Returns:
            str: The summarized text
        """
        prompt = f"Summarize the following text in no more than {max_length} words:\n\n{text}"
        try:
            message = self.client.messages.create(
                model=self.model,
                system="You are a helpful assistant that provides concise summaries.",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_length * 5,  # Rough estimate for token count
                stream=False,  # Explicitly disable streaming to avoid the warning
            )
            return message.content[0].text.strip()
        except Exception as e:
            ic(f"Error in summarize_text: {e}")
            return f"Error generating summary: {e!s}"

    def extract_keywords(self, text: str, num_keywords: int = 5) -> list[str]:
        """
        Extract keywords from the given text using the Claude model.

        Args:
            text (str): The text to extract keywords from
            num_keywords (int): The number of keywords to extract

        Returns:
            list[str]: The extracted keywords
        """
        prompt = f"Extract exactly {num_keywords} keywords from the following text. Respond with just a comma-separated list of keywords, nothing else:\n\n{text}"
        try:
            message = self.client.messages.create(
                model=self.model,
                system="You are a helpful assistant that extracts keywords from text.",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                stream=False,  # Explicitly disable streaming to avoid the warning
            )
            content = message.content[0].text.strip()

            # Parse the comma-separated list
            keywords = [k.strip() for k in content.split(",")]
            return keywords[:num_keywords]  # Ensure we don't exceed requested number
        except Exception as e:
            ic(f"Error in extract_keywords: {e}")
            return [str(e)]

    def classify_text(self, text: str, categories: list[str]) -> str:
        """
        Classify the given text into one of the provided categories using the Claude model.

        Args:
            text (str): The text to classify
            categories (list[str]): The list of possible categories

        Returns:
            str: The predicted category
        """
        categories_str = ", ".join(categories)
        prompt = f"Classify the following text into exactly one of these categories: {categories_str}\n\nRespond with only the category name, nothing else.\n\nText: {text}"
        try:
            message = self.client.messages.create(
                model=self.model,
                system="You are a helpful assistant that classifies text.",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                stream=False,  # Explicitly disable streaming to avoid the warning
            )
            return message.content[0].text.strip()
        except Exception as e:
            ic(f"Error in classify_text: {e}")
            return str(e)

    def answer_question(
        self,
        context: str,
        question: str,
        schema: dict[str, Any],
    ) -> str:
        """
        Answer a question based on the given context using the Claude model.

        Args:
            context (str): The context to base the answer on
            question (str): The question to answer
            schema (dict[str, Any]): The schema for the response

        Returns:
            str: The answer to the question in JSON format
        """
        prompt = f"Context: {context}\n\nUser query: {question}\n\nRespond with a valid JSON following this schema:\n{json.dumps(schema, indent=2)}"
        try:
            ic("Starting answer_question call to Claude")
            start_time = time.time()

            message = self.client.messages.create(
                model=self.model,
                system="You are a helpful assistant that always responds with valid JSON.",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=self.max_tokens_to_sample,
                stream=False,  # Explicitly disable streaming to avoid the warning
            )

            elapsed_time = time.time() - start_time
            ic(f"answer_question API call completed in {elapsed_time:.2f} seconds")

            content = message.content[0].text.strip()

            # Try to extract JSON from the response
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

        except Exception as e:
            ic(f"Error in answer_question: {type(e).__name__}: {e}")
            return {"error": f"Error in answer_question: {type(e).__name__}: {e!s}"}

    def get_completion(
        self,
        context: str,
        question: str,
        schema: dict[str, Any],
    ) -> Any:
        """
        Get a completion for a prompt from Claude. Returns the raw completion object.

        Args:
            context (str): The context to base the answer on
            question (str): The question to answer
            schema (dict[str, Any]): The schema for the response

        Returns:
            Any: The raw completion result
        """
        prompt = f"Context: {context}\n\nUser query: {question}\n\nRespond with a valid JSON following this schema:\n{json.dumps(schema, indent=2)}"
        ic(prompt)
        message = self.client.messages.create(
            model=self.model,
            system="You are a helpful assistant that always responds with valid JSON.",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=self.max_tokens_to_sample,
            stream=False,  # Explicitly disable streaming to avoid warning
        )
        return message

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
            message = self.client.messages.create(
                model=self.model,
                system="You are a helpful assistant.",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,  # Explicitly disable streaming to avoid warning
            )
            return message.content[0].text.strip()
        except Exception as e:
            ic(f"Error in generate_text: {e!s}")
            return f"Error generating text: {e!s}"

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
            message = self.client.messages.create(
                model=self.model,
                system="You are a semantic analysis assistant. Always respond with valid JSON.",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=1000,
                stream=False,  # Explicitly disable streaming to avoid the warning
            )

            content = message.content[0].text.strip()

            # Try to extract JSON from the response
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

        except Exception as e:
            ic(f"Error extracting semantic attributes: {e}")
            # Return a minimal valid response
            return {attr: [] for attr in attr_types}
