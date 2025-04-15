"""
OpenAI adapter module for Fire Circle.

This module provides adapter implementations for connecting the Fire Circle protocol
with OpenAI's API, allowing integration with GPT models and other OpenAI services.
"""

import json
from typing import Dict, List, Any, Optional

try:
    import openai
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

from ..base import ModelAdapter, FireCircleRequest, FireCircleResponse, FireCircleMessage


class OpenAIAdapter(ModelAdapter):
    """Adapter for OpenAI's models."""
    
    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        organization: Optional[str] = None
    ):
        """
        Initialize a new OpenAI adapter.
        
        Args:
            model: The OpenAI model to use
            api_key: Optional OpenAI API key (uses environment variable if not provided)
            organization: Optional OpenAI organization ID
        """
        if not HAS_OPENAI:
            raise ImportError(
                "The OpenAI package is not installed. "
                "Please install it with `pip install openai>=1.0.0`."
            )
        
        self.model = model
        self.client = OpenAI(api_key=api_key, organization=organization)
    
    def _convert_to_openai_messages(self, messages: List[FireCircleMessage]) -> List[Dict[str, Any]]:
        """Convert Fire Circle messages to OpenAI message format."""
        return [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in messages
        ]
    
    def _convert_to_openai_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert Fire Circle tools to OpenAI tool format."""
        return tools  # Currently assuming tools are already in OpenAI format
    
    def process_request(self, request: FireCircleRequest) -> FireCircleResponse:
        """
        Process a Fire Circle request using OpenAI's API.
        
        Args:
            request: The Fire Circle request to process
            
        Returns:
            A Fire Circle response
        """
        openai_messages = self._convert_to_openai_messages(request.messages)
        
        # Prepare the API call parameters
        params = {
            "model": self.model,
            "messages": openai_messages,
        }
        
        # Add tools if provided
        if request.tools:
            params["tools"] = self._convert_to_openai_tools(request.tools)
        
        # Add model parameters
        for key, value in request.model_parameters.items():
            params[key] = value
        
        # Make the API call
        response = self.client.chat.completions.create(**params)
        
        # Convert the response to Fire Circle format
        message_content = response.choices[0].message.content or ""
        message = FireCircleMessage(
            role="assistant",
            content=message_content,
            metadata={"model": self.model}
        )
        
        # Extract tool calls if present
        tool_calls = []
        if hasattr(response.choices[0].message, "tool_calls") and response.choices[0].message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in response.choices[0].message.tool_calls
            ]
        
        # Extract usage statistics
        usage = {}
        if hasattr(response, "usage"):
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        
        return FireCircleResponse(
            message=message,
            usage=usage,
            tool_calls=tool_calls
        )
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get the capabilities of this model adapter.
        
        Returns:
            A dictionary of capability information
        """
        return {
            "provider": "openai",
            "model": self.model,
            "features": {
                "tools": True,
                "vision": self.model in ["gpt-4-vision", "gpt-4o"],
                "token_window": 128000 if "gpt-4o" in self.model else 8192
            }
        }