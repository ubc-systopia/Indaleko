"""Base interfaces for the ablation framework."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Tuple, Union
from uuid import UUID

from pydantic import BaseModel, Field


class ISyntheticCollector(ABC):
    """Interface for synthetic data collectors.
    
    Synthetic collectors generate fake activity data for ablation studies.
    They follow the collector pattern and don't write to the database directly.
    """
    
    @abstractmethod
    def collect(self) -> Dict:
        """Generate synthetic activity data.
        
        Returns:
            Dict: The generated activity data.
        """
        pass
    
    @abstractmethod
    def generate_truth_data(self, query: str) -> Set[UUID]:
        """Generate truth data for a specific query.
        
        This method identifies which entities should match a given query.
        
        Args:
            query: The natural language query to generate truth data for.
            
        Returns:
            Set[UUID]: The set of UUIDs that should match the query.
        """
        pass


class ISyntheticRecorder(ABC):
    """Interface for synthetic data recorders.
    
    Synthetic recorders process data from collectors and write it to the database.
    They follow the recorder pattern and handle the database integration.
    """
    
    @abstractmethod
    def record(self, data: Dict) -> bool:
        """Record synthetic activity data to the database.
        
        Args:
            data: The activity data to record.
            
        Returns:
            bool: True if recording was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def record_truth_data(self, query_id: UUID, entity_ids: Set[UUID]) -> bool:
        """Record truth data for a specific query.
        
        Args:
            query_id: The UUID of the query.
            entity_ids: The set of entity UUIDs that should match the query.
            
        Returns:
            bool: True if recording was successful, False otherwise.
        """
        pass


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
    
    @property
    def impact(self) -> float:
        """Calculate the impact score of ablating this collection.
        
        The impact is defined as 1 - f1_score, representing how much
        performance degradation occurs when the collection is ablated.
        
        Returns:
            float: The impact score (0.0 to 1.0)
        """
        return 1.0 - self.f1_score
