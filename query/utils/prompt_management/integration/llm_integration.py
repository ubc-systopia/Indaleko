"""
LLM integration for Prompt Management System.

Project Indaleko.
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

import logging
from typing import Any, Dict, Optional, Union

from query.utils.llm_connector.factory import LLMFactory
from query.utils.prompt_management.prompt_manager import PromptManager, PromptVariable

logger = logging.getLogger(__name__)


class PromptManagerLLMIntegration:
    """
    Integration class for using PromptManager with LLM connectors.
    
    This class provides a bridge between the PromptManager and the
    LLM connectors, enabling optimized prompts to be used with
    various LLM providers.
    """
    
    def __init__(
        self,
        prompt_manager: PromptManager,
        llm_factory: Optional[LLMFactory] = None,
    ):
        """
        Initialize the integration.
        
        Args:
            prompt_manager: The PromptManager instance
            llm_factory: The LLMFactory instance (created if not provided)
        """
        self.prompt_manager = prompt_manager
        self.llm_factory = llm_factory or LLMFactory()

    def get_completion(
        self,
        template_id: str,
        variables: list[PromptVariable],
        provider: str = "preferred",
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        optimize: bool = True,
        evaluate_stability: bool = True,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Get completion using an optimized prompt.
        
        Args:
            template_id: The template ID to use
            variables: List of variables to bind to the template
            provider: The LLM provider to use
            model: The specific model to use (provider-dependent)
            system_prompt: Optional system prompt to use (for compatible providers)
            optimize: Whether to optimize the prompt
            evaluate_stability: Whether to evaluate prompt stability
            options: Additional provider-specific options
            
        Returns:
            The LLM completion text
            
        Raises:
            ValueError: If template is not found or variables are invalid
        """
        # Create the prompt
        prompt_result = self.prompt_manager.create_prompt(
            template_id=template_id,
            variables=variables,
            optimize=optimize,
            evaluate_stability=evaluate_stability,
        )
        
        # Get the LLM instance
        llm = self.llm_factory.get_llm(provider=provider, model=model)
        
        # Set up options
        provider_options = options or {}
        
        # Get completion with system prompt if provided (for compatible providers)
        if system_prompt:
            completion = llm.get_completion(
                system_prompt=system_prompt,
                user_prompt=prompt_result.prompt,
                **provider_options,
            )
        else:
            # For providers that don't support system prompts
            completion = llm.get_completion(
                user_prompt=prompt_result.prompt,
                **provider_options,
            )
        
        # Log the token usage
        logger.info(
            "LLM request: %s tokens (originally %s, saved %s), stability: %.2f",
            prompt_result.token_count,
            prompt_result.original_token_count,
            prompt_result.token_savings,
            prompt_result.stability_score,
        )
        
        return completion


# Factory function to create an integrated manager
def create_integrated_manager(
    prompt_manager: Optional[PromptManager] = None,
    llm_factory: Optional[LLMFactory] = None,
) -> PromptManagerLLMIntegration:
    """
    Create an integrated prompt manager with LLM support.
    
    Args:
        prompt_manager: Optional PromptManager instance
        llm_factory: Optional LLMFactory instance
        
    Returns:
        An integrated prompt manager instance
    """
    prompt_manager = prompt_manager or PromptManager()
    llm_factory = llm_factory or LLMFactory()
    
    return PromptManagerLLMIntegration(
        prompt_manager=prompt_manager,
        llm_factory=llm_factory,
    )