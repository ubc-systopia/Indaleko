"""
Query Handler Mixin that provides common functionality for Indaleko query handlers.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import argparse
import datetime
import logging
import os
from typing import Any

from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from db.db_config import IndalekoDBConfig
from query.history.data_models.query_history import QueryHistoryData
from query.query_processing.data_models.query_input import StructuredQuery
from query.query_processing.data_models.translator_response import TranslatorOutput
from query.query_processing.nl_parser import NLParser
from query.query_processing.query_history import QueryHistory
from query.utils.llm_connector.openai_connector import OpenAIConnector

logger = logging.getLogger(__name__)


class QueryHandlerMixin:
    """Handler mixin for CLI query operations."""

    @staticmethod
    def get_pre_parser() -> argparse.Namespace | None:
        """
        Get the pre-parser for query tools.

        This method sets up common arguments for query tools.
        """
        parser = argparse.ArgumentParser(add_help=False)

        # Add debug flag that can be used across all query tools
        parser.add_argument("--debug", action="store_true", help="Enable debug output")

        parser.add_argument(
            "--no-history", action="store_true", help="Disable query history recording",
        )

        return parser

    @staticmethod
    def initialize_components() -> tuple[NLParser, QueryHistory]:
        """
        Initialize the common components needed for query processing.

        Returns:
            Tuple containing:
            - NL parser
            - Query history manager
        """
        # Initialize configuration
        config_path = os.path.join(
            os.environ.get("INDALEKO_ROOT", "."), "config", "indaleko-db-config.ini",
        )
        db_config = IndalekoDBConfig(config_file=config_path)
        logger.info("DB config initialized")

        # Initialize API key
        api_key = QueryHandlerMixin.load_api_key()
        logger.info("API key loaded")

        # Initialize collections metadata
        collections_metadata = IndalekoDBCollectionsMetadata(db_config)
        logger.info("Collections metadata initialized")

        # Initialize LLM connector
        llm_connector = OpenAIConnector(api_key=api_key, model="gpt-4o-mini")
        logger.info("LLM connector initialized")

        # Initialize NL parser
        nl_parser = NLParser(collections_metadata, llm_connector)
        logger.info("NL parser initialized")

        # Initialize query history
        query_history = QueryHistory(db_config)
        logger.info("Query history initialized")

        return nl_parser, query_history

    @staticmethod
    def load_api_key() -> str:
        """Load the OpenAI API key from config file."""
        import configparser

        config_file = os.path.join(
            os.environ.get("INDALEKO_ROOT", "."), "config", "openai-key.ini",
        )

        if not os.path.exists(config_file):
            raise ValueError(f"API key file not found: {config_file}")

        config = configparser.ConfigParser()
        config.read(config_file, encoding="utf-8-sig")

        if "openai" not in config or "api_key" not in config["openai"]:
            raise ValueError("OpenAI API key not found in config file")

        openai_key = config["openai"]["api_key"]

        # Clean up the key if it has quotes
        if openai_key[0] in ["'", '"'] and openai_key[-1] in ["'", '"']:
            openai_key = openai_key[1:-1]

        return openai_key

    @staticmethod
    def record_query_history(
        query: str,
        parsed_results: Any,
        translated_output: Any,
        raw_results: list[dict[str, Any]],
        analyzed_results: list[dict[str, Any]],
        query_history: QueryHistory,
        llm_connector: Any,
        start_time: datetime.datetime = None,
        end_time: datetime.datetime = None,
    ) -> None:
        """
        Record a query in the query history database.

        Args:
            query: The original query text
            parsed_results: Results from the NL parser
            translated_output: Results from the translator
            raw_results: Raw database results
            analyzed_results: Processed results
            query_history: QueryHistory instance
            llm_connector: LLM connector for metadata
            start_time: Start timestamp (defaults to now)
            end_time: End timestamp (defaults to now)
        """
        if start_time is None:
            start_time = datetime.datetime.now(datetime.UTC)

        if end_time is None:
            end_time = datetime.datetime.now(datetime.UTC)

        elapsed_time = (end_time - start_time).total_seconds()

        # Create structured query if needed
        if not isinstance(translated_output, TranslatorOutput):
            translated_output = TranslatorOutput(
                aql_query="", bind_vars={}, confidence=1.0, explanation="Test query",
            )

        # Prepare query history data
        query_history_data = QueryHistoryData(
            OriginalQuery=query,
            ParsedResults=parsed_results,
            LLMName=(
                llm_connector.get_llm_name()
                if hasattr(llm_connector, "get_llm_name")
                else "Unknown"
            ),
            LLMQuery=StructuredQuery(query=query, search_type="query"),
            TranslatedOutput=translated_output,
            ExecutionPlan=None,  # Optional
            RawResults=raw_results or [],
            AnalyzedResults=analyzed_results or [],
            Facets={},  # Can be enhanced with actual facets
            RankedResults=[],  # Can be enhanced with actual ranked results
            StartTimestamp=start_time,
            EndTimestamp=end_time,
            ElapsedTime=elapsed_time,
        )

        # Add to query history
        try:
            query_history.add(query_history_data)
            logger.info(f"Query '{query}' recorded in query history")
            return True
        except Exception as e:
            logger.error(f"Failed to record query in history: {e}")
            return False
