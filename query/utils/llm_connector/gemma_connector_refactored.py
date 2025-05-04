"""
Gemma LLM connector for the Indaleko system with prompt management integration.

This module provides a connector for local Gemma instances running via LM Studio,
with integrated prompt management capabilities.

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
from pathlib import Path
from textwrap import dedent
from typing import Any

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
import openai

from query.query_processing.data_models.query_output import LLMTranslateQueryResponse
from query.utils.llm_connector.llm_base import IndalekoLLMBase

# Import the prompt management components
from query.utils.prompt_management.guardian.llm_guardian import (
    LLMGuardian,
    LLMRequestMode,
    VerificationLevel,
)
from query.utils.prompt_management.prompt_manager import PromptVariable

# Create logger
logger = logging.getLogger(__name__)

# pylint: enable=wrong-import-position


class GemmaConnector(IndalekoLLMBase):
    """
    Connector for Gemma models running locally via LM Studio with integrated prompt management.

    This connector supports both direct access and guardian-managed modes,
    with comprehensive token tracking and security verification.
    """

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
                - use_guardian (bool): Whether to use LLMGuardian (default: True)
                - verification_level (str): Verification level for prompts (default: "STANDARD")
                - request_mode (str): Request mode for handling verification results (default: "WARN")
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
        self.max_tokens = kwargs.get("max_tokens", 4096)

        # Prompt management configuration
        self.use_guardian = kwargs.get("use_guardian", True)

        # Initialize client
        self.client = openai.OpenAI(base_url=self.base_url, api_key="not-needed")

        # Initialize tokenizer (using cl100k_base as a fallback for token estimation)
        try:
            import tiktoken

            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except (ImportError, ValueError):
            logger.warning("tiktoken not installed or cl100k_base not found. Token estimation will be approximate.")
            self.tokenizer = None

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
                request_mode = getattr(LLMRequestMode, request_mode_str)
            else:
                request_mode = request_mode_str

            # Create LLMGuardian instance
            self.guardian = LLMGuardian(
                default_verification_level=verification_level,
                default_request_mode=request_mode,
            )

            # Log initialization
            logger.info(
                f"Initialized Gemma connector with LLMGuardian (verification: {verification_level.name}, "
                f"mode: {request_mode.name}, model: {self.model})",
            )
        else:
            self.guardian = None
            logger.info(f"Initialized Gemma connector without LLMGuardian (model: {self.model})")

    def get_llm_name(self) -> str:
        """
        Get the name of the LLM.
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
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Simple approximation: 4 chars = 1 token
            return len(text) // 4

    def _extract_json_from_content(self, content: str) -> dict[str, Any]:
        """
        Extract JSON from text response.

        Args:
            content (str): The response content

        Returns:
            Dict[str, Any]: The parsed JSON or an error dict
        """
        content = content.strip()

        # Try to find JSON in the response
        json_start = content.find("{")
        json_end = content.rfind("}")

        if json_start >= 0 and json_end >= 0:
            json_content = content[json_start : json_end + 1]

            # Try to parse the JSON
            try:
                return json.loads(json_content)
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON response: {e}")
                return {
                    "error": True,
                    "error_message": f"Failed to parse JSON: {e!s}",
                    "content": content[:300] + ("..." if len(content) > 300 else ""),
                }
        else:
            logger.warning(f"No JSON found in response: {content[:100]}...")
            return {
                "error": True,
                "error_message": "No valid JSON found in response",
                "content": content[:300] + ("..." if len(content) > 300 else ""),
            }

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
        # Log submission details
        ic("Submitting prompt to Gemma")
        ic(f"Using model: {self.model}")
        ic(f"System prompt length: {len(prompt['system'])}")
        ic(f"User prompt length: {len(prompt['user'])}")

        # Get response schema
        response_schema = LLMTranslateQueryResponse.model_json_schema()

        # If using guardian, process through it
        if self.use_guardian and self.guardian:
            # Combine system and user prompts into a format for the guardian
            combined_prompt = {
                "system": prompt["system"],
                "user": prompt["user"],
            }

            # Generate a unique request ID
            request_id = f"gemma_{int(time.time() * 1000)}_{hash(str(prompt)) % 10000}"

            # Get completion from the guardian
            try:
                # Add JSON schema instruction to the prompt
                combined_prompt[
                    "user"
                ] += f"\n\nPlease respond with a valid JSON according to the following schema:\n{json.dumps(response_schema, indent=2)}"

                # Process through guardian
                completion_text, metadata = self.guardian.get_completion_from_prompt(
                    prompt=json.dumps(combined_prompt),
                    provider="gemma",
                    model=self.model,
                    optimize=True,
                    options={
                        "temperature": temperature,
                        "max_tokens": 2000,
                    },
                )

                # Check if the request was blocked
                if completion_text is None:
                    ic(f"Request blocked by guardian: {metadata.get('block_reason', 'Unknown reason')}")
                    return LLMTranslateQueryResponse(
                        query=prompt.get("query", ""),
                        translated_query="",
                        explanation=f"Request blocked by LLMGuardian: {metadata.get('block_reason', 'Unknown reason')}",
                        error=True,
                        error_message=metadata.get("block_reason", "Unknown reason"),
                    )

                # Try to extract JSON from the response content
                json_data = self._extract_json_from_content(completion_text)

                # Check if there was an error
                if json_data.get("error", False):
                    return LLMTranslateQueryResponse(
                        query=prompt.get("query", ""),
                        translated_query="",
                        explanation=f"Error processing response: {json_data.get('error_message', 'Unknown error')}",
                        error=True,
                        error_message=json_data.get("error_message", "Unknown error"),
                    )

                # Parse response and return
                return LLMTranslateQueryResponse(**json_data)

            except Exception as e:
                ic(f"Error generating query with guardian: {e}")
                return LLMTranslateQueryResponse(
                    query=prompt.get("query", ""),
                    translated_query="",
                    explanation=f"Error: {e!s}",
                    error=True,
                    error_message=str(e),
                )

        # If not using guardian, use the standard implementation
        try:
            # For Gemma and similar models via LM Studio, we'll use the combined system+user format
            # as a single message because some models don't support system messages
            combined_prompt = dedent(
                f"""
                System: {prompt['system']}\n\nUser: {prompt['user']}\n\n
                Please respond with a valid JSON according to the following schema:
                \n{json.dumps(response_schema, indent=2)}
                """,
            )

            start_time = time.time()
            ic("Starting Gemma API call")

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

            except Exception as e:
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

            # Process response and extract JSON
            json_data = self._extract_json_from_content(content)

            # Check if there was an error
            if json_data.get("error", False):
                return LLMTranslateQueryResponse(
                    query=prompt.get("query", ""),
                    translated_query="",
                    explanation=f"Error processing response: {json_data.get('error_message', 'Unknown error')}",
                    error=True,
                    error_message=json_data.get("error_message", "Unknown error"),
                )

            # Create and return the response object
            return LLMTranslateQueryResponse(**json_data)

        except Exception as e:
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
        if self.use_guardian and self.guardian:
            # Create a template-based prompt for the guardian
            template = f"Summarize the following text in no more than {max_length} words:\n\n{{text}}"

            # Create the variable list
            variables = [
                PromptVariable(name="text", value=text),
            ]

            # Get completion from the guardian
            completion_text, _ = self.guardian.get_completion_from_prompt(
                prompt=template,
                provider="gemma",
                model=self.model,
                system_prompt="You are a helpful assistant that facilitates finding relevant files in a unified personal index of storage.",
                options={
                    "max_tokens": max_length * 5,  # Rough estimate for token count
                },
            )

            return completion_text or "Error generating summary with guardian"

        # Fall back to original implementation if guardian not enabled
        prompt = f"Summarize the following text in no more than {max_length} words:\n\n{text}"
        try:
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
            except Exception as e:
                ic(f"Error in summarize_text (chat): {e}")
                # Try the completions API as fallback
                response = self.client.completions.create(
                    model=self.model,
                    prompt=f"You are a helpful assistant that facilitates finding relevant files in a unified personal index of storage.\n\n{prompt}",
                    max_tokens=max_length * 2,  # Rough estimate of token count
                )
                return response.choices[0].text.strip()
        except Exception as e:
            ic(f"Error in summarize_text: {e}")
            return f"Error generating summary: {e!s}"

    def extract_keywords(self, text: str, num_keywords: int = 5) -> list[str]:
        """
        Extract keywords from the given text using the Gemma model.

        Args:
            text (str): The text to extract keywords from
            num_keywords (int): The number of keywords to extract

        Returns:
            list[str]: The extracted keywords
        """
        if self.use_guardian and self.guardian:
            # Create a template-based prompt for the guardian
            template = f"Extract exactly {num_keywords} keywords from the following text. Respond with just a comma-separated list of keywords, nothing else:\n\n{{text}}"

            # Create the variable list
            variables = [
                PromptVariable(name="text", value=text),
            ]

            # Get completion from the guardian
            completion_text, _ = self.guardian.get_completion_from_prompt(
                prompt=template,
                provider="gemma",
                model=self.model,
                system_prompt="You are a helpful assistant that extracts keywords from text.",
                options={
                    "max_tokens": 100,
                },
            )

            if completion_text:
                # Parse the comma-separated list
                keywords = [k.strip() for k in completion_text.split(",")]
                return keywords[:num_keywords]  # Ensure we don't exceed requested number
            return ["Error extracting keywords with guardian"]

        # Fall back to original implementation if guardian not enabled
        prompt = f"Extract {num_keywords} keywords from the following text:\n\n{text}"
        try:
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
            except Exception as e:
                ic(f"Error in extract_keywords (chat): {e}")
                # Try the completions API as fallback
                response = self.client.completions.create(
                    model=self.model,
                    prompt=f"You are a helpful assistant that extracts keywords from text.\n\n{prompt}",
                    max_tokens=100,
                )
                content = response.choices[0].text.strip()

            # Parse the response
            if "," in content:
                keywords = content.split(",")
            else:
                # Try to find words wrapped in quotes or separated by newlines
                import re

                keywords = re.findall(r'[\'"](.*?)[\'"]|^([^\n]+)$', content, re.MULTILINE)
                # Flatten and clean the results
                keywords = [match[0] or match[1] for match in keywords if match[0] or match[1]]

            return [keyword.strip() for keyword in keywords[:num_keywords]]

        except Exception as e:
            ic(f"Error in extract_keywords: {e}")
            return [str(e)]

    def classify_text(self, text: str, categories: list[str]) -> str:
        """
        Classify the given text into one of the provided categories using the Gemma model.

        Args:
            text (str): The text to classify
            categories (list[str]): The list of possible categories

        Returns:
            str: The predicted category
        """
        if self.use_guardian and self.guardian:
            # Create a template-based prompt for the guardian
            categories_str = ", ".join(categories)
            template = f"Classify the following text into exactly one of these categories: {categories_str}\n\nRespond with only the category name, nothing else.\n\nText: {{text}}"

            # Create the variable list
            variables = [
                PromptVariable(name="text", value=text),
            ]

            # Get completion from the guardian
            completion_text, _ = self.guardian.get_completion_from_prompt(
                prompt=template,
                provider="gemma",
                model=self.model,
                system_prompt="You are a helpful assistant that classifies text.",
                options={
                    "max_tokens": 50,
                },
            )

            return completion_text or "Error classifying text with guardian"

        # Fall back to original implementation if guardian not enabled
        categories_str = ", ".join(categories)
        prompt = f"Classify the following text into one of these categories: {categories_str}\n\nText: {text}"
        try:
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
            except Exception as e:
                ic(f"Error in classify_text (chat): {e}")
                # Try the completions API as fallback
                response = self.client.completions.create(
                    model=self.model,
                    prompt=f"You are a helpful assistant that classifies text.\n\n{prompt}",
                    max_tokens=50,
                )
                return response.choices[0].text.strip()
        except Exception as e:
            ic(f"Error in classify_text: {e}")
            return str(e)

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
        if self.use_guardian and self.guardian:
            # Convert the question and context into a template format
            template = "Context: {context}\n\nUser query: {question}\n\nRespond with a valid JSON following this schema:\n{schema}"

            # Create the variable list
            variables = [
                PromptVariable(name="context", value=context),
                PromptVariable(name="question", value=question),
                PromptVariable(name="schema", value=json.dumps(schema, indent=2)),
            ]

            # Get completion from the guardian
            completion_text, _ = self.guardian.get_completion_from_prompt(
                prompt=template,
                provider="gemma",
                model=self.model,
                system_prompt="You are a helpful assistant that always responds with valid JSON.",
                options={
                    "temperature": 0,
                    "max_tokens": 1000,
                },
            )

            if completion_text:
                # Extract JSON from the response
                json_data = self._extract_json_from_content(completion_text)
                return json_data

            return {"error": "No response from guardian", "answer": None}

        # Fall back to original implementation if guardian not enabled
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
            except Exception as e:
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

            # Extract JSON from the response
            return self._extract_json_from_content(content)

        except Exception as e:
            ic(f"Error in answer_question: {type(e).__name__}: {e}")
            return {"error": f"Error in answer_question: {type(e).__name__}: {e!s}"}

    def get_completion(
        self,
        system_prompt: str | None = None,
        user_prompt: str = "",
        **kwargs: Any,
    ) -> tuple[str, dict[str, Any]]:
        """
        Get a simple completion for a prompt from Gemma.

        This method is designed to work with the LLMFactory interface and
        provides a standardized way to get completions with token tracking.

        Args:
            system_prompt: The system prompt to control the model's behavior
            user_prompt: The user's query or input
            **kwargs: Additional parameters for the model

        Returns:
            Tuple of (completion text, metadata)
        """
        # Extract options from kwargs
        temperature = kwargs.get("temperature", 0)
        max_tokens = kwargs.get("max_tokens", 1000)

        # Generate a request ID for tracking
        request_id = f"gemma_{int(time.time() * 1000)}_{hash(user_prompt) % 10000}"

        # Start with basic metadata
        metadata = {
            "request_id": request_id,
            "provider": "gemma",
            "model": self.model,
            "tokens": {"prompt": None, "completion": None, "total": None},
        }

        # Process through guardian if enabled
        if self.use_guardian and self.guardian:
            # Set up the prompt structure
            if system_prompt:
                prompt_text = {
                    "system": system_prompt,
                    "user": user_prompt,
                }
                prompt_str = json.dumps(prompt_text)
            else:
                # For simple prompts without system prompt
                prompt_str = user_prompt

            # Get options
            options = {
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            options.update({k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]})

            # Get completion through guardian
            completion_text, guardian_metadata = self.guardian.get_completion_from_prompt(
                prompt=prompt_str,
                provider="gemma",
                model=self.model,
                optimize=True,
                options=options,
            )

            # Update metadata with guardian info
            metadata.update(
                {
                    "verification": guardian_metadata.get("verification", {}),
                    "token_metrics": guardian_metadata.get("token_metrics", {}),
                    "total_time_ms": guardian_metadata.get("total_time_ms"),
                    "guardian_used": True,
                },
            )

            return completion_text or "", metadata

        # Direct completion without guardian
        try:
            start_time = time.time()

            # For Gemma through LM Studio, combine system and user prompts if needed
            if system_prompt:
                combined_prompt = f"System: {system_prompt}\n\nUser: {user_prompt}"
            else:
                combined_prompt = user_prompt

            try:
                # Try chat completions first
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": combined_prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                completion_text = response.choices[0].message.content.strip()
            except Exception as e:
                ic(f"Chat completion failed: {e}, trying regular completion")
                # Fall back to regular completions
                response = self.client.completions.create(
                    model=self.model,
                    prompt=combined_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                completion_text = response.choices[0].text.strip()

            # Calculate time taken
            elapsed_time_ms = int((time.time() - start_time) * 1000)

            # Update metadata
            metadata.update(
                {
                    "total_time_ms": elapsed_time_ms,
                    "guardian_used": False,
                },
            )

            # Estimate token usage since LM Studio doesn't provide exact counts
            if self.tokenizer:
                prompt_tokens = self._count_tokens(combined_prompt)
                completion_tokens = self._count_tokens(completion_text)
                metadata["tokens"] = {
                    "prompt": prompt_tokens,
                    "completion": completion_tokens,
                    "total": prompt_tokens + completion_tokens,
                }

            return completion_text, metadata

        except Exception as e:
            ic(f"Error in get_completion: {e!s}")
            metadata["error"] = str(e)
            return f"Error: {e!s}", metadata

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
        if self.use_guardian and self.guardian:
            # Use the guardian for the completion
            completion_text, _ = self.guardian.get_completion_from_prompt(
                prompt=prompt,
                provider="gemma",
                model=self.model,
                system_prompt="You are a helpful assistant.",
                options={
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )

            return completion_text or "Error generating text with guardian"

        # Fall back to original implementation if guardian not enabled
        try:
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
            except Exception as e:
                ic(f"Chat completion failed: {e}, trying regular completion")
                # Fall back to regular completions
                response = self.client.completions.create(
                    model=self.model,
                    prompt=f"You are a helpful assistant.\n\n{prompt}",
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.choices[0].text.strip()
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

        if self.use_guardian and self.guardian:
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
                provider="gemma",
                model=self.model,
                system_prompt="You are a semantic analysis assistant. Always respond with valid JSON.",
                options={
                    "temperature": 0,
                    "max_tokens": 1000,
                },
            )

            if completion_text:
                # Extract JSON from the response
                json_data = self._extract_json_from_content(completion_text)

                # Check if there was an error
                if json_data.get("error", False):
                    return {attr: [] for attr in attr_types}

                # Filter to only include requested attribute types
                return {k: v for k, v in json_data.items() if k in attr_types}

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
            except Exception as e:
                ic(f"Chat completion failed: {e}, trying regular completion")
                # Fall back to regular completions
                response = self.client.completions.create(
                    model=self.model,
                    prompt=f"You are a semantic analysis assistant.\n\n{prompt}\n\nRespond with a valid JSON object.",
                    temperature=0,
                    max_tokens=1000,
                )
                content = response.choices[0].text

            # Extract JSON from the response
            json_data = self._extract_json_from_content(content)

            # Check if there was an error
            if json_data.get("error", False):
                return {attr: [] for attr in attr_types}

            # Filter to only include requested attribute types
            return {k: v for k, v in json_data.items() if k in attr_types}

        except Exception as e:
            ic(f"Error extracting semantic attributes: {e}")
            # Return a minimal valid response
            return {attr: [] for attr in attr_types}
