#!/usr/bin/env python
"""
Example script to demonstrate the cross-collection query generator.

This script shows how to use the CrossCollectionQueryGenerator to create
queries that span multiple activity types for ablation testing.
"""

import argparse
import logging
import json
import os
import sys
from datetime import datetime

# Ensure INDALEKO_ROOT is set
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from research.ablation.models.activity import ActivityType
from research.ablation.query.enhanced.cross_collection_query_generator import (
    CrossCollectionQueryGenerator,
    CrossCollectionRelationshipType,
)


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger(__name__)


def run_example(count=5, verbose=False, output_file=None, specific_pair=None, specific_relationship=None):
    """Run a cross-collection query generator example.
    
    Args:
        count: Number of queries to generate
        verbose: Whether to print full query details
        output_file: Optional path to save results to
        specific_pair: Optional tuple of activity types to use
        specific_relationship: Optional relationship type to use
    """
    logger = setup_logging()
    logger.info("Starting cross-collection query generator example")
    
    # Initialize generator
    generator = CrossCollectionQueryGenerator()
    logger.info("CrossCollectionQueryGenerator initialized")
    
    # Define activity type pairs to use for examples
    if specific_pair:
        # Parse specific activity types
        activity_map = {
            "music": ActivityType.MUSIC,
            "location": ActivityType.LOCATION,
            "task": ActivityType.TASK,
            "collaboration": ActivityType.COLLABORATION,
            "storage": ActivityType.STORAGE,
            "media": ActivityType.MEDIA,
        }
        act_type1 = activity_map.get(specific_pair[0].lower())
        act_type2 = activity_map.get(specific_pair[1].lower())
        
        if not act_type1 or not act_type2:
            logger.error(f"Invalid activity type pair: {specific_pair}")
            sys.exit(1)
            
        activity_pairs = [(act_type1, act_type2)]
    else:
        # Use a variety of predefined pairs
        activity_pairs = [
            (ActivityType.MUSIC, ActivityType.LOCATION),
            (ActivityType.TASK, ActivityType.COLLABORATION),
            (ActivityType.LOCATION, ActivityType.TASK),
            (ActivityType.MUSIC, ActivityType.TASK),
            (ActivityType.COLLABORATION, ActivityType.STORAGE),
        ]
    
    # Define relationship types
    if specific_relationship:
        relationship_types = [specific_relationship]
    else:
        relationship_types = [
            CrossCollectionRelationshipType.TEMPORAL,
            CrossCollectionRelationshipType.SPATIAL,
            CrossCollectionRelationshipType.CONTEXT,
            CrossCollectionRelationshipType.CAUSAL,
            CrossCollectionRelationshipType.SEMANTIC,
        ]
    
    # Generate queries
    queries = []
    total_per_pair = max(1, count // len(activity_pairs))
    
    for pair in activity_pairs:
        logger.info(f"Generating queries for activity pair: {pair[0].name} + {pair[1].name}")
        
        # Get supported relationships for this pair
        supported_relationships = generator.relationship_mappings.get(pair, [])
        if not supported_relationships:
            logger.warning(f"No supported relationships for {pair}, skipping")
            continue
            
        # Filter to use only supported relationships
        pair_relationships = [r for r in relationship_types if r in supported_relationships]
        if not pair_relationships:
            logger.warning(f"No matching relationships for {pair}, using defaults")
            pair_relationships = supported_relationships
        
        # Generate queries for each relationship type
        for relationship in pair_relationships:
            logger.info(f"Generating queries with relationship: {relationship}")
            
            # Generate a smaller batch for this specific combination
            batch_size = max(1, total_per_pair // len(pair_relationships))
            pair_queries = generator.generate_queries_batch(
                count=batch_size,
                activity_type_pairs=[pair],
                relationship_types=[relationship],
                difficulty_levels=["easy", "medium", "hard"],
            )
            
            # Add to the full set
            queries.extend(pair_queries)
            
    # Limit to requested count
    queries = queries[:count]
    
    # Print results
    logger.info(f"Generated {len(queries)} cross-collection queries:")
    for i, query in enumerate(queries, 1):
        activity_types = ", ".join([a.name for a in query.activity_types])
        relationship = query.metadata.get("relationship_type", "unknown")
        difficulty = query.difficulty
        
        print(f"\n{i}. Query: {query.query_text}")
        print(f"   Activity Types: {activity_types}")
        print(f"   Relationship: {relationship}")
        print(f"   Difficulty: {difficulty}")
        
        if verbose:
            # Print additional details
            print(f"   Query ID: {query.query_id}")
            print(f"   Expected Matches: {len(query.expected_matches)}")
            entities = query.metadata.get("entities", {})
            if entities:
                print("   Entities:")
                for entity_type, entity_list in entities.items():
                    if entity_list:
                        print(f"     {entity_type}: {', '.join(entity_list)}")
    
    # Save results to file if requested
    if output_file:
        # Create serializable version of queries
        serializable_queries = []
        for query in queries:
            serializable_query = {
                "query_id": str(query.query_id),
                "query_text": query.query_text,
                "activity_types": [a.name for a in query.activity_types],
                "difficulty": query.difficulty,
                "relationship_type": query.metadata.get("relationship_type", "unknown"),
                "entities": query.metadata.get("entities", {}),
                "expected_matches": query.expected_matches,
            }
            serializable_queries.append(serializable_query)
        
        # Save to file
        with open(output_file, "w") as f:
            json.dump({"queries": serializable_queries}, f, indent=2)
        logger.info(f"Saved results to {output_file}")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Cross-collection query generator example")
    parser.add_argument("--count", type=int, default=5, help="Number of queries to generate (default: 5)")
    parser.add_argument("--verbose", action="store_true", help="Print full query details")
    parser.add_argument("--output", type=str, help="Path to save results to")
    parser.add_argument("--activity-types", type=str, nargs=2, 
                        choices=["music", "location", "task", "collaboration", "storage", "media"],
                        help="Specific activity type pair to use")
    parser.add_argument("--relationship", type=str, 
                        choices=["temporal", "spatial", "context", "causal", "semantic"],
                        help="Specific relationship type to use")
    
    args = parser.parse_args()
    
    try:
        run_example(
            count=args.count,
            verbose=args.verbose,
            output_file=args.output,
            specific_pair=args.activity_types,
            specific_relationship=args.relationship,
        )
    except KeyboardInterrupt:
        print("\nOperation interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()