"""Registry module for the ablation framework.

This module provides registry services for tracking entities and their
relationships across different collections in the ablation framework.
"""

from .shared_entity_registry import SharedEntityRegistry, EntityReference

__all__ = ["SharedEntityRegistry", "EntityReference"]