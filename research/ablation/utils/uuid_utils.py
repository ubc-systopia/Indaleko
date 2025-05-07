"""UUID utilities for the ablation framework."""

import hashlib
from typing import Optional, Union
from uuid import UUID, uuid4, uuid5

# Namespace for deterministic UUID generation
ABLATION_NAMESPACE = UUID('f47ac10b-58cc-4372-a567-0e02b2c3d479')


def generate_deterministic_uuid(seed_string: str, namespace: Optional[UUID] = None) -> UUID:
    """Generate a deterministic UUID from a seed string.
    
    This function creates UUIDs that are consistent for the same input,
    which helps with reproducibility in ablation testing.
    
    Args:
        seed_string: The string to use as the seed.
        namespace: The namespace to use for UUID generation. Default is ABLATION_NAMESPACE.
        
    Returns:
        UUID: A deterministic UUID derived from the seed string.
    """
    if namespace is None:
        namespace = ABLATION_NAMESPACE
    
    return uuid5(namespace, seed_string)


def generate_uuid_for_entity(entity_type: str, natural_key: str) -> UUID:
    """Generate a UUID for an entity based on its type and natural key.
    
    Args:
        entity_type: The type of entity (e.g., 'music_track', 'location', etc.)
        natural_key: A unique identifier for the entity within its type
        
    Returns:
        UUID: A deterministic UUID for the entity.
    """
    seed = f"{entity_type}:{natural_key}"
    return generate_deterministic_uuid(seed)


def generate_random_uuid() -> UUID:
    """Generate a random UUID.
    
    Returns:
        UUID: A random UUID.
    """
    return uuid4()
