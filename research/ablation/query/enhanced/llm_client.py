#!/usr/bin/env python3
"""
Simple LLM client for testing and development.

This module provides a basic, standalone LLM client that works specifically for
the ablation testing framework without requiring the full Indaleko LLM infrastructure.
"""

import configparser
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Set up paths to find Indaleko root
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (current_path / "Indaleko.py").exists():
        current_path = current_path.parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# Try to import Anthropic library
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    logger.warning("Anthropic Python SDK not installed. Please run: pip install anthropic")
    ANTHROPIC_AVAILABLE = False


def load_api_key(provider: str = "anthropic") -> str:
    """
    Load the API key from environment variables or the config file.

    Args:
        provider: The LLM provider name (e.g., "anthropic", "openai")

    Returns:
        The API key

    Raises:
        ValueError: If the API key cannot be found
    """
    # Try to load from environment variable first
    env_var = f"{provider.upper()}_API_KEY"
    api_key = os.environ.get(env_var)
    if api_key:
        return api_key

    # Try to load from config file
    indaleko_root = os.environ.get("INDALEKO_ROOT")
    config_dir = os.path.join(indaleko_root, "config")
    key_path = os.path.join(config_dir, "llm-keys.ini")

    if not os.path.exists(key_path):
        raise ValueError(f"Config file not found: {key_path}")

    # Parse the config file
    config = configparser.ConfigParser()
    config.read(key_path)

    # Check if section exists
    if provider not in config:
        raise ValueError(f"Provider '{provider}' not found in config file")

    # Check if api_key exists in section
    if "api_key" not in config[provider]:
        raise ValueError(f"API key for '{provider}' not found in config file")

    # Get the API key
    api_key = config[provider]["api_key"]

    # Clean up quotes if present
    if api_key and api_key[0] in ["'", '"'] and api_key[-1] in ["'", '"']:
        api_key = api_key[1:-1]

    if not api_key or api_key == "Not Required":
        raise ValueError(f"No valid API key found for '{provider}'")

    return api_key


class SimpleLLMClient:
    """Simple client for LLM APIs without the full Indaleko infrastructure."""

    def __init__(
        self,
        model: str = "claude-3-7-sonnet-latest",
        api_key: Optional[str] = None,
        max_tokens: int = 2000,
    ):
        """
        Initialize the simple LLM client.

        Args:
            model: Model name to use
            api_key: API key (if None, will load from config or environment)
            max_tokens: Maximum tokens for generation
        """
        self.model = model
        self.max_tokens = max_tokens
        self.client = None

        # Check if Anthropic SDK is available
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic SDK not available. Install with: pip install anthropic")

        # Get API key from args, environment, or config file
        if api_key is None:
            try:
                api_key = load_api_key("anthropic")
            except ValueError as e:
                raise ValueError(f"Failed to load Anthropic API key: {e}")

        self.client = anthropic.Anthropic(api_key=api_key)

    def get_completion(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Get a completion from the LLM.

        Args:
            user_prompt: User prompt text
            system_prompt: Optional system prompt
            temperature: Generation temperature
            max_tokens: Optional override for max tokens
            **kwargs: Additional provider-specific arguments

        Returns:
            The completion text
        """
        if not self.client:
            raise ValueError("Anthropic client not initialized")

        try:
            # Create message parameters with required parameters
            message_params = {
                "model": self.model,
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": user_prompt}],
                "stream": False,  # Critical to avoid the 10-minute streaming warning
            }

            # Add system prompt if provided
            if system_prompt:
                message_params["system"] = system_prompt

            # Add any extra parameters
            for key, value in kwargs.items():
                if key not in message_params:
                    message_params[key] = value

            # Create the message
            message = self.client.messages.create(**message_params)

            # Extract text from response
            if hasattr(message, "content") and message.content:
                content = message.content[0].text
                return content
            else:
                logger.error("Unexpected content format in Claude response")
                return "Error: Unexpected content format in Claude response"

        except Exception as e:
            logger.error(f"Error getting completion from Anthropic: {e}")
            return f"Error: {str(e)}"
    
    def generate_queries_for_activity_type(
        self,
        activity_type: str,
        count: int = 5,
        temperature: float = 0.7,
    ) -> list[str]:
        """
        Generate queries for a specific activity type.
        
        Args:
            activity_type: String name of the activity type (e.g., "music", "location")
            count: Number of queries to generate
            temperature: Temperature for generation (higher = more creative)
            
        Returns:
            List of query strings for the activity type
        """
        # Create activity type description
        activity_descriptions = {
            "music": "music listening activities (e.g., songs, artists, albums, playlists)",
            "location": "location activities (e.g., places, coordinates, visits)",
            "task": "task management activities (e.g., to-dos, projects, deadlines)",
            "collaboration": "collaboration activities (e.g., meetings, shared documents, messages)",
            "storage": "storage activities (e.g., file operations, downloads, folders)",
            "media": "media consumption activities (e.g., videos, streaming services, content)",
        }
        
        description = activity_descriptions.get(
            activity_type.lower(), 
            f"{activity_type} activities"
        )
        
        # Set up system and user prompts
        system_prompt = f"""You are an expert at generating realistic search queries for {description}.
Your queries should capture how real users would search for files based on their {activity_type} activities.
Make the queries diverse in structure, length, and complexity.
"""

        user_prompt = f"""Generate {count} realistic search queries related to {description}.

Each query should be something a person might type to find files or documents related to their {activity_type} activities.
Make the queries diverse in format, structure, and complexity.
Some should be questions, some commands, some just keywords.
Vary the length from very short (2-3 words) to longer complex queries.

Just list {count} different search queries, numbered from 1 to {count}.
"""

        # Generate queries using our get_completion method
        response = self.get_completion(
            user_prompt=user_prompt, 
            system_prompt=system_prompt, 
            temperature=temperature
        )
        
        logger.info(f"Got response of length {len(response)} for {activity_type} queries")
        
        # Parse the response
        queries = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                # Remove the number/bullet and any trailing punctuation
                query = line.split(".", 1)[-1].strip() if "." in line else line
                query = query.split(")", 1)[-1].strip() if ")" in line else query
                query = query.lstrip("- ").strip()
                if query:
                    queries.append(query)
        
        # If parsing failed or returned no queries, fail immediately (fail-stop approach)
        if not queries:
            logger.error("CRITICAL: Failed to parse queries from LLM response")
            logger.error("This is required for proper ablation testing - fix the query generator")
            sys.exit(1)  # Fail-stop immediately - no fallbacks
        
        logger.info(f"Generated {len(queries)} queries for {activity_type}")
        
        # Limit to requested count
        return queries[:count]
        
    def generate_queries(self, activity_type: str, count: int = 5) -> list[str]:
        """Alias for generate_queries_for_activity_type for compatibility with the original interface."""
        return self.generate_queries_for_activity_type(activity_type, count)