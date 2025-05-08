"""
Base interfaces and classes for the ablation study framework.

This module provides the core interfaces and abstract base classes used
throughout the ablation framework, including collectors, recorders, and
data models.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from uuid import UUID

# Constants for collection names
MUSIC_ACTIVITY_COLLECTION = "AblationMusicActivity"
LOCATION_ACTIVITY_COLLECTION = "AblationLocationActivity"
TASK_ACTIVITY_COLLECTION = "AblationTaskActivity"
COLLABORATION_ACTIVITY_COLLECTION = "AblationCollaborationActivity"
STORAGE_ACTIVITY_COLLECTION = "AblationStorageActivity"
MEDIA_ACTIVITY_COLLECTION = "AblationMediaActivity"
QUERY_TRUTH_COLLECTION = "AblationQueryTruth"
NAMED_ENTITIES_COLLECTION = "AblationNamedEntities"

# Activity types
ACTIVITY_TYPES = {
    "music": MUSIC_ACTIVITY_COLLECTION,
    "location": LOCATION_ACTIVITY_COLLECTION,
    "task": TASK_ACTIVITY_COLLECTION,
    "collaboration": COLLABORATION_ACTIVITY_COLLECTION,
    "storage": STORAGE_ACTIVITY_COLLECTION,
    "media": MEDIA_ACTIVITY_COLLECTION
}


class ISyntheticCollector(ABC):
    """Interface for all synthetic data collectors."""
    
    @abstractmethod
    def generate_data(self, sample_size: int, output_path: Path) -> None:
        """Generate synthetic data samples and write to the output path.
        
        Args:
            sample_size: Number of synthetic data samples to generate
            output_path: Path to write the generated data to
        """
        pass
    
    @abstractmethod
    def generate_matching_data(self, query_components: Dict[str, Any], 
                              count: int, output_path: Path) -> List[str]:
        """Generate data that should match a specific query.
        
        Args:
            query_components: Components of the query to match against
            count: Number of matching samples to generate
            output_path: Path to write the generated data to
            
        Returns:
            List of identifiers for the generated matching data
        """
        pass
    
    @abstractmethod
    def generate_non_matching_data(self, query_components: Dict[str, Any], 
                                  count: int, output_path: Path) -> None:
        """Generate data that should NOT match a specific query.
        
        Args:
            query_components: Components of the query to NOT match against
            count: Number of non-matching samples to generate
            output_path: Path to write the generated data to
        """
        pass


class ISyntheticRecorder(ABC):
    """Interface for all synthetic data recorders."""
    
    @abstractmethod
    def record_data(self, input_path: Path) -> List[str]:
        """Read data from the input path and write to the database.
        
        Args:
            input_path: Path to the data file to read and record
            
        Returns:
            List of identifiers for the recorded data
        """
        pass
    
    @abstractmethod
    def get_collection_name(self) -> str:
        """Return the name of the database collection used by this recorder.
        
        Returns:
            The name of the database collection
        """
        pass
    
    @abstractmethod
    def clear_data(self) -> None:
        """Clear all data written by this recorder."""
        pass


class IQueryGenerator(ABC):
    """Interface for query generation."""
    
    @abstractmethod
    def generate_queries(self, activity_type: str, count: int) -> List[Dict[str, Any]]:
        """Generate queries for a specific activity type.
        
        Args:
            activity_type: The type of activity to generate queries for
            count: The number of queries to generate
            
        Returns:
            List of query dictionaries with natural language and components
        """
        pass
    
    @abstractmethod
    def parse_query(self, query: str) -> Dict[str, Any]:
        """Parse a natural language query into components.
        
        Args:
            query: The natural language query to parse
            
        Returns:
            Dictionary of query components (entities, attributes, relationships)
        """
        pass


class ITruthDataTracker(ABC):
    """Interface for tracking truth data for queries."""
    
    @abstractmethod
    def record_query_truth(self, query_id: str, 
                          matching_ids: List[str],
                          activity_type: str) -> None:
        """Record the truth data for a query.
        
        Args:
            query_id: The identifier for the query
            matching_ids: List of identifiers for records that should match
            activity_type: The type of activity the query targets
        """
        pass
    
    @abstractmethod
    def get_matching_ids(self, query_id: str) -> List[str]:
        """Get the identifiers that should match a query.
        
        Args:
            query_id: The identifier for the query
            
        Returns:
            List of identifiers for records that should match
        """
        pass
    
    @abstractmethod
    def calculate_metrics(self, query_id: str, 
                         result_ids: List[str]) -> Dict[str, float]:
        """Calculate precision, recall, and F1 for query results.
        
        Args:
            query_id: The identifier for the query
            result_ids: List of identifiers returned by the query
            
        Returns:
            Dictionary with precision, recall, and F1 scores
        """
        pass


class IAblationTester(ABC):
    """Interface for the ablation testing framework."""
    
    @abstractmethod
    def setup_all_collections(self) -> None:
        """Create all collections needed for ablation testing."""
        pass
    
    @abstractmethod
    def ablate_collection(self, collection_name: str) -> None:
        """Temporarily remove a collection from query execution.
        
        Args:
            collection_name: The name of the collection to ablate
        """
        pass
    
    @abstractmethod
    def restore_collection(self, collection_name: str) -> None:
        """Restore a previously ablated collection.
        
        Args:
            collection_name: The name of the collection to restore
        """
        pass
    
    @abstractmethod
    def execute_query(self, query: str, 
                     ablated_collections: Optional[List[str]] = None) -> List[str]:
        """Execute a query with optional collection ablation.
        
        Args:
            query: The natural language query to execute
            ablated_collections: Optional list of collections to ablate
            
        Returns:
            List of identifiers for matching records
        """
        pass
    
    @abstractmethod
    def run_ablation_test(self, 
                         queries: List[str], 
                         activity_types: List[str]) -> Dict[str, Any]:
        """Run a complete ablation test.
        
        Args:
            queries: List of natural language queries to test
            activity_types: List of activity types to ablate
            
        Returns:
            Dictionary with comprehensive test results
        """
        pass


class INamedEntityManager(ABC):
    """Interface for managing named entities."""
    
    @abstractmethod
    def get_entity(self, name: str, entity_type: str) -> Optional[Dict[str, Any]]:
        """Get a named entity by name and type.
        
        Args:
            name: The name of the entity
            entity_type: The type of the entity
            
        Returns:
            Entity dictionary if found, None otherwise
        """
        pass
    
    @abstractmethod
    def add_entity(self, name: str, entity_type: str, 
                  attributes: Dict[str, Any]) -> str:
        """Add a new named entity.
        
        Args:
            name: The name of the entity
            entity_type: The type of the entity
            attributes: Dictionary of entity attributes
            
        Returns:
            Identifier for the added entity
        """
        pass
    
    @abstractmethod
    def update_entity(self, entity_id: str, 
                     attributes: Dict[str, Any]) -> bool:
        """Update an existing entity.
        
        Args:
            entity_id: The identifier for the entity
            attributes: Dictionary of updated attributes
            
        Returns:
            True if the update succeeded, False otherwise
        """
        pass
    
    @abstractmethod
    def get_entities_by_type(self, entity_type: str) -> List[Dict[str, Any]]:
        """Get all entities of a specific type.
        
        Args:
            entity_type: The type of entities to retrieve
            
        Returns:
            List of entity dictionaries
        """
        pass
    
    @abstractmethod
    def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity.
        
        Args:
            entity_id: The identifier for the entity to delete
            
        Returns:
            True if the deletion succeeded, False otherwise
        """
        pass