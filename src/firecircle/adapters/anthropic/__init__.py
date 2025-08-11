"""
Anthropic adapter module for Fire Circle.

This module provides adapter implementations for connecting the Fire Circle protocol
with Anthropic's API, allowing integration with Claude models and other Anthropic services.
"""

import json

from typing import Any, Dict, List, Optional


try:
    import anthropic

    from anthropic import Anthropic

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from adapters.base import FireCircleMessage, FireCircleRequest, FireCircleResponse, ModelAdapter


class AnthropicAdapter(ModelAdapter):
    """Adapter for Anthropic's models."""

    def __init__(
        self,
        model: str = "claude-3-opus-20240229",
        api_key: str | None = None,
    ) -> None:
        """
        Initialize a new Anthropic adapter.

        Args:
            model: The Anthropic model to use
            api_key: Optional Anthropic API key (uses environment variable if not provided)
        """
        if not HAS_ANTHROPIC:
            raise ImportError(
                "The Anthropic package is not installed. Please install it with `pip install anthropic>=0.5.0`.",
            )

        self.model = model
        self.client = Anthropic(api_key=api_key)

    def _convert_to_anthropic_messages(
        self,
        messages: list[FireCircleMessage],
    ) -> list[dict[str, Any]]:
        """Convert Fire Circle messages to Anthropic message format."""
        # Map Fire Circle roles to Anthropic roles
        role_mapping = {"system": "system", "user": "user", "assistant": "assistant"}

        return [
            {
                "role": role_mapping.get(
                    msg.role,
                    "user",
                ),  # Default to user for unknown roles
                "content": msg.content,
            }
            for msg in messages
        ]

    def _convert_to_anthropic_tools(
        self,
        tools: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Convert Fire Circle tools to Anthropic tool format."""
        # Anthropic uses a slightly different tool format than OpenAI
        return [
            {
                "name": tool.get("function", {}).get("name", ""),
                "description": tool.get("description", ""),
                "input_schema": tool.get("function", {}).get("parameters", {}),
            }
            for tool in tools
        ]

    def process_request(self, request: FireCircleRequest) -> FireCircleResponse:
        """
        Process a Fire Circle request using Anthropic's API.

        Args:
            request: The Fire Circle request to process

        Returns:
            A Fire Circle response
        """
        anthropic_messages = self._convert_to_anthropic_messages(request.messages)

        # Prepare the API call parameters
        params = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": request.model_parameters.get("max_tokens", 1024),
        }

        # Add temperature if provided
        if "temperature" in request.model_parameters:
            params["temperature"] = request.model_parameters["temperature"]

        # Add tools if provided
        if request.tools:
            params["tools"] = self._convert_to_anthropic_tools(request.tools)

        # Make the API call
        response = self.client.messages.create(**params)

        # Convert the response to Fire Circle format
        message_content = response.content[0].text
        message = FireCircleMessage(
            role="assistant",
            content=message_content,
            metadata={"model": self.model},
        )

        # Extract tool calls if present
        tool_calls = []
        if hasattr(response, "tool_use") and response.tool_use:
            tool_calls = [
                {
                    "id": response.id,
                    "type": "function",
                    "function": {
                        "name": response.tool_use.name,
                        "arguments": json.dumps(response.tool_use.input),
                    },
                },
            ]

        # Extract usage statistics
        usage = {}
        if hasattr(response, "usage"):
            usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }

        return FireCircleResponse(message=message, usage=usage, tool_calls=tool_calls)

    def get_capabilities(self) -> dict[str, Any]:
        """
        Get the capabilities of this model adapter.

        Returns:
            A dictionary of capability information
        """
        # Claude version to capabilities mapping
        capabilities = {
            "claude-3-opus": {"token_window": 200000, "vision": True, "tools": True},
            "claude-3-sonnet": {"token_window": 180000, "vision": True, "tools": True},
            "claude-3-haiku": {"token_window": 150000, "vision": True, "tools": True},
            "claude-2.1": {"token_window": 100000, "vision": False, "tools": False},
        }

        # Determine the model family by removing version numbers and dates
        model_family = "claude-3-opus"  # Default
        for key in capabilities:
            if key in self.model:
                model_family = key
                break

        return {
            "provider": "anthropic",
            "model": self.model,
            "features": capabilities.get(
                model_family,
                {"token_window": 100000, "vision": True, "tools": False},
            ),
        }
