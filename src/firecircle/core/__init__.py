"""
Core implementation of Fire Circle entities.

This module provides concrete implementations of the entity roles defined
in the Fire Circle protocol.
"""

import uuid

from typing import Any, Dict, List, Optional, Tuple, Type

from ..adapters.anthropic import AnthropicAdapter
from ..adapters.base import (
    FireCircleMessage,
    FireCircleRequest,
    FireCircleResponse,
    ModelAdapter,
)
from ..adapters.openai import OpenAIAdapter
from ..protocol import ENTITY_PROFILES, EntityInterface, EntityProfile, EntityRole


class ModelAdapterFactory:
    """Factory for creating model adapters."""

    @staticmethod
    def create_adapter(provider: str, model: str, **kwargs) -> ModelAdapter:
        """
        Create a model adapter for the given provider and model.

        Args:
            provider: The provider name (e.g., "openai", "anthropic")
            model: The model name
            **kwargs: Additional arguments to pass to the adapter constructor

        Returns:
            A model adapter instance

        Raises:
            ValueError: If the provider is not supported
        """
        if provider.lower() == "openai":
            return OpenAIAdapter(model=model, **kwargs)
        if provider.lower() == "anthropic":
            return AnthropicAdapter(model=model, **kwargs)
        raise ValueError(f"Unsupported provider: {provider}")


class FireCircleEntity(EntityInterface):
    """Base implementation of a Fire Circle entity role."""

    def __init__(
        self,
        role: EntityRole,
        model: str | None = None,
        provider: str | None = None,
        adapter: ModelAdapter | None = None,
        **kwargs,
    ) -> None:
        """
        Initialize a new Fire Circle entity.

        Args:
            role: The role of this entity
            model: Optional model to use (defaults to role's default model)
            provider: Optional provider to use (defaults to role's default provider)
            adapter: Optional pre-configured adapter to use
            **kwargs: Additional arguments to pass to the adapter constructor
        """
        self.role = role
        self.profile = ENTITY_PROFILES[role]

        # Use provided adapter or create one
        if adapter:
            self.adapter = adapter
        else:
            # Use provided model/provider or defaults from profile
            model = model or self.profile.default_model
            provider = provider or self.profile.default_provider

            # Create adapter
            self.adapter = ModelAdapterFactory.create_adapter(
                provider=provider,
                model=model,
                **kwargs,
            )

    def get_profile(self) -> EntityProfile:
        """Get the profile for this entity."""
        return self.profile

    def process_message(self, message: str, context: dict[str, Any] | None = None) -> str:
        """
        Process a message from the perspective of this entity role.

        Args:
            message: The input message to process
            context: Additional context information

        Returns:
            The response message from this entity
        """
        context = context or {}

        # Create conversation history
        messages = [
            FireCircleMessage(role="system", content=self.profile.system_prompt),
        ]

        # Add context messages if provided
        if "history" in context and isinstance(context["history"], list):
            for msg in context["history"]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                messages.append(FireCircleMessage(role=role, content=content))

        # Add current message
        messages.append(FireCircleMessage(role="user", content=message))

        # Create request
        request = FireCircleRequest(
            messages=messages,
            model_parameters={
                "temperature": context.get("temperature", 0.7),
                "max_tokens": context.get("max_tokens", 2048),
            },
        )

        # Process request
        response = self.adapter.process_request(request)

        # Return response content
        return response.message.content

    def can_handle_task(self, task_description: str) -> float:
        """
        Evaluate whether this entity is suited to handle a given task.

        Args:
            task_description: Description of the task to evaluate

        Returns:
            A score from 0.0 to 1.0 indicating suitability
        """
        # This is a simplified implementation that could be enhanced with more
        # sophisticated task matching based on the entity's capabilities

        # Create a request to evaluate task suitability
        messages = [
            FireCircleMessage(
                role="system",
                content=f"""
            You are evaluating whether a {self.role.value} role is suitable for a given task.

            The {self.role.value} role has these capabilities:
            {', '.join(self.profile.capabilities)}

            The {self.role.value} role is described as: {self.profile.description}

            You must return ONLY a single number between 0.0 and 1.0 representing the suitability
            of this role for the task, where:
            - 0.0 means completely unsuitable
            - 1.0 means perfectly suited

            Do not include any other text in your response.
            """,
            ),
            FireCircleMessage(role="user", content=f"Task: {task_description}"),
        ]

        request = FireCircleRequest(
            messages=messages,
            model_parameters={
                "temperature": 0.1,
            },  # Low temperature for more consistent results
        )

        # Process request
        response = self.adapter.process_request(request)

        # Parse the response as a float
        try:
            score = float(response.message.content.strip())
            # Ensure score is in valid range
            return max(0.0, min(1.0, score))
        except ValueError:
            # Default to moderate score if parsing fails
            return 0.5


# Factory functions for creating entities with specific roles


def create_storyteller(
    model: str | None = None,
    provider: str | None = None,
    **kwargs,
) -> FireCircleEntity:
    """Create a Storyteller entity."""
    return FireCircleEntity(EntityRole.STORYTELLER, model, provider, **kwargs)


def create_analyst(
    model: str | None = None,
    provider: str | None = None,
    **kwargs,
) -> FireCircleEntity:
    """Create an Analyst entity."""
    return FireCircleEntity(EntityRole.ANALYST, model, provider, **kwargs)


def create_critic(
    model: str | None = None,
    provider: str | None = None,
    **kwargs,
) -> FireCircleEntity:
    """Create a Critic entity."""
    return FireCircleEntity(EntityRole.CRITIC, model, provider, **kwargs)


def create_synthesizer(
    model: str | None = None,
    provider: str | None = None,
    **kwargs,
) -> FireCircleEntity:
    """Create a Synthesizer entity."""
    return FireCircleEntity(EntityRole.SYNTHESIZER, model, provider, **kwargs)


def create_coordinator(
    model: str | None = None,
    provider: str | None = None,
    **kwargs,
) -> FireCircleEntity:
    """Create a Coordinator entity."""
    return FireCircleEntity(EntityRole.COORDINATOR, model, provider, **kwargs)
