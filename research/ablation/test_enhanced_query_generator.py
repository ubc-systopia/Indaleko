#!/usr/bin/env python3
"""
Test script for the enhanced query generator.

This script tests the enhanced query generator independently of the full ablation framework.
"""

import argparse
import logging
import os
import sys
from typing import List

from pathlib import Path

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

from research.ablation.query.enhanced.enhanced_query_generator import EnhancedQueryGenerator


def setup_logging(verbose=False):
    """Set up logging for the test script."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )


def test_generator(activity_type: str, count: int, verbose: bool = False) -> List[str]:
    """Test the enhanced query generator for a specific activity type.
    
    Args:
        activity_type: The activity type to generate queries for
        count: Number of queries to generate
        verbose: Whether to enable verbose logging
        
    Returns:
        List of generated queries
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Create the generator
        generator = EnhancedQueryGenerator()
        
        # Log the generator class
        logger.info(f"Created generator: {generator.__class__.__name__}")
        
        # Generate queries with enhanced diversity
        logger.info(f"Generating enhanced queries for {activity_type}...")
        
        try:
            # Try to generate queries
            queries = generator.generate_enhanced_queries(activity_type, count=count)
            logger.info(f"Successfully generated {len(queries)} queries")
            
            # Log the queries
            for i, query in enumerate(queries, 1):
                logger.info(f"  Query {i}: {query}")
                
            return queries
            
        except Exception as e:
            logger.error(f"Error generating enhanced queries: {e}")
            logger.debug("Falling back to direct LLM query generation")
            
            # Fall back to direct generation from the base generator
            try:
                direct_queries = generator.generator.generate_queries_for_activity_type(
                    activity_type, count=count
                )
                logger.info(f"Generated {len(direct_queries)} queries using direct generation")
                
                # Log the queries
                for i, query in enumerate(direct_queries, 1):
                    logger.info(f"  Direct Query {i}: {query}")
                    
                return direct_queries
                
            except Exception as e2:
                logger.error(f"Error in direct query generation: {e2}")
                logger.debug("Using fallback template queries")
                
                # Use template-based fallback
                template_queries = [
                    f"Find {activity_type} files",
                    f"Search for {activity_type} documents",
                    f"Show me {activity_type} data",
                    f"What {activity_type} information do I have?",
                    f"{activity_type} files from yesterday",
                    f"Recent {activity_type} activities",
                    f"{activity_type}",
                    f"All {activity_type} documents",
                    f"My {activity_type} history",
                    f"Find {activity_type} from last week"
                ][:count]
                
                logger.info(f"Generated {len(template_queries)} template queries")
                
                # Log the queries
                for i, query in enumerate(template_queries, 1):
                    logger.info(f"  Template Query {i}: {query}")
                    
                return template_queries
                
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return []


def main():
    """Run the test script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test the enhanced query generator")
    parser.add_argument("--activity-type", type=str, default="location", 
                        help="Activity type to generate queries for")
    parser.add_argument("--count", type=int, default=5, 
                        help="Number of queries to generate")
    parser.add_argument("--verbose", action="store_true", 
                        help="Enable verbose logging")
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger(__name__)
    
    logger.info(f"Testing enhanced query generator for {args.activity_type}")
    
    # Test the generator
    queries = test_generator(args.activity_type, args.count, args.verbose)
    
    # Print results
    if queries:
        print("\nGenerated Queries:")
        for i, query in enumerate(queries, 1):
            print(f"{i}. {query}")
    else:
        print("\nNo queries were generated.")


if __name__ == "__main__":
    main()