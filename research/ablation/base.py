"""Base interfaces for the ablation framework."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ISyntheticCollector(ABC):
    """Interface for synthetic data collectors.

    Synthetic collectors generate fake activity data for ablation studies.
    They follow the collector pattern and don't write to the database directly.
    """

    @abstractmethod
    def collect(self) -> dict:
        """Generate synthetic activity data.

        Returns:
            Dict: The generated activity data.
        """

    @abstractmethod
    def generate_truth_data(self, query: str) -> set[UUID]:
        """Generate truth data for a specific query.

        This method identifies which entities should match a given query.

        Args:
            query: The natural language query to generate truth data for.

        Returns:
            Set[UUID]: The set of UUIDs that should match the query.
        """

    @abstractmethod
    def generate_batch(self, count: int) -> list[dict[str, Any]]:
        """Generate a batch of synthetic activity data.

        Args:
            count: Number of activity records to generate.

        Returns:
            List[Dict]: List of generated activity data.
        """

    @abstractmethod
    def generate_matching_data(self, query: str, count: int = 1) -> list[dict[str, Any]]:
        """Generate activity data that should match a specific query.

        Args:
            query: The natural language query to generate matching data for.
            count: Number of matching records to generate.

        Returns:
            List[Dict]: List of generated activity data that should match the query.
        """

    @abstractmethod
    def generate_non_matching_data(self, query: str, count: int = 1) -> list[dict[str, Any]]:
        """Generate activity data that should NOT match a specific query.

        Args:
            query: The natural language query to generate non-matching data for.
            count: Number of non-matching records to generate.

        Returns:
            List[Dict]: List of generated activity data that should NOT match the query.
        """

    @abstractmethod
    def seed(self, seed_value: int) -> None:
        """Set the random seed for deterministic data generation.

        Args:
            seed_value: The seed value to use.
        """


class ISyntheticRecorder(ABC):
    """Interface for synthetic data recorders.

    Synthetic recorders process data from collectors and write it to the database.
    They follow the recorder pattern and handle the database integration.
    """

    @abstractmethod
    def record(self, data: dict) -> bool:
        """Record synthetic activity data to the database.

        Args:
            data: The activity data to record.

        Returns:
            bool: True if recording was successful, False otherwise.
        """

    @abstractmethod
    def record_truth_data(self, query_id: UUID, entity_ids: set[UUID]) -> bool:
        """Record truth data for a specific query.

        Args:
            query_id: The UUID of the query.
            entity_ids: The set of entity UUIDs that should match the query.

        Returns:
            bool: True if recording was successful, False otherwise.
        """

    @abstractmethod
    def record_batch(self, data_batch: list[dict[str, Any]]) -> bool:
        """Record a batch of synthetic activity data to the database.

        Args:
            data_batch: List of activity data to record.

        Returns:
            bool: True if recording was successful, False otherwise.
        """

    @abstractmethod
    def delete_all(self) -> bool:
        """Delete all records created by this recorder.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """

    @abstractmethod
    def get_collection_name(self) -> str:
        """Get the name of the collection this recorder writes to.

        Returns:
            str: The collection name.
        """

    @abstractmethod
    def count_records(self) -> int:
        """Count the number of records in the collection.

        Returns:
            int: The record count.
        """


class AblationResult(BaseModel):
    """Model for storing the results of an ablation test."""

    query_id: UUID
    ablated_collection: str
    precision: float
    recall: float
    f1_score: float
    execution_time_ms: int
    result_count: int
    true_positives: int
    false_positives: int
    false_negatives: int
    aql_query: str = ""  # The AQL query used for testing

    @property
    def impact(self) -> float:
        """Calculate the impact score of ablating this collection.

        The impact is defined as 1 - f1_score, representing how much
        performance degradation occurs when the collection is ablated.

        Returns:
            float: The impact score (0.0 to 1.0)
        """
        return 1.0 - self.f1_score
