"""
Grok connector for the Indaleko system with prompt management integration.

This module provides a connector for xAI's Grok models with integrated
prompt management capabilities.

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

# Import the prompt management components
from query.utils.prompt_management.guardian.llm_guardian import (
    LLMGuardian,
    LLMRequestMode,
    VerificationLevel,
)
from query.utils.prompt_management.prompt_manager import PromptVariable

# Create logger
logger = logging.getLogger(__name__)

try:
    import openai
except ImportError:
    ic("Warning: OpenAI Python SDK not installed. Please run: pip install openai")
    openai = None

# pylint: enable=wrong-import-position


class GrokConnector(IndalekoLLMBase):
    """
    Connector for xAI's Grok models with integrated prompt management.

    This connector supports both direct access and guardian-managed modes,
    with comprehensive token tracking and security verification.

    Grok uses an OpenAI-compatible API interface, so we can leverage much of
    the same code structure but with specific customizations for Grok models.
    """

    llm_name = "Grok"

    def __init__(self, **kwargs: dict) -> None:
        """
        Initialize the Grok connector.

        Args:
            kwargs: Additional optional parameters
                - api_key (str): The Grok API key
                - api_base (str): The Grok API base URL (default: https://api.grok.x/v1)
                - model (str): The name of the Grok model to use
                    (default: "grok-1")
                - max_tokens (int): Maximum tokens for prompts (default: 8192)
                - use_guardian (bool): Whether to use LLMGuardian (default: True)
                - verification_level (str): Verification level for prompts (default: "STANDARD")
                - request_mode (str): Request mode for handling verification results (default: "WARN")
        """
        self.api_key = kwargs.get("api_key")
        self.api_base = kwargs.get("api_base", "https://api.grok.x/v1")
        self.model = kwargs.get("model", "grok-1")

        # Configuration for tokens and generation
        self.max_tokens = int(kwargs.get("max_tokens", 8192))

        # Prompt management configuration
        self.use_guardian = kwargs.get("use_guardian", True)

        # Initialize the OpenAI client
        if not openai:
            logger.error("OpenAI Python SDK not installed. Please run: pip install openai")
            self.client = None
        else:
            try:
                self.client = openai.OpenAI(
                    api_key=self.api_key,
                    base_url=self.api_base,
                )
                logger.info(f"Grok client initialized successfully with model {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize Grok client: {e}")
                self.client = None

        # Initialize tokenizer (Using tiktoken for token estimation, same as OpenAI)
        try:
            import tiktoken

            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except (ImportError, ValueError):
            logger.warning("tiktoken not installed or encoding not found. Token estimation will be approximate.")
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
                f"Initialized Grok connector with LLMGuardian (verification: {verification_level.name}, "
                f"mode: {request_mode.name}, model: {self.model})",
            )
        else:
            self.guardian = None
            logger.info(f"Initialized Grok connector without LLMGuardian (model: {self.model})")

    def get_llm_name(self) -> str:
        """
        Get the name of the LLM provider.

        Returns:
            str: The name of the LLM provider.
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
        Generate a query using the Grok model.

        Args:
            prompt (Dict[str, str]): The prompt to generate the query from
                Should contain 'system' and 'user' keys
            temperature (float): Temperature parameter for generation

        Returns:
            LLMTranslateQueryResponse: The generated query response
        """
        # Check if client is initialized
        if not self.client:
            return LLMTranslateQueryResponse(
                query="",
                translated_query="",
                explanation="Error: Grok client not initialized. Please check API key and SDK installation.",
                error=True,
                error_message="Client not initialized",
            )

        # Log submission details
        ic("Submitting prompt to Grok")
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
            request_id = f"grok_{int(time.time() * 1000)}_{hash(str(prompt)) % 10000}"

            # Get completion from the guardian
            try:
                # Add JSON schema instruction to the prompt
                combined_prompt[
                    "user"
                ] += f"\n\nPlease respond with a valid JSON according to the following schema:\n{json.dumps(response_schema, indent=2)}"

                # Process through guardian
                completion_text, metadata = self.guardian.get_completion_from_prompt(
                    prompt=json.dumps(combined_prompt),
                    provider="grok",
                    model=self.model,
                    optimize=True,
                    options={
                        "temperature": temperature,
                        "max_tokens": self.max_tokens,
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
            start_time = time.time()
            ic("Starting Grok API call")

            # Create the messages format that OpenAI API expects
            messages = [
                {"role": "system", "content": prompt["system"]},
                {
                    "role": "user",
                    "content": f"{prompt['user']}\n\nPlease respond with a valid JSON according to the following schema:\n{json.dumps(response_schema, indent=2)}",
                },
            ]

            # Call the model
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
            )

            elapsed_time = time.time() - start_time
            ic(f"Grok API call completed in {elapsed_time:.2f} seconds")
            ic("Received response from Grok")

            # Extract content from response
            content_text = response.choices[0].message.content

            # Process response and extract JSON
            json_data = self._extract_json_from_content(content_text)

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
            ic(f"Grok API error: {e!s}")
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
        Summarize the given text using the Grok model.

        Args:
            text (str): The text to summarize
            max_length (int): The maximum length of the summary

        Returns:
            str: The summarized text
        """
        # Check if client is initialized
        if not self.client:
            return "Error: Grok client not initialized. Please check API key and SDK installation."

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
                provider="grok",
                model=self.model,
                system_prompt="You are a helpful assistant that provides concise summaries.",
                options={
                    "max_tokens": max_length * 5,  # Rough estimate for token count
                },
                variables=variables,
            )

            return completion_text or "Error generating summary with guardian"

        # Fall back to original implementation if guardian not enabled
        prompt = f"Summarize the following text in no more than {max_length} words:\n\n{text}"
        try:
            # Create the messages
            messages = [
                {"role": "system", "content": "You are a helpful assistant that provides concise summaries."},
                {"role": "user", "content": prompt},
            ]

            # Call the model
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_length * 5,  # Rough estimate
                temperature=0,
            )

            return response.choices[0].message.content

        except Exception as e:
            ic(f"Error in summarize_text: {e}")
            return f"Error generating summary: {e!s}"

    def extract_keywords(self, text: str, num_keywords: int = 5) -> list[str]:
        """
        Extract keywords from the given text using the Grok model.

        Args:
            text (str): The text to extract keywords from
            num_keywords (int): The number of keywords to extract

        Returns:
            list[str]: The extracted keywords
        """
        # Check if client is initialized
        if not self.client:
            return ["Error: Grok client not initialized. Please check API key and SDK installation."]

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
                provider="grok",
                model=self.model,
                system_prompt="You are a helpful assistant that extracts keywords from text.",
                options={
                    "max_tokens": 100,
                },
                variables=variables,
            )

            if completion_text:
                # Parse the comma-separated list
                keywords = [k.strip() for k in completion_text.split(",")]
                return keywords[:num_keywords]  # Ensure we don't exceed requested number
            return ["Error extracting keywords with guardian"]

        # Fall back to original implementation if guardian not enabled
        prompt = f"Extract exactly {num_keywords} keywords from the following text. Respond with just a comma-separated list of keywords, nothing else:\n\n{text}"
        try:
            # Create the messages
            messages = [
                {"role": "system", "content": "You are a helpful assistant that extracts keywords from text."},
                {"role": "user", "content": prompt},
            ]

            # Call the model
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=100,
                temperature=0,
            )

            # Parse the comma-separated list
            content = response.choices[0].message.content.strip()
            keywords = [k.strip() for k in content.split(",")]
            return keywords[:num_keywords]  # Ensure we don't exceed requested number

        except Exception as e:
            ic(f"Error in extract_keywords: {e}")
            return [str(e)]

    def classify_text(self, text: str, categories: list[str]) -> str:
        """
        Classify the given text into one of the provided categories using the Grok model.

        Args:
            text (str): The text to classify
            categories (list[str]): The list of possible categories

        Returns:
            str: The predicted category
        """
        # Check if client is initialized
        if not self.client:
            return "Error: Grok client not initialized. Please check API key and SDK installation."

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
                provider="grok",
                model=self.model,
                system_prompt="You are a helpful assistant that classifies text.",
                options={
                    "max_tokens": 50,
                },
                variables=variables,
            )

            return completion_text or "Error classifying text with guardian"

        # Fall back to original implementation if guardian not enabled
        categories_str = ", ".join(categories)
        prompt = f"Classify the following text into exactly one of these categories: {categories_str}\n\nRespond with only the category name, nothing else.\n\nText: {text}"
        try:
            # Create the messages
            messages = [
                {"role": "system", "content": "You are a helpful assistant that classifies text."},
                {"role": "user", "content": prompt},
            ]

            # Call the model
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=50,
                temperature=0,
            )

            return response.choices[0].message.content.strip()

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
        Answer a question based on the given context using the Grok model.

        Args:
            context (str): The context to base the answer on
            question (str): The question to answer
            schema (dict[str, Any]): The schema for the response

        Returns:
            dict[str, Any]: The answer to the question
        """
        # Check if client is initialized
        if not self.client:
            return {
                "error": "Grok client not initialized. Please check API key and SDK installation.",
                "answer": None,
            }

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
                provider="grok",
                model=self.model,
                system_prompt="You are a helpful assistant that always responds with valid JSON.",
                options={
                    "temperature": 0,
                    "max_tokens": self.max_tokens,
                },
                variables=variables,
            )

            if completion_text:
                # Extract JSON from the response
                json_data = self._extract_json_from_content(completion_text)
                return json_data

            return {"error": "No response from guardian", "answer": None}

        # Fall back to original implementation if guardian not enabled
        prompt = f"Context: {context}\n\nUser query: {question}\n\nRespond with a valid JSON following this schema:\n{json.dumps(schema, indent=2)}"
        try:
            ic("Starting answer_question call to Grok")
            start_time = time.time()

            # Create the messages
            messages = [
                {"role": "system", "content": "You are a helpful assistant that always responds with valid JSON."},
                {"role": "user", "content": prompt},
            ]

            # Call the model
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1000,
                temperature=0,
                response_format={"type": "json_object"},
            )

            elapsed_time = time.time() - start_time
            ic(f"answer_question API call completed in {elapsed_time:.2f} seconds")

            # Extract JSON from the response
            return self._extract_json_from_content(response.choices[0].message.content)

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
        Get a simple completion for a prompt from Grok.

        This method is designed to work with the LLMFactory interface and
        provides a standardized way to get completions with token tracking.

        Args:
            system_prompt: The system prompt to control the model's behavior
            user_prompt: The user's query or input
            **kwargs: Additional parameters for the model

        Returns:
            Tuple of (completion text, metadata)
        """
        # Check if client is initialized
        if not self.client:
            return (
                "Error: Grok client not initialized. Please check API key and SDK installation.",
                {"error": "Client not initialized"},
            )

        # Extract options from kwargs
        temperature = kwargs.get("temperature", 0)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)

        # Generate a request ID for tracking
        request_id = f"grok_{int(time.time() * 1000)}_{hash(user_prompt) % 10000}"

        # Start with basic metadata
        metadata = {
            "request_id": request_id,
            "provider": "grok",
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
                provider="grok",
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

            # Create messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})

            # Call the model
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            # Calculate time taken
            elapsed_time_ms = int((time.time() - start_time) * 1000)

            # Extract the response content
            completion_text = response.choices[0].message.content.strip()

            # Update metadata
            metadata.update(
                {
                    "total_time_ms": elapsed_time_ms,
                    "guardian_used": False,
                },
            )

            # Add token usage if available from the response
            if hasattr(response, "usage") and response.usage is not None:
                metadata["tokens"] = {
                    "prompt": response.usage.prompt_tokens,
                    "completion": response.usage.completion_tokens,
                    "total": response.usage.total_tokens,
                }
            # Estimate token usage if not available
            elif self.tokenizer:
                prompt_text = f"{system_prompt or ''}\n\n{user_prompt}"
                prompt_tokens = self._count_tokens(prompt_text)
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
        # Check if client is initialized
        if not self.client:
            return "Error: Grok client not initialized. Please check API key and SDK installation."

        if self.use_guardian and self.guardian:
            # Use the guardian for the completion
            completion_text, _ = self.guardian.get_completion_from_prompt(
                prompt=prompt,
                provider="grok",
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
            # Create the messages
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ]

            # Call the model
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            return response.choices[0].message.content.strip()

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
        # Check if client is initialized
        if not self.client:
            return {attr: [] for attr in (attr_types or ["entities", "keywords", "sentiment", "topics"])}

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
                provider="grok",
                model=self.model,
                system_prompt="You are a semantic analysis assistant. Always respond with valid JSON.",
                options={
                    "temperature": 0,
                    "max_tokens": 1000,
                },
                variables=variables,
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

        try:
            # Create the messages
            messages = [
                {"role": "system", "content": "You are a semantic analysis assistant. Always respond with valid JSON."},
                {"role": "user", "content": prompt},
            ]

            # Call the model
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1000,
                temperature=0,
                response_format={"type": "json_object"},
            )

            # Extract JSON from the response
            json_data = self._extract_json_from_content(response.choices[0].message.content)

            # Check if there was an error
            if json_data.get("error", False):
                return {attr: [] for attr in attr_types}

            # Filter to only include requested attribute types
            return {k: v for k, v in json_data.items() if k in attr_types}

        except Exception as e:
            ic(f"Error extracting semantic attributes: {e}")
            # Return a minimal valid response
            return {attr: [] for attr in attr_types}
