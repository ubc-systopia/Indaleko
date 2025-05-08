"""
Query generator for the ablation study framework.

This module provides functionality for generating natural language queries
and extracting their components for synthetic metadata generation.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# Try to import LLM connector from Indaleko
try:
    from query.utils.llm_connector.factory import LLMFactory
except ImportError:
    # Fallback to mock implementation if not available
    class LLMFactory:
        """Mock LLM factory for standalone testing."""
        
        @staticmethod
        def get_llm(provider="openai"):
            """Get a mock LLM connector."""
            return MockLLM()

class MockLLM:
    """Mock LLM for testing without actual LLM integration."""
    
    def generate_text(self, prompt, **kwargs):
        """Generate mock text based on the prompt."""
        return f"Mock response for: {prompt[:50]}..."


class QueryGenerator:
    """Generator for natural language queries and components extraction.
    
    This class provides functionality for generating realistic natural language
    queries for different activity types and extracting their components for
    synthetic metadata generation.
    """
    
    # Templates for different query types
    QUERY_TEMPLATES = {
        "music": [
            "What songs did I listen to by {artist} last {time_period}?",
            "When did I last listen to {song_title}?",
            "Show me all albums I've listened to by {artist}",
            "Which songs did I play most frequently last {time_period}?",
            "Find songs I listened to with a {mood} mood"
        ],
        "location": [
            "Where was I on {date}?",
            "How many times did I visit {location} last {time_period}?",
            "What places did I visit in {city} during {month}?",
            "When was the last time I was at {location}?",
            "How long did I stay at {location} on {date}?"
        ],
        "task": [
            "What tasks did I complete last {time_period}?",
            "Show me all tasks related to {project}",
            "When did I last work on {task_name}?",
            "What tasks are due this {time_period}?",
            "How much time did I spend on {project} tasks last {time_period}?"
        ],
        "collaboration": [
            "Who did I meet with about {topic} last {time_period}?",
            "Show me all files shared during the {project} meeting",
            "When was my last meeting with {person}?",
            "What documents were shared in the {project} collaboration?",
            "How many collaboration sessions did I have about {topic}?"
        ],
        "storage": [
            "Find all documents I modified last {time_period}",
            "When did I last access {filename}?",
            "Which files did I share with {person}?",
            "Show me all {file_type} files I created in {project} folder",
            "What files did I download from {source} last {time_period}?"
        ],
        "media": [
            "What videos did I watch about {topic} last {time_period}?",
            "How long did I watch {channel} videos last {time_period}?",
            "When did I last watch a video about {topic}?",
            "Show me all videos I watched on {channel}",
            "Which {genre} videos did I watch last {time_period}?"
        ]
    }
    
    # Fill-in values for templates
    TEMPLATE_VALUES = {
        "artist": ["Taylor Swift", "The Beatles", "Drake", "Adele", "BTS"],
        "song_title": ["Shape of You", "Blinding Lights", "Bad Guy", "Uptown Funk", "Dynamite"],
        "mood": ["happy", "relaxed", "energetic", "melancholy", "focused"],
        "date": ["January 15th", "last Tuesday", "March 3rd", "yesterday", "April 10th"],
        "location": ["Coffee Shop", "Gym", "Office", "Park", "Restaurant"],
        "city": ["New York", "London", "Tokyo", "Paris", "Seattle"],
        "month": ["January", "February", "June", "August", "December"],
        "time_period": ["week", "month", "year", "day", "weekend"],
        "project": ["Marketing Campaign", "Website Redesign", "Q1 Report", "Mobile App", "Research Paper"],
        "task_name": ["Create Presentation", "Write Documentation", "Design Logo", "Code Review", "Data Analysis"],
        "topic": ["Budget Planning", "Product Launch", "Customer Feedback", "Market Research", "Technical Issues"],
        "person": ["John", "Sarah", "Alex", "Maria", "David"],
        "filename": ["Quarterly Report.docx", "Presentation.pptx", "Budget.xlsx", "Proposal.pdf", "Notes.txt"],
        "file_type": ["PDF", "Word", "Excel", "Image", "Video"],
        "source": ["Email", "Company Portal", "Google Drive", "Dropbox", "OneDrive"],
        "channel": ["TED Talks", "National Geographic", "Technology Reviews", "Cooking Tutorials", "Educational"],
        "genre": ["Documentary", "Educational", "Tutorial", "Entertainment", "News"]
    }
    
    def __init__(self, llm_provider: str = "openai", seed: Optional[int] = None):
        """Initialize the query generator.
        
        Args:
            llm_provider: The LLM provider to use
            seed: Optional random seed for reproducibility
        """
        self.llm = LLMFactory.get_llm(provider=llm_provider)
        self.logger = logging.getLogger(__name__)
        
        # Set random seed if provided
        if seed is not None:
            import random
            random.seed(seed)
    
    def generate_queries(self, activity_type: str, count: int) -> List[Dict[str, Any]]:
        """Generate natural language queries for a specific activity type.
        
        Args:
            activity_type: The type of activity to generate queries for
            count: The number of queries to generate
            
        Returns:
            List of query dictionaries with natural language and components
        """
        if activity_type not in self.QUERY_TEMPLATES:
            raise ValueError(f"Unsupported activity type: {activity_type}")
        
        queries = []
        
        for _ in range(count):
            query_text = self._generate_query_text(activity_type)
            query_components = self.parse_query(query_text, activity_type)
            
            query_id = str(uuid.uuid4())
            query_data = {
                "id": query_id,
                "text": query_text,
                "activity_type": activity_type,
                "components": query_components,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            queries.append(query_data)
            
        return queries
    
    def _generate_query_text(self, activity_type: str) -> str:
        """Generate a natural language query for a specific activity type.
        
        Args:
            activity_type: The type of activity to generate the query for
            
        Returns:
            A natural language query string
        """
        import random
        
        # Get a random template for the activity type
        templates = self.QUERY_TEMPLATES[activity_type]
        template = random.choice(templates)
        
        # Fill in the template
        filled_template = template
        
        # Find all placeholders in the template
        import re
        placeholders = re.findall(r'\{([^}]+)\}', template)
        
        # Replace each placeholder with a random value
        for placeholder in placeholders:
            if placeholder in self.TEMPLATE_VALUES:
                value = random.choice(self.TEMPLATE_VALUES[placeholder])
                filled_template = filled_template.replace(f"{{{placeholder}}}", value)
        
        return filled_template
    
    def parse_query(self, query: str, activity_type: Optional[str] = None) -> Dict[str, Any]:
        """Parse a natural language query into components.
        
        This method extracts entities, attributes, and relationships from
        a natural language query to facilitate metadata generation.
        
        Args:
            query: The natural language query to parse
            activity_type: Optional activity type to guide parsing
            
        Returns:
            Dictionary of query components (entities, attributes, relationships)
        """
        # First, try to use the LLM to extract components
        components = self._extract_components_with_llm(query, activity_type)
        
        # If LLM extraction fails, fall back to rule-based extraction
        if not components:
            components = self._extract_components_rule_based(query, activity_type)
        
        return components
    
    def _extract_components_with_llm(self, query: str, activity_type: Optional[str] = None) -> Dict[str, Any]:
        """Extract query components using an LLM.
        
        Args:
            query: The natural language query to parse
            activity_type: Optional activity type to guide parsing
            
        Returns:
            Dictionary of query components
        """
        prompt = self._build_extraction_prompt(query, activity_type)
        
        try:
            response = self.llm.generate_text(prompt)
            components = self._parse_llm_response(response)
            return components
        except Exception as e:
            self.logger.error(f"Error extracting components with LLM: {e}")
            return {}
    
    def _build_extraction_prompt(self, query: str, activity_type: Optional[str] = None) -> str:
        """Build a prompt for extracting query components with an LLM.
        
        Args:
            query: The natural language query to parse
            activity_type: Optional activity type to guide parsing
            
        Returns:
            Prompt string for the LLM
        """
        prompt = f"""
        Extract the key components from the following query, categorizing them as entities, attributes, and relationships.
        Output the result as a JSON object.
        
        Query: "{query}"
        
        """
        
        if activity_type:
            prompt += f"\nThis query is related to {activity_type} activity."
        
        prompt += """
        
        Format the output as a JSON object with these fields:
        - entities: array of entity objects (name, type)
        - attributes: array of attribute objects (name, value, entity)
        - relationships: array of relationship objects (source, target, type)
        - temporal: object with time-related aspects (period, specific_date, frequency)
        
        Example output:
        {
          "entities": [
            {"name": "Taylor Swift", "type": "artist"},
            {"name": "songs", "type": "media"}
          ],
          "attributes": [
            {"name": "listened", "value": true, "entity": "songs"}
          ],
          "relationships": [
            {"source": "songs", "target": "Taylor Swift", "type": "created_by"}
          ],
          "temporal": {
            "period": "last week",
            "specific_date": null,
            "frequency": null
          }
        }
        """
        
        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response into a structured components dictionary.
        
        Args:
            response: The LLM response to parse
            
        Returns:
            Dictionary of query components
        """
        try:
            # Extract JSON from the response
            import re
            json_match = re.search(r'\{.+\}', response, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                components = json.loads(json_str)
                return components
            else:
                self.logger.error("Could not find JSON in LLM response")
                return {}
        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            return {}
    
    def _extract_components_rule_based(self, query: str, activity_type: Optional[str] = None) -> Dict[str, Any]:
        """Extract query components using rule-based methods.
        
        This is a fallback method when LLM extraction fails.
        
        Args:
            query: The natural language query to parse
            activity_type: Optional activity type to guide parsing
            
        Returns:
            Dictionary of query components
        """
        components = {
            "entities": [],
            "attributes": [],
            "relationships": [],
            "temporal": {
                "period": None,
                "specific_date": None,
                "frequency": None
            }
        }
        
        # Extract temporal information
        time_periods = ["day", "week", "month", "year", "weekend"]
        for period in time_periods:
            if f"last {period}" in query.lower():
                components["temporal"]["period"] = f"last {period}"
                break
            if f"this {period}" in query.lower():
                components["temporal"]["period"] = f"this {period}"
                break
        
        # Extract entities based on activity type
        if activity_type:
            # Extract entities from named entity values in the template
            for entity_type, values in self.TEMPLATE_VALUES.items():
                for value in values:
                    if value in query:
                        # Map template values to entity types based on activity type
                        entity_mapping = {
                            "music": {"artist": "artist", "song_title": "song", "mood": "mood"},
                            "location": {"location": "place", "city": "city"},
                            "task": {"project": "project", "task_name": "task"},
                            "collaboration": {"person": "person", "project": "project", "topic": "topic"},
                            "storage": {"filename": "file", "file_type": "file_type", "project": "project"},
                            "media": {"channel": "channel", "topic": "topic", "genre": "genre"}
                        }
                        
                        if activity_type in entity_mapping and entity_type in entity_mapping[activity_type]:
                            entity_type_name = entity_mapping[activity_type][entity_type]
                            components["entities"].append({
                                "name": value,
                                "type": entity_type_name
                            })
        
        return components
    
    def save_queries(self, queries: List[Dict[str, Any]], output_path: Path) -> None:
        """Save generated queries to a file.
        
        Args:
            queries: List of query dictionaries
            output_path: Path to save the queries to
        """
        with open(output_path, 'w') as f:
            json.dump(queries, f, indent=2)
    
    def load_queries(self, input_path: Path) -> List[Dict[str, Any]]:
        """Load queries from a file.
        
        Args:
            input_path: Path to load the queries from
            
        Returns:
            List of query dictionaries
        """
        with open(input_path, 'r') as f:
            queries = json.load(f)
        return queries