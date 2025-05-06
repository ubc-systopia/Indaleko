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
from db.db_config import IndalekoDBConfig
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from query.query_processing.nl_parser import NLParser
from query.query_processing.enhanced_nl_parser import EnhancedNLParser
from query.query_processing.query_translator.aql_translator import AQLTranslator
from query.query_processing.query_translator.enhanced_aql_translator import EnhancedAQLTranslator
from query.search_execution.query_executor.aql_executor import AQLExecutor
from query.query_processing.data_models.translator_input import TranslatorInput
from query.utils.llm_connector.openai_connector import OpenAIConnector


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

    Args:
        query_text: Natural language query to execute
        capture_aql: Whether to capture and include the AQL in the results

    Returns:
        List of query results
    """
    try:
        # Initialize components
        db_config = IndalekoDBConfig()
        collections_metadata = IndalekoDBCollectionsMetadata(db_config)

        # Create LLM connector
        api_key = get_api_key()
        llm_connector = OpenAIConnector(api_key=api_key, model="gpt-4o-mini")

        # Initialize parsers and translators
        use_enhanced_nl = True
        if use_enhanced_nl:
            nl_parser = EnhancedNLParser(
                llm_connector=llm_connector,
                collections_metadata=collections_metadata
            )
            translator = EnhancedAQLTranslator(collections_metadata)
        else:
            nl_parser = NLParser(
                llm_connector=llm_connector,
                collections_metadata=collections_metadata
            )
            translator = AQLTranslator(collections_metadata)

        # Initialize executor
        executor = AQLExecutor()

        # Log the query
        logging.info(f"Executing query: {query_text}")

        # Parse the query
        if use_enhanced_nl:
            parsed_query = nl_parser.parse_enhanced(query=query_text)
        else:
            parsed_query = nl_parser.parse(query=query_text)

        # Create translator input
        translator_input = TranslatorInput(
            Query=parsed_query,
            Connector=llm_connector
        )

        # Translate to AQL
        if use_enhanced_nl:
            translation_result = translator.translate_enhanced(
                parsed_query,
                translator_input
            )
        else:
            translation_result = translator.translate(translator_input)

        # Remove LIMIT statements that could cause partial results
        aql_query = translation_result.aql_query
        # Use an improved regex pattern that handles multi-line LIMIT statements
        aql_query = re.sub(r'LIMIT\s+\d+', '', aql_query)
        # Log the query transformation for debugging
        logging.info(f"Original query with LIMIT: {translation_result.aql_query}")
        logging.info(f"Transformed query without LIMIT: {aql_query}")
        translation_result.aql_query = aql_query

        # Execute the query
        results = executor.execute(
            translation_result.aql_query,
            db_config,
            bind_vars=translation_result.bind_vars
        )

        # Add AQL to results if requested
        if capture_aql and results:
            for result in results:
                if not isinstance(result, dict):
                    continue

                if "_debug" not in result:
                    result["_debug"] = {}

                result["_debug"]["aql"] = translation_result.aql_query

        return results

    except Exception as e:
        logging.error(f"Error executing query: {e}")
        import traceback
        traceback.print_exc()
        return []
