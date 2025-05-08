"""Seed management for deterministic testing."""

import hashlib
import logging
import random
import time
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class SeedManager:
    """Manager for random seeds in the ablation framework.

    This class provides utilities for setting and managing random seeds
    to ensure deterministic behavior during testing.
    """

    def __init__(self, base_seed: int | None = None):
        """Initialize the seed manager.

        Args:
            base_seed: The base seed to use for all random operations.
                If not provided, a timestamp-based seed will be used.
        """
        self.base_seed = base_seed or int(time.time())
        self._seed_registry: dict[str, int] = {}
        self._current_context: str | None = None

        # Initialize the random number generators
        self.set_global_seed(self.base_seed)

        logger.info(f"Initialized seed manager with base seed {self.base_seed}")

    def set_global_seed(self, seed: int) -> None:
        """Set the global random seed.

        This method sets the seed for all random number generators.

        Args:
            seed: The seed to use.
        """
        # Set Python's built-in random seed
        random.seed(seed)

        # Set NumPy's random seed, if available
        try:
            np.random.seed(seed)
        except (ImportError, AttributeError):
            logger.debug("NumPy not available, skipping NumPy seed initialization")

        # Set any other random seeds here if needed
        logger.debug(f"Set global random seed to {seed}")

    def get_seed_for_context(self, context: str) -> int:
        """Get a deterministic seed for a specific context.

        This method generates a deterministic seed based on the base seed
        and the provided context.

        Args:
            context: The context for which to generate a seed.

        Returns:
            int: The seed for the context.
        """
        # If we've already generated a seed for this context, return it
        if context in self._seed_registry:
            return self._seed_registry[context]

        # Generate a deterministic seed based on the base seed and context
        hash_input = f"{self.base_seed}_{context}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()

        # Convert the hash to an integer
        seed = int(hash_value, 16) % (2**32 - 1)

        # Register the seed
        self._seed_registry[context] = seed

        logger.debug(f"Generated seed {seed} for context '{context}'")
        return seed

    def set_seed_for_context(self, context: str) -> int:
        """Set the random seed for a specific context.

        This method sets the random seed for the given context and
        returns the seed value.

        Args:
            context: The context for which to set the seed.

        Returns:
            int: The seed for the context.
        """
        seed = self.get_seed_for_context(context)
        self.set_global_seed(seed)
        self._current_context = context
        return seed

    def reset_to_base_seed(self) -> None:
        """Reset to the base seed."""
        self.set_global_seed(self.base_seed)
        self._current_context = None

    def get_current_context(self) -> str | None:
        """Get the current context.

        Returns:
            Optional[str]: The current context, or None if no context is set.
        """
        return self._current_context

    def clear_context(self) -> None:
        """Clear the current context."""
        self._current_context = None

    def register_seed(self, context: str, seed: int) -> None:
        """Register a specific seed for a context.

        Args:
            context: The context.
            seed: The seed value.
        """
        self._seed_registry[context] = seed
        logger.debug(f"Registered seed {seed} for context '{context}'")

    def get_registered_seeds(self) -> dict[str, int]:
        """Get all registered seeds.

        Returns:
            Dict[str, int]: Dictionary mapping contexts to seeds.
        """
        return self._seed_registry.copy()


class SeedContext:
    """Context manager for setting a random seed.

    This class provides a context manager for setting and restoring
    random seeds to ensure deterministic behavior within a specific scope.
    """

    def __init__(self, seed_manager: SeedManager, context: str):
        """Initialize the seed context.

        Args:
            seed_manager: The seed manager.
            context: The context for which to set the seed.
        """
        self.seed_manager = seed_manager
        self.context = context
        self.previous_context = None

    def __enter__(self) -> int:
        """Enter the context.

        Returns:
            int: The seed for the context.
        """
        # Save the previous context
        self.previous_context = self.seed_manager.get_current_context()

        # Set the seed for the new context
        return self.seed_manager.set_seed_for_context(self.context)

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Exit the context.

        Args:
            exc_type: The exception type, if an exception was raised.
            exc_value: The exception value, if an exception was raised.
            traceback: The traceback, if an exception was raised.
        """
        # Restore the previous context
        if self.previous_context:
            self.seed_manager.set_seed_for_context(self.previous_context)
        else:
            self.seed_manager.reset_to_base_seed()


def deterministic(seed_manager: SeedManager | None = None) -> callable:
    """Decorator to make a function deterministic.

    This decorator sets a consistent random seed before calling the function
    and restores the previous seed afterward.

    Args:
        seed_manager: The seed manager to use. If not provided, a new
            seed manager will be created for each call.

    Returns:
        callable: The decorated function.
    """

    def decorator(func: callable) -> callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Create or use the provided seed manager
            nonlocal seed_manager
            if seed_manager is None:
                seed_manager = SeedManager()

            # Set the seed for the function
            context = f"{func.__module__}.{func.__name__}"
            with SeedContext(seed_manager, context):
                return func(*args, **kwargs)

        return wrapper

    return decorator


# Global seed manager instance
_global_seed_manager = SeedManager()


def get_global_seed_manager() -> SeedManager:
    """Get the global seed manager.

    Returns:
        SeedManager: The global seed manager.
    """
    return _global_seed_manager


def set_global_seed(seed: int) -> None:
    """Set the global random seed.

    Args:
        seed: The seed to use.
    """
    _global_seed_manager.set_global_seed(seed)


def get_seed_for_context(context: str) -> int:
    """Get a deterministic seed for a specific context.

    Args:
        context: The context for which to generate a seed.

    Returns:
        int: The seed for the context.
    """
    return _global_seed_manager.get_seed_for_context(context)


def set_seed_for_context(context: str) -> int:
    """Set the random seed for a specific context.

    Args:
        context: The context for which to set the seed.

    Returns:
        int: The seed for the context.
    """
    return _global_seed_manager.set_seed_for_context(context)


def reset_to_base_seed() -> None:
    """Reset to the base seed."""
    _global_seed_manager.reset_to_base_seed()


def with_seed(context: str) -> SeedContext:
    """Create a context manager for setting a random seed.

    Args:
        context: The context for which to set the seed.

    Returns:
        SeedContext: The seed context.
    """
    return SeedContext(_global_seed_manager, context)
