#!/usr/bin/env python3
"""Statistical distribution utilities for data generation.

This module provides utilities for generating values from various
statistical distributions and for working with weighted random selections.
"""

import random
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np


class Distribution:
    """Base class for all statistical distributions."""
    
    @staticmethod
    def create(config: Dict[str, Any]) -> 'Distribution':
        """Factory method to create a distribution from a configuration.
        
        Args:
            config: Distribution configuration dictionary
            
        Returns:
            A Distribution instance
            
        Raises:
            ValueError: If the distribution type is not supported
        """
        dist_type = config.get("type", "").lower()
        
        if dist_type == "normal":
            return NormalDistribution(
                mean=config.get("mean", 0),
                std=config.get("std", 1),
            )
        elif dist_type == "lognormal":
            return LogNormalDistribution(
                mu=config.get("mu", 0),
                sigma=config.get("sigma", 1),
            )
        elif dist_type == "uniform":
            return UniformDistribution(
                min_val=config.get("min", 0),
                max_val=config.get("max", 1),
            )
        elif dist_type == "exponential":
            return ExponentialDistribution(
                lambda_=config.get("lambda", 1),
            )
        elif dist_type == "weighted":
            return WeightedDistribution(
                values=config.get("values", {}),
            )
        elif dist_type == "zipf":
            return ZipfDistribution(
                alpha=config.get("alpha", 1.5),
                size=config.get("size", 100),
            )
        else:
            raise ValueError(f"Unsupported distribution type: {dist_type}")
    
    def sample(self, size: Optional[int] = None) -> Union[float, np.ndarray]:
        """Sample from the distribution.
        
        Args:
            size: Number of samples to generate (None for a single sample)
            
        Returns:
            A single value or an array of values
        """
        raise NotImplementedError("Subclasses must implement sample()")


class NormalDistribution(Distribution):
    """Normal (Gaussian) distribution."""
    
    def __init__(self, mean: Union[float, str], std: Union[float, str]):
        """Initialize a normal distribution.
        
        Args:
            mean: Mean of the distribution (or a time string like "now-30d")
            std: Standard deviation of the distribution (or a time string like "15d")
        """
        self.mean = self._parse_time_value(mean) if isinstance(mean, str) else mean
        self.std = self._parse_time_delta(std) if isinstance(std, str) else std
    
    def sample(self, size: Optional[int] = None) -> Union[float, np.ndarray]:
        """Sample from the normal distribution.
        
        Args:
            size: Number of samples to generate (None for a single sample)
            
        Returns:
            A single value or an array of values
        """
        return np.random.normal(self.mean, self.std, size=size)
    
    def _parse_time_value(self, time_str: str) -> float:
        """Parse a time string into a Unix timestamp.
        
        Args:
            time_str: Time string (e.g., "now", "now-30d", "now+2h")
            
        Returns:
            Unix timestamp
        """
        if time_str.lower() == "now":
            return time.time()
        
        if "-" in time_str:
            base, delta = time_str.split("-", 1)
            if base.lower() == "now":
                return time.time() - self._parse_time_delta(delta)
        
        if "+" in time_str:
            base, delta = time_str.split("+", 1)
            if base.lower() == "now":
                return time.time() + self._parse_time_delta(delta)
        
        # Try to parse as a datetime string
        try:
            dt = datetime.fromisoformat(time_str)
            return dt.timestamp()
        except ValueError:
            raise ValueError(f"Invalid time string: {time_str}")
    
    def _parse_time_delta(self, delta_str: str) -> float:
        """Parse a time delta string into seconds.
        
        Args:
            delta_str: Time delta string (e.g., "30d", "2h", "10m", "30s")
            
        Returns:
            Time delta in seconds
        """
        if not delta_str:
            return 0.0
        
        unit = delta_str[-1].lower()
        try:
            value = float(delta_str[:-1])
        except ValueError:
            raise ValueError(f"Invalid time delta string: {delta_str}")
        
        if unit == "d":
            return value * 86400  # days to seconds
        elif unit == "h":
            return value * 3600  # hours to seconds
        elif unit == "m":
            return value * 60  # minutes to seconds
        elif unit == "s":
            return value  # seconds
        else:
            try:
                # Try to parse the entire string as a number
                return float(delta_str)
            except ValueError:
                raise ValueError(f"Invalid time delta unit: {unit}")


class LogNormalDistribution(Distribution):
    """Log-normal distribution."""
    
    def __init__(self, mu: float, sigma: float):
        """Initialize a log-normal distribution.
        
        Args:
            mu: Mean of the underlying normal distribution
            sigma: Standard deviation of the underlying normal distribution
        """
        self.mu = mu
        self.sigma = sigma
    
    def sample(self, size: Optional[int] = None) -> Union[float, np.ndarray]:
        """Sample from the log-normal distribution.
        
        Args:
            size: Number of samples to generate (None for a single sample)
            
        Returns:
            A single value or an array of values
        """
        return np.random.lognormal(self.mu, self.sigma, size=size)


class UniformDistribution(Distribution):
    """Uniform distribution."""
    
    def __init__(self, min_val: float, max_val: float):
        """Initialize a uniform distribution.
        
        Args:
            min_val: Minimum value
            max_val: Maximum value
        """
        self.min_val = min_val
        self.max_val = max_val
    
    def sample(self, size: Optional[int] = None) -> Union[float, np.ndarray]:
        """Sample from the uniform distribution.
        
        Args:
            size: Number of samples to generate (None for a single sample)
            
        Returns:
            A single value or an array of values
        """
        return np.random.uniform(self.min_val, self.max_val, size=size)


class ExponentialDistribution(Distribution):
    """Exponential distribution."""
    
    def __init__(self, lambda_: float):
        """Initialize an exponential distribution.
        
        Args:
            lambda_: Rate parameter
        """
        self.lambda_ = lambda_
    
    def sample(self, size: Optional[int] = None) -> Union[float, np.ndarray]:
        """Sample from the exponential distribution.
        
        Args:
            size: Number of samples to generate (None for a single sample)
            
        Returns:
            A single value or an array of values
        """
        return np.random.exponential(1 / self.lambda_, size=size)


class WeightedDistribution(Distribution):
    """Weighted random selection distribution."""
    
    def __init__(self, values: Dict[Any, float]):
        """Initialize a weighted distribution.
        
        Args:
            values: Dictionary mapping values to weights
        """
        self.values = list(values.keys())
        self.weights = list(values.values())
        
        # Normalize weights
        total = sum(self.weights)
        if total > 0:
            self.weights = [w / total for w in self.weights]
    
    def sample(self, size: Optional[int] = None) -> Union[Any, List[Any]]:
        """Sample from the weighted distribution.
        
        Args:
            size: Number of samples to generate (None for a single sample)
            
        Returns:
            A single value or a list of values
        """
        if size is None:
            return random.choices(self.values, weights=self.weights, k=1)[0]
        else:
            return random.choices(self.values, weights=self.weights, k=size)


class ZipfDistribution(Distribution):
    """Zipf distribution for modeling popularity/frequency phenomena."""
    
    def __init__(self, alpha: float, size: int):
        """Initialize a Zipf distribution.
        
        Args:
            alpha: Exponent parameter (larger values = more skewed)
            size: Number of elements in the distribution
        """
        self.alpha = alpha
        self.size = size
    
    def sample(self, size: Optional[int] = None) -> Union[int, np.ndarray]:
        """Sample from the Zipf distribution.
        
        Args:
            size: Number of samples to generate (None for a single sample)
            
        Returns:
            A single value or an array of values (1-indexed)
        """
        return np.random.zipf(self.alpha, size=size) % self.size + 1