#!/usr/bin/env python3
"""Base classes for metadata generators.

This module provides abstract base classes and common utilities for
all metadata generator implementations.
"""

import abc
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from tools.data_generator_enhanced.utils.statistical import Distribution


class BaseGenerator(abc.ABC):
    """Abstract base class for all metadata generators."""

    def __init__(self, config: Dict[str, Any], seed: Optional[int] = None):
        """Initialize the generator with the given configuration.
        
        Args:
            config: Configuration dictionary for the generator
            seed: Optional random seed for reproducible generation
        """
        self.config = config
        self.seed = seed
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abc.abstractmethod
    def generate(self, count: int) -> List[Dict[str, Any]]:
        """Generate the specified number of metadata records.
        
        Args:
            count: Number of records to generate
            
        Returns:
            List of generated metadata records
        """
        pass
        
    @abc.abstractmethod
    def generate_truth(self, count: int, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate truth records that match specific criteria.
        
        Args:
            count: Number of truth records to generate
            criteria: Criteria that the truth records must satisfy
            
        Returns:
            List of generated truth records
        """
        pass


class StorageMetadataGenerator(BaseGenerator):
    """Base class for storage metadata generators."""
    
    def __init__(self, config: Dict[str, Any], seed: Optional[int] = None):
        """Initialize the storage metadata generator.
        
        Args:
            config: Configuration dictionary for the generator
            seed: Optional random seed for reproducible generation
        """
        super().__init__(config, seed)
        
    @abc.abstractmethod
    def generate_paths(self, count: int) -> List[str]:
        """Generate realistic file paths.
        
        Args:
            count: Number of paths to generate
            
        Returns:
            List of generated file paths
        """
        pass


class SemanticMetadataGenerator(BaseGenerator):
    """Base class for semantic metadata generators."""
    
    def __init__(self, config: Dict[str, Any], seed: Optional[int] = None):
        """Initialize the semantic metadata generator.
        
        Args:
            config: Configuration dictionary for the generator
            seed: Optional random seed for reproducible generation
        """
        super().__init__(config, seed)
        
    @abc.abstractmethod
    def generate_for_storage(self, storage_metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate semantic metadata for the given storage metadata.
        
        Args:
            storage_metadata: Storage metadata records
            
        Returns:
            List of generated semantic metadata records
        """
        pass


class ActivityMetadataGenerator(BaseGenerator):
    """Base class for activity metadata generators."""
    
    def __init__(self, config: Dict[str, Any], seed: Optional[int] = None):
        """Initialize the activity metadata generator.
        
        Args:
            config: Configuration dictionary for the generator
            seed: Optional random seed for reproducible generation
        """
        super().__init__(config, seed)
        
    @abc.abstractmethod
    def generate_for_storage(self, storage_metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate activity metadata for the given storage metadata.
        
        Args:
            storage_metadata: Storage metadata records
            
        Returns:
            List of generated activity metadata records
        """
        pass


class RelationshipGenerator(BaseGenerator):
    """Base class for relationship generators."""
    
    def __init__(self, config: Dict[str, Any], seed: Optional[int] = None):
        """Initialize the relationship generator.
        
        Args:
            config: Configuration dictionary for the generator
            seed: Optional random seed for reproducible generation
        """
        super().__init__(config, seed)
        
    @abc.abstractmethod
    def generate_relationships(self, metadata: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Generate relationships between metadata records.
        
        Args:
            metadata: Dictionary mapping metadata types to lists of metadata records
            
        Returns:
            List of generated relationship records
        """
        pass