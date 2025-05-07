#!/usr/bin/env python3
"""
Cluster Generator for the Indaleko ablation study.

This module provides a class for managing activity source grouping into
experimental and control clusters for ablation testing.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import os
import sys
import random
import logging
import json
import uuid
from typing import Dict, List, Any, Optional, Set, Union, NamedTuple
from dataclasses import dataclass

# Add the Indaleko root to the path
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import Indaleko modules
from db.db_collections import IndalekoDBCollections


@dataclass
class ActivitySource:
    """Information about an activity data source."""
    
    name: str
    collection: str
    description: str
    # Metadata categories associated with this source
    categories: List[str]


class ClusterGenerator:
    """Generator for activity source clusters used in ablation testing."""
    
    def __init__(self, seed: int = None):
        """Initialize the cluster generator.
        
        Args:
            seed: Random seed for reproducible results (default: None)
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Set random seed if provided
        if seed is not None:
            random.seed(seed)
            self.logger.info(f"ClusterGenerator initialized with seed {seed}")
        else:
            self.logger.info("ClusterGenerator initialized with system random seed")
        
        # Define all activity sources - use only collections that actually exist in the codebase
        self.sources = [
            ActivitySource(
                name="activity",
                collection=IndalekoDBCollections.Indaleko_ActivityContext_Collection,
                description="General activity records",
                categories=["temporal", "activity", "collaborator"]
            ),
            ActivitySource(
                name="music",
                collection=IndalekoDBCollections.Indaleko_MusicActivityData_Collection,
                description="Music listening activity",
                categories=["temporal", "activity", "ambient"]
            ),
            ActivitySource(
                name="location",
                collection=IndalekoDBCollections.Indaleko_GeoActivityData_Collection,
                description="Geolocation and spatial activity",
                categories=["spatial", "activity"]
            ),
            ActivitySource(
                name="environmental",
                collection=IndalekoDBCollections.Indaleko_TempActivityData_Collection,
                description="Environmental data including temperature",
                categories=["ambient", "environmental"]
            ),
            ActivitySource(
                name="semantic",
                collection=IndalekoDBCollections.Indaleko_SemanticData_Collection,
                description="Semantic metadata",
                categories=["content", "semantic"]
            ),
            ActivitySource(
                name="query_history",
                collection=IndalekoDBCollections.Indaleko_Query_History_Collection,
                description="Query history",
                categories=["activity", "temporal", "query"]
            )
        ]
        
        self.logger.info(f"Initialized with {len(self.sources)} activity sources")
    
    def list_sources(self) -> List[Dict[str, Any]]:
        """Get a list of all available activity sources.
        
        Returns:
            List of activity source information dictionaries
        """
        return [
            {
                "name": source.name,
                "collection": source.collection,
                "description": source.description,
                "categories": source.categories
            }
            for source in self.sources
        ]
    
    def generate_clusters(self, num_clusters: int = 3) -> List[Dict[str, Any]]:
        """Generate random clusters for ablation testing.
        
        This method creates random clusters with a 4/2 split of experimental
        and control sources, with each cluster having a different random
        assignment.
        
        Args:
            num_clusters: Number of clusters to generate (default: 3)
        
        Returns:
            List of cluster dictionaries
        """
        clusters = []
        
        for i in range(num_clusters):
            # Create a random permutation of sources
            sources_copy = self.sources.copy()
            random.shuffle(sources_copy)
            
            # Split into experimental (4) and control (2) groups
            experimental_sources = sources_copy[:4]
            control_sources = sources_copy[4:]
            
            # Store source information
            experimental_info = [
                {
                    "name": source.name,
                    "collection": source.collection,
                    "categories": source.categories
                }
                for source in experimental_sources
            ]
            
            control_info = [
                {
                    "name": source.name,
                    "collection": source.collection,
                    "categories": source.categories
                }
                for source in control_sources
            ]
            
            # Extract the categories covered by each group
            experimental_categories = set()
            for source in experimental_sources:
                experimental_categories.update(source.categories)
                
            control_categories = set()
            for source in control_sources:
                control_categories.update(source.categories)
                
            # Create the cluster dictionary
            cluster = {
                "id": f"cluster_{i+1}",
                "name": f"Cluster {i+1}",
                "experimental_sources": experimental_info,
                "control_sources": control_info,
                "experimental_categories": sorted(list(experimental_categories)),
                "control_categories": sorted(list(control_categories))
            }
            
            clusters.append(cluster)
            
            # Log cluster information
            self.logger.info(f"Generated cluster {i+1}:")
            self.logger.info(f"  Experimental sources: {', '.join(s.name for s in experimental_sources)}")
            self.logger.info(f"  Control sources: {', '.join(s.name for s in control_sources)}")
            self.logger.info(f"  Experimental categories: {', '.join(experimental_categories)}")
            self.logger.info(f"  Control categories: {', '.join(control_categories)}")
        
        return clusters
    
    def get_source_collections(self, source_names: List[str]) -> List[str]:
        """Get collection names for specified sources.
        
        Args:
            source_names: List of source names
        
        Returns:
            List of collection names
        """
        collections = []
        
        for name in source_names:
            for source in self.sources:
                if source.name == name:
                    collections.append(source.collection)
                    break
        
        return collections
    
    def create_balanced_clusters(self, target_categories: List[str] = None) -> List[Dict[str, Any]]:
        """Create category-balanced clusters.
        
        This method creates clusters that try to balance metadata categories
        across experimental and control groups, rather than using pure randomization.
        
        Args:
            target_categories: List of categories to prioritize (default: None)
        
        Returns:
            List of cluster dictionaries
        """
        if not target_categories:
            # Default to all available categories
            target_categories = set()
            for source in self.sources:
                target_categories.update(source.categories)
            target_categories = sorted(list(target_categories))
            
        self.logger.info(f"Creating balanced clusters targeting categories: {target_categories}")
            
        # Create three balanced clusters
        clusters = []
        
        # Calculate category coverage for each source
        source_categories = {}
        for source in self.sources:
            source_categories[source.name] = set(
                cat for cat in source.categories if cat in target_categories
            )
        
        # For each cluster, create a unique balanced split
        for i in range(3):
            if i == 0:
                # First cluster: optimize for balanced category coverage
                experimental_sources, control_sources = self._create_balanced_split(source_categories)
            elif i == 1:
                # Second cluster: emphasize temporal/activity vs. spatial/content
                temporal_activity = ["temporal", "activity"]
                spatial_content = ["spatial", "content"]
                
                # Find sources that cover these categories
                temporal_activity_sources = []
                spatial_content_sources = []
                other_sources = []
                
                for source in self.sources:
                    source_cats = set(source.categories)
                    if any(cat in temporal_activity for cat in source_cats):
                        temporal_activity_sources.append(source)
                    elif any(cat in spatial_content for cat in source_cats):
                        spatial_content_sources.append(source)
                    else:
                        other_sources.append(source)
                
                # Ensure we have at least 4 sources for experimental
                if len(temporal_activity_sources) < 4:
                    # Add some other sources
                    needed = 4 - len(temporal_activity_sources)
                    temporal_activity_sources.extend(other_sources[:needed])
                    other_sources = other_sources[needed:]
                
                # Ensure we have at least 2 sources for control
                if len(spatial_content_sources) < 2:
                    # Add some other sources
                    needed = 2 - len(spatial_content_sources)
                    spatial_content_sources.extend(other_sources[:needed])
                
                # Shuffle to avoid deterministic patterns
                random.shuffle(temporal_activity_sources)
                random.shuffle(spatial_content_sources)
                
                # Take only the required number of sources
                experimental_sources = temporal_activity_sources[:4]
                control_sources = spatial_content_sources[:2]
            else:
                # Third cluster: emphasize activity/collaborator vs. ambient/environmental
                activity_collab = ["activity", "collaborator"]
                ambient_env = ["ambient", "environmental"]
                
                # Find sources that cover these categories
                activity_collab_sources = []
                ambient_env_sources = []
                other_sources = []
                
                for source in self.sources:
                    source_cats = set(source.categories)
                    if any(cat in activity_collab for cat in source_cats):
                        activity_collab_sources.append(source)
                    elif any(cat in ambient_env for cat in source_cats):
                        ambient_env_sources.append(source)
                    else:
                        other_sources.append(source)
                
                # Ensure we have at least 4 sources for experimental
                if len(activity_collab_sources) < 4:
                    # Add some other sources
                    needed = 4 - len(activity_collab_sources)
                    activity_collab_sources.extend(other_sources[:needed])
                    other_sources = other_sources[needed:]
                
                # Ensure we have at least 2 sources for control
                if len(ambient_env_sources) < 2:
                    # Add some other sources
                    needed = 2 - len(ambient_env_sources)
                    ambient_env_sources.extend(other_sources[:needed])
                
                # Shuffle to avoid deterministic patterns
                random.shuffle(activity_collab_sources)
                random.shuffle(ambient_env_sources)
                
                # Take only the required number of sources
                experimental_sources = activity_collab_sources[:4]
                control_sources = ambient_env_sources[:2]
            
            # Extract categories covered by each group
            experimental_categories = set()
            for source in experimental_sources:
                experimental_categories.update(source.categories)
                
            control_categories = set()
            for source in control_sources:
                control_categories.update(source.categories)
            
            # Create the cluster dictionary
            cluster = {
                "id": f"cluster_{i+1}",
                "name": f"Cluster {i+1}",
                "experimental_sources": [
                    {
                        "name": source.name,
                        "collection": source.collection,
                        "categories": source.categories
                    }
                    for source in experimental_sources
                ],
                "control_sources": [
                    {
                        "name": source.name,
                        "collection": source.collection,
                        "categories": source.categories
                    }
                    for source in control_sources
                ],
                "experimental_categories": sorted(list(experimental_categories)),
                "control_categories": sorted(list(control_categories))
            }
            
            clusters.append(cluster)
            
            # Log cluster information
            self.logger.info(f"Generated balanced cluster {i+1}:")
            self.logger.info(f"  Experimental sources: {', '.join(s.name for s in experimental_sources)}")
            self.logger.info(f"  Control sources: {', '.join(s.name for s in control_sources)}")
            self.logger.info(f"  Experimental categories: {', '.join(experimental_categories)}")
            self.logger.info(f"  Control categories: {', '.join(control_categories)}")
        
        return clusters
    
    def _create_balanced_split(self, source_categories: Dict[str, Set[str]]) -> tuple:
        """Create a balanced split of sources based on category coverage.
        
        Args:
            source_categories: Dictionary mapping source names to their categories
        
        Returns:
            Tuple of (experimental_sources, control_sources)
        """
        # Calculate unique categories
        all_categories = set()
        for cats in source_categories.values():
            all_categories.update(cats)
        
        # Calculate category coverage score for each source
        source_scores = {}
        for source in self.sources:
            # Score is the number of unique categories covered
            source_scores[source.name] = len(source_categories.get(source.name, set()))
        
        # Sort sources by score (highest first)
        sorted_sources = sorted(
            self.sources,
            key=lambda s: source_scores.get(s.name, 0),
            reverse=True
        )
        
        # Pick 4 sources for experimental group
        experimental_sources = sorted_sources[:4]
        
        # Pick 2 sources for control group
        control_sources = sorted_sources[4:6]
        
        return experimental_sources, control_sources
    
    def save_clusters_to_file(self, clusters: List[Dict[str, Any]], file_path: str) -> bool:
        """Save generated clusters to a JSON file.
        
        Args:
            clusters: List of cluster dictionaries
            file_path: Path to save the JSON file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'w') as f:
                json.dump({
                    "sources": self.list_sources(),
                    "clusters": clusters
                }, f, indent=2)
            
            self.logger.info(f"Saved {len(clusters)} clusters to {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving clusters to file: {e}")
            return False
    
    def load_clusters_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Load clusters from a JSON file.
        
        Args:
            file_path: Path to the JSON file
        
        Returns:
            List of cluster dictionaries
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            clusters = data.get("clusters", [])
            self.logger.info(f"Loaded {len(clusters)} clusters from {file_path}")
            return clusters
        except Exception as e:
            self.logger.error(f"Error loading clusters from file: {e}")
            return []


def main():
    """Test the ClusterGenerator."""
    logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
    
    # Create a generator with a fixed seed for reproducibility
    generator = ClusterGenerator(seed=42)
    
    print("\nAvailable Activity Sources:")
    for source in generator.list_sources():
        print(f"- {source['name']}: {source['description']}")
        print(f"  Collection: {source['collection']}")
        print(f"  Categories: {', '.join(source['categories'])}")
    
    # Generate random clusters
    print("\nGenerating Random Clusters:")
    clusters = generator.generate_clusters(num_clusters=3)
    
    # Save clusters to file
    generator.save_clusters_to_file(clusters, "ablation_clusters.json")
    print("\nClusters saved to ablation_clusters.json")
    
    # Generate balanced clusters
    print("\nGenerating Balanced Clusters:")
    balanced_clusters = generator.create_balanced_clusters()
    
    # Save balanced clusters to file
    generator.save_clusters_to_file(balanced_clusters, "balanced_ablation_clusters.json")
    print("\nBalanced clusters saved to balanced_ablation_clusters.json")


if __name__ == "__main__":
    main()