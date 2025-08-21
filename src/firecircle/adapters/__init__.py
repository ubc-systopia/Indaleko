"""
Adapters module for Fire Circle.

This module provides adapters for connecting the Fire Circle protocol with various
AI model providers, including OpenAI, Anthropic, and potentially others.

The adapter layer translates between the standardized Fire Circle message protocol
and the specific API requirements of each provider, ensuring consistent communication
across different AI models regardless of their underlying implementation.
"""

# Export adapter classes
from adapters.anthropic import AnthropicAdapter
from adapters.base import FireCircleMessage, FireCircleRequest, FireCircleResponse, ModelAdapter
from adapters.openai import OpenAIAdapter


# Dictionary of available adapter classes, keyed by provider name
AVAILABLE_ADAPTERS = {"openai": OpenAIAdapter, "anthropic": AnthropicAdapter}
