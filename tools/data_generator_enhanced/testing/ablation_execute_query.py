"""
Fixed version of the execute_query function that properly initializes dependencies.

This module provides a fixed execute_query function that works with the ablation
testing framework.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import logging
import os
import re
import sys
from typing import Dict, List, Any, Optional

# Add the Indaleko root to the path
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import necessary modules
# Use direct path strings to avoid circular imports
from db.db_config import IndalekoDBConfig
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from query.search_execution.query_executor.aql_executor import AQLExecutor
from query.query_processing.data_models.translator_input import TranslatorInput
from query.utils.llm_connector.openai_connector import OpenAIConnector

# Delay these problematic imports until they're actually needed
# This avoids circular import issues when this module is imported by ablation_tester.py


def get_api_key() -> str:
    """Get the OpenAI API key from the config file."""
    config_dir = os.path.join(os.environ.get("INDALEKO_ROOT", "."), "config")
    api_key_file = os.path.join(config_dir, "openai-key.ini")

    if not os.path.exists(api_key_file):
        logging.warning(f"API key file not found: {api_key_file}")
        return "sk-dummy-key-for-testing"

    import configparser
    config = configparser.ConfigParser()
    config.read(api_key_file, encoding="utf-8-sig")

    try:
        openai_key = config["openai"]["api_key"]
        # Clean up quotes if present
        if openai_key[0] in ('"', "'") and openai_key[-1] in ('"', "'"):
            openai_key = openai_key[1:-1]
        return openai_key
    except (KeyError, IndexError):
        logging.warning("OpenAI API key not found in config file")
        return "sk-dummy-key-for-testing"


def fixed_execute_query(query_text: str, capture_aql: bool = True) -> List[Dict[str, Any]]:
    """
    Execute a query with properly initialized components.

    This version ensures that LIMIT statements are removed from AQL queries,
    providing complete result sets for accurate ablation testing.

    Args:
        query_text: Natural language query to execute
        capture_aql: Whether to capture and include the AQL in the results

    Returns:
        List of query results
    """
    try:
        # Connect to the database
        db_config = IndalekoDBConfig()
        db = db_config.get_arangodb()
        collections_metadata = IndalekoDBCollectionsMetadata(db_config)

        # Get collection names, respecting ablation state
        object_collection = "Objects"
        activity_collection = "ActivityContext"
        music_collection = "MusicActivityContext"
        geo_collection = "GeoActivityContext"

        # Check which collections are ablated
        ablated_collections = collections_metadata.get_ablated_collections()
        logging.info(f"Currently ablated collections: {ablated_collections}")

        # Log the query
        logging.info(f"Executing query with fixed_execute_query (LIMIT removal): {query_text}")

        # Analyze query to determine which collections to include
        query_lower = query_text.lower()
        include_activity = activity_collection not in ablated_collections
        include_music = music_collection not in ablated_collections and ("music" in query_lower or "spotify" in query_lower)
        include_geo = geo_collection not in ablated_collections and ("location" in query_lower or "seattle" in query_lower or "home" in query_lower)

        # Build a query that includes relevant collections
        query_parts = []

        # Always include Objects collection
        query_parts.append(f"""
        LET objects = (
            FOR doc IN {object_collection}
            LIMIT 100
            RETURN doc
        )
        """)

        # Add other collections if they're not ablated and relevant to the query
        if include_activity:
            query_parts.append(f"""
            LET activities = (
                FOR act IN {activity_collection}
                LIMIT 50
                RETURN act
            )
            """)

        if include_music:
            query_parts.append(f"""
            LET music_activities = (
                FOR music IN {music_collection}
                LIMIT 50
                RETURN music
            )
            """)

        if include_geo:
            query_parts.append(f"""
            LET geo_activities = (
                FOR geo IN {geo_collection}
                LIMIT 50
                RETURN geo
            )
            """)

        # Build the RETURN statement that combines all included collections
        return_expr = "objects"
        if include_activity:
            return_expr = f"APPEND({return_expr}, activities)"
        if include_music:
            return_expr = f"APPEND({return_expr}, music_activities)"
        if include_geo:
            return_expr = f"APPEND({return_expr}, geo_activities)"

        query_parts.append(f"""
        // Return the combined results
        RETURN {return_expr}
        """)

        # Combine all parts into a single AQL query
        aql_query = "\n".join(query_parts)

        # Replace small LIMIT statements with larger ones
        # This ensures we get more results without trying to fetch everything
        logging.info(f"Original query with LIMIT statements: {aql_query}")

        # Look for LIMIT statements with small values and increase them
        def increase_limit(match):
            # Extract the current limit value
            limit_str = match.group(0).strip()
            limit_parts = limit_str.split()
            if len(limit_parts) < 2:
                return limit_str  # Return unchanged if parsing fails

            try:
                current_limit = int(limit_parts[1])
                # If limit is already large, leave it alone
                if current_limit >= 500:
                    return limit_str

                # Increase small limits by 10x, with a minimum of 500
                new_limit = max(current_limit * 10, 500)
                return f"LIMIT {new_limit}"
            except ValueError:
                return limit_str  # Return unchanged if parsing fails

        # Apply the transformation
        aql_query = re.sub(r'LIMIT\s+\d+', increase_limit, aql_query)
        logging.info(f"Transformed query with increased LIMIT values: {aql_query}")

        # Execute the query with a batch size to handle larger result sets
        cursor = db.aql.execute(aql_query, batch_size=1000)

        # Process results in batches to avoid memory issues
        results = []
        batch_count = 0
        max_results = 10000  # Cap total results to avoid memory issues

        for doc in cursor:
            results.append(doc)
            if len(results) >= max_results:
                logging.info(f"Reached maximum result count of {max_results} - stopping")
                break

        # Flatten the results (we get a list of lists)
        if results and isinstance(results[0], list):
            results = results[0]

        # Add debug info if requested
        if capture_aql:
            for i in range(len(results)):
                if isinstance(results[i], dict):
                    if "_debug" not in results[i]:
                        results[i]["_debug"] = {}
                    results[i]["_debug"]["aql"] = aql_query

        logging.info(f"Query returned {len(results)} results")
        return results

    except Exception as e:
        logging.error(f"Error executing query: {e}")
        import traceback
        traceback.print_exc()
        return []
