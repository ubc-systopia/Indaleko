"""Query generation for ablation testing."""

from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class QueryTemplate(BaseModel):
    """Template for generating natural language queries."""
    
    id: UUID = Field(default_factory=uuid4)
    template: str
    parameters: Dict[str, List[str]] = Field(default_factory=dict)
    activity_type: str
    description: str
    
    def generate_query(self, params: Optional[Dict[str, str]] = None) -> str:
        """Generate a query from this template.
        
        Args:
            params: Optional dictionary of parameter values to use.
                   If not provided, random values will be selected.
                   
        Returns:
            str: The generated query.
        """
        # Simple implementation for now - to be expanded
        query = self.template
        if params:
            for key, value in params.items():
                placeholder = f"{{{key}}}"
                query = query.replace(placeholder, value)
        return query


class QueryGenerator:
    """Generator for natural language queries to test ablation."""
    
    def __init__(self, templates: Optional[List[QueryTemplate]] = None):
        """Initialize the query generator.
        
        Args:
            templates: Optional list of QueryTemplate objects to use.
                      If not provided, default templates will be loaded.
        """
        self.templates = templates or self._load_default_templates()
        
    def _load_default_templates(self) -> List[QueryTemplate]:
        """Load default query templates.
        
        Returns:
            List[QueryTemplate]: A list of default query templates.
        """
        # Placeholder implementation - to be expanded with real templates
        return [
            QueryTemplate(
                template="Find documents I worked on while listening to {artist}",
                parameters={"artist": ["Taylor Swift", "The Beatles", "Beyoncé"]},
                activity_type="music",
                description="Query for documents with music activity context"
            ),
            QueryTemplate(
                template="Show files I accessed at {location}",
                parameters={"location": ["home", "work", "coffee shop"]},
                activity_type="location",
                description="Query for files accessed at a specific location"
            ),
        ]
        
    def generate_queries(self, count: int = 10) -> List[Tuple[str, str]]:
        """Generate a set of natural language queries for testing.
        
        Args:
            count: The number of queries to generate.
            
        Returns:
            List[Tuple[str, str]]: A list of (query, activity_type) tuples.
        """
        # Placeholder implementation - to be expanded with real generation logic
        result = []
        
        import random
        for _ in range(count):
            template = random.choice(self.templates)
            query = template.generate_query()
            result.append((query, template.activity_type))
            
        return result
