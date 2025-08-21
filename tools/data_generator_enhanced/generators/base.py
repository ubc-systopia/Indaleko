#!/usr/bin/env python3
"""Base classes for metadata generators.

This module provides abstract base classes and common utilities for
all metadata generator implementations.
"""

import abc
import logging

from typing import Any


class BaseGenerator(abc.ABC):
    """Abstract base class for all metadata generators."""

    def __init__(self, config: dict[str, Any], seed: int | None = None) -> None:
        """Initialize the generator with the given configuration.

        Args:
            config: Configuration dictionary for the generator
            seed: Optional random seed for reproducible generation
        """
        self.config = config
        self.seed = seed
        self.logger = logging.getLogger(self.__class__.__name__)

    @abc.abstractmethod
    def generate(self, count: int) -> list[dict[str, Any]]:
        """Generate the specified number of metadata records.

        Args:
            count: Number of records to generate

        Returns:
            List of generated metadata records
        """

    @abc.abstractmethod
    def generate_truth(self, count: int, criteria: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate truth records that match specific criteria.

        Args:
            count: Number of truth records to generate
            criteria: Criteria that the truth records must satisfy

        Returns:
            List of generated truth records
        """


class StorageMetadataGenerator(BaseGenerator):
    """Base class for storage metadata generators."""

    def __init__(self, config: dict[str, Any], seed: int | None = None) -> None:
        """Initialize the storage metadata generator.

        Args:
            config: Configuration dictionary for the generator
            seed: Optional random seed for reproducible generation
        """
        super().__init__(config, seed)

    @abc.abstractmethod
    def generate_paths(self, count: int) -> list[str]:
        """Generate realistic file paths.

        Args:
            count: Number of paths to generate

        Returns:
            List of generated file paths
        """


class SemanticMetadataGenerator(BaseGenerator):
    """Base class for semantic metadata generators."""

    def __init__(self, config: dict[str, Any], seed: int | None = None) -> None:
        """Initialize the semantic metadata generator.

        Args:
            config: Configuration dictionary for the generator
            seed: Optional random seed for reproducible generation
        """
        super().__init__(config, seed)

    @abc.abstractmethod
    def generate_for_storage(self, storage_metadata: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Generate semantic metadata for the given storage metadata.

        Args:
            storage_metadata: Storage metadata records

        Returns:
            List of generated semantic metadata records
        """


class ActivityMetadataGenerator(BaseGenerator):
    """Base class for activity metadata generators."""

    def __init__(self, config: dict[str, Any], seed: int | None = None) -> None:
        """Initialize the activity metadata generator.

        Args:
            config: Configuration dictionary for the generator
            seed: Optional random seed for reproducible generation
        """
        super().__init__(config, seed)

    @abc.abstractmethod
    def generate_for_storage(self, storage_metadata: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Generate activity metadata for the given storage metadata.

        Args:
            storage_metadata: Storage metadata records

        Returns:
            List of generated activity metadata records
        """


class RelationshipGenerator(BaseGenerator):
    """Base class for relationship generators."""

    def __init__(self, config: dict[str, Any], seed: int | None = None) -> None:
        """Initialize the relationship generator.

        Args:
            config: Configuration dictionary for the generator
            seed: Optional random seed for reproducible generation
        """
        super().__init__(config, seed)

    @abc.abstractmethod
    def generate_relationships(self, metadata: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        """Generate relationships between metadata records.

        Args:
            metadata: Dictionary mapping metadata types to lists of metadata records

        Returns:
            List of generated relationship records
        """
