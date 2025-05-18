#!/usr/bin/env python
"""
Cross-collection query generator for ablation testing.

This module extends the existing query generators to support queries
that span multiple collections with relationships.
"""

import json
import logging
import random
import sys
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from research.ablation.models.activity import ActivityType
from research.ablation.query.enhanced.enhanced_query_generator import EnhancedQueryGenerator
from research.ablation.query.generator import TestQuery
from research.ablation.registry.shared_entity_registry import SharedEntityRegistry


class CrossCollectionQueryGenerator:
    """
    Generator for queries that span multiple collections with relationships.
    
    This class extends the EnhancedQueryGenerator to create queries that leverage
    the cross-collection references established with the SharedEntityRegistry.
    """
    
    # Relationship types that can be used in cross-collection queries
    DEFAULT_RELATIONSHIP_TYPES = [
        "created_in",      # Task created in a meeting
        "has_tasks",       # Meeting has associated tasks 
        "located_at",      # Meeting located at a specific place
        "hosted_meetings", # Location hosted specific meetings
        "discussed_in",    # Task discussed in a meeting
        "related_to",      # Generic relationship
        "part_of",         # Entity is part of another entity
    ]
    
    # Default collection pairs for cross-collection queries
    DEFAULT_COLLECTION_PAIRS = [
        (ActivityType.TASK, ActivityType.COLLABORATION),
        (ActivityType.COLLABORATION, ActivityType.LOCATION),
        (ActivityType.TASK, ActivityType.LOCATION),
        (ActivityType.MUSIC, ActivityType.LOCATION),
    ]
    
    def __init__(self, entity_registry: Optional[SharedEntityRegistry] = None, api_key: str = None):
        """
        Initialize the cross-collection query generator.
        
        Args:
            entity_registry: Optional SharedEntityRegistry to use for entity references
            api_key: Optional API key for the LLM service
        """
        self.logger = logging.getLogger(__name__)
        
        # Store or create the entity registry
        self.entity_registry = entity_registry or SharedEntityRegistry()
        
        # Use the enhanced query generator for base functionality
        self.enhanced_generator = EnhancedQueryGenerator(api_key=api_key)
        
        # Descriptions for activity types and relationships
        self.activity_descriptions = {
            ActivityType.MUSIC: "music listening activities (e.g., songs, artists, albums, playlists)",
            ActivityType.LOCATION: "location activities (e.g., places, coordinates, visits)",
            ActivityType.TASK: "task management activities (e.g., to-dos, projects, deadlines)",
            ActivityType.COLLABORATION: "collaboration activities (e.g., meetings, shared documents, messages)",
            ActivityType.STORAGE: "storage activities (e.g., file operations, downloads, folders)",
            ActivityType.MEDIA: "media consumption activities (e.g., videos, streaming services, content)",
        }
        
        # Descriptions of relationships between collection types
        self.relationship_descriptions = {
            "created_in": "tasks that were created during specific meetings",
            "has_tasks": "meetings where specific tasks were assigned or created",
            "located_at": "meetings that took place at specific locations",
            "hosted_meetings": "locations where specific meetings were held",
            "discussed_in": "tasks that were discussed in specific meetings",
            "related_to": "entities that are related to each other in some way",
            "part_of": "entities that are part of larger entities or activities",
        }
    
    def generate_cross_collection_queries(
        self,
        count: int,
        relationship_types: List[str] = None,
        collection_pairs: List[Tuple[ActivityType, ActivityType]] = None,
    ) -> List[TestQuery]:
        """
        Generate queries that span multiple collections with relationships.
        
        Args:
            count: Number of queries to generate
            relationship_types: Optional list of relationship types to include
            collection_pairs: Optional list of collection pairs to focus on
            
        Returns:
            List of TestQuery objects with cross-collection references
        """
        self.logger.info(f"Generating {count} cross-collection queries")
        
        # Use default relationship types if not specified
        if not relationship_types:
            relationship_types = self.DEFAULT_RELATIONSHIP_TYPES
        
        # Use default collection pairs if not specified
        if not collection_pairs:
            collection_pairs = self.DEFAULT_COLLECTION_PAIRS
        
        queries = []
        for i in range(count):
            # Select a collection pair
            pair_idx = i % len(collection_pairs)
            primary_type, secondary_type = collection_pairs[pair_idx]
            
            # Select a relationship type
            rel_idx = i % len(relationship_types)
            relationship = relationship_types[rel_idx]
            
            # Generate the cross-collection query
            query = self._generate_single_cross_collection_query(
                primary_type, secondary_type, relationship
            )
            
            if query:
                queries.append(query)
            else:
                self.logger.error(f"Failed to generate cross-collection query for {primary_type.name}-{secondary_type.name} with relationship {relationship}")
                self.logger.error("This is required for proper ablation testing - fix the query generator")
                sys.exit(1)  # Fail-stop immediately - no fallbacks
        
        return queries
    
    def _generate_single_cross_collection_query(
        self,
        primary_type: ActivityType,
        secondary_type: ActivityType,
        relationship_type: str,
    ) -> Optional[TestQuery]:
        """
        Generate a single query spanning two collections with a relationship.
        
        Args:
            primary_type: Primary activity type
            secondary_type: Secondary activity type
            relationship_type: Type of relationship between entities
            
        Returns:
            TestQuery object or None if generation failed
        """
        # Create a system prompt focusing on the relationship
        system_prompt = f"""Generate a natural language search query that relates {self.activity_descriptions[primary_type]} with {self.activity_descriptions[secondary_type]} using the relationship '{relationship_type}'.

For example, if '{relationship_type}' is 'created_in', the query might be 'Find documents for tasks created during the team meeting'.

Your query should search for files based on their relationship across different activity types. Make the query sound natural, as a real user would ask it.
"""
        
        # Create a user prompt with guidelines for the query
        user_prompt = f"""Create ONE realistic search query that spans multiple activity types.

The query should relate {primary_type.name.lower()} activities and {secondary_type.name.lower()} activities through the '{relationship_type}' relationship ({self.relationship_descriptions.get(relationship_type, "entities related in some way")}).

Examples:
- "Find documents related to tasks created during the quarterly planning meeting" (TASK + COLLABORATION with 'created_in')
- "Show files I worked on at the coffee shop where I had my team meeting" (LOCATION + COLLABORATION with 'hosted_meetings')
- "Get documents for projects discussed in meetings at the downtown office" (TASK + COLLABORATION + LOCATION with multiple relationships)

Respond with ONLY a JSON object in this exact format:
{{
  "query": "the search query text",
  "entities": {{
    "primary_entities": ["entity1", "entity2"],
    "secondary_entities": ["entity3", "entity4"]
  }},
  "relationship": "{relationship_type}",
  "primary_type": "{primary_type.name}",
  "secondary_type": "{secondary_type.name}",
  "reasoning": "brief explanation of how this query shows the relationship"
}}

The query should include specific named entities that might appear in both collections.
"""
        
        try:
            # Get completion from LLM
            response_text = self.enhanced_generator.generator.get_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7
            )
            
            # Extract JSON from the response
            import re
            json_match = re.search(r"({.*})", response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
                response = json.loads(json_text)
            else:
                # Try parsing the whole response
                response = json.loads(response_text)
            
            query_text = response.get("query", "")
            
            # Clean up the query if needed
            if query_text.startswith('"') and query_text.endswith('"'):
                query_text = query_text[1:-1]
            
            # Extract metadata for expected matches
            entities = response.get("entities", {})
            primary_entities = entities.get("primary_entities", [])
            secondary_entities = entities.get("secondary_entities", [])
            
            # Generate expected matches considering both collections
            expected_matches = self._generate_cross_collection_matches(
                primary_type, secondary_type, relationship_type,
                primary_entities, secondary_entities
            )
            
            # Create metadata with relationship information
            metadata = {
                "relationship_type": relationship_type,
                "primary_activity": primary_type.name,
                "secondary_activity": secondary_type.name,
                "entities": entities,
                "reasoning": response.get("reasoning", ""),
                "cross_collection": True,
                "llm_generated": True,
            }
            
            # Create the TestQuery object
            query = TestQuery(
                query_text=query_text,
                activity_types=[primary_type, secondary_type],
                expected_matches=expected_matches,
                metadata=metadata,
                difficulty="medium"  # Default to medium difficulty for cross-collection queries
            )
            
            return query
            
        except Exception as e:
            self.logger.error(f"Error generating cross-collection query: {e}")
            return None
    
    def _generate_cross_collection_matches(
        self,
        primary_type: ActivityType,
        secondary_type: ActivityType,
        relationship_type: str,
        primary_entities: List[str] = None,
        secondary_entities: List[str] = None,
    ) -> List[str]:
        """
        Generate expected matches for a cross-collection query.
        
        Args:
            primary_type: Primary activity type
            secondary_type: Secondary activity type
            relationship_type: Type of relationship between entities
            primary_entities: Entities from the primary collection
            secondary_entities: Entities from the secondary collection
            
        Returns:
            List of document IDs that should match the query
        """
        matches = []
        
        # Generate consistent collection names
        primary_collection = f"ablation_{primary_type.name.lower()}"
        secondary_collection = f"ablation_{secondary_type.name.lower()}"
        
        # Look for real entity relationships in the registry if available
        if self.entity_registry:
            # Get entities that have relationships of this type
            entity_matches = self._find_matching_entity_relationships(
                primary_type, secondary_type, relationship_type
            )
            
            if entity_matches:
                for entity_id in entity_matches:
                    doc_id = f"Objects/{entity_id}"
                    matches.append(doc_id)
        
        # If no matches found through registry, generate synthetic ones
        if not matches:
            # Use the entities mentioned in the query to create deterministic matches
            primary_entity_part = "_".join(
                e.lower().replace(" ", "_") for e in (primary_entities or [])[:2]
            ) if primary_entities else ""
            
            secondary_entity_part = "_".join(
                e.lower().replace(" ", "_") for e in (secondary_entities or [])[:2]
            ) if secondary_entities else ""
            
            # Create synthetic document IDs
            for i in range(5):  # Default to 5 matches for cross-collection queries
                doc_id = f"Objects/{primary_collection}"
                if primary_entity_part:
                    doc_id += f"_{primary_entity_part}"
                doc_id += f"_{relationship_type}"
                if secondary_entity_part:
                    doc_id += f"_{secondary_entity_part}"
                doc_id += f"_{i+1}"
                
                matches.append(doc_id)
        
        return matches
    
    def _find_matching_entity_relationships(
        self,
        primary_type: ActivityType,
        secondary_type: ActivityType,
        relationship_type: str,
    ) -> List[UUID]:
        """
        Find real entity relationships in the registry that match the query.
        
        Args:
            primary_type: Primary activity type
            secondary_type: Secondary activity type
            relationship_type: Type of relationship between entities
            
        Returns:
            List of entity UUIDs that match the criteria
        """
        matching_entities = []
        
        # Generate collection names
        primary_collection = f"ablation_{primary_type.name.lower()}"
        secondary_collection = f"ablation_{secondary_type.name.lower()}"
        
        # Get all entities in the primary collection
        primary_entities = self.entity_registry.get_entities_by_collection(primary_collection)
        
        # For each primary entity, check if it has the relationship
        for entity_id in primary_entities:
            references = self.entity_registry.get_entity_references(entity_id, relationship_type)
            
            # Check if any references point to the secondary collection
            for ref in references:
                if ref.collection_name == secondary_collection:
                    matching_entities.append(entity_id)
                    break
        
        return matching_entities
    
    def generate_diverse_cross_collection_queries(
        self,
        count: int,
        similarity_threshold: float = 0.85,
        max_attempts: int = 100,
    ) -> List[TestQuery]:
        """
        Generate a diverse set of cross-collection queries.
        
        Args:
            count: Number of diverse queries to generate
            similarity_threshold: Maximum similarity allowed between queries
            max_attempts: Maximum attempts to generate diverse queries
            
        Returns:
            List of diverse TestQuery objects
        """
        self.logger.info(f"Generating {count} diverse cross-collection queries")
        
        diverse_queries = []
        attempts = 0
        
        while len(diverse_queries) < count and attempts < max_attempts:
            # Generate a candidate query
            collection_pairs = random.sample(self.DEFAULT_COLLECTION_PAIRS, 1)
            relationship_types = random.sample(self.DEFAULT_RELATIONSHIP_TYPES, 1)
            
            candidate_queries = self.generate_cross_collection_queries(
                1, relationship_types, collection_pairs
            )
            
            if not candidate_queries:
                attempts += 1
                continue
                
            candidate = candidate_queries[0]
            candidate_text = candidate.query_text
            
            # Check similarity with existing queries
            is_diverse = True
            for existing_query in diverse_queries:
                existing_text = existing_query.query_text
                
                # Use a simple similarity check 
                # (can be replaced with Jaro-Winkler if available)
                word_set1 = set(candidate_text.lower().split())
                word_set2 = set(existing_text.lower().split())
                
                if not word_set1 or not word_set2:
                    continue
                    
                common_words = len(word_set1.intersection(word_set2))
                total_words = len(word_set1.union(word_set2))
                
                similarity = common_words / total_words
                
                if similarity >= similarity_threshold:
                    is_diverse = False
                    break
            
            # Add to diverse set if sufficiently different
            if is_diverse:
                diverse_queries.append(candidate)
            
            attempts += 1
        
        # If we couldn't get enough diverse queries, return what we have
        if len(diverse_queries) < count:
            self.logger.warning(
                f"Could only generate {len(diverse_queries)}/{count} diverse queries after {attempts} attempts",
            )
        
        return diverse_queries


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logger = logging.getLogger(__name__)
    
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description="Cross-collection query generation")
    parser.add_argument("--count", type=int, default=5, help="Number of queries to generate")
    parser.add_argument("--relationship", type=str, help="Specific relationship type to use")
    parser.add_argument("--diverse", action="store_true", help="Generate diverse queries")
    args = parser.parse_args()
    
    try:
        # Create generator
        generator = CrossCollectionQueryGenerator()
        
        # Generate queries
        if args.diverse:
            queries = generator.generate_diverse_cross_collection_queries(args.count)
        else:
            relationship_types = [args.relationship] if args.relationship else None
            queries = generator.generate_cross_collection_queries(args.count, relationship_types)
        
        # Print the generated queries
        print(f"\nGenerated {len(queries)} cross-collection queries:\n")
        for i, query in enumerate(queries, 1):
            print(f"{i}. {query.query_text}")
            print(f"   Relationship: {query.metadata.get('relationship_type')}")
            print(f"   Collections: {query.metadata.get('primary_activity')} + {query.metadata.get('secondary_activity')}")
            print(f"   Expected matches: {len(query.expected_matches)}")
            print()
            
    except Exception as e:
        logger.error(f"Error running cross-collection query generation: {e}", exc_info=True)