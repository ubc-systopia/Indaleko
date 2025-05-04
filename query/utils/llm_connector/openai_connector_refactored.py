"""
This module defines the OpenAI connector for the Indaleko prompt management system.

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
import logging
import os
import sys
import time
from typing import Any

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
# ruff: noqa: E402
from query.query_processing.data_models.query_output import LLMTranslateQueryResponse
from query.utils.llm_connector.llm_base import IndalekoLLMBase

# Import the prompt management components
from query.utils.prompt_management.guardian.llm_guardian import (
    LLMGuardian,
    RequestMode,
    VerificationLevel,
)
from query.utils.prompt_management.prompt_manager import PromptVariable

# Create logger
logger = logging.getLogger(__name__)

# ruff: qa: E402
# pylint: enable=wrong-import-position


class OpenAIConnector(IndalekoLLMBase):
    """Connector for OpenAI's language models with integrated prompt management."""

    llm_name = "OpenAI"

    def __init__(
        self,
        api_key: str,
        **kwargs: dict,
    ) -> None:
        """
        Initialize the OpenAI connector.

        Args:
            api_key (str): The OpenAI API key
            kwargs: Additional optional parameters
                - model (str): The name of the OpenAI model to use (default: "gpt-4o")
                - max_tokens (int): Maximum tokens for prompts (default: 8000)
                - use_guardian (bool): Whether to use the LLMGuardian (default: True)
                - verification_level (str): Verification level for prompts (default: "STANDARD")
                - request_mode (str): Request mode for handling verification results (default: "WARN")
        """
        self.model = kwargs.get("model", "gpt-4o")
        self.max_tokens = kwargs.get("max_tokens", 8000)
        self.use_guardian = kwargs.get("use_guardian", True)

        # Initialize OpenAI client
        self.client = openai.OpenAI(api_key=api_key)

        # Initialize tokenizer for token counting
        self.tokenizer = tiktoken.encoding_for_model(self.model)

        # Initialize LLMGuardian if enabled
        if self.use_guardian:
            # Convert string verification level to enum if needed
            verification_level_str = kwargs.get("verification_level", "STANDARD")
            if isinstance(verification_level_str, str):
                verification_level = getattr(VerificationLevel, verification_level_str)
            else:
                verification_level = verification_level_str

            # Convert string request mode to enum if needed
            request_mode_str = kwargs.get("request_mode", "WARN")
            if isinstance(request_mode_str, str):
                request_mode = getattr(RequestMode, request_mode_str)
            else:
                request_mode = request_mode_str

            # Create LLMGuardian instance
            self.guardian = LLMGuardian(
                default_verification_level=verification_level,
                default_request_mode=request_mode,
            )

            # Log initialization
            logger.info(
                f"Initialized OpenAI connector with LLMGuardian (verification: {verification_level.name}, "
                f"mode: {request_mode.name}, model: {self.model})",
            )
        else:
            self.guardian = None
            logger.info(f"Initialized OpenAI connector without LLMGuardian (model: {self.model})")

    def get_llm_name(self) -> str:
        """
        Get the name of the LLM.

        Returns:
            str: The name of the LLM
        """
        return self.llm_name

    def _count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text string.

        Args:
            text (str): The text to count tokens for

        Returns:
            int: The number of tokens
        """
        return len(self.tokenizer.encode(text))

    def _log_token_usage(self, request_id: str, usage_data: dict[str, int]) -> None:
        """
        Log token usage for analytics.

        Args:
            request_id (str): The request ID
            usage_data (Dict[str, int]): Token usage data from the API response
        """
        # If guardian is enabled, it already handles token logging
        if not self.use_guardian:
            logger.info(
                f"Request {request_id} token usage: "
                f"prompt={usage_data.get('prompt_tokens', 0)}, "
                f"completion={usage_data.get('completion_tokens', 0)}, "
                f"total={usage_data.get('total_tokens', 0)}",
            )

    def generate_query(self, prompt: dict[str, str], temperature=0) -> LLMTranslateQueryResponse:
        """
        Generate a query using OpenAI's model.

        Args:
            prompt (Dict[str, str]): The prompt to generate the query from
                Should contain 'system' and 'user' keys
            temperature (float): Temperature parameter for generation

        Returns:
            LLMTranslateQueryResponse: The generated query response
        """
        # Log submission details
        ic("Submitting prompt to OpenAI")
        ic(f"Using model: {self.model}")
        ic(f"System prompt length: {len(prompt['system'])}")
        ic(f"User prompt length: {len(prompt['user'])}")

        # Generate a unique request ID
        request_id = f"oai_{int(time.time() * 1000)}_{hash(str(prompt)) % 10000}"

        # If using guardian, process through it
        if self.use_guardian:
            # Combine system and user prompts into a format for the guardian
            combined_prompt = {
                "system": prompt["system"],
                "user": prompt["user"],
            }

            # Get completion from the guardian
            try:
                # Process through guardian
                completion_text, metadata = self.guardian.get_completion_from_prompt(
                    prompt=json.dumps(combined_prompt),
                    provider="openai",
                    model=self.model,
                    optimize=True,
                    options={
                        "temperature": temperature,
                        "response_format": {
                            "type": "json_schema",
                            "json_schema": {
                                "name": "OpenAIQueryResponse",
                                "schema": LLMTranslateQueryResponse.model_json_schema(),
                            },
                        },
                    },
                )

                # Check if the request was blocked
                if completion_text is None:
                    ic(f"Request blocked by guardian: {metadata.get('block_reason', 'Unknown reason')}")
                    raise ValueError(
                        f"Request blocked by LLMGuardian: {metadata.get('block_reason', 'Unknown reason')}",
                    )

                # Parse response and return
                doc = json.loads(completion_text)
                response = LLMTranslateQueryResponse(**doc)
                return response

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                ic(f"Error parsing response from LLMGuardian: {e}")
                raise ValueError(f"Failed to parse response: {e!s}")

        # If not using guardian, use the original implementation
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

            # Log token usage if available
            if hasattr(completion, "usage") and completion.usage:
                self._log_token_usage(
                    request_id,
                    {
                        "prompt_tokens": completion.usage.prompt_tokens,
                        "completion_tokens": completion.usage.completion_tokens,
                        "total_tokens": completion.usage.total_tokens,
                    },
                )

            # Process response
            doc = json.loads(completion.choices[0].message.content)
            response = LLMTranslateQueryResponse(**doc)
            return response

        except openai.APITimeoutError as e:
            ic(f"OpenAI API timeout: {e}")
            raise TimeoutError(f"OpenAI API timeout: {e!s}")
        except openai.APIError as e:
            ic(f"OpenAI API error: {e}")
            raise ValueError(f"OpenAI API error: {e!s}")
        except openai.AuthenticationError as e:
            ic(f"OpenAI authentication error: {e}")
            raise ValueError("OpenAI authentication error: Check your API key")
        except openai.RateLimitError as e:
            ic(f"OpenAI rate limit exceeded: {e}")
            raise ValueError(f"OpenAI rate limit exceeded: {e!s}")
        except openai.APIConnectionError as e:
            ic(f"OpenAI API connection error: {e}")
            raise ConnectionError("OpenAI API connection error: Check your network connection")
        except (GeneratorExit, RecursionError, MemoryError, NotImplementedError) as e:
            ic(f"Unexpected error generating query: {type(e).__name__}: {e}")
            raise ValueError(f"Unexpected error: {type(e).__name__}: {e!s}")

    def summarize_text(self, text: str, max_length: int = 100) -> str:
        """
        Summarize the given text using OpenAI's model.

        Args:
            text (str): The text to summarize
            max_length (int): The maximum length of the summary

        Returns:
            str: The summarized text
        """
        if self.use_guardian:
            # Create a template-based prompt for the guardian
            template = f"Summarize the following text in no more than {max_length} words:\n\n{{text}}"

            # Create the variable list
            variables = [
                PromptVariable(name="text", value=text),
            ]

            # Get completion from the guardian
            completion_text, _ = self.guardian.get_completion_from_prompt(
                prompt=template,
                provider="openai",
                model=self.model,
                system_prompt="You are a helpful assistant that facilitates finding relevant files in a unified personal index of storage.",
            )

            return completion_text or ""

        # Fall back to original implementation if guardian not enabled
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
        return response.choices[0].message.content.strip()

    def extract_keywords(self, text: str, num_keywords: int = 5) -> list[str]:
        """
        Extract keywords from the given text using OpenAI's model.

        Args:
            text (str): The text to extract keywords from
            num_keywords (int): The number of keywords to extract

        Returns:
            list[str]: The extracted keywords
        """
        if self.use_guardian:
            # Create a template-based prompt for the guardian
            template = f"Extract {num_keywords} keywords from the following text:\n\n{{text}}"

            # Create the variable list
            variables = [
                PromptVariable(name="text", value=text),
            ]

            # Get completion from the guardian
            completion_text, _ = self.guardian.get_completion_from_prompt(
                prompt=template,
                provider="openai",
                model=self.model,
                system_prompt="You are a helpful assistant that extracts keywords from text.",
            )

            if completion_text:
                keywords = completion_text.strip().split(",")
                return [keyword.strip() for keyword in keywords[:num_keywords]]
            return []

        # Fall back to original implementation if guardian not enabled
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
        if self.use_guardian:
            # Create a template-based prompt for the guardian
            categories_str = ", ".join(categories)
            template = f"Classify the following text into one of these categories: {categories_str}\n\nText: {{text}}"

            # Create the variable list
            variables = [
                PromptVariable(name="text", value=text),
            ]

            # Get completion from the guardian
            completion_text, _ = self.guardian.get_completion_from_prompt(
                prompt=template,
                provider="openai",
                model=self.model,
                system_prompt="You are a helpful assistant that classifies text.",
            )

            return completion_text or ""

        # Fall back to original implementation if guardian not enabled
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
        if self.use_guardian:
            # Convert the question and context into a template format
            template = "Context: {context}\n\nUser query: {question}"

            # Create the variable list
            variables = [
                PromptVariable(name="context", value=context),
                PromptVariable(name="question", value=question),
            ]

            # Get completion from the guardian with schema
            completion_text, _ = self.guardian.get_completion_from_prompt(
                prompt=template,
                provider="openai",
                model=self.model,
                options={
                    "temperature": 0,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "OpenAIAnswerResponse",
                            "schema": schema,
                        },
                    },
                },
            )

            if completion_text:
                return json.loads(completion_text)
            return {}

        # Fall back to original implementation if guardian not enabled
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
            raise TimeoutError(f"OpenAI API timeout: {e!s}")
        except openai.APIError as e:
            ic(f"OpenAI API error in answer_question: {e}")
            raise ValueError(f"OpenAI API error: {e!s}")
        except (GeneratorExit, RecursionError, MemoryError, NotImplementedError) as e:
            ic(f"Error in answer_question: {type(e).__name__}: {e}")
            raise ValueError(f"Error in answer_question: {type(e).__name__}: {e!s}")

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
        # This method returns the raw completion object, so we can't use the guardian here
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
        if self.use_guardian:
            # Use the guardian for the completion
            completion_text, _ = self.guardian.get_completion_from_prompt(
                prompt=prompt,
                provider="openai",
                model=self.model,
                system_prompt="You are a helpful assistant.",
                options={
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )

            return completion_text or ""

        # Fall back to original implementation if guardian not enabled
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

        if self.use_guardian:
            # Create a template-based prompt for the guardian
            attr_types_str = ", ".join(attr_types)
            template = f"""Extract the following semantic attributes from the text: {attr_types_str}

For each attribute type, provide relevant information found in the text.
Format your response as a JSON object with keys matching the requested attribute types.

Text to analyze:
{{text}}
            """

            # Create the variable list
            variables = [
                PromptVariable(name="text", value=text),
            ]

            # Define schema for expected output
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

            # Get completion from the guardian
            completion_text, _ = self.guardian.get_completion_from_prompt(
                prompt=template,
                provider="openai",
                model=self.model,
                system_prompt="You are a semantic analysis assistant.",
                options={
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                },
            )

            if completion_text:
                try:
                    attributes = json.loads(completion_text)
                    return {k: v for k, v in attributes.items() if k in attr_types}
                except json.JSONDecodeError:
                    return {attr: [] for attr in attr_types}

            return {attr: [] for attr in attr_types}

        # Fall back to original implementation if guardian not enabled
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

        except (GeneratorExit, RecursionError, MemoryError, NotImplementedError) as e:
            ic(f"Error extracting semantic attributes: {e}")
            # Return a minimal valid response
            return {attr: [] for attr in attr_types}
