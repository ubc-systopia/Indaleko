"""Base implementations for collectors and recorders."""

import random
from typing import Any

from .base import ISyntheticCollector, ISyntheticRecorder
from .models.activity import ActivityData, ActivityType


class BaseSyntheticCollector(ISyntheticCollector):
    """Base implementation for synthetic data collectors.

    This provides common functionality for all collectors.
    """

    def __init__(self, activity_type: ActivityType, activity_model_class: type[ActivityData]):
        """Initialize the collector.

        Args:
            activity_type: The type of activity this collector generates.
            activity_model_class: The model class for the activity data.
        """
        self.activity_type = activity_type
        self.activity_model_class = activity_model_class
        self._seed_value = None

    def seed(self, seed_value: int) -> None:
        """Set the random seed for deterministic data generation.

        Args:
            seed_value: The seed value to use.
        """
        self._seed_value = seed_value
        random.seed(seed_value)

    def generate_batch(self, count: int) -> list[dict[str, Any]]:
        """Generate a batch of synthetic activity data.

        Args:
            count: Number of activity records to generate.

        Returns:
            List[Dict]: List of generated activity data.
        """
        result = []
        for _ in range(count):
            result.append(self.collect())
        return result

    def generate_matching_data(self, query: str, count: int = 1) -> list[dict[str, Any]]:
        """Generate activity data that should match a specific query.

        This base implementation must be overridden by specific collectors
        to implement query-matching logic.

        Args:
            query: The natural language query to generate matching data for.
            count: Number of matching records to generate.

        Returns:
            List[Dict]: List of generated activity data that should match the query.
        """
        raise NotImplementedError("Subclasses must implement generate_matching_data()")

    def generate_non_matching_data(self, query: str, count: int = 1) -> list[dict[str, Any]]:
        """Generate activity data that should NOT match a specific query.

        This base implementation must be overridden by specific collectors
        to implement query non-matching logic.

        Args:
            query: The natural language query to generate non-matching data for.
            count: Number of non-matching records to generate.

        Returns:
            List[Dict]: List of generated activity data that should NOT match the query.
        """
        raise NotImplementedError("Subclasses must implement generate_non_matching_data()")


class BaseSyntheticRecorder(ISyntheticRecorder):
    """Base implementation for synthetic data recorders.

    This provides common functionality for all recorders.
    """

    def __init__(self, collection_name: str, truth_collection_name: str):
        """Initialize the recorder.

        Args:
            collection_name: The name of the collection to write activity data to.
            truth_collection_name: The name of the collection to write truth data to.
        """
        self.collection_name = collection_name
        self.truth_collection_name = truth_collection_name

    def get_collection_name(self) -> str:
        """Get the name of the collection this recorder writes to.

        Returns:
            str: The collection name.
        """
        return self.collection_name

    def record_batch(self, data_batch: list[dict[str, Any]]) -> bool:
        """Record a batch of synthetic activity data to the database.

        Args:
            data_batch: List of activity data to record.

        Returns:
            bool: True if recording was successful, False otherwise.
        """
        # Default implementation calls record() for each item
        success = True
        for data in data_batch:
            if not self.record(data):
                success = False
        return success
