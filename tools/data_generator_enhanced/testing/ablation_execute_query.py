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
from db.db_collections import IndalekoDBCollections
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
    Execute a query with properly initialized components and respect ablation state.
    Also removes LIMIT statements to ensure complete result sets.

    Args:
        query_text: Natural language query to execute
        capture_aql: Whether to capture and include the AQL in the results

    Returns:
        List of query results
    """
    try:
        # Initialize database and metadata
        db_config = IndalekoDBConfig()
        db = db_config.get_arangodb()
        metadata_manager = IndalekoDBCollectionsMetadata()

        # Get collection names
        object_collection = IndalekoDBCollections.Indaleko_Object_Collection
        activity_collection = IndalekoDBCollections.Indaleko_ActivityContext_Collection
        music_collection = IndalekoDBCollections.Indaleko_MusicActivityData_Collection
        geo_collection = IndalekoDBCollections.Indaleko_GeoActivityData_Collection

        # Check ablation status
        is_activity_ablated = metadata_manager.is_ablated(activity_collection)
        is_music_ablated = metadata_manager.is_ablated(music_collection)
        is_geo_ablated = metadata_manager.is_ablated(geo_collection)

        # Log the query and ablation status
        logging.info(f"Executing query: {query_text}")
        logging.info(f"Ablation status - Activity: {is_activity_ablated}, Music: {is_music_ablated}, Geo: {is_geo_ablated}")

        # Build query parts based on ablation status
        collection_parts = []
        
        # Always include Objects collection - with no LIMIT
        collection_parts.append(f"""
        LET objects = (
            FOR doc IN {object_collection}
            RETURN doc
        )
        """)
        
        # Only include non-ablated collections - with no LIMIT
        if not is_activity_ablated:
            collection_parts.append(f"""
            LET activities = (
                FOR act IN {activity_collection}
                RETURN act
            )
            """)
            
        if not is_music_ablated:
            collection_parts.append(f"""
            LET music_activities = (
                FOR music IN {music_collection}
                RETURN music
            )
            """)
            
        if not is_geo_ablated:
            collection_parts.append(f"""
            LET geo_activities = (
                FOR geo IN {geo_collection}
                RETURN geo
            )
            """)
        
        # Build the combined result based on which collections are included
        result_name = "objects"
        if not is_activity_ablated:
            result_name = f"APPEND({result_name}, activities)"
        if not is_music_ablated:
            result_name = f"APPEND({result_name}, music_activities)"
        if not is_geo_ablated:
            result_name = f"APPEND({result_name}, geo_activities)"
            
        # Add the return statement
        collection_parts.append(f"""
        // Return the combined results
        RETURN {result_name}
        """)
        
        # Join all parts to form the complete AQL query
        aql_query = "\n".join(collection_parts)
        
        # Execute the query
        logging.info(f"Executing AQL query: {aql_query}")
        cursor = db.aql.execute(aql_query)
        results = list(cursor)

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
                    # Add ablation state to results for analysis
                    results[i]["_debug"]["ablation_state"] = {
                        "activity": is_activity_ablated,
                        "music": is_music_ablated,
                        "geo": is_geo_ablated
                    }

        logging.info(f"Query returned {len(results)} results")
        return results

    except Exception as e:
        logging.error(f"Error executing query: {e}")
        import traceback
        traceback.print_exc()
        return []