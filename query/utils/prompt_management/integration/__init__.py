"""
Integration modules for the Prompt Management System.

This package provides integration points for connecting the Prompt Management
System with other components of the Indaleko platform, such as LLM connectors,
database systems, and data generators.
"""

from query.utils.prompt_management.integration.llm_integration import (
    PromptManagerLLMIntegration, create_integrated_manager
)

__all__ = [
    'PromptManagerLLMIntegration',
    'create_integrated_manager',
]