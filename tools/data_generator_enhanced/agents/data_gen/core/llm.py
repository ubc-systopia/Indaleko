"""
LLM provider interface for data generation agents.

This module provides a unified interface for different LLM providers
that can be used by data generation agents.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, List, Optional, Union

try:
    from openai import OpenAI, BadRequestError, RateLimitError
except ImportError:
    OpenAI = None

try:
    from anthropic import Anthropic, APIError, RateLimitError as AnthropicRateLimitError
except ImportError:
    Anthropic = None


class LLMProvider(ABC):
    """Base class for LLM providers."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the LLM provider with configuration.

        Args:
            config: Provider-specific configuration
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def generate(self, prompt: str, tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Generate a response or tool call based on the prompt.

        Args:
            prompt: The prompt to send to the LLM
            tools: Optional list of tool definitions

        Returns:
            Response from the LLM
        """
        pass

    @abstractmethod
    def stream_generate(self, prompt: str, tools: Optional[List[Dict[str, Any]]] = None) -> Iterator[Dict[str, Any]]:
        """Stream a response or tool calls based on the prompt.

        Args:
            prompt: The prompt to send to the LLM
            tools: Optional list of tool definitions

        Returns:
            Iterator of response chunks from the LLM
        """
        pass

    def retry_with_backoff(self, func, *args, max_retries: int = 3, base_delay: float = 1.0, **kwargs):
        """Retry a function with exponential backoff.

        Args:
            func: Function to retry
            *args: Arguments to pass to the function
            max_retries: Maximum number of retries
            base_delay: Base delay in seconds
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Result of the function

        Raises:
            Exception: If the function fails after all retries
        """
        retries = 0
        while True:
            try:
                return func(*args, **kwargs)
            except (RateLimitError, AnthropicRateLimitError) as e:
                retries += 1
                if retries > max_retries:
                    self.logger.error(f"Rate limit exceeded after {max_retries} retries")
                    raise

                delay = base_delay * (2 ** (retries - 1))
                self.logger.warning(f"Rate limit exceeded, retrying in {delay} seconds")
                time.sleep(delay)
            except Exception as e:
                self.logger.error(f"Error calling LLM: {str(e)}")
                raise


class OpenAIProvider(LLMProvider):
    """OpenAI implementation of LLM provider."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the OpenAI provider.

        Args:
            config: OpenAI-specific configuration including api_key
        """
        super().__init__(config)

        if OpenAI is None:
            raise ImportError("OpenAI package is not installed. Install it with 'pip install openai'.")

        self.client = OpenAI(api_key=config.get("api_key"))
        self.model = config.get("model", "gpt-4o")
        self.max_tokens = config.get("max_tokens", 4096)
        self.temperature = config.get("temperature", 0.7)

    def generate(self, prompt: str, tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Generate a response or tool call using OpenAI.

        Args:
            prompt: The prompt to send to the LLM
            tools: Optional list of tool definitions

        Returns:
            Response from the LLM
        """
        messages = [{"role": "user", "content": prompt}]

        try:
            if tools:
                response = self.retry_with_backoff(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )

                message = response.choices[0].message

                # Check if there are tool calls
                if message.tool_calls:
                    tool_calls = []
                    for tool_call in message.tool_calls:
                        tool_calls.append({
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        })

                    return {
                        "content": message.content,
                        "tool_calls": tool_calls
                    }

                return {
                    "content": message.content,
                    "tool_calls": []
                }
            else:
                response = self.retry_with_backoff(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )

                return {
                    "content": response.choices[0].message.content,
                    "tool_calls": []
                }
        except Exception as e:
            self.logger.error(f"Error generating with OpenAI: {str(e)}")
            raise

    def stream_generate(self, prompt: str, tools: Optional[List[Dict[str, Any]]] = None) -> Iterator[Dict[str, Any]]:
        """Stream a response or tool calls using OpenAI.

        Args:
            prompt: The prompt to send to the LLM
            tools: Optional list of tool definitions

        Returns:
            Iterator of response chunks from the LLM
        """
        messages = [{"role": "user", "content": prompt}]

        try:
            if tools:
                response = self.retry_with_backoff(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    stream=True
                )

                for chunk in response:
                    if not chunk.choices:
                        continue

                    delta = chunk.choices[0].delta

                    if delta.tool_calls:
                        for tool_call in delta.tool_calls:
                            yield {
                                "type": "tool_call",
                                "id": tool_call.id if tool_call.id else None,
                                "name": tool_call.function.name if tool_call.function and tool_call.function.name else None,
                                "arguments": tool_call.function.arguments if tool_call.function and tool_call.function.arguments else None
                            }

                    if delta.content:
                        yield {
                            "type": "content",
                            "content": delta.content
                        }
            else:
                response = self.retry_with_backoff(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    stream=True
                )

                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield {
                            "type": "content",
                            "content": chunk.choices[0].delta.content
                        }
        except Exception as e:
            self.logger.error(f"Error streaming with OpenAI: {str(e)}")
            raise


class AnthropicProvider(LLMProvider):
    """Anthropic implementation of LLM provider."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the Anthropic provider.

        Args:
            config: Anthropic-specific configuration including api_key
        """
        super().__init__(config)

        if Anthropic is None:
            raise ImportError("Anthropic package is not installed. Install it with 'pip install anthropic'.")

        self.client = Anthropic(api_key=config.get("api_key"))
        self.model = config.get("model", "claude-3-opus-20240229")
        self.max_tokens = config.get("max_tokens", 4096)
        self.temperature = config.get("temperature", 0.7)

    def generate(self, prompt: str, tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Generate a response or tool call using Anthropic.

        Args:
            prompt: The prompt to send to the LLM
            tools: Optional list of tool definitions

        Returns:
            Response from the LLM
        """
        try:
            if tools:
                response = self.retry_with_backoff(
                    self.client.messages.create,
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=[{"role": "user", "content": prompt}],
                    tools=tools
                )

                # Check if there are tool calls
                if response.content and isinstance(response.content, list):
                    tool_calls = []
                    content_text = ""

                    for block in response.content:
                        if block.type == "tool_use":
                            tool_calls.append({
                                "id": block.id,
                                "type": "function",
                                "function": {
                                    "name": block.name,
                                    "arguments": json.dumps(block.input)
                                }
                            })
                        elif block.type == "text":
                            content_text += block.text

                    return {
                        "content": content_text,
                        "tool_calls": tool_calls
                    }
                else:
                    return {
                        "content": response.content[0].text if response.content else "",
                        "tool_calls": []
                    }
            else:
                response = self.retry_with_backoff(
                    self.client.messages.create,
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=[{"role": "user", "content": prompt}]
                )

                return {
                    "content": response.content[0].text if response.content else "",
                    "tool_calls": []
                }
        except Exception as e:
            self.logger.error(f"Error generating with Anthropic: {str(e)}")
            raise

    def stream_generate(self, prompt: str, tools: Optional[List[Dict[str, Any]]] = None) -> Iterator[Dict[str, Any]]:
        """Stream a response or tool calls using Anthropic.

        Args:
            prompt: The prompt to send to the LLM
            tools: Optional list of tool definitions

        Returns:
            Iterator of response chunks from the LLM
        """
        try:
            if tools:
                with self.retry_with_backoff(
                    self.client.messages.stream,
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=[{"role": "user", "content": prompt}],
                    tools=tools
                ) as stream:
                    for chunk in stream:
                        if chunk.delta and chunk.delta.stop_reason:
                            break

                        if chunk.delta and chunk.delta.tool_use:
                            tool_use = chunk.delta.tool_use
                            yield {
                                "type": "tool_call",
                                "id": tool_use.id if tool_use.id else None,
                                "name": tool_use.name if tool_use.name else None,
                                "arguments": json.dumps(tool_use.input) if tool_use.input else None
                            }

                        if chunk.delta and chunk.delta.text:
                            yield {
                                "type": "content",
                                "content": chunk.delta.text
                            }
            else:
                with self.retry_with_backoff(
                    self.client.messages.stream,
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    messages=[{"role": "user", "content": prompt}]
                ) as stream:
                    for chunk in stream:
                        if chunk.delta and chunk.delta.stop_reason:
                            break

                        if chunk.delta and chunk.delta.text:
                            yield {
                                "type": "content",
                                "content": chunk.delta.text
                            }
        except Exception as e:
            self.logger.error(f"Error streaming with Anthropic: {str(e)}")
            raise


class LLMProviderFactory:
    """Factory for creating LLM providers."""

    @staticmethod
    def create_provider(provider_name: str, config: Dict[str, Any]) -> LLMProvider:
        """Create an LLM provider based on the provider name.

        Args:
            provider_name: Name of the provider (openai, anthropic)
            config: Provider-specific configuration

        Returns:
            LLM provider instance

        Raises:
            ValueError: If the provider is unknown
        """
        if provider_name == "openai":
            return OpenAIProvider(config)
        elif provider_name == "anthropic":
            return AnthropicProvider(config)
        else:
            raise ValueError(f"Unknown LLM provider: {provider_name}")
