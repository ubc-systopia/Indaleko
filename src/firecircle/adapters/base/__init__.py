"""
Base adapter interface for Fire Circle.

This module defines the abstract base classes that all model-specific adapters
must implement to be compatible with the Fire Circle protocol.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class FireCircleMessage:
    """Represents a standardized message in the Fire Circle protocol."""

    def __init__(
        self,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Initialize a new Fire Circle message.

        Args:
            role: The role of the message sender (e.g., "user", "assistant", "system", or custom roles)
            content: The content of the message
            metadata: Optional metadata associated with the message
        """
        self.role = role
        self.content = content
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert the message to a dictionary representation."""
        return {"role": self.role, "content": self.content, "metadata": self.metadata}


class FireCircleRequest:
    """Represents a request in the Fire Circle protocol."""

    def __init__(
        self,
        messages: list[FireCircleMessage],
        tools: list[dict[str, Any]] | None = None,
        model_parameters: dict[str, Any] | None = None,
    ):
        """
        Initialize a new Fire Circle request.

        Args:
            messages: List of messages in the conversation
            tools: Optional list of tools available to the model
            model_parameters: Optional parameters for the model (temperature, etc.)
        """
        self.messages = messages
        self.tools = tools or []
        self.model_parameters = model_parameters or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert the request to a dictionary representation."""
        return {
            "messages": [msg.to_dict() for msg in self.messages],
            "tools": self.tools,
            "model_parameters": self.model_parameters,
        }


class FireCircleResponse:
    """Represents a response in the Fire Circle protocol."""

    def __init__(
        self,
        message: FireCircleMessage,
        usage: dict[str, Any] | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
    ):
        """
        Initialize a new Fire Circle response.

        Args:
            message: The response message
            usage: Optional usage statistics
            tool_calls: Optional tool calls made by the model
        """
        self.message = message
        self.usage = usage or {}
        self.tool_calls = tool_calls or []

    def to_dict(self) -> dict[str, Any]:
        """Convert the response to a dictionary representation."""
        return {
            "message": self.message.to_dict(),
            "usage": self.usage,
            "tool_calls": self.tool_calls,
        }


class ModelAdapter(ABC):
    """Abstract base class for model-specific adapters."""

    @abstractmethod
    def process_request(self, request: FireCircleRequest) -> FireCircleResponse:
        """
        Process a Fire Circle request and return a response.

        Args:
            request: The Fire Circle request to process

        Returns:
            A Fire Circle response
        """

    @abstractmethod
    def get_capabilities(self) -> dict[str, Any]:
        """
        Get the capabilities of this model adapter.

        Returns:
            A dictionary of capability information
        """
