"""
Google Gemini connector for the Indaleko system with prompt management integration.

This module provides a connector for Google's Gemini models with integrated
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

# Create logger
logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types
except ImportError:
    ic("Warning: Google Generative AI Python SDK not installed. Please run: pip install google-genai")
    genai = None
    types = None

# pylint: enable=wrong-import-position


class GoogleConnector(IndalekoLLMBase):
    """
    Connector for Google's Gemini models with integrated prompt management.

    This connector supports both direct access and guardian-managed modes,
    with comprehensive token tracking and security verification.
    """

    llm_name = "Gemini"

    def __init__(self, **kwargs: dict) -> None:
        """
        Initialize the Google Gemini connector.

        Args:
            kwargs: Additional optional parameters
                - api_key (str): The Google API key
                - model (str): The name of the Gemini model to use
                    (default: "gemini-2.0-flash")
                - max_tokens (int): Maximum tokens for prompts (default: 100000)
                - use_guardian (bool): Whether to use LLMGuardian (default: True)
                - verification_level (str): Verification level for prompts (default: "STANDARD")
                - request_mode (str): Request mode for handling verification results (default: "WARN")
        """
        self.api_key = kwargs.get("api_key")
        self.model = kwargs.get("model", "gemini-2.0-flash")

        # Configuration for tokens and generation
        self.max_tokens = int(kwargs.get("max_tokens", 100000))

        # Initialize the Google Generative AI client
        if not genai:
            logger.error("Google Generative AI Python SDK not installed. Please run: pip install google-genai")
            self.client = None
        else:
            try:
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"Google Gemini client initialized successfully with model {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize Google Gemini client: {e}")
                self.client = None

        # Initialize tokenizer (Use tiktoken as a fallback for token estimation)
        try:
            import tiktoken

            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except (ImportError, ValueError):
            logger.warning("tiktoken not installed or encoding not found. Token estimation will be approximate.")
            self.tokenizer = None

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
        Generate a query using the Gemini model.

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
                explanation="Error: Google Gemini client not initialized. Please check API key and SDK installation.",
                error=True,
                error_message="Client not initialized",
            )

        # Log submission details
        ic("Submitting prompt to Google Gemini")
        ic(f"Using model: {self.model}")
        ic(f"System prompt length: {len(prompt['system'])}")
        ic(f"User prompt length: {len(prompt['user'])}")

        # Get response schema
        response_schema = LLMTranslateQueryResponse.model_json_schema()

        # For Gemini, we'll combine system and user prompts
        full_prompt = f"{prompt['system']}\n\n{prompt['user']}\n\nPlease respond with a valid JSON according to the following schema:\n{json.dumps(response_schema, indent=2)}"

        # Create Google GenAI types.ContentUnion input
        content = types.Content(parts=[types.Part.from_text(text=full_prompt)])

        start_time = time.time()
        ic("Starting Google Gemini API call")

        # Create the generation config
        generation_config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=self.max_tokens,
            response_mime_type="application/json",
        )

        # Call the model
        response = self.client.models.generate_content(model=self.model, contents=content, config=generation_config)

        elapsed_time = time.time() - start_time
        ic(f"Google Gemini API call completed in {elapsed_time:.2f} seconds")
        ic("Received response from Google Gemini")

        # Extract content from response
        content_text = response.text

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

    def summarize_text(self, text: str, max_length: int = 100) -> str:
        """
        Summarize the given text using the Gemini model.

        Args:
            text (str): The text to summarize
            max_length (int): The maximum length of the summary

        Returns:
            str: The summarized text
        """
        # Check if client is initialized
        if not self.client:
            return "Error: Google Gemini client not initialized. Please check API key and SDK installation."

        # Fall back to original implementation if guardian not enabled
        prompt = f"Summarize the following text in no more than {max_length} words:\n\n{text}"
        # Create generation config
        generation_config = types.GenerateContentConfig(
            max_output_tokens=max_length * 5,  # Rough estimate
            temperature=0,
        )

        # Call the model
        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_text(text="You are a helpful assistant that provides concise summaries."),
                    ],
                    role="system",
                ),
                types.Content(
                    parts=[
                        types.Part.from_text(text=prompt),
                    ],
                    role="user",
                ),
            ],
            config=generation_config,
        )

        return response.text

    def extract_keywords(self, text: str, num_keywords: int = 5) -> list[str]:
        """
        Extract keywords from the given text using the Gemini model.

        Args:
            text (str): The text to extract keywords from
            num_keywords (int): The number of keywords to extract

        Returns:
            list[str]: The extracted keywords
        """
        # Check if client is initialized
        if not self.client:
            return ["Error: Google Gemini client not initialized. Please check API key and SDK installation."]

        prompt = f"Extract exactly {num_keywords} keywords from the following text. Respond with just a comma-separated list of keywords, nothing else:\n\n{text}"
        # Create generation config
        generation_config = types.GenerateContentConfig(
            max_output_tokens=100,
            temperature=0,
        )

        # Call the model
        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_text(text="You are a helpful assistant that extracts keywords from text."),
                    ],
                    role="system",
                ),
                types.Content(
                    parts=[
                        types.Part.from_text(text=prompt),
                    ],
                    role="user",
                ),
            ],
            config=generation_config,
        )

        # Parse the comma-separated list
        content = response.text.strip()
        keywords = [k.strip() for k in content.split(",")]
        return keywords[:num_keywords]  # Ensure we don't exceed requested number

    def classify_text(self, text: str, categories: list[str]) -> str:
        """
        Classify the given text into one of the provided categories using the Gemini model.

        Args:
            text (str): The text to classify
            categories (list[str]): The list of possible categories

        Returns:
            str: The predicted category
        """
        # Check if client is initialized
        if not self.client:
            return "Error: Google Gemini client not initialized. Please check API key and SDK installation."

        # Fall back to original implementation if guardian not enabled
        categories_str = ", ".join(categories)
        prompt = f"Classify the following text into exactly one of these categories: {categories_str}\n\nRespond with only the category name, nothing else.\n\nText: {text}"
        # Create generation config
        generation_config = types.GenerateContentConfig(
            max_output_tokens=50,
            temperature=0,
        )

        # Call the model
        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_text(text="You are a helpful assistant that classifies text."),
                    ],
                    role="system",
                ),
                types.Content(
                    parts=[
                        types.Part.from_text(text=prompt),
                    ],
                    role="user",
                ),
            ],
            config=generation_config,
        )

        return response.text.strip()

    def answer_question(
        self,
        context: str,
        question: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Answer a question based on the given context using the Gemini model.

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
                "error": "Google Gemini client not initialized. Please check API key and SDK installation.",
                "answer": None,
            }

        prompt = f"Context: {context}\n\nUser query: {question}\n\nRespond with a valid JSON following this schema:\n{json.dumps(schema, indent=2)}"
        ic("Starting answer_question call to Google Gemini")
        start_time = time.time()

        # Create generation config
        generation_config = types.GenerateContentConfig(
            max_output_tokens=1000,
            temperature=0,
            response_mime_type="application/json",
        )

        # Call the model
        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_text(
                            text="You are a helpful assistant that always responds with valid JSON.",
                        ),
                    ],
                    role="system",
                ),
                types.Content(
                    parts=[
                        types.Part.from_text(text=prompt),
                    ],
                    role="user",
                ),
            ],
            config=generation_config,
        )

        elapsed_time = time.time() - start_time
        ic(f"answer_question API call completed in {elapsed_time:.2f} seconds")

        # Extract JSON from the response
        return self._extract_json_from_content(response.text)

    def get_completion(
        self,
        system_prompt: str | None = None,
        user_prompt: str = "",
        **kwargs: Any,
    ) -> tuple[str, dict[str, Any]]:
        """
        Get a simple completion for a prompt from Gemini.

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
                "Error: Google Gemini client not initialized. Please check API key and SDK installation.",
                {"error": "Client not initialized"},
            )

        # Extract options from kwargs
        temperature = kwargs.get("temperature", 0)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)

        # Generate a request ID for tracking
        request_id = f"google_{int(time.time() * 1000)}_{hash(user_prompt) % 10000}"

        # Start with basic metadata
        metadata = {
            "request_id": request_id,
            "provider": "google",
            "model": self.model,
            "tokens": {"prompt": None, "completion": None, "total": None},
        }

        start_time = time.time()

        # Create generation config
        generation_config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        )

        # Create contents based on whether we have a system prompt
        if system_prompt:
            contents = [
                types.Content(
                    parts=[
                        types.Part.from_text(text=system_prompt),
                    ],
                    role="system",
                ),
                types.Content(
                    parts=[
                        types.Part.from_text(text=user_prompt),
                    ],
                    role="user",
                ),
            ]
        else:
            contents = [
                types.Content(
                    parts=[
                        types.Part.from_text(text=user_prompt),
                    ],
                    role="user",
                ),
            ]

        # Call the model
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=generation_config,
        )

        # Calculate time taken
        elapsed_time_ms = int((time.time() - start_time) * 1000)

        # Extract the response content
        completion_text = response.text.strip()

        # Update metadata
        metadata.update(
            {
                "total_time_ms": elapsed_time_ms,
                "guardian_used": False,
            },
        )

        # Estimate token usage
        if self.tokenizer:
            prompt_text = f"{system_prompt or ''}\n\n{user_prompt}"
            prompt_tokens = self._count_tokens(prompt_text)
            completion_tokens = self._count_tokens(completion_text)
            metadata["tokens"] = {
                "prompt": prompt_tokens,
                "completion": completion_tokens,
                "total": prompt_tokens + completion_tokens,
            }

        return completion_text, metadata

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
            return "Error: Google Gemini client not initialized. Please check API key and SDK installation."

        # Create generation config
        generation_config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        )

        # Call the model
        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_text(text="You are a helpful assistant."),
                    ],
                    role="system",
                ),
                types.Content(
                    parts=[
                        types.Part.from_text(text=prompt),
                    ],
                    role="user",
                ),
            ],
            config=generation_config,
        )

        return response.text.strip()

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

        attr_types_str = ", ".join(attr_types)
        prompt = f"""Extract the following semantic attributes from the text: {attr_types_str}

For each attribute type, provide relevant information found in the text.
Format your response as a JSON object with keys matching the requested attribute types.

Text to analyze:
{text}
        """
