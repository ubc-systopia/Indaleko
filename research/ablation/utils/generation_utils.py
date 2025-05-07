"""Utility functions for synthetic data generation."""

import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Tuple, Union
from uuid import UUID, uuid4


def random_date(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> datetime:
    """Generate a random datetime between start_date and end_date.
    
    Args:
        start_date: The start date (inclusive). Defaults to 7 days ago.
        end_date: The end date (inclusive). Defaults to now.
        
    Returns:
        datetime: A random datetime between start_date and end_date.
    """
    if start_date is None:
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
    
    if end_date is None:
        end_date = datetime.now(timezone.utc)
    
    # Convert to timestamps
    start_ts = start_date.timestamp()
    end_ts = end_date.timestamp()
    
    # Generate a random timestamp in the range
    random_ts = random.uniform(start_ts, end_ts)
    
    # Convert back to datetime
    return datetime.fromtimestamp(random_ts, tz=timezone.utc)


def random_duration(min_seconds: int = 60, max_seconds: int = 3600) -> int:
    """Generate a random duration in seconds.
    
    Args:
        min_seconds: The minimum duration in seconds. Defaults to 60 (1 minute).
        max_seconds: The maximum duration in seconds. Defaults to 3600 (1 hour).
        
    Returns:
        int: A random duration in seconds.
    """
    return random.randint(min_seconds, max_seconds)


def random_coordinates(base_lat: float = 37.7749, base_lng: float = -122.4194, radius_km: float = 10.0) -> Tuple[float, float]:
    """Generate random coordinates near a base location.
    
    Args:
        base_lat: The base latitude. Defaults to San Francisco.
        base_lng: The base longitude. Defaults to San Francisco.
        radius_km: The maximum distance in kilometers from the base. Defaults to 10 km.
        
    Returns:
        Tuple[float, float]: A tuple of (latitude, longitude).
    """
    import math
    
    # Convert radius from km to degrees (approximate)
    radius_lat = radius_km / 111.0  # 1 degree latitude is approximately 111 km
    radius_lng = radius_km / (111.0 * abs(math.cos(math.radians(base_lat))))
    
    # Generate random offsets
    lat_offset = random.uniform(-radius_lat, radius_lat)
    lng_offset = random.uniform(-radius_lng, radius_lng)
    
    # Calculate new coordinates
    lat = base_lat + lat_offset
    lng = base_lng + lng_offset
    
    return (lat, lng)


def weighted_choice(choices: List[str], weights: Optional[List[float]] = None) -> str:
    """Choose a random item from a list with optional weights.
    
    Args:
        choices: The list of choices.
        weights: Optional list of weights for each choice. If not provided, all choices have equal weight.
        
    Returns:
        str: A randomly selected choice.
    """
    if weights is None:
        return random.choice(choices)
    
    # Normalize weights if needed
    if sum(weights) != 1.0:
        total = sum(weights)
        weights = [w / total for w in weights]
    
    # Generate a random value between 0 and 1
    rand_val = random.random()
    
    # Find the corresponding choice
    cumulative = 0.0
    for i, weight in enumerate(weights):
        cumulative += weight
        if rand_val <= cumulative:
            return choices[i]
    
    # Fallback (should not reach here if weights sum to 1.0)
    return choices[-1]
